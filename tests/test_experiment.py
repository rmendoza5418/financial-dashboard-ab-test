import numpy as np

from data.generate_data import generate_advisors, generate_daily_events
from src.experiment import dar_test


def _small_sample(n=80):
    rng = np.random.default_rng(11)
    advisors = generate_advisors(rng)
    # keep the test fast: 40 advisors per arm
    sample = advisors.groupby("arm").head(n // 2).reset_index(drop=True)
    return advisors, generate_daily_events(sample, rng)


def test_advisors_are_balanced_across_arms():
    advisors, _ = _small_sample()
    counts = advisors["arm"].value_counts()
    assert counts["control"] == counts["treatment"]


def test_daily_events_are_valid():
    _, events = _small_sample()
    assert set(events["active"]) <= {0, 1}
    assert (events["session_duration_secs"] >= 0).all()
    # inactive days must not carry session activity
    inactive = events[events["active"] == 0]
    assert (inactive["client_drilldowns"] == 0).all()


def test_dar_test_returns_consistent_result():
    _, events = _small_sample()
    result = dar_test(events)
    assert 0 <= result.control_value <= 1
    assert 0 <= result.treatment_value <= 1
    assert result.ci_lower <= result.lift <= result.ci_upper
    assert 0 <= result.p_value <= 1
