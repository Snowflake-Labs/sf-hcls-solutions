---
name: medical-device-streaming
description: >
  Install or teardown the Medical Device Streaming Platform solution.
  Usage: /sf-hcls-solutions:medical-device-streaming | /sf-hcls-solutions:medical-device-streaming teardown
  Triggers: medical device, streaming, ECG, EDA, PPG, biosignal, snowpipe, real-time, IoT, telemetry.
tools:
  - snowflake_sql_execute
  - snowflake_object_search
  - Bash
  - Read
  - Glob
  - Grep
---

# Medical Device Streaming Platform

Parse the action from `$ARGUMENTS`:
- If `$ARGUMENTS` is "install" or empty -> run **Install** flow
- If `$ARGUMENTS` is "teardown" -> run **Teardown** flow
- Otherwise -> show usage help

## Overview

- **Industry:** Healthcare & Life Sciences
- **Database:** SF_SOLUTIONS
- **Schemas:** MEDICAL_DEVICE_CLINICAL, MEDICAL_DEVICE_TELEMETRY
- **Features:** Snowpipe Streaming (High-Performance), PIPE Objects, ASOF Joins, VARIANT Data, Flattened Views
- **Role Required:** ACCOUNTADMIN
- **Optional Marketplace Dataset:** Synthetic Healthcare Data - Clinical and Claims (free, for patient demographics)

## Install

1. Locate the sf-hcls-solutions repository:
   - Check `~/project/sf-hcls-solutions/`
   - Check current working directory
   - If not found: `git clone https://github.com/Snowflake-Labs/sf-hcls-solutions.git /tmp/sf-hcls-solutions`

2. Read `solutions/medical-device-streaming/manifest.json`.

3. Present the installation plan:
   ```
   Solution: Medical Device Streaming Platform v1.0.0
   Industry: Healthcare & Life Sciences
   Database: SF_SOLUTIONS
   Schemas:  MEDICAL_DEVICE_CLINICAL, MEDICAL_DEVICE_TELEMETRY
   Role:     ACCOUNTADMIN

   What will be created:
     - 2 schemas (clinical + telemetry)
     - 5 tables (PATIENT_SESSIONS, DEVICE_REGISTRY, ECG_DATA, EDA_DATA, PPG_DATA, DEVICE_TELEMETRY)
     - 4 streaming pipes (ECG, EDA, PPG, TELEMETRY)
     - 5 analytics views (3 flattened + PATIENT_VITAL_SIGNS consolidated + DEVICE_TELEMETRY_FLATTENED)
     - Grants for streaming and query access

   Optional:
     - Synthetic Healthcare Data (free Marketplace dataset for patient demographics)

   Proceed with installation?
   ```

4. Wait for user confirmation.

5. Read `solutions/medical-device-streaming/scripts/setup.sql` and execute it.

   Execution strategy:
   - Execute statement by statement (all are independent DDL/DML)
   - Log progress after each major section (schemas, tables, pipes, views, grants)

6. Load sample data:
   Read `solutions/medical-device-streaming/scripts/data.sql` and execute it.
   This inserts realistic sample data so the Streamlit dashboard displays charts immediately.

   > **Important:** This is static demo data for initial visualization. For real-time
   > streaming that updates continuously, users must run the Python streaming client
   > (see NEXT_ACTIONS.md "Run the Streaming Demo" section).

   Execution strategy:
   - Execute statement by statement
   - All INSERT statements are independent and can be run in parallel via subagents

7. Verify installation:
   ```sql
   -- Check tables
   SELECT TABLE_SCHEMA, TABLE_NAME
   FROM SF_SOLUTIONS.INFORMATION_SCHEMA.TABLES
   WHERE TABLE_SCHEMA IN ('MEDICAL_DEVICE_CLINICAL', 'MEDICAL_DEVICE_TELEMETRY')
   ORDER BY TABLE_SCHEMA, TABLE_NAME;

   -- Check pipes
   SHOW PIPES IN SCHEMA SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL;
   SHOW PIPES IN SCHEMA SF_SOLUTIONS.MEDICAL_DEVICE_TELEMETRY;

   -- Check views
   SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
   FROM SF_SOLUTIONS.INFORMATION_SCHEMA.TABLES
   WHERE TABLE_SCHEMA IN ('MEDICAL_DEVICE_CLINICAL', 'MEDICAL_DEVICE_TELEMETRY')
     AND TABLE_TYPE = 'VIEW'
   ORDER BY TABLE_SCHEMA, TABLE_NAME;
   ```

8. **Deploy Streamlit app (CRITICAL — app won't exist without this):**

   First, locate the streamlit files in the repository:
   - `solutions/medical-device-streaming/streamlit/streamlit_app.py`
   - `solutions/medical-device-streaming/streamlit/environment.yml`

   Step 8a — Set context and create stage:
   ```sql
   USE ROLE ACCOUNTADMIN;
   USE DATABASE SF_SOLUTIONS;
   USE WAREHOUSE SF_SOLUTIONS_WH;
   USE SCHEMA MEDICAL_DEVICE_CLINICAL;
   CREATE STAGE IF NOT EXISTS SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL.STREAMLIT_STAGE DIRECTORY = (ENABLE = TRUE);
   ```

   Step 8b — Upload files to stage via PUT:
   ```sql
   PUT file://<repo_path>/solutions/medical-device-streaming/streamlit/streamlit_app.py @SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL.STREAMLIT_STAGE/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
   ```
   ```sql
   PUT file://<repo_path>/solutions/medical-device-streaming/streamlit/environment.yml @SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL.STREAMLIT_STAGE/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
   ```

   Replace `<repo_path>` with the actual absolute path to the repository on disk.

   **If PUT fails**, write the file contents to `/tmp/streamlit_app.py` and `/tmp/environment.yml` first, then PUT those:
   ```sql
   PUT file:///tmp/streamlit_app.py @SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL.STREAMLIT_STAGE/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
   PUT file:///tmp/environment.yml @SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL.STREAMLIT_STAGE/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
   ```

   Step 8c — Verify files are on stage:
   ```sql
   LIST @SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL.STREAMLIT_STAGE;
   ```
   You MUST see `streamlit_app.py` and `environment.yml`. If not, retry PUT.

   Step 8d — Execute `solutions/medical-device-streaming/scripts/deploy_streamlit.sql`:
   This creates the STREAMLIT object and adds the LIVE version. Execute it statement by statement:
   ```sql
   CREATE OR REPLACE STREAMLIT SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL.MEDICAL_DEVICE_MONITOR
       FROM '@SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL.STREAMLIT_STAGE'
       MAIN_FILE = 'streamlit_app.py'
       QUERY_WAREHOUSE = SF_SOLUTIONS_WH;
   ```
   ```sql
   ALTER STREAMLIT SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL.MEDICAL_DEVICE_MONITOR ADD LIVE VERSION FROM LAST;
   ```

   Step 8e — Verify Streamlit was created:
   ```sql
   SHOW STREAMLITS IN SCHEMA SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL;
   ```
   You MUST see MEDICAL_DEVICE_MONITOR in the output. If not, something went wrong.

9. **[MANDATORY — DO NOT SKIP]** Retrieve and display the Streamlit app URL.
   Execute this query:
   ```sql
   SELECT 'https://app.snowflake.com/'
       || LOWER(CURRENT_ORGANIZATION_NAME()) || '/' || LOWER(CURRENT_ACCOUNT_NAME())
       || '/#/streamlit-apps/SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL.MEDICAL_DEVICE_MONITOR' AS STREAMLIT_URL;
   ```
   You MUST display the result to the user in this exact format:
   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Streamlit Dashboard:
   <paste the STREAMLIT_URL query result here>
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

   This step is NON-OPTIONAL. If you skip this, the installation is INCOMPLETE.
   The user MUST see the Streamlit URL. Do NOT substitute with a Snowsight schema browser URL.

10. Show final summary (MUST include the Streamlit URL from step 9):
   ```
   Installation complete: Medical Device Streaming Platform v1.0.0

   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Streamlit Dashboard:
   <the URL from step 9>
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   Created:
     - SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL (5 tables, 3 pipes, 4 views, 1 Streamlit app)
     - SF_SOLUTIONS.MEDICAL_DEVICE_TELEMETRY (1 table, 1 pipe, 1 view)

   Next Actions:
   1. Open the Streamlit Dashboard URL above
   2. Dashboard shows sample data immediately (static demo data)
   3. For real-time streaming: run the Python client (see NEXT_ACTIONS.md)
   4. Watch live vital signs update in the dashboard

   Teardown: /sf-hcls-solutions:medical-device-streaming teardown
   ```

## Teardown

If `$ARGUMENTS` is "teardown":

1. Confirm with user: "This will drop MEDICAL_DEVICE_CLINICAL and MEDICAL_DEVICE_TELEMETRY schemas (including all tables, pipes, and views). Proceed?"
2. Read and execute `solutions/medical-device-streaming/scripts/teardown.sql` statement by statement.
3. Confirm: "Medical Device Streaming Platform removed."

## Next Actions

If the user asks "what next?", "what can I do?", or "how to use this":

Read and present the content from `NEXT_ACTIONS.md` (located in this skill's directory).
Present the relevant section based on user intent:
- Just exploring -> Quick Exploration section
- Wants to run streaming demo -> Run the Streaming Demo section
- Wants to connect real devices -> Connect Real Data section
- Ready for production -> Production Deployment section

## Usage Help

```
Usage:
  /sf-hcls-solutions:medical-device-streaming           - Install the solution
  /sf-hcls-solutions:medical-device-streaming teardown   - Remove the solution
```
