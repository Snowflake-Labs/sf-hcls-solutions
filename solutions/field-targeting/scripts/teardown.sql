-- =============================================================================
-- Teardown: HCLS Field Targeting Platform
-- Drops the FIELD_TARGETING schema only.
-- Does NOT drop SF_SOLUTIONS database or SF_SOLUTIONS_WH warehouse
-- (shared across all solutions).
-- =============================================================================

USE ROLE ACCOUNTADMIN;

DROP SCHEMA IF EXISTS SF_SOLUTIONS.FIELD_TARGETING CASCADE;
