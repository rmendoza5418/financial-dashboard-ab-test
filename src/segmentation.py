"""
Subgroup analysis for the Financial Dashboard A/B Experiment.

Analyzes treatment effect heterogeneity across AUM tier, advisor tenure,
and region. Results are exploratory — not decision-making criteria.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from typing import Optional


def subgroup_dar_analysis(
    advisors_df: pd.DataFrame,
    daily_df: pd.DataFrame,
    subgroup_col: str,
) -> pd.DataFrame:
    """
    Compute per-subgroup DAR lift with confidence intervals.

    Args:
        advisors_df: Advisor metadata with arm assignment
        daily_df: Daily event log
        subgroup_col: Column in advisors_df to segment on (e.g., 'aum_tier')

    Returns:
        DataFrame with one row per subgroup showing lift and p-value.
    """
    advisor_dar = (
        daily_df.groupby("advisor_id")["active"]
        .mean()
        .reset_index()
        .rename(columns={"active": "dar"})
    )
    merged = advisor_dar.merge(advisors_df[["advisor_id", "arm", subgroup_col]], on="advisor_id")

    results = []
    for group_val in merged[subgroup_col].unique():
        subset = merged[merged[subgroup_col] == group_val]
        ctrl = subset[subset["arm"] == "control"]["dar"]
        trt = subset[subset["arm"] == "treatment"]["dar"]

        if len(ctrl) < 10 or len(trt) < 10:
            continue

        lift = trt.mean() - ctrl.mean()
        _, p_val = stats.ttest_ind(trt, ctrl, equal_var=False)
        se = np.sqrt(trt.var() / len(trt) + ctrl.var() / len(ctrl))

        results.append({
            "subgroup": str(group_val),
            "n_control": len(ctrl),
            "n_treatment": len(trt),
            "control_dar": round(ctrl.mean(), 4),
            "treatment_dar": round(trt.mean(), 4),
            "lift": round(lift, 4),
            "ci_lower": round(lift - 1.96 * se, 4),
            "ci_upper": round(lift + 1.96 * se, 4),
            "p_value": round(p_val, 4),
        })

    df = pd.DataFrame(results).sort_values("lift", ascending=False).reset_index(drop=True)
    df["significant_uncorrected"] = df["p_value"] < 0.05
    return df


def check_interaction_effect(
    advisors_df: pd.DataFrame,
    daily_df: pd.DataFrame,
    subgroup_col: str,
) -> dict:
    """
    Test whether treatment effect varies significantly by subgroup (interaction test).
    A significant interaction would suggest heterogeneous treatment effects worth
    reporting to the business — e.g., "the new dashboard helps junior advisors
    more than senior ones."

    Returns dict with F-statistic and p-value for the arm × subgroup interaction.
    """
    advisor_dar = (
        daily_df.groupby("advisor_id")["active"]
        .mean()
        .reset_index()
        .rename(columns={"active": "dar"})
    )
    merged = advisor_dar.merge(advisors_df[["advisor_id", "arm", subgroup_col]], on="advisor_id")
    merged["arm_bin"] = (merged["arm"] == "treatment").astype(int)

    # Fit group means and compute within-group vs. cross-group variance
    group_means = merged.groupby([subgroup_col, "arm"])["dar"].mean().reset_index()
    ctrl_means = group_means[group_means["arm"] == "control"].set_index(subgroup_col)["dar"]
    trt_means = group_means[group_means["arm"] == "treatment"].set_index(subgroup_col)["dar"]
    lifts = (trt_means - ctrl_means).dropna()

    # Simple F-test on lift variance across subgroups
    overall_lift = lifts.mean()
    ss_between = sum((l - overall_lift) ** 2 for l in lifts) * (len(merged) // len(lifts))
    ss_within = merged.groupby([subgroup_col, "arm"])["dar"].var().sum()
    df_between = len(lifts) - 1
    df_within = len(merged) - 2 * len(lifts)
    f_stat = (ss_between / df_between) / (ss_within / df_within) if df_within > 0 else 0
    p_val = 1 - stats.f.cdf(f_stat, df_between, df_within) if f_stat > 0 else 1.0

    return {
        "subgroup_col": subgroup_col,
        "n_subgroups": len(lifts),
        "lift_variance": round(lifts.var(), 6),
        "f_statistic": round(f_stat, 4),
        "p_value": round(p_val, 4),
        "interaction_significant": p_val < 0.05,
        "subgroup_lifts": lifts.to_dict(),
    }
