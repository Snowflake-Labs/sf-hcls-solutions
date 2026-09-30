-- =============================================================================
-- Sample Data: HCLS Field Targeting Platform
-- Generates synthetic HCP, Rx, microsegmentation, and call activity data
-- using Snowflake-native GENERATOR() + SEQ4() + UNIFORM() — no Python required.
--
-- 6 tables, designed for 4-parallel subagent execution:
--   Subagent 1: HCP_MASTER_PROFILE + HCP_SUPPRESSION_FLAGS
--   Subagent 2: BRAND_EXCLUSION_LIST + RX_WEEKLY_HCP
--   Subagent 3: HCP_MICROSEGMENT
--   Subagent 4: CALL_ACTIVITY
-- After all 4 complete: populate CALL_NOTES_RAW/ENRICHED, CALL_MATERIAL_USAGE
-- =============================================================================

USE ROLE ACCOUNTADMIN;
USE DATABASE SF_SOLUTIONS;
USE WAREHOUSE SF_SOLUTIONS_WH;
USE SCHEMA FIELD_TARGETING;

-- =============================================================================
-- TERRITORY lookup CTE (reusable across inserts)
-- 50 territories mapped to region, field force, city, state
-- =============================================================================

-- =============================================================================
-- TABLE 1: HCP_MASTER_PROFILE (1,000 rows)
-- Specialty distribution: ~33% RHEUM, ~33% DERM, ~34% IM/FP
-- =============================================================================

INSERT INTO SF_SOLUTIONS.FIELD_TARGETING.HCP_MASTER_PROFILE (
    MDM_ID, CUST_ID, INT_HCP_ID, HCP_REG_NUM, FRST_NM, LAST_NM, FULL_NM,
    SPEC_CD, SPEC_DESC, SPEC_GRP_CD, SPEC_GRP_DESC, PRIMARY_SPECIALTY,
    CITY, STATE, ZIP_CD,
    TERR_ID, TERR, FF_ID, FF_NM,
    DATA_PERIOD, VERSION_ID,
    AUDIT_INSRT_DT, AUDIT_INSRT_NM, AUDIT_UPDT_DT, AUDIT_UPDT_NM
)
WITH terr_lookup AS (
    SELECT COLUMN1 AS TERR_ID, COLUMN2 AS CITY, COLUMN3 AS STATE, COLUMN4 AS FF_ID, COLUMN5 AS FF_NM
    FROM VALUES
        ('NY-NYC-001','New York','NY','FF-NE-01','Northeast Field Force'),
        ('NY-NYC-002','New York','NY','FF-NE-01','Northeast Field Force'),
        ('NJ-NWK-001','Newark','NJ','FF-NE-01','Northeast Field Force'),
        ('CT-HRT-001','Hartford','CT','FF-NE-01','Northeast Field Force'),
        ('NY-ALB-001','Albany','NY','FF-NE-01','Northeast Field Force'),
        ('MA-BOS-001','Boston','MA','FF-NE-01','Northeast Field Force'),
        ('MA-BOS-002','Boston','MA','FF-NE-01','Northeast Field Force'),
        ('PA-PHL-001','Philadelphia','PA','FF-NE-01','Northeast Field Force'),
        ('PA-PHL-002','Philadelphia','PA','FF-NE-01','Northeast Field Force'),
        ('RI-PVD-001','Providence','RI','FF-NE-01','Northeast Field Force'),
        ('FL-MIA-001','Miami','FL','FF-SE-01','Southeast Field Force'),
        ('FL-MIA-002','Fort Lauderdale','FL','FF-SE-01','Southeast Field Force'),
        ('FL-ORL-001','Orlando','FL','FF-SE-01','Southeast Field Force'),
        ('FL-TPA-001','Tampa','FL','FF-SE-01','Southeast Field Force'),
        ('FL-JAX-001','Jacksonville','FL','FF-SE-01','Southeast Field Force'),
        ('GA-ATL-001','Atlanta','GA','FF-SE-01','Southeast Field Force'),
        ('GA-ATL-002','Atlanta','GA','FF-SE-01','Southeast Field Force'),
        ('NC-CLT-001','Charlotte','NC','FF-SE-01','Southeast Field Force'),
        ('NC-RDU-001','Raleigh','NC','FF-SE-01','Southeast Field Force'),
        ('VA-RIC-001','Richmond','VA','FF-SE-01','Southeast Field Force'),
        ('IL-CHI-001','Chicago','IL','FF-MW-01','Midwest Field Force'),
        ('IL-CHI-002','Chicago','IL','FF-MW-01','Midwest Field Force'),
        ('OH-CLE-001','Cleveland','OH','FF-MW-01','Midwest Field Force'),
        ('OH-COL-001','Columbus','OH','FF-MW-01','Midwest Field Force'),
        ('MI-DET-001','Detroit','MI','FF-MW-01','Midwest Field Force'),
        ('MN-MSP-001','Minneapolis','MN','FF-MW-01','Midwest Field Force'),
        ('WI-MKE-001','Milwaukee','WI','FF-MW-01','Midwest Field Force'),
        ('IN-IND-001','Indianapolis','IN','FF-MW-01','Midwest Field Force'),
        ('MO-STL-001','St Louis','MO','FF-MW-01','Midwest Field Force'),
        ('MO-KCI-001','Kansas City','MO','FF-MW-01','Midwest Field Force'),
        ('CA-LAX-001','Los Angeles','CA','FF-WE-01','West Field Force'),
        ('CA-LAX-002','Irvine','CA','FF-WE-01','West Field Force'),
        ('CA-SFO-001','San Francisco','CA','FF-WE-01','West Field Force'),
        ('CA-SDG-001','San Diego','CA','FF-WE-01','West Field Force'),
        ('WA-SEA-001','Seattle','WA','FF-WE-01','West Field Force'),
        ('AZ-PHX-001','Phoenix','AZ','FF-WE-01','West Field Force'),
        ('CO-DEN-001','Denver','CO','FF-WE-01','West Field Force'),
        ('OR-PDX-001','Portland','OR','FF-WE-01','West Field Force'),
        ('NV-LAS-001','Las Vegas','NV','FF-WE-01','West Field Force'),
        ('UT-SLC-001','Salt Lake City','UT','FF-WE-01','West Field Force'),
        ('TX-HOU-001','Houston','TX','FF-SC-01','South Central Field Force'),
        ('TX-DAL-001','Dallas','TX','FF-SC-01','South Central Field Force'),
        ('TX-SAT-001','San Antonio','TX','FF-SC-01','South Central Field Force'),
        ('TX-AUS-001','Austin','TX','FF-SC-01','South Central Field Force'),
        ('LA-NOR-001','New Orleans','LA','FF-SC-01','South Central Field Force'),
        ('LA-NOR-002','Baton Rouge','LA','FF-SC-01','South Central Field Force'),
        ('TN-NSH-001','Nashville','TN','FF-SC-01','South Central Field Force'),
        ('TN-MEM-001','Memphis','TN','FF-SC-01','South Central Field Force'),
        ('AL-BHM-001','Birmingham','AL','FF-SC-01','South Central Field Force'),
        ('OK-OKC-001','Oklahoma City','OK','FF-SC-01','South Central Field Force')
),
hcp_gen AS (
    SELECT
        SEQ4() + 1 AS RN,
        'MDM_' || LPAD((SEQ4() + 1)::VARCHAR, 5, '0') AS MDM_ID,
        'CUST_' || LPAD((SEQ4() + 1)::VARCHAR, 7, '0') AS CUST_ID,
        'INT_' || LPAD((SEQ4() + 1)::VARCHAR, 6, '0') AS INT_HCP_ID,
        (1000000000 + ABS(MOD(HASH('REG' || SEQ4()), 8999999999)))::VARCHAR AS HCP_REG_NUM,
        -- Specialty: ~17% RHE, ~16% DER, ~17% RHEUM, ~16% DERM, ~17% IM, ~17% FP
        CASE MOD(ABS(MOD(HASH('SPEC' || SEQ4()), 100)), 6)
            WHEN 0 THEN 'RHE'   WHEN 1 THEN 'DER'
            WHEN 2 THEN 'RHEUM' WHEN 3 THEN 'DERM'
            WHEN 4 THEN 'IM'    ELSE 'FP'
        END AS SPEC_CD,
        -- Territory: round-robin across 50 territories
        MOD(SEQ4(), 50) AS TERR_IDX,
        -- Version: 95% v1, 5% v2
        CASE WHEN UNIFORM(0, 100, RANDOM()) < 95 THEN 1 ELSE 2 END AS VERSION_ID,
        -- Names from a deterministic pool
        CASE MOD(ABS(MOD(HASH('FN' || SEQ4()), 20)), 20)
            WHEN 0  THEN 'James'     WHEN 1  THEN 'Mary'
            WHEN 2  THEN 'John'      WHEN 3  THEN 'Patricia'
            WHEN 4  THEN 'Robert'    WHEN 5  THEN 'Jennifer'
            WHEN 6  THEN 'Michael'   WHEN 7  THEN 'Linda'
            WHEN 8  THEN 'William'   WHEN 9  THEN 'Barbara'
            WHEN 10 THEN 'David'     WHEN 11 THEN 'Susan'
            WHEN 12 THEN 'Richard'   WHEN 13 THEN 'Dorothy'
            WHEN 14 THEN 'Joseph'    WHEN 15 THEN 'Lisa'
            WHEN 16 THEN 'Thomas'    WHEN 17 THEN 'Nancy'
            WHEN 18 THEN 'Charles'   ELSE 'Karen'
        END AS FRST_NM,
        CASE MOD(ABS(MOD(HASH('LN' || SEQ4()), 20)), 20)
            WHEN 0  THEN 'Smith'     WHEN 1  THEN 'Johnson'
            WHEN 2  THEN 'Williams'  WHEN 3  THEN 'Brown'
            WHEN 4  THEN 'Jones'     WHEN 5  THEN 'Garcia'
            WHEN 6  THEN 'Miller'    WHEN 7  THEN 'Davis'
            WHEN 8  THEN 'Rodriguez' WHEN 9  THEN 'Martinez'
            WHEN 10 THEN 'Hernandez' WHEN 11 THEN 'Lopez'
            WHEN 12 THEN 'Gonzalez'  WHEN 13 THEN 'Wilson'
            WHEN 14 THEN 'Anderson'  WHEN 15 THEN 'Thomas'
            WHEN 16 THEN 'Taylor'    WHEN 17 THEN 'Moore'
            WHEN 18 THEN 'Jackson'   ELSE 'Martin'
        END AS LAST_NM,
        LPAD((10000 + ABS(MOD(HASH('ZIP' || SEQ4()), 89999)))::VARCHAR, 5, '0') AS ZIP_CD
    FROM TABLE(GENERATOR(ROWCOUNT => 1000))
),
spec_lookup AS (
    SELECT COLUMN1 AS SPEC_CD, COLUMN2 AS SPEC_DESC, COLUMN3 AS SPEC_GRP
    FROM VALUES
        ('RHE','Rheumatology','Specialty'),
        ('DER','Dermatology','Specialty'),
        ('RHEUM','Rheumatology','Specialty'),
        ('DERM','Dermatology','Specialty'),
        ('IM','Internal Medicine','Primary Care'),
        ('FP','Family Practice','Primary Care')
),
terr_indexed AS (
    SELECT *, ROW_NUMBER() OVER (ORDER BY TERR_ID) - 1 AS IDX FROM terr_lookup
)
SELECT
    h.MDM_ID, h.CUST_ID, h.INT_HCP_ID, h.HCP_REG_NUM,
    h.FRST_NM, h.LAST_NM,
    'Dr. ' || h.FRST_NM || ' ' || h.LAST_NM AS FULL_NM,
    h.SPEC_CD, s.SPEC_DESC,
    s.SPEC_GRP AS SPEC_GRP_CD, s.SPEC_DESC AS SPEC_GRP_DESC, s.SPEC_DESC AS PRIMARY_SPECIALTY,
    t.CITY, t.STATE, h.ZIP_CD,
    t.TERR_ID, t.TERR_ID AS TERR, t.FF_ID, t.FF_NM,
    '2026-03-09 10:00:00'::TIMESTAMP_NTZ AS DATA_PERIOD,
    h.VERSION_ID,
    '2026-03-09 10:00:00'::TIMESTAMP_NTZ AS AUDIT_INSRT_DT, 'DATA_PIPELINE' AS AUDIT_INSRT_NM,
    '2026-03-09 10:00:00'::TIMESTAMP_NTZ AS AUDIT_UPDT_DT, 'DATA_PIPELINE' AS AUDIT_UPDT_NM
FROM hcp_gen h
JOIN spec_lookup s ON h.SPEC_CD = s.SPEC_CD
JOIN terr_indexed t ON h.TERR_IDX = t.IDX;

-- =============================================================================
-- TABLE 2: HCP_SUPPRESSION_FLAGS (1,000 rows, matching HCP_MASTER_PROFILE)
-- debarred 0.5%, sanctioned 0.3%, global_suppress 1%, call 3%, email 5%
-- =============================================================================

INSERT INTO SF_SOLUTIONS.FIELD_TARGETING.HCP_SUPPRESSION_FLAGS (
    MDM_ID, IS_DEBARRED, IS_SANCTIONED, GLOBAL_SUPPRESS_FLG,
    CALL_SUPPRESS_FLG, EMAIL_SUPPRESS_FLG, DIGITAL_SUPPRESS_FLG,
    SAMPLE_SUPPRESS_FLG, SPEAKER_SUPPRESS_FLG
)
SELECT
    'MDM_' || LPAD((SEQ4() + 1)::VARCHAR, 5, '0') AS MDM_ID,
    CASE WHEN UNIFORM(0, 1000, RANDOM()) < 5  THEN 'Y' ELSE 'N' END AS IS_DEBARRED,
    CASE WHEN UNIFORM(0, 1000, RANDOM()) < 3  THEN 'Y' ELSE 'N' END AS IS_SANCTIONED,
    CASE WHEN UNIFORM(0, 100,  RANDOM()) < 1  THEN 'Y' ELSE 'N' END AS GLOBAL_SUPPRESS_FLG,
    CASE WHEN UNIFORM(0, 100,  RANDOM()) < 3  THEN 'Y' ELSE 'N' END AS CALL_SUPPRESS_FLG,
    CASE WHEN UNIFORM(0, 100,  RANDOM()) < 5  THEN 'Y' ELSE 'N' END AS EMAIL_SUPPRESS_FLG,
    CASE WHEN UNIFORM(0, 100,  RANDOM()) < 2  THEN 'Y' ELSE 'N' END AS DIGITAL_SUPPRESS_FLG,
    CASE WHEN UNIFORM(0, 1000, RANDOM()) < 10 THEN 'Y' ELSE 'N' END AS SAMPLE_SUPPRESS_FLG,
    CASE WHEN UNIFORM(0, 1000, RANDOM()) < 5  THEN 'Y' ELSE 'N' END AS SPEAKER_SUPPRESS_FLG
FROM TABLE(GENERATOR(ROWCOUNT => 1000));

-- =============================================================================
-- TABLE 3: BRAND_EXCLUSION_LIST (~30 rows, ~3% of HCPs)
-- =============================================================================

INSERT INTO SF_SOLUTIONS.FIELD_TARGETING.BRAND_EXCLUSION_LIST (
    MDM_ID, EXCLUSION_REASON, IS_ACTIVE, EFFECTIVE_DATE, EXPIRY_DATE
)
SELECT
    'MDM_' || LPAD((ABS(MOD(HASH('EXCL' || SEQ4()), 1000)) + 1)::VARCHAR, 5, '0') AS MDM_ID,
    CASE MOD(ABS(MOD(HASH('RSN' || SEQ4()), 100)), 5)
        WHEN 0 THEN 'CLOSED_NETWORK_A'
        WHEN 1 THEN 'SYSTEM_RESTRICTION_B'
        WHEN 2 THEN 'DATA_PRIVACY_OPT_OUT'
        WHEN 3 THEN 'STATE_RESTRICTION'
        ELSE 'COMPLIANCE_HOLD'
    END AS EXCLUSION_REASON,
    'Y' AS IS_ACTIVE,
    DATEADD('day', -UNIFORM(1, 365, RANDOM()), '2026-03-09'::DATE)::TIMESTAMP_NTZ AS EFFECTIVE_DATE,
    CASE WHEN UNIFORM(0, 100, RANDOM()) < 60 THEN NULL ELSE '2099-12-31'::TIMESTAMP_NTZ END AS EXPIRY_DATE
FROM TABLE(GENERATOR(ROWCOUNT => 30));

-- =============================================================================
-- TABLE 4: RX_WEEKLY_HCP (~2,640 rows)
-- Only eligible specialties (RHE/DER/RHEUM/DERM, ~66% of 1000 HCPs = ~660)
-- 4 weekly snapshots each → ~2,640 rows
-- Power-law Rx by tier: top 10% = 5-20 TRx, next 20% = 2-8, next 30% = 0.5-3, rest = 0-1
-- =============================================================================

INSERT INTO SF_SOLUTIONS.FIELD_TARGETING.RX_WEEKLY_HCP (
    MDM_ID, PRODUCT, METRIC, RX, WEEK_ID, GEO_ID, GEO_DESC, TERR_ID
)
WITH eligible_hcps AS (
    SELECT MDM_ID, TERR_ID, ZIP_CD, CITY, STATE,
        ROW_NUMBER() OVER (ORDER BY MDM_ID) AS RK,
        COUNT(*) OVER () AS TOTAL_ELIGIBLE
    FROM SF_SOLUTIONS.FIELD_TARGETING.HCP_MASTER_PROFILE
    WHERE SPEC_CD IN ('RHE', 'DER', 'RHEUM', 'DERM')
),
weekly_dates AS (
    SELECT COLUMN1::DATE AS WEEK_ID FROM VALUES
        ('2026-03-09'), ('2026-03-02'), ('2026-02-23'), ('2026-02-16')
)
SELECT
    h.MDM_ID,
    'ZENIXAR' AS PRODUCT,
    'TRX' AS METRIC,
    GREATEST(0,
        CASE
            WHEN h.RK <= h.TOTAL_ELIGIBLE * 0.10 THEN ROUND(UNIFORM(5.0, 20.0, RANDOM()) + UNIFORM(-0.3, 0.3, RANDOM()), 1)
            WHEN h.RK <= h.TOTAL_ELIGIBLE * 0.30 THEN ROUND(UNIFORM(2.0, 8.0, RANDOM()) + UNIFORM(-0.3, 0.3, RANDOM()), 1)
            WHEN h.RK <= h.TOTAL_ELIGIBLE * 0.60 THEN ROUND(UNIFORM(0.5, 3.0, RANDOM()) + UNIFORM(-0.3, 0.3, RANDOM()), 1)
            ELSE ROUND(UNIFORM(0.0, 1.0, RANDOM()) + UNIFORM(-0.1, 0.1, RANDOM()), 1)
        END
    ) AS RX,
    w.WEEK_ID,
    h.ZIP_CD AS GEO_ID,
    h.CITY || ', ' || h.STATE AS GEO_DESC,
    h.TERR_ID
FROM eligible_hcps h
CROSS JOIN weekly_dates w;

-- =============================================================================
-- TABLE 5: HCP_MICROSEGMENT (1,000 rows)
-- Derived from HCP_MASTER_PROFILE — propensity scores, tiers, KOL flags
-- =============================================================================

INSERT INTO SF_SOLUTIONS.FIELD_TARGETING.HCP_MICROSEGMENT (
    MDM_ID, CUST_ID, INT_HCP_ID, HCP_REG_ID,
    DECILE, DECILE_PROD_A, DECILE_PROD_B,
    TIER, TIER_PROD_A, TIER_PROD_B,
    LIFECYCLE_STAGE, CHANNEL_PREFERENCE,
    PROPENSITY_SCORE, ADOPTION_PROPENSITY, SWITCH_PROPENSITY, GROWTH_POTENTIAL,
    DIGITAL_AFFINITY_SCORE, EMAIL_RESPONSIVENESS, CALL_RECEPTIVITY,
    IS_KOL, IS_KOI, KOL_RANK, INFLUENCE_SCORE,
    PRIM_SPEC_CD, PRIM_SPEC_DESC, SPEC_GRP_DESC, SPECIALTY_CODE,
    SEGMENT_AS_OF_DT, MODEL_VERSION,
    AUDIT_INSRT_DT, AUDIT_INSRT_NM, AUDIT_UPDT_DT, AUDIT_UPDT_NM
)
WITH hcp_base AS (
    SELECT
        MDM_ID, CUST_ID, INT_HCP_ID, HCP_REG_NUM,
        SPEC_CD, SPEC_DESC,
        ROW_NUMBER() OVER (ORDER BY MDM_ID) AS RN,
        COUNT(*) OVER () AS TOTAL
    FROM SF_SOLUTIONS.FIELD_TARGETING.HCP_MASTER_PROFILE
),
scored AS (
    SELECT *,
        ROUND(LEAST(1.0, GREATEST(0.0, UNIFORM(0.1, 0.9, RANDOM()))), 4) AS ADOPT,
        ROUND(LEAST(1.0, GREATEST(0.0, UNIFORM(0.1, 0.8, RANDOM()))), 4) AS SWITCH_P,
        ROUND(LEAST(1.0, GREATEST(0.0, UNIFORM(0.1, 0.9, RANDOM()))), 4) AS GROWTH,
        -- KOL: ~15% have rank >= 60
        CASE WHEN UNIFORM(0, 100, RANDOM()) < 15
            THEN UNIFORM(60, 100, RANDOM())::INT
            ELSE UNIFORM(0, 59, RANDOM())::INT
        END AS KOL_RANK_VAL
    FROM hcp_base
),
with_propensity AS (
    SELECT *,
        ROUND((ADOPT + SWITCH_P + GROWTH) / 3.0, 4) AS PROP_SCORE,
        NTILE(10) OVER (ORDER BY (ADOPT + SWITCH_P + GROWTH)) AS DEC
    FROM scored
)
SELECT
    MDM_ID, CUST_ID, INT_HCP_ID, HCP_REG_NUM AS HCP_REG_ID,
    DEC AS DECILE, DEC AS DECILE_PROD_A, DEC AS DECILE_PROD_B,
    CASE WHEN DEC <= 2 THEN 'T1' WHEN DEC <= 4 THEN 'T2'
         WHEN DEC <= 7 THEN 'T3' WHEN DEC <= 9 THEN 'T4' ELSE 'NT' END AS TIER,
    CASE WHEN DEC <= 2 THEN 'T1' WHEN DEC <= 4 THEN 'T2'
         WHEN DEC <= 7 THEN 'T3' WHEN DEC <= 9 THEN 'T4' ELSE 'NT' END AS TIER_PROD_A,
    CASE WHEN DEC <= 2 THEN 'T1' WHEN DEC <= 4 THEN 'T2'
         WHEN DEC <= 7 THEN 'T3' WHEN DEC <= 9 THEN 'T4' ELSE 'NT' END AS TIER_PROD_B,
    CASE MOD(ABS(MOD(HASH('LS' || MDM_ID), 5)), 5)
        WHEN 0 THEN 'ADVOCATE' WHEN 1 THEN 'ADOPTER' WHEN 2 THEN 'TRIALIST'
        WHEN 3 THEN 'AWARE'    ELSE 'NAIVE'
    END AS LIFECYCLE_STAGE,
    CASE MOD(ABS(MOD(HASH('CP' || MDM_ID), 3)), 3)
        WHEN 0 THEN 'F2F' WHEN 1 THEN 'DIGITAL' ELSE 'HYBRID'
    END AS CHANNEL_PREFERENCE,
    PROP_SCORE, ADOPT AS ADOPTION_PROPENSITY, SWITCH_P AS SWITCH_PROPENSITY, GROWTH AS GROWTH_POTENTIAL,
    ROUND(UNIFORM(0.2, 0.9, RANDOM()), 4) AS DIGITAL_AFFINITY_SCORE,
    ROUND(UNIFORM(0.2, 0.8, RANDOM()), 4) AS EMAIL_RESPONSIVENESS,
    ROUND(UNIFORM(0.3, 0.9, RANDOM()), 4) AS CALL_RECEPTIVITY,
    CASE WHEN KOL_RANK_VAL >= 60 THEN 'Y' ELSE 'N' END AS IS_KOL,
    CASE WHEN UNIFORM(0, 100, RANDOM()) < 5 THEN 'Y' ELSE 'N' END AS IS_KOI,
    KOL_RANK_VAL AS KOL_RANK,
    ROUND(LEAST(1.0, KOL_RANK_VAL / 100.0 + UNIFORM(-0.05, 0.05, RANDOM())), 4) AS INFLUENCE_SCORE,
    SPEC_CD AS PRIM_SPEC_CD, SPEC_DESC AS PRIM_SPEC_DESC,
    SPEC_DESC AS SPEC_GRP_DESC, SPEC_CD AS SPECIALTY_CODE,
    '2026-03-09 10:00:00'::TIMESTAMP_NTZ AS SEGMENT_AS_OF_DT,
    'v2.3.1' AS MODEL_VERSION,
    '2026-03-09 10:00:00'::TIMESTAMP_NTZ, 'SEGMENTATION_MODEL',
    '2026-03-09 10:00:00'::TIMESTAMP_NTZ, 'SEGMENTATION_MODEL'
FROM with_propensity;

-- =============================================================================
-- TABLE 6: CALL_ACTIVITY (~1,980 rows)
-- Only eligible HCPs (RHEUM/DERM), avg 3 calls each (2-4 range)
-- Call dates: 2026-01-15 to 2026-03-09 (53-day window)
-- =============================================================================

INSERT INTO SF_SOLUTIONS.FIELD_TARGETING.CALL_ACTIVITY (
    CALL_ID, MDM_ID, CALL_DATE, CALL_STATUS, CALL_TYPE,
    TERR, FF, PROD_FAM, PROD_FAM_NAME, PHYS_SEEN,
    CALL_DURATION_MIN, DETAIL_PRIORITY
)
WITH eligible_hcps AS (
    SELECT h.MDM_ID, h.TERR_ID, h.FF_NM,
        ROW_NUMBER() OVER (ORDER BY h.MDM_ID) AS HCP_RN
    FROM SF_SOLUTIONS.FIELD_TARGETING.HCP_MASTER_PROFILE h
    WHERE h.SPEC_CD IN ('RHE', 'DER', 'RHEUM', 'DERM')
),
-- Expand each HCP to 3 calls (slots 1,2,3)
call_slots AS (
    SELECT
        h.MDM_ID, h.TERR_ID, h.FF_NM, h.HCP_RN,
        f.VALUE::INT AS SLOT
    FROM eligible_hcps h,
        LATERAL FLATTEN(ARRAY_CONSTRUCT(1, 2, 3)) f
)
SELECT
    'CALL_' || LPAD(ROW_NUMBER() OVER (ORDER BY MDM_ID, SLOT)::VARCHAR, 8, '0') AS CALL_ID,
    MDM_ID,
    DATEADD('day',
        ABS(MOD(HASH(MDM_ID || SLOT::VARCHAR), 53))::INT,
        '2026-01-15'::DATE
    ) AS CALL_DATE,
    CASE WHEN UNIFORM(0, 100, RANDOM()) < 90 THEN 'Completed' ELSE 'Planned' END AS CALL_STATUS,
    CASE MOD(ABS(MOD(HASH('CT' || MDM_ID || SLOT::VARCHAR), 10)), 10)
        WHEN 0 THEN 'Sample' WHEN 1 THEN 'Other' ELSE 'Detail'
    END AS CALL_TYPE,
    TERR_ID AS TERR,
    FF_NM AS FF,
    'ZENIXAR' AS PROD_FAM,
    'Zenixar SC' AS PROD_FAM_NAME,
    CASE WHEN UNIFORM(0, 100, RANDOM()) < 90 THEN 'Y' ELSE 'N' END AS PHYS_SEEN,
    CASE WHEN UNIFORM(0, 100, RANDOM()) < 90
        THEN UNIFORM(5, 30, RANDOM())::INT ELSE NULL END AS CALL_DURATION_MIN,
    UNIFORM(1, 3, RANDOM())::INT AS DETAIL_PRIORITY
FROM call_slots;

-- =============================================================================
-- POST-LOAD: Generate CALL_NOTES_RAW from CALL_ACTIVITY
-- =============================================================================

INSERT INTO SF_SOLUTIONS.FIELD_TARGETING.CALL_NOTES_RAW
    (MDM_ID, CALL_DATE, TERR_ID, NOTE_TEXT, TEMPLATE_DISPOSITION)
WITH hcp_calls AS (
    SELECT
        ca.MDM_ID, ca.CALL_DATE, ca.TERR AS TERR_ID,
        hcp.FULL_NM,
        ROW_NUMBER() OVER (PARTITION BY ca.MDM_ID ORDER BY ca.CALL_DATE) AS NOTE_SEQ,
        ABS(MOD(HASH(ca.MDM_ID || ca.CALL_DATE::VARCHAR), 4)) AS DISP_IDX
    FROM SF_SOLUTIONS.FIELD_TARGETING.CALL_ACTIVITY ca
    JOIN SF_SOLUTIONS.FIELD_TARGETING.HCP_MASTER_PROFILE hcp ON ca.MDM_ID = hcp.MDM_ID
    WHERE ca.CALL_STATUS = 'Completed'
),
templates AS (
    SELECT COLUMN1 AS DISP_IDX, COLUMN2 AS DISPOSITION, COLUMN3 AS TEMPLATE
    FROM VALUES
        (0, 'conversion_ready', 'Discussed Zenixar efficacy data with Dr. {NAME}. Physician expressed strong interest in switching 2-3 patients from current biologic therapy. Requested samples and starter kits.'),
        (1, 'engaged', 'Productive meeting with Dr. {NAME}. Reviewed head-to-head data vs competitor biologics. Physician is considering Zenixar for moderate-to-severe patients who have failed first-line therapy.'),
        (2, 'resistant', 'Dr. {NAME} remains satisfied with current Competitor-A therapy for most patients. Expressed concern about switching stable patients. Will continue monitoring outcomes before considering change.'),
        (3, 'neutral', 'Routine call with Dr. {NAME}. Reviewed updated dosing guidelines. Physician acknowledges Zenixar data but has limited PsO patient volume currently.')
)
SELECT
    c.MDM_ID,
    c.CALL_DATE,
    c.TERR_ID,
    REPLACE(t.TEMPLATE, '{NAME}', c.FULL_NM) AS NOTE_TEXT,
    t.DISPOSITION AS TEMPLATE_DISPOSITION
FROM hcp_calls c
JOIN templates t ON c.DISP_IDX = t.DISP_IDX
WHERE c.NOTE_SEQ <= 3;

-- =============================================================================
-- POST-LOAD: Generate CALL_NOTES_ENRICHED from CALL_NOTES_RAW
-- =============================================================================

INSERT INTO SF_SOLUTIONS.FIELD_TARGETING.CALL_NOTES_ENRICHED
    (MDM_ID, CALL_DATE, TERR_ID, NOTE_TEXT, SENTIMENT_SCORE, DISPOSITION, KEY_SIGNALS)
SELECT
    MDM_ID, CALL_DATE, TERR_ID, NOTE_TEXT,
    CASE TEMPLATE_DISPOSITION
        WHEN 'conversion_ready' THEN ROUND(0.75 + (ABS(MOD(HASH(MDM_ID || CALL_DATE::VARCHAR), 20)) / 100.0), 3)
        WHEN 'engaged'          THEN ROUND(0.40 + (ABS(MOD(HASH(MDM_ID || CALL_DATE::VARCHAR), 25)) / 100.0), 3)
        WHEN 'resistant'        THEN ROUND(-0.30 - (ABS(MOD(HASH(MDM_ID || CALL_DATE::VARCHAR), 20)) / 100.0), 3)
        ELSE                         ROUND(0.05 + (ABS(MOD(HASH(MDM_ID || CALL_DATE::VARCHAR), 15)) / 100.0), 3)
    END AS SENTIMENT_SCORE,
    TEMPLATE_DISPOSITION AS DISPOSITION,
    CASE TEMPLATE_DISPOSITION
        WHEN 'conversion_ready' THEN PARSE_JSON('{"conversion_likelihood":"high","objections":null,"next_steps":["Send samples","Schedule follow-up"]}')
        WHEN 'engaged'          THEN PARSE_JSON('{"conversion_likelihood":"medium","objections":["Wants more data"],"next_steps":["Share clinical papers","Invite to speaker program"]}')
        WHEN 'resistant'        THEN PARSE_JSON('{"conversion_likelihood":"low","objections":["Satisfied with current therapy"],"next_steps":["Monitor","Maintain relationship"]}')
        ELSE                         PARSE_JSON('{"conversion_likelihood":"low","objections":null,"next_steps":["Follow up next quarter"]}')
    END AS KEY_SIGNALS
FROM SF_SOLUTIONS.FIELD_TARGETING.CALL_NOTES_RAW;

-- =============================================================================
-- POST-LOAD: Generate CALL_MATERIAL_USAGE from CALL_ACTIVITY
-- =============================================================================

INSERT INTO SF_SOLUTIONS.FIELD_TARGETING.CALL_MATERIAL_USAGE
    (CALL_ID, MDM_ID, MATERIAL_ID, USAGE_TYPE, REACTION, TERR_ID, CALL_DATE, REP_ID)
WITH sampled_calls AS (
    SELECT
        ca.CALL_ID, ca.MDM_ID, ca.TERR AS TERR_ID, ca.CALL_DATE,
        sr.EMP_ID AS REP_ID,
        ABS(MOD(HASH(ca.CALL_ID), 100)) AS HASH_VAL,
        CASE
            WHEN ABS(MOD(HASH(ca.CALL_ID || 'cnt'), 100)) < 50 THEN 1
            WHEN ABS(MOD(HASH(ca.CALL_ID || 'cnt'), 100)) < 85 THEN 2
            ELSE 3
        END AS MAT_COUNT
    FROM SF_SOLUTIONS.FIELD_TARGETING.CALL_ACTIVITY ca
    LEFT JOIN SF_SOLUTIONS.FIELD_TARGETING.REP_TERRITORY_DIM rr ON ca.TERR = rr.TERR_ID
    LEFT JOIN SF_SOLUTIONS.FIELD_TARGETING.SALES_REPS sr ON rr.EMP_ID = sr.EMP_ID
    WHERE ABS(MOD(HASH(ca.CALL_ID), 100)) < 18
),
expanded AS (
    SELECT
        sc.CALL_ID, sc.MDM_ID, sc.TERR_ID, sc.CALL_DATE, sc.REP_ID,
        f.VALUE::INT AS SLOT,
        ABS(MOD(HASH(sc.CALL_ID || f.VALUE::VARCHAR), 1000)) AS SLOT_HASH
    FROM sampled_calls sc,
        LATERAL FLATTEN(ARRAY_CONSTRUCT(1, 2, 3)) f
    WHERE f.VALUE::INT <= sc.MAT_COUNT
),
material_assigned AS (
    SELECT *,
        CASE
            WHEN SLOT = 1 THEN
                CASE
                    WHEN SLOT_HASH < 100 THEN 'MAT_001' WHEN SLOT_HASH < 200 THEN 'MAT_002'
                    WHEN SLOT_HASH < 280 THEN 'MAT_003' WHEN SLOT_HASH < 350 THEN 'MAT_004'
                    WHEN SLOT_HASH < 400 THEN 'MAT_024' WHEN SLOT_HASH < 480 THEN 'MAT_005'
                    WHEN SLOT_HASH < 550 THEN 'MAT_006' WHEN SLOT_HASH < 620 THEN 'MAT_007'
                    WHEN SLOT_HASH < 700 THEN 'MAT_008' WHEN SLOT_HASH < 740 THEN 'MAT_009'
                    WHEN SLOT_HASH < 790 THEN 'MAT_018' WHEN SLOT_HASH < 830 THEN 'MAT_019'
                    WHEN SLOT_HASH < 870 THEN 'MAT_013' WHEN SLOT_HASH < 910 THEN 'MAT_014'
                    WHEN SLOT_HASH < 950 THEN 'MAT_015' ELSE 'MAT_022'
                END
            WHEN SLOT = 2 THEN
                CASE
                    WHEN SLOT_HASH < 150 THEN 'MAT_005' WHEN SLOT_HASH < 300 THEN 'MAT_006'
                    WHEN SLOT_HASH < 430 THEN 'MAT_007' WHEN SLOT_HASH < 540 THEN 'MAT_011'
                    WHEN SLOT_HASH < 640 THEN 'MAT_012' WHEN SLOT_HASH < 730 THEN 'MAT_008'
                    WHEN SLOT_HASH < 820 THEN 'MAT_009' WHEN SLOT_HASH < 900 THEN 'MAT_019'
                    ELSE 'MAT_021'
                END
            ELSE
                CASE
                    WHEN SLOT_HASH < 300 THEN 'MAT_013' WHEN SLOT_HASH < 550 THEN 'MAT_014'
                    WHEN SLOT_HASH < 750 THEN 'MAT_011' ELSE 'MAT_012'
                END
        END AS MATERIAL_ID
    FROM expanded
)
SELECT
    CALL_ID, MDM_ID,
    MATERIAL_ID,
    CASE
        WHEN MATERIAL_ID IN ('MAT_013', 'MAT_014') THEN 'Sampled'
        WHEN MATERIAL_ID IN ('MAT_005','MAT_006','MAT_007','MAT_008','MAT_009','MAT_011','MAT_012','MAT_023') THEN 'Left-Behind'
        WHEN MATERIAL_ID IN ('MAT_018','MAT_019','MAT_020','MAT_021','MAT_022') THEN
            CASE WHEN SLOT_HASH < 600 THEN 'Presented' ELSE 'E-Sent' END
        ELSE 'Presented'
    END AS USAGE_TYPE,
    CASE
        WHEN ABS(MOD(HASH(CALL_ID || MATERIAL_ID || 'rxn'), 100)) < 35 THEN 'Positive'
        WHEN ABS(MOD(HASH(CALL_ID || MATERIAL_ID || 'rxn'), 100)) < 75 THEN 'Neutral'
        WHEN ABS(MOD(HASH(CALL_ID || MATERIAL_ID || 'rxn'), 100)) < 85 THEN 'Negative'
        ELSE 'Not Observed'
    END AS REACTION,
    TERR_ID, CALL_DATE, REP_ID
FROM material_assigned;

-- Backfill CALL_ACTIVITY.MATERIAL_CD
UPDATE SF_SOLUTIONS.FIELD_TARGETING.CALL_ACTIVITY ca
SET ca.MATERIAL_CD = mat_list.MATERIAL_NAMES
FROM (
    SELECT cmu.CALL_ID,
        LISTAGG(DISTINCT pmc.MATERIAL_NAME, ', ') WITHIN GROUP (ORDER BY pmc.MATERIAL_NAME) AS MATERIAL_NAMES
    FROM SF_SOLUTIONS.FIELD_TARGETING.CALL_MATERIAL_USAGE cmu
    INNER JOIN SF_SOLUTIONS.FIELD_TARGETING.PROMO_MATERIALS_CATALOG pmc ON cmu.MATERIAL_ID = pmc.MATERIAL_ID
    GROUP BY cmu.CALL_ID
) mat_list
WHERE ca.CALL_ID = mat_list.CALL_ID;
