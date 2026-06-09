# Financial Dashboard A/B Test — Feature Rollout Experiment

A controlled experiment measuring the impact of a redesigned account summary dashboard on client engagement in a financial services context.

## Business Problem

A wealth management firm redesigned its primary account summary dashboard (the first screen advisors see after login) to surface actionable alerts, YoY performance comparisons, and client-at-risk indicators. Before rolling out to all 2,400 advisors, the BI team ran a controlled experiment to validate that the new design actually improved engagement and didn't introduce unintended friction.

## Experiment Design

| Parameter | Value |
|---|---|
| Unit of randomization | Individual advisor |
| Control | Existing account summary dashboard |
| Treatment | Redesigned dashboard with alert surfacing + YoY comparisons |
| Primary metric | Daily Active Rate (% of assigned advisors who opened the dashboard on a given day) |
| Secondary metrics | Avg. session duration, client profile drill-down rate, report export rate |
| Guardrail metrics | Error rate, page load time P95, help desk tickets |
| Sample size | 1,200 per arm |
| Duration | 28 days |
| Statistical design | Two-sample proportions z-test, α = 0.05, target power = 0.80 |

## Why This Matters for BI Teams

Dashboard redesigns in financial services are high-stakes: advisors have tight workflows and low tolerance for friction. A BI team that ships a new dashboard without measuring adoption impact is flying blind. This experiment shows how to:

- Design a valid randomized experiment within an existing BI platform
- Choose the right unit of randomization (advisor, not session)
- Separate signal from noise when usage patterns are seasonal (week-of-month effects in wealth management)
- Present results in a format that drives a clear go/no-go decision

## Results Summary

The redesigned dashboard drove a statistically significant **+9.2pp** lift in daily active rate (p < 0.001, 95% CI: [7.1pp, 11.3pp]) and a **+22%** lift in client profile drill-down rate, with no significant difference in error rate or help desk tickets. Full rollout recommended.

## Repository Structure

```
financial-dashboard-ab-test/
├── src/
│   ├── experiment.py          # Statistical test functions
│   ├── segmentation.py        # Subgroup analysis (by region, tenure, AUM tier)
│   └── visualizations.py      # Chart generation
├── data/
│   └── generate_data.py       # Synthetic advisor engagement dataset
├── notebooks/
│   └── dashboard_ab_analysis.py   # Full analysis walkthrough
├── tableau/
│   └── DASHBOARD_NOTES.md     # Companion Tableau dashboard design notes
├── outputs/                   # Generated charts
└── requirements.txt
```

## Running the Analysis

```bash
pip install -r requirements.txt
python data/generate_data.py
python notebooks/dashboard_ab_analysis.py
```

## Key Concepts Demonstrated

- Week-of-month detrending for financial services data (usage spikes at month-end)
- Subgroup analysis with multiple comparison correction (Benjamini-Hochberg)
- Practical significance vs. statistical significance — what lift actually justifies a rollout
- Communicating uncertainty to non-technical stakeholders (CI interpretation)
- Guardrail metric monitoring — how to know when to stop an experiment early
