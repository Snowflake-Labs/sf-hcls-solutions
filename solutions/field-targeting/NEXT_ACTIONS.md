---
description: >
  Show next actions after installing the HCLS Field Targeting Platform.
  Triggers: what next, next steps, rules engine, call planning, semantic view.
---

# Next Actions: HCLS Field Targeting Platform

## What Was Installed

The installation populated **source and reference tables** with synthetic demo data:
- 1,000 HCPs (Rheumatology/Dermatology/IM/FP)
- ~2,640 weekly Rx records
- ~1,980 call activity records
- Call notes enriched with sentiment and disposition scores
- Promotional materials catalog + usage analytics

The **Streamlit dashboard** (What-If Scenario tab) shows data from `RE_STEP4_REFINED_TIERED*`
and `SNAPSHOT_*` tables, which are **populated by the 9-step rules engine skills**.

## Step 1: Run the Rules Engine

The rules engine skills are in the source repo under `.cortex/skills/`:

```
$rule-engine-suppressions         # Step 1: eligible universe
$rule-engine-universe-tiering     # Steps 2-4: Rx join, tiering, refinement
$rule-engine-call-planning        # Steps 5-9: call planning, workload balance
```

After running these, the Streamlit dashboard will show tier distributions and scenario analysis.

## Step 2: Explore the Semantic View

The `HCP_UNIVERSE_SV` semantic view is in `solutions/field-targeting/semantic_view/`.
Deploy it via Snowsight or Cortex Analyst to enable natural language queries:

- "How many T1 HCPs are in the Northeast?"
- "Which territories have the most conversion-ready HCPs?"
- "Show material usage by type"

## Step 3: Run Snapshot Comparisons

After a what-if scenario (e.g., T1 = top 15%):

```
$rule-engine-universe-tiering whatif   # Generate WHATIF tables
$snapshot-comparator                   # Compare baseline vs scenario
```

## Step 4: Query the Data Directly

```sql
-- HCP tier distribution
SELECT SPEC_CD, COUNT(*) AS HCPs
FROM SF_SOLUTIONS.FIELD_TARGETING.HCP_MASTER_PROFILE
GROUP BY SPEC_CD ORDER BY HCPs DESC;

-- Call note sentiment by disposition
SELECT DISPOSITION, COUNT(*) AS NOTES,
    ROUND(AVG(SENTIMENT_SCORE), 3) AS AVG_SENTIMENT
FROM SF_SOLUTIONS.FIELD_TARGETING.CALL_NOTES_ENRICHED
GROUP BY DISPOSITION ORDER BY NOTES DESC;

-- Top materials by usage
SELECT * FROM SF_SOLUTIONS.FIELD_TARGETING.MATERIAL_EFFECTIVENESS
ORDER BY TOTAL_USES DESC LIMIT 10;

-- Rx by territory
SELECT TERR_ID, ROUND(SUM(RX), 1) AS TOTAL_TRX
FROM SF_SOLUTIONS.FIELD_TARGETING.RX_WEEKLY_HCP
GROUP BY TERR_ID ORDER BY TOTAL_TRX DESC LIMIT 10;
```
