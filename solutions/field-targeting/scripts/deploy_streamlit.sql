-- =============================================================================
-- Deploy Streamlit: HCLS Field Targeting Platform
--
-- Prerequisites:
--   1. setup.sql must have been executed
--   2. data.sql must have been executed
--   3. streamlit_app.py and environment.yml must be on stage:
--      PUT file://<repo>/solutions/field-targeting/streamlit/streamlit_app.py
--          @SF_SOLUTIONS.FIELD_TARGETING.STREAMLIT_STAGE
--          AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--      PUT file://<repo>/solutions/field-targeting/streamlit/environment.yml
--          @SF_SOLUTIONS.FIELD_TARGETING.STREAMLIT_STAGE
--          AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--
-- This script is executed by the installer AFTER PUT succeeds.
-- =============================================================================

USE ROLE ACCOUNTADMIN;
USE DATABASE SF_SOLUTIONS;
USE SCHEMA FIELD_TARGETING;
USE WAREHOUSE SF_SOLUTIONS_WH;

CREATE OR REPLACE STREAMLIT SF_SOLUTIONS.FIELD_TARGETING.FIELD_TARGETING_DASHBOARD
    FROM '@SF_SOLUTIONS.FIELD_TARGETING.STREAMLIT_STAGE'
    MAIN_FILE = 'streamlit_app.py'
    QUERY_WAREHOUSE = SF_SOLUTIONS_WH;

ALTER STREAMLIT SF_SOLUTIONS.FIELD_TARGETING.FIELD_TARGETING_DASHBOARD ADD LIVE VERSION FROM LAST;
