---
name: field-targeting
description: >
  Install or teardown the HCLS Field Targeting Platform solution.
  Usage: $sf-hcls-solutions:field-targeting | $sf-hcls-solutions:field-targeting teardown
  Triggers: field targeting, HCP, pharmaceutical, call planning, territory, Zenixar, rules engine.
tools:
  - snowflake_sql_execute
  - snowflake_object_search
  - Bash
  - Read
  - Glob
  - Grep
---

# HCLS Field Targeting Platform

Parse the action from `$ARGUMENTS`:
- If `$ARGUMENTS` is "install" or empty → run **Install** flow
- If `$ARGUMENTS` is "teardown" → run **Teardown** flow
- Otherwise → show usage help

## Overview

- **Industry:** Healthcare & Life Sciences
- **Database:** SF_SOLUTIONS
- **Schema:** FIELD_TARGETING
- **Features:** Cortex AI (SENTIMENT, CLASSIFY_TEXT), Semantic View (Cortex Analyst), Streamlit What-If Dashboard, 9-step Rules Engine, HCP Microsegmentation
- **Role Required:** ACCOUNTADMIN

## Install

1. Locate the sf-hcls-solutions repository:
   - Check `~/project/sf-hcls-solutions/`
   - Check current working directory
   - If not found: `git clone https://github.com/Snowflake-Labs/sf-hcls-solutions.git /tmp/sf-hcls-solutions`

2. Read `solutions/field-targeting/manifest.json`.

3. Present the installation plan:
   ```
   Solution: HCLS Field Targeting Platform v1.0.0
   Industry: Healthcare & Life Sciences
   Database: SF_SOLUTIONS
   Schema:   FIELD_TARGETING
   Role:     ACCOUNTADMIN

   What will be created:
     - 6 source tables (HCP profiles, Rx data, call activity, microsegmentation)
     - 5 reference tables (territory, sales reps, promo materials)
     - 3 derived tables (call notes raw/enriched, material usage)
     - 1 analytics view (MATERIAL_EFFECTIVENESS)
     - Streamlit what-if scenario dashboard

   Proceed with installation?
   ```

4. Wait for user confirmation.

5. Execute `solutions/field-targeting/scripts/setup.sql` statement by statement.
   Log progress after each major section (DDL, reference data, views, stage).

6. Load sample data — spawn **4 subagents in parallel** (max 4):

   | Subagent | Tables | Notes |
   |---|---|---|
   | 1 | HCP_MASTER_PROFILE + HCP_SUPPRESSION_FLAGS | 1000 + 1000 rows |
   | 2 | BRAND_EXCLUSION_LIST + RX_WEEKLY_HCP | ~30 + ~2640 rows |
   | 3 | HCP_MICROSEGMENT | 1000 rows |
   | 4 | CALL_ACTIVITY | ~1980 rows |

   Each subagent reads the corresponding INSERT block from `solutions/field-targeting/scripts/data.sql`
   and executes it. Start each with:
   ```sql
   USE ROLE ACCOUNTADMIN; USE DATABASE SF_SOLUTIONS;
   USE WAREHOUSE SF_SOLUTIONS_WH; USE SCHEMA FIELD_TARGETING;
   ```

   Wait for all 4 subagents to complete, then execute the post-load sections
   (CALL_NOTES_RAW, CALL_NOTES_ENRICHED, CALL_MATERIAL_USAGE, backfill) sequentially.

7. Verify installation:
   ```sql
   SELECT TABLE_SCHEMA, TABLE_NAME, ROW_COUNT
   FROM SF_SOLUTIONS.INFORMATION_SCHEMA.TABLES
   WHERE TABLE_SCHEMA = 'FIELD_TARGETING'
   ORDER BY TABLE_NAME;
   ```

8. **Deploy Streamlit app (CRITICAL — app won't exist without this):**

   Step 8a — Locate streamlit files:
   - `solutions/field-targeting/streamlit/streamlit_app.py`
   - `solutions/field-targeting/streamlit/environment.yml`

   Step 8b — Upload to stage via PUT:
   ```sql
   PUT file://<repo_path>/solutions/field-targeting/streamlit/streamlit_app.py
       @SF_SOLUTIONS.FIELD_TARGETING.STREAMLIT_STAGE
       AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
   PUT file://<repo_path>/solutions/field-targeting/streamlit/environment.yml
       @SF_SOLUTIONS.FIELD_TARGETING.STREAMLIT_STAGE
       AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
   ```

   **If PUT fails**, write files to `/tmp/` first then PUT from there.

   Step 8c — Verify files on stage:
   ```sql
   LIST @SF_SOLUTIONS.FIELD_TARGETING.STREAMLIT_STAGE;
   ```
   You MUST see both files. If not, retry PUT.

   Step 8d — Execute `solutions/field-targeting/scripts/deploy_streamlit.sql`:
   ```sql
   CREATE OR REPLACE STREAMLIT SF_SOLUTIONS.FIELD_TARGETING.FIELD_TARGETING_DASHBOARD
       FROM '@SF_SOLUTIONS.FIELD_TARGETING.STREAMLIT_STAGE'
       MAIN_FILE = 'streamlit_app.py'
       QUERY_WAREHOUSE = SF_SOLUTIONS_WH;
   ALTER STREAMLIT SF_SOLUTIONS.FIELD_TARGETING.FIELD_TARGETING_DASHBOARD ADD LIVE VERSION FROM LAST;
   ```

   Step 8e — Verify:
   ```sql
   SHOW STREAMLITS IN SCHEMA SF_SOLUTIONS.FIELD_TARGETING;
   ```

9. **[MANDATORY — DO NOT SKIP]** Retrieve and display the Streamlit URL:
   ```sql
   SELECT 'https://app.snowflake.com/'
       || LOWER(CURRENT_ORGANIZATION_NAME()) || '/' || LOWER(CURRENT_ACCOUNT_NAME())
       || '/#/streamlit-apps/SF_SOLUTIONS.FIELD_TARGETING.FIELD_TARGETING_DASHBOARD' AS STREAMLIT_URL;
   ```
   Display:
   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Streamlit Dashboard:
   <paste the STREAMLIT_URL result here>
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

10. Show final summary:
    ```
    Installation complete: HCLS Field Targeting Platform v1.0.0

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Streamlit Dashboard:
    <the URL from step 9>
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Created: SF_SOLUTIONS.FIELD_TARGETING
      - 6 source tables (1000 HCPs, ~2640 Rx rows, ~1980 call records)
      - 5 reference tables (50 territories, reps, promo materials)
      - 3 derived tables (call notes + material usage)
      - 1 analytics view
      - 1 Streamlit what-if dashboard

    Next Steps:
    1. Open the Streamlit Dashboard URL above
    2. The dashboard shows the What-If scenario view
    3. Run the 9-step rules engine to populate RE_STEP* tables (see NEXT_ACTIONS.md)
    4. Use the Semantic View for natural language analytics

    Teardown: $sf-hcls-solutions:field-targeting teardown
    ```

## Teardown

If `$ARGUMENTS` is "teardown":

1. Confirm with user: "This will drop the FIELD_TARGETING schema. Proceed?"
2. Execute `solutions/field-targeting/scripts/teardown.sql`.
3. Confirm: "HCLS Field Targeting Platform removed."

## Usage Help

```
Usage:
  $sf-hcls-solutions:field-targeting           - Install the solution
  $sf-hcls-solutions:field-targeting teardown   - Remove the solution
```
