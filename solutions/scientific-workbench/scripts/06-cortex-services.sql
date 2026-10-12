-- =============================================================================
-- 06-cortex-services.sql
-- Cortex Agent, Cortex Search services, and Semantic Views
-- Run as SYSADMIN
-- =============================================================================

USE DATABASE SCIENTIFIC_WORKBENCH;
USE WAREHOUSE WORKBENCH_XS;

-- =============================================================================
-- 1. CORTEX SEARCH SERVICES
-- =============================================================================

-- Asset Catalog Search (datasets, tools, experiments)
CREATE OR REPLACE CORTEX SEARCH SERVICE CATALOG.ASSET_SEARCH
  ON asset_name
  ATTRIBUTES description, asset_type, domain, schema_name, owner
  WAREHOUSE = WORKBENCH_XS
  TARGET_LAG = '1 hour'
  AS (
    SELECT
      asset_id,
      asset_name,
      description,
      asset_type,
      domain,
      schema_name,
      owner,
      created_at
    FROM SCIENTIFIC_WORKBENCH.CATALOG.ASSETS
  )
  ;

-- Tool Search (agent discovers tools by intent)
CREATE OR REPLACE CORTEX SEARCH SERVICE CATALOG.TOOL_SEARCH
  ON description
  ATTRIBUTES display_name, domain, parameters, example_usage, tool_type
  WAREHOUSE = WORKBENCH_XS
  TARGET_LAG = '1 hour'
  AS (
    SELECT
      tool_id,
      display_name,
      description,
      domain::VARCHAR AS domain,
      parameters,
      example_usage,
      function_reference,
      tool_type
    FROM SCIENTIFIC_WORKBENCH.CATALOG.TOOLS
    WHERE status = 'active'
  )
  ;

-- Re-granted on every run: CREATE OR REPLACE above drops existing grants.
GRANT USAGE ON CORTEX SEARCH SERVICE CATALOG.TOOL_SEARCH TO ROLE WORKBENCH_ADMIN;
GRANT USAGE ON CORTEX SEARCH SERVICE CATALOG.ASSET_SEARCH TO ROLE WORKBENCH_ADMIN;
GRANT USAGE ON CORTEX SEARCH SERVICE CATALOG.TOOL_SEARCH TO ROLE WORKBENCH_SCIENTIST;
GRANT USAGE ON CORTEX SEARCH SERVICE CATALOG.ASSET_SEARCH TO ROLE WORKBENCH_SCIENTIST;

-- =============================================================================
-- 2. CKE CONFIGURATION TABLE + AUTO-DISCOVERY
-- =============================================================================
-- CKEs from Marketplace install into their own databases. The search procedures
-- read CKE_CONFIG at runtime to resolve the fully-qualified service name, so
-- deployers don't need to edit procedure source. This table stores the mapping.

CREATE TABLE IF NOT EXISTS CATALOG.CKE_CONFIG (
    CKE_NAME        VARCHAR NOT NULL,         -- PUBMED | CLINICAL_TRIALS
    DATABASE_NAME   VARCHAR NOT NULL,         -- Marketplace database name
    SCHEMA_NAME     VARCHAR NOT NULL,
    SERVICE_NAME    VARCHAR NOT NULL,         -- Cortex Search service name
    SERVICE_FQN     VARCHAR NOT NULL,         -- Fully qualified: DB.SCHEMA.SERVICE
    ACTIVE          BOOLEAN DEFAULT TRUE,
    DISCOVERED_AT   TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
COMMENT = 'Maps CKE Marketplace subscriptions to their fully-qualified search service names';

-- Auto-discover installed CKEs by scanning Cortex Search services in the account.
-- Well-known CKE service patterns (publisher-defined names):
MERGE INTO CATALOG.CKE_CONFIG AS tgt
USING (
    SELECT 'PUBMED' AS CKE_NAME,
           'PUBMED_BIOMEDICAL_RESEARCH_CORPUS' AS DATABASE_NAME,
           'OA_COMM' AS SCHEMA_NAME,
           'PUBMED_CKE' AS SERVICE_NAME,
           'PUBMED_BIOMEDICAL_RESEARCH_CORPUS.OA_COMM.PUBMED_CKE' AS SERVICE_FQN
    UNION ALL
    SELECT 'CLINICAL_TRIALS',
           'CLINICAL_TRIALS_RESEARCH_DATABASE',
           'CT',
           'CLINICAL_TRIALS_SEARCH_SERVICE',
           'CLINICAL_TRIALS_RESEARCH_DATABASE.CT.CLINICAL_TRIALS_SEARCH_SERVICE'
) AS src
ON tgt.CKE_NAME = src.CKE_NAME
WHEN NOT MATCHED THEN INSERT (CKE_NAME, DATABASE_NAME, SCHEMA_NAME, SERVICE_NAME, SERVICE_FQN)
    VALUES (src.CKE_NAME, src.DATABASE_NAME, src.SCHEMA_NAME, src.SERVICE_NAME, src.SERVICE_FQN)
WHEN MATCHED THEN UPDATE SET
    SERVICE_FQN = src.SERVICE_FQN,
    DISCOVERED_AT = CURRENT_TIMESTAMP();

GRANT SELECT ON TABLE CATALOG.CKE_CONFIG TO ROLE WORKBENCH_ADMIN;
GRANT SELECT ON TABLE CATALOG.CKE_CONFIG TO ROLE WORKBENCH_SCIENTIST;

-- =============================================================================
-- 3. CORTEX AGENT
-- =============================================================================
-- DISCOVERY_AGENT is created in Phase 5 by engine/sql/create_workflow_runner.sql
-- with the full YAML specification. Not created here to avoid overwriting.
-- =============================================================================

-- =============================================================================
-- 4. SEMANTIC VIEWS (Cortex Analyst)
-- =============================================================================
-- See data/semantic_views/ for full DDL:
--   - sv_chemistry.sql (compounds, activities, targets)
--   - sv_genomics.sql (genes, expression, pathways)
--   - sv_clinical.sql (patients, outcomes, trials)
