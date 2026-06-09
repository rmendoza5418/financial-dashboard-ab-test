"""
Statistical analysis functions for the Financial Dashboard A/B Experiment.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from dataclasses import dataclass


@dataclass
class MetricResult:
    metric: str
    control_value: float
    treatment_value: float
    lift: float
    lift_pct: float
    p_value: float
    ci_lower: float
    ci_upper: float
    significant: bool
    test_type: str

    def __str__(self) -> str:
        sig = "✓ SIGNIFICANT" if self.significant else "✗ not significant"
        return (
            f"{self.metric} [{self.test_type}]\n"
            f"  Control: {self.control_value:.4f}  |  Treatment: {self.treatment_value:.4f}\n"
            f"  Lift: {self.lift:+.4f} ({self.lift_pct:+.1f}%)  95% CI [{self.ci_lower:.4f}, {self.ci_upper:.4f}]\n"
            f"  p = {self.p_value:.4f}  {sig}"
        )


def dar_test(daily_df: pd.DataFrame, alpha: float = 0.05) -> MetricResult:
    """
    Test daily active rate (DAR) using a clustered proportions approach.

    Unit of analysis: advisor-day. Because observations are clustered within advisor,
    we use advisor-level mean DAR as the unit for the t-test rather than pooling
    all advisor-days (which would underestimate variance).
    """
    advisor_dar = daily_df.groupby(["advisor_id", "arm"])["active"].mean().reset_index()
    ctrl = advisor_dar[advisor_dar["arm"] == "control"]["active"]
    trt = advisor_dar[advisor_dar["arm"] == "treatment"]["active"]

    t_stat, p_value = stats.ttest_ind(trt, ctrl, equal_var=False)
    lift = trt.mean() - ctrl.mean()

    # Bootstrap CI
    rng = np.random.default_rng(42)
    boot_lifts = [
        rng.choice(trt.values, size=len(trt), replace=True).mean() -
        rng.choice(ctrl.values, size=len(ctrl), replace=True).mean()
        for _ in range(10_000)
    ]
    ci_lower, ci_upper = np.percentile(boot_lifts, [2.5, 97.5])

    return MetricResult(
        metric="Daily Active Rate",
        control_value=ctrl.mean(),
        treatment_value=trt.mean(),
        lift=lift,
        lift_pct=(lift / ctrl.mean()) * 100,
        p_value=p_value,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        significant=p_value < alpha,
        test_type="Welch t-test on advisor means",
    )


def session_duration_test(daily_df: pd.DataFrame, alpha: float = 0.05) -> MetricResult:
    """Test average session duration among active days only (Mann-Whitney U)."""
    active = daily_df[daily_df["active"] == 1]
    ctrl = active[active["arm"] == "control"]["session_duration_secs"]
    trt = active[active["arm"] == "treatment"]["session_duration_secs"]

    u_stat, p_value = stats.mannwhitneyu(trt, ctrl, alternative="two-sided")
    lift = trt.median() - ctrl.median()

    rng = np.random.default_rng(42)
    boot_lifts = [
        np.median(rng.choice(trt.values, size=len(trt), replace=True)) -
        np.median(rng.choice(ctrl.values, size=len(ctrl), replace=True))
        for _ in range(10_000)
    ]
    ci_lower, ci_upper = np.percentile(boot_lifts, [2.5, 97.5])

    return MetricResult(
        metric="Session Duration (median, active days)",
        control_value=ctrl.median(),
        treatment_value=trt.median(),
        lift=lift,
        lift_pct=(lift / ctrl.median()) * 100,
        p_value=p_value,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        significant=p_value < alpha,
        test_type="Mann-Whitney U on active sessions",
    )


def drilldown_rate_test(daily_df: pd.DataFrame, alpha: float = 0.05) -> MetricResult:
    """Test client profile drill-down rate (proportion of active sessions with ≥1 drilldown)."""
    active = daily_df[daily_df["active"] == 1].copy()
    active["drilled"] = (active["client_drilldowns"] > 0).astype(int)
    advisor_drill = active.groupby(["advisor_id", "arm"])["drilled"].mean().reset_index()

    ctrl = advisor_drill[advisor_drill["arm"] == "control"]["drilled"]
    trt = advisor_drill[advisor_drill["arm"] == "treatment"]["drilled"]

    t_stat, p_value = stats.ttest_ind(trt, ctrl, equal_var=False)
    lift = trt.mean() - ctrl.mean()

    rng = np.random.default_rng(42)
    boot_lifts = [
        rng.choice(trt.values, size=len(trt), replace=True).mean() -
        rng.choice(ctrl.values, size=len(ctrl), replace=True).mean()
        for _ in range(10_000)
    ]
    ci_lower, ci_upper = np.percentile(boot_lifts, [2.5, 97.5])

    return MetricResult(
        metric="Client Profile Drill-down Rate",
        control_value=ctrl.mean(),
        treatment_value=trt.mean(),
        lift=lift,
        lift_pct=(lift / ctrl.mean()) * 100,
        p_value=p_value,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        significant=p_value < alpha,
        test_type="Welch t-test on advisor means",
    )


def error_rate_guardrail(daily_df: pd.DataFrame, alpha: float = 0.05) -> MetricResult:
    """
    Guardrail test: error rate should NOT be significantly higher in treatment.
    Uses a one-sided test (treatment worse = bad).
    """
    advisor_err = daily_df.groupby(["advisor_id", "arm"]).agg(
        errors=("error_occurred", "sum"),
        days=("day", "count")
    ).reset_index()
    advisor_err["error_rate"] = advisor_err["errors"] / advisor_err["days"]

    ctrl = advisor_err[advisor_err["arm"] == "control"]["error_rate"]
    trt = advisor_err[advisor_err["arm"] == "treatment"]["error_rate"]

    # One-sided: H1 = treatment error rate > control
    t_stat, p_two = stats.ttest_ind(trt, ctrl, equal_var=False)
    p_one_sided = p_two / 2 if t_stat > 0 else 1 - p_two / 2

    lift = trt.mean() - ctrl.mean()
    return MetricResult(
        metric="Error Rate (guardrail — lower is better)",
        control_value=ctrl.mean(),
        treatment_value=trt.mean(),
        lift=lift,
        lift_pct=(lift / ctrl.mean()) * 100 if ctrl.mean() > 0 else 0,
        p_value=p_one_sided,
        ci_lower=lift - 1.96 * np.sqrt(trt.var() / len(trt) + ctrl.var() / len(ctrl)),
        ci_upper=lift + 1.96 * np.sqrt(trt.var() / len(trt) + ctrl.var() / len(ctrl)),
        significant=p_one_sided < alpha,
        test_type="One-sided Welch t-test (guardrail)",
    )


def benjamini_hochberg_correction(results: list[MetricResult], alpha: float = 0.05) -> list[MetricResult]:
    """
    Apply Benjamini-Hochberg FDR correction to secondary metrics.
    Modifies 'significant' in-place for the passed results.
    """
    p_values = [r.p_value for r in results]
    n = len(p_values)
    sorted_idx = np.argsort(p_values)
    bh_thresholds = [(i + 1) * alpha / n for i in range(n)]

    corrected = [False] * n
    for rank, idx in enumerate(sorted_idx):
        if p_values[idx] <= bh_thresholds[rank]:
            corrected[idx] = True

    for i, r in enumerate(results):
        r.significant = corrected[i]
    return results
