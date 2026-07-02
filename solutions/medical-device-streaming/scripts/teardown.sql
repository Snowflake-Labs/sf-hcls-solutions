-- =============================================================================
-- Teardown: Medical Device Streaming Platform
-- Drops solution schemas only (preserves shared SF_SOLUTIONS database/warehouse)
-- =============================================================================

USE ROLE ACCOUNTADMIN;

DROP SCHEMA IF EXISTS SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL CASCADE;
DROP SCHEMA IF EXISTS SF_SOLUTIONS.MEDICAL_DEVICE_TELEMETRY CASCADE;
