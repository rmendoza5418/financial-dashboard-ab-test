# Companion Tableau Dashboard — Design Notes

## Overview

The Python analysis in this repo generates the statistical findings. This document describes the
Tableau dashboard that surfaces those findings to BI leadership and business stakeholders who
don't live in notebooks.

The principle: **the experiment dashboard should answer three questions at a glance**:
1. Did the new design win?
2. By how much, and are we confident?
3. Are there any populations we should treat differently?

---

## Dashboard Structure

### Sheet 1 — Experiment Scorecard (top of dashboard)
A summary KPI row with 4 tiles:

| Tile | Metric | Visualization |
|------|--------|---------------|
| Primary Lift | +9.2pp DAR lift | Big number + green arrow |
| p-value | < 0.001 | Formatted text (green if < 0.05) |
| 95% CI | [7.1pp, 11.3pp] | Inline range bar |
| Guardrail | PASSED | Green badge |

**Key calculated fields:**
```
// Format lift as signed percentage
IF [Lift] > 0 THEN "+" + STR(ROUND([Lift]*100, 1)) + "pp"
ELSE STR(ROUND([Lift]*100, 1)) + "pp" END

// Traffic-light color for p-value
IF [P_Value] < 0.001 THEN "Significant"
ELSEIF [P_Value] < 0.05 THEN "Marginal"
ELSE "Not Significant" END
```

---

### Sheet 2 — Daily Active Rate Trend
**Chart type:** Dual-line with shaded confidence band

- X-axis: Experiment day (1–28)
- Y-axis: Daily Active Rate (%)
- Reference band: Month-end window (days 22–28), shaded orange
- Annotation: "Month-end spike — parallel in both arms"

**Parameters needed:**
- `p_Arm_Toggle`: All | Control | Treatment (for filtering)

---

### Sheet 3 — Metric Deep Dive
**Chart type:** Grouped bar chart

Metrics on rows: DAR, Session Duration, Drilldown Rate, Error Rate
Columns: Control vs. Treatment
Color: Treatment bar green if significant, gray if not
Error bars: 95% CI

---

### Sheet 4 — Subgroup Forest Plot
**Chart type:** Gantt / custom reference lines

One row per AUM tier segment. Shows:
- Lift point estimate (dot)
- 95% CI (line)
- Overall average lift (dashed reference line)

Key Tableau technique: Use a dual-axis chart with a circle mark on one axis
(point estimate) and a Gantt bar on the other (CI range). Synchronize axes.

---

### Sheet 5 — Raw Data Table
Advisor-level summary for business users who want to audit. Filterable by arm, region, AUM tier, tenure.

---

## Dashboard Layout

```
┌──────────────────────────────────────────────────────┐
│  EXPERIMENT SCORECARD (4 KPI tiles)                  │
├────────────────────┬─────────────────────────────────┤
│  Daily Rate Trend  │  Metric Deep Dive (bar chart)   │
│  (line chart)      │                                 │
├────────────────────┴─────────────────────────────────┤
│  Subgroup Forest Plot (AUM tier)                     │
├──────────────────────────────────────────────────────┤
│  Raw Data Table (collapsible)                        │
└──────────────────────────────────────────────────────┘
```

---

## Color Palette

| Use | Hex |
|-----|-----|
| Control arm | #4C72B0 |
| Treatment arm | #55A868 |
| Significant | #2CA02C |
| Not significant | #AAAAAA |
| Warning / guardrail fail | #D62728 |
| Month-end band | #FF7F0E (10% opacity) |

---

## Performance Notes

- Data source: CSV export from Python analysis (`outputs/` folder)
- Extract recommended (not live connection) — dataset is static post-experiment
- Expected load time < 2 seconds
- No LOD calculations needed — aggregations handled in Python
