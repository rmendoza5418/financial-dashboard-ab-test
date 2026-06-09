"""
Synthetic dataset generator for the Financial Dashboard A/B Experiment.

Generates realistic advisor engagement data with:
- Week-of-month usage patterns (month-end spikes in wealth management)
- AUM tier stratification (advisors with larger books behave differently)
- Advisor tenure effects (newer advisors adopt new tooling faster)
"""

import numpy as np
import pandas as pd
from pathlib import Path

SEED = 99
N_PER_ARM = 1_200
EXPERIMENT_DAYS = 28
AUM_TIERS = ["under_50M", "50M_to_150M", "over_150M"]
AUM_TIER_WEIGHTS = [0.45, 0.35, 0.20]
REGIONS = ["Northeast", "Southeast", "Midwest", "West", "Central"]
TENURE_BUCKETS = ["0-2yr", "3-5yr", "6-10yr", "10+yr"]

# Arm-level parameters
CONTROL_BASE_DAR = 0.52      # daily active rate
TREATMENT_BASE_DAR = 0.61    # +9pp lift
CONTROL_SESSION_SECS = 185   # avg session duration
TREATMENT_SESSION_SECS = 218 # +18% lift
CONTROL_DRILLDOWN_RATE = 0.28
TREATMENT_DRILLDOWN_RATE = 0.34
CONTROL_EXPORT_RATE = 0.11
TREATMENT_EXPORT_RATE = 0.13


def week_of_month_multiplier(day: int) -> float:
    """
    Simulate month-end usage spikes common in wealth management.
    Days 24-28 (month-end) see ~30% more activity.
    """
    if day >= 24:
        return 1.30
    elif day >= 17:
        return 1.05
    elif day >= 10:
        return 0.95
    else:
        return 0.90


def generate_advisors(rng: np.random.Generator) -> pd.DataFrame:
    """One row per advisor with covariates and arm assignment."""
    records = []
    for arm, base_dar, base_session, base_drill, base_export in [
        ("control",   CONTROL_BASE_DAR,   CONTROL_SESSION_SECS,   CONTROL_DRILLDOWN_RATE,   CONTROL_EXPORT_RATE),
        ("treatment", TREATMENT_BASE_DAR, TREATMENT_SESSION_SECS, TREATMENT_DRILLDOWN_RATE, TREATMENT_EXPORT_RATE),
    ]:
        for i in range(N_PER_ARM):
            aum_tier = rng.choice(AUM_TIERS, p=AUM_TIER_WEIGHTS)
            tenure = rng.choice(TENURE_BUCKETS, p=[0.20, 0.30, 0.30, 0.20])
            region = rng.choice(REGIONS)

            # AUM and tenure modifiers (high-AUM advisors are stickier; newer ones adopt faster)
            aum_mult = {"under_50M": 0.93, "50M_to_150M": 1.0, "over_150M": 1.08}[aum_tier]
            tenure_mult = {"0-2yr": 1.10, "3-5yr": 1.02, "6-10yr": 0.98, "10+yr": 0.92}[tenure]

            advisor_dar = np.clip(base_dar * aum_mult * tenure_mult + rng.normal(0, 0.04), 0.05, 0.99)
            advisor_session = max(30, base_session * aum_mult + rng.normal(0, 20))

            records.append({
                "advisor_id": f"{arm[0].upper()}{i+1:05d}",
                "arm": arm,
                "aum_tier": aum_tier,
                "tenure_bucket": tenure,
                "region": region,
                "base_dar": round(advisor_dar, 4),
                "base_session_secs": round(advisor_session, 1),
                "drilldown_rate": round(np.clip(base_drill * aum_mult + rng.normal(0, 0.03), 0, 1), 4),
                "export_rate": round(np.clip(base_export + rng.normal(0, 0.015), 0, 1), 4),
            })

    return pd.DataFrame(records).sample(frac=1, random_state=SEED).reset_index(drop=True)


def generate_daily_events(advisors_df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """One row per advisor per day, tracking session-level metrics."""
    records = []
    for _, adv in advisors_df.iterrows():
        for day in range(1, EXPERIMENT_DAYS + 1):
            wom_mult = week_of_month_multiplier(day)
            daily_p = np.clip(adv["base_dar"] * wom_mult + rng.normal(0, 0.02), 0, 1)
            active = rng.binomial(1, daily_p)

            session_secs = 0
            drilldowns = 0
            exports = 0
            error_occurred = 0

            if active:
                session_secs = max(10, adv["base_session_secs"] + rng.normal(0, 25))
                drilldowns = rng.binomial(5, adv["drilldown_rate"])
                exports = rng.binomial(1, adv["export_rate"])
                error_occurred = rng.binomial(1, 0.008 if adv["arm"] == "control" else 0.009)

            records.append({
                "advisor_id": adv["advisor_id"],
                "arm": adv["arm"],
                "day": day,
                "active": int(active),
                "session_duration_secs": round(session_secs, 1),
                "client_drilldowns": int(drilldowns),
                "report_exports": int(exports),
                "error_occurred": int(error_occurred),
            })

    return pd.DataFrame(records)


def main():
    rng = np.random.default_rng(SEED)
    out_dir = Path(__file__).parent

    advisors_df = generate_advisors(rng)
    daily_df = generate_daily_events(advisors_df, rng)

    advisors_df.to_csv(out_dir / "advisors.csv", index=False)
    daily_df.to_csv(out_dir / "daily_events.csv", index=False)

    print(f"Generated {len(advisors_df)} advisors → advisors.csv")
    print(f"Generated {len(daily_df)} daily event rows → daily_events.csv")

    # Quick sanity check
    summary = daily_df.groupby("arm").agg(
        dar=("active", "mean"),
        avg_session=("session_duration_secs", lambda x: x[x > 0].mean()),
        avg_drilldowns=("client_drilldowns", "mean"),
    ).round(3)
    print("\nSanity check — arm summary:")
    print(summary)


if __name__ == "__main__":
    main()
