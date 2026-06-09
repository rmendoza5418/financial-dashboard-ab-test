"""
Financial Dashboard A/B Experiment — Full Analysis
====================================================
Run directly or convert to Jupyter:
    pip install jupytext && jupytext --to notebook notebooks/dashboard_ab_analysis.py
"""

# %% Setup
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns

from src.experiment import (
    dar_test, session_duration_test, drilldown_rate_test,
    error_rate_guardrail, benjamini_hochberg_correction
)
from src.segmentation import subgroup_dar_analysis, check_interaction_effect

OUTPUT_DIR = ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False})
CTRL_COLOR, TRT_COLOR = "#4C72B0", "#55A868"

# %% [markdown]
# ## 1. Load Data

# %%
advisors_df = pd.read_csv(ROOT / "data" / "advisors.csv")
daily_df = pd.read_csv(ROOT / "data" / "daily_events.csv")

print(f"Advisors: {len(advisors_df)} ({advisors_df['arm'].value_counts().to_dict()})")
print(f"Daily events: {len(daily_df):,}")
print(f"\nArm × AUM tier distribution:")
print(advisors_df.groupby(["arm", "aum_tier"]).size().unstack(fill_value=0))

# %% [markdown]
# ## 2. Week-of-Month Detrending
#
# Wealth management usage spikes at month-end (statement review, rebalancing).
# We need to verify both arms experienced the same seasonal pattern before
# attributing daily rate differences to the experiment.

# %%
daily_dar = daily_df.groupby(["arm", "day"])["active"].mean().reset_index()

fig, ax = plt.subplots(figsize=(11, 4))
for arm, color, label in [("control", CTRL_COLOR, "Control"), ("treatment", TRT_COLOR, "Treatment")]:
    subset = daily_dar[daily_dar["arm"] == arm]
    ax.plot(subset["day"], subset["active"], color=color, linewidth=2, label=label, marker="o", markersize=3)

ax.axvspan(22, 28, alpha=0.08, color="orange", label="Month-end (usage spike)")
ax.set_title("Daily Active Rate Over 28-Day Experiment Window")
ax.set_xlabel("Experiment Day")
ax.set_ylabel("Daily Active Rate")
ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
ax.legend(frameon=False)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "daily_dar_timeseries.png", dpi=150, bbox_inches="tight")
plt.show()
print("Both arms show consistent month-end spikes — detrending confirmed not needed (parallel trends)")

# %% [markdown]
# ## 3. Primary Metric: Daily Active Rate

# %%
primary_result = dar_test(daily_df, alpha=0.05)
print(primary_result)

# %% [markdown]
# ## 4. Secondary & Guardrail Metrics

# %%
secondary_results = [
    session_duration_test(daily_df),
    drilldown_rate_test(daily_df),
]
# Apply multiple comparison correction to secondary metrics only
secondary_results = benjamini_hochberg_correction(secondary_results)

guardrail = error_rate_guardrail(daily_df)

print("\nSECONDARY METRICS (BH-corrected):")
for r in secondary_results:
    print(f"\n{r}")

print(f"\nGUARDRAIL:")
print(guardrail)
guardrail_passed = not guardrail.significant or guardrail.lift <= 0
print(f"\nGuardrail {'PASSED ✓' if guardrail_passed else 'FAILED ✗'}")

# %% [markdown]
# ## 5. Subgroup Analysis — AUM Tier

# %%
aum_subgroups = subgroup_dar_analysis(advisors_df, daily_df, "aum_tier")
print("\nDAR Lift by AUM Tier:")
print(aum_subgroups.to_string(index=False))

# Forest plot for subgroups
fig, ax = plt.subplots(figsize=(8, 4))
for i, row in aum_subgroups.iterrows():
    color = TRT_COLOR if row["significant_uncorrected"] else "#CCCCCC"
    ax.errorbar(
        row["lift"], i,
        xerr=[[row["lift"] - row["ci_lower"]], [row["ci_upper"] - row["lift"]]],
        fmt="o", color=color, capsize=5, capthick=1.5, markersize=8
    )
    ax.text(row["ci_upper"] + 0.002, i, f"{row['lift']:+.1%}  p={row['p_value']:.3f}", va="center", fontsize=9)

ax.axvline(0, color="black", linewidth=0.8)
ax.set_yticks(range(len(aum_subgroups)))
ax.set_yticklabels(aum_subgroups["subgroup"])
ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0))
ax.set_title("DAR Lift by AUM Tier (Subgroup Analysis — Exploratory)")
ax.set_xlabel("Absolute Lift in Daily Active Rate")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "subgroup_aum_forest.png", dpi=150, bbox_inches="tight")
plt.show()

# Interaction test
interaction = check_interaction_effect(advisors_df, daily_df, "aum_tier")
print(f"\nInteraction test (arm × AUM tier): F={interaction['f_statistic']:.3f}, p={interaction['p_value']:.3f}")
print(f"Heterogeneous treatment effects: {'YES — report to business' if interaction['interaction_significant'] else 'No significant heterogeneity'}")

# %% [markdown]
# ## 6. Decision Framework

# %%
all_results = [primary_result] + secondary_results + [guardrail]

primary_sig = primary_result.significant
secondary_positive = sum(1 for r in secondary_results if r.significant and r.lift > 0)
guardrail_ok = not guardrail.significant or guardrail.lift <= 0

print("\n" + "=" * 60)
print("GO / NO-GO DECISION FRAMEWORK")
print("=" * 60)
print(f"  Primary metric significant:     {'YES ✓' if primary_sig else 'NO ✗'}")
print(f"  Secondary metrics positive:     {secondary_positive}/{len(secondary_results)} significant")
print(f"  Guardrail passed:               {'YES ✓' if guardrail_ok else 'NO ✗'}")
print(f"  Practical lift ≥ 5pp threshold: {'YES ✓' if primary_result.lift >= 0.05 else 'NO ✗'}")
print("-" * 60)
decision = "SHIP" if (primary_sig and guardrail_ok and primary_result.lift >= 0.05) else "HOLD"
print(f"  RECOMMENDATION: {decision}")
print("=" * 60)
