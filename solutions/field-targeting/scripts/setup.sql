-- =============================================================================
-- Solution: HCLS Field Targeting Platform
-- Industry: Healthcare & Life Sciences
-- Database: SF_SOLUTIONS
-- Schema:   FIELD_TARGETING
--
-- Pharmaceutical HCP field targeting platform demonstrating Cortex AI
-- (COMPLETE, SENTIMENT, CLASSIFY_TEXT), Semantic View, and a Streamlit
-- what-if scenario dashboard for rules-engine-based call planning.
-- =============================================================================

USE ROLE ACCOUNTADMIN;

-- Shared infrastructure (idempotent)
CREATE DATABASE IF NOT EXISTS SF_SOLUTIONS;
CREATE WAREHOUSE IF NOT EXISTS SF_SOLUTIONS_WH
    WITH WAREHOUSE_SIZE = 'LARGE'
    AUTO_SUSPEND = 300
    AUTO_RESUME = TRUE;

USE DATABASE SF_SOLUTIONS;
USE WAREHOUSE SF_SOLUTIONS_WH;

CREATE SCHEMA IF NOT EXISTS FIELD_TARGETING;
USE SCHEMA SF_SOLUTIONS.FIELD_TARGETING;

-- =============================================================================
-- SECTION 1: Source Tables (DDL)
-- =============================================================================

-- 1. HCP_MASTER_PROFILE
CREATE OR REPLACE TABLE SF_SOLUTIONS.FIELD_TARGETING.HCP_MASTER_PROFILE (
    MDM_ID              VARCHAR,
    CUST_ID             VARCHAR,
    INT_HCP_ID          VARCHAR,
    HCP_REG_NUM         VARCHAR,
    EXT_DATA_ID         VARCHAR,
    MED_ASSOC_NUM       VARCHAR,
    CTRL_LICENSE_NUM    VARCHAR,
    FRST_NM             VARCHAR,
    LAST_NM             VARCHAR,
    MDL_NM              VARCHAR,
    FULL_NM             VARCHAR,
    NM_SFFX             VARCHAR,
    DEG_TITLE           VARCHAR,
    SPEC_CD             VARCHAR,
    SPEC_DESC           VARCHAR,
    SPEC_GRP_CD         VARCHAR,
    SPEC_GRP_DESC       VARCHAR,
    PRIMARY_SPECIALTY   VARCHAR,
    ADDR_ID             VARCHAR,
    ADDR_LINE_1         VARCHAR,
    ADDR_LINE_2         VARCHAR,
    ADDR_LINE_3         VARCHAR,
    ADDR_SRC            VARCHAR,
    ADDR_RANK           NUMBER,
    ADDR_TERR_CNT       NUMBER,
    IS_PO_ADDR_TYP      VARCHAR,
    VLD_ADDR_PRIORITY   NUMBER,
    CITY                VARCHAR,
    STATE               VARCHAR,
    ZIP_CD              VARCHAR,
    TELEPHONE_NUM       VARCHAR,
    VALID_ADDR_IND      VARCHAR,
    NO_MKT              VARCHAR,
    OPT_OUT             VARCHAR,
    BSNS_STAT           VARCHAR,
    INST_FF_FLAG        VARCHAR,
    TERR_ID             VARCHAR,
    TERR                VARCHAR,
    FF_ID               VARCHAR,
    FF_NUM              VARCHAR,
    FF_NM               VARCHAR,
    LAST_CALLED_DT      TIMESTAMP_NTZ,
    MDM_LAST_MOD_DT     TIMESTAMP_NTZ,
    SRC_LAST_MOD_DT     TIMESTAMP_NTZ,
    DATA_PERIOD         TIMESTAMP_NTZ,
    VERSION_ID          NUMBER,
    AUDIT_BATCH_ID      VARCHAR,
    AUDIT_INSRT_DT      TIMESTAMP_NTZ,
    AUDIT_INSRT_NM      VARCHAR,
    AUDIT_UPDT_DT       TIMESTAMP_NTZ,
    AUDIT_UPDT_NM       VARCHAR
);

-- 2. HCP_SUPPRESSION_FLAGS
CREATE OR REPLACE TABLE SF_SOLUTIONS.FIELD_TARGETING.HCP_SUPPRESSION_FLAGS (
    MDM_ID              VARCHAR,
    IS_DEBARRED         VARCHAR,
    IS_SANCTIONED       VARCHAR,
    GLOBAL_SUPPRESS_FLG VARCHAR,
    CALL_SUPPRESS_FLG   VARCHAR,
    EMAIL_SUPPRESS_FLG  VARCHAR,
    DIGITAL_SUPPRESS_FLG VARCHAR,
    SAMPLE_SUPPRESS_FLG VARCHAR,
    SPEAKER_SUPPRESS_FLG VARCHAR
);

-- 3. BRAND_EXCLUSION_LIST
CREATE OR REPLACE TABLE SF_SOLUTIONS.FIELD_TARGETING.BRAND_EXCLUSION_LIST (
    CONSTRAINT_ID    NUMBER AUTOINCREMENT,
    MDM_ID           VARCHAR,
    EXCLUSION_REASON VARCHAR,
    IS_ACTIVE        VARCHAR,
    EFFECTIVE_DATE   TIMESTAMP_NTZ,
    EXPIRY_DATE      TIMESTAMP_NTZ
);

-- 4. RX_WEEKLY_HCP
CREATE OR REPLACE TABLE SF_SOLUTIONS.FIELD_TARGETING.RX_WEEKLY_HCP (
    MDM_ID  VARCHAR,
    PRODUCT VARCHAR,
    METRIC  VARCHAR,
    RX      FLOAT,
    WEEK_ID DATE,
    GEO_ID  VARCHAR,
    GEO_DESC VARCHAR
);

-- 5. HCP_MICROSEGMENT
CREATE OR REPLACE TABLE SF_SOLUTIONS.FIELD_TARGETING.HCP_MICROSEGMENT (
    MDM_ID                  VARCHAR,
    CUST_ID                 VARCHAR,
    INT_HCP_ID              VARCHAR,
    HCP_REG_ID              VARCHAR,
    PROD_CD                 VARCHAR,
    PROD_NM                 VARCHAR,
    MICROSEGMENT            VARCHAR,
    MICROSEGMENT_CD         VARCHAR,
    DECILE                  NUMBER,
    DECILE_PROD_A           NUMBER,
    DECILE_PROD_B           NUMBER,
    TIER                    VARCHAR,
    TIER_PROD_A             VARCHAR,
    TIER_PROD_B             VARCHAR,
    LIFECYCLE_STAGE         VARCHAR,
    LIFECYCLE_PROD_A        VARCHAR,
    LIFECYCLE_PROD_B        VARCHAR,
    PROPENSITY_SCORE        FLOAT,
    PROPENSITY_PROD_A       FLOAT,
    PROPENSITY_PROD_B       FLOAT,
    ADOPTION_PROPENSITY     FLOAT,
    SWITCH_PROPENSITY       FLOAT,
    GROWTH_POTENTIAL        FLOAT,
    CHANNEL_PREFERENCE      VARCHAR,
    DIGITAL_AFFINITY_SCORE  FLOAT,
    EMAIL_RESPONSIVENESS    FLOAT,
    CALL_RECEPTIVITY        FLOAT,
    IS_KOL                  VARCHAR,
    IS_KOI                  VARCHAR,
    INFLUENCE_SCORE         FLOAT,
    PRIM_SPEC_CD            VARCHAR,
    PRIM_SPEC_DESC          VARCHAR,
    SPEC_GRP_DESC           VARCHAR,
    SPECIALTY_CODE          VARCHAR,
    SEGMENT_AS_OF_DT        TIMESTAMP_NTZ,
    MODEL_VERSION           VARCHAR,
    KOL_RANK                NUMBER,
    AUDIT_BATCH_ID          VARCHAR,
    AUDIT_INSRT_DT          TIMESTAMP_NTZ,
    AUDIT_INSRT_NM          VARCHAR,
    AUDIT_UPDT_DT           TIMESTAMP_NTZ,
    AUDIT_UPDT_NM           VARCHAR
);

-- 6. CALL_ACTIVITY
CREATE OR REPLACE TABLE SF_SOLUTIONS.FIELD_TARGETING.CALL_ACTIVITY (
    ACCOUNT_DEPT    VARCHAR,
    ACCTID          VARCHAR,
    ACCT_MDM_ID     VARCHAR,
    ACCT_NAME       VARCHAR,
    ADDR_LINE_1     VARCHAR,
    ADDR_LINE_2     VARCHAR,
    ADJ_SYNC_DATE   TIMESTAMP_NTZ,
    ADMIN_SEEN      VARCHAR,
    CALL_DATE       DATE,
    CALL_FOCUS      VARCHAR,
    CALL_ID         VARCHAR,
    CALL_METHOD     VARCHAR,
    CALL_NAME       VARCHAR,
    CALL_STATUS     VARCHAR,
    CALL_SUBTYPE    VARCHAR,
    CALL_TYPE       VARCHAR,
    CITY            VARCHAR,
    CREATED_DATE    TIMESTAMP_NTZ,
    EVENT_TYPE      VARCHAR,
    FELLOW_SEEN     VARCHAR,
    FF              VARCHAR,
    FOCUS           VARCHAR,
    INDICATION      VARCHAR,
    INTERN_SEEN     VARCHAR,
    IS_EVENT        VARCHAR,
    LAST_SYNC_DATE  TIMESTAMP_NTZ,
    LAST_UPD_DATE   TIMESTAMP_NTZ,
    MAX_ATTENDEE    NUMBER,
    MDM_CUST_TYPE   VARCHAR,
    MDM_ID          VARCHAR,
    INT_HCP_ID      VARCHAR,
    INT_LOC_ID      VARCHAR,
    HCP_REG_ID      VARCHAR,
    NP_SEEN         VARCHAR,
    NURSE_SEEN      VARCHAR,
    ORG_ACCTID      VARCHAR,
    ORIG_TERR       VARCHAR,
    OTHER_SEEN      VARCHAR,
    OWNER_TERRITORY VARCHAR,
    PARENT_CALL_ID  VARCHAR,
    PA_SEEN         VARCHAR,
    PHARMACIST_SEEN VARCHAR,
    PHYS_SEEN       VARCHAR,
    PRIORITY        VARCHAR,
    PROD_FAM        VARCHAR,
    PROD_FAM_NAME   VARCHAR,
    PROD_TYPE       VARCHAR,
    PROF_FIRST_NAME VARCHAR,
    PROF_LAST_NAME  VARCHAR,
    MATERIAL_CD     VARCHAR,
    SAMPLE_PROD_CD  VARCHAR,
    SAMPLE_PROD_NM  VARCHAR,
    RECORD_TYPE     VARCHAR,
    REPID           VARCHAR,
    RESIDENT_SEEN   VARCHAR,
    SEQNUM          NUMBER,
    SRCE_SYS_SKEY   VARCHAR,
    STAFF_SEEN      VARCHAR,
    STATE           VARCHAR,
    SYNC_CREATE_DATE TIMESTAMP_NTZ,
    SYNC_STATUS     VARCHAR,
    TERR            VARCHAR,
    TERR_PRIOR_RR   VARCHAR,
    ZIP             VARCHAR
);

-- =============================================================================
-- SECTION 2: Reference Tables (DDL + Seed Data)
-- =============================================================================

-- RESPONSE_CURVE (40 rows)
CREATE OR REPLACE TABLE SF_SOLUTIONS.FIELD_TARGETING.RESPONSE_CURVE (
    TIER           VARCHAR(4)  NOT NULL,
    PRODUCT_FAMILY VARCHAR(50) NOT NULL,
    CALLS          NUMBER      NOT NULL,
    RX             FLOAT       NOT NULL
);

INSERT INTO SF_SOLUTIONS.FIELD_TARGETING.RESPONSE_CURVE (TIER, PRODUCT_FAMILY, CALLS, RX)
VALUES
    ('T1', 'ZENIXAR SC', 0, 0.0), ('T1', 'ZENIXAR SC', 1, 2.5),
    ('T1', 'ZENIXAR SC', 2, 4.2), ('T1', 'ZENIXAR SC', 3, 5.5),
    ('T2', 'ZENIXAR SC', 0, 0.0), ('T2', 'ZENIXAR SC', 1, 1.8),
    ('T2', 'ZENIXAR SC', 2, 3.0), ('T2', 'ZENIXAR SC', 3, 3.8),
    ('T3', 'ZENIXAR SC', 0, 0.0), ('T3', 'ZENIXAR SC', 1, 1.2),
    ('T3', 'ZENIXAR SC', 2, 1.9), ('T3', 'ZENIXAR SC', 3, 2.3),
    ('T4', 'ZENIXAR SC', 0, 0.0), ('T4', 'ZENIXAR SC', 1, 0.6),
    ('T4', 'ZENIXAR SC', 2, 0.9), ('T4', 'ZENIXAR SC', 3, 1.1),
    ('NT', 'ZENIXAR SC', 0, 0.0), ('NT', 'ZENIXAR SC', 1, 0.2),
    ('NT', 'ZENIXAR SC', 2, 0.3), ('NT', 'ZENIXAR SC', 3, 0.4),
    ('T1', 'ZENIXAR', 0, 0.0),    ('T1', 'ZENIXAR', 1, 2.625),
    ('T1', 'ZENIXAR', 2, 4.41),   ('T1', 'ZENIXAR', 3, 5.775),
    ('T2', 'ZENIXAR', 0, 0.0),    ('T2', 'ZENIXAR', 1, 1.89),
    ('T2', 'ZENIXAR', 2, 3.15),   ('T2', 'ZENIXAR', 3, 3.99),
    ('T3', 'ZENIXAR', 0, 0.0),    ('T3', 'ZENIXAR', 1, 1.26),
    ('T3', 'ZENIXAR', 2, 1.995),  ('T3', 'ZENIXAR', 3, 2.415),
    ('T4', 'ZENIXAR', 0, 0.0),    ('T4', 'ZENIXAR', 1, 0.63),
    ('T4', 'ZENIXAR', 2, 0.945),  ('T4', 'ZENIXAR', 3, 1.155),
    ('NT', 'ZENIXAR', 0, 0.0),    ('NT', 'ZENIXAR', 1, 0.21),
    ('NT', 'ZENIXAR', 2, 0.315),  ('NT', 'ZENIXAR', 3, 0.42);

-- TERRITORY_DIM (50 rows)
CREATE OR REPLACE TABLE SF_SOLUTIONS.FIELD_TARGETING.TERRITORY_DIM (
    TERR_ID        VARCHAR(20)  NOT NULL,
    TERR_NM        VARCHAR(100) NOT NULL,
    REGN           VARCHAR(20)  NOT NULL,
    BASE_CITY      VARCHAR(50)  NOT NULL,
    BASE_STATE     VARCHAR(2)   NOT NULL,
    IS_ACTIVE      VARCHAR(1)   DEFAULT 'Y',
    PARENT_TERR_ID VARCHAR(20)  NOT NULL
);

INSERT INTO SF_SOLUTIONS.FIELD_TARGETING.TERRITORY_DIM
    (TERR_ID, TERR_NM, REGN, BASE_CITY, BASE_STATE, IS_ACTIVE, PARENT_TERR_ID)
VALUES
    ('NY-NYC-001', 'New York Metro North',    'NORTHEAST', 'New York',      'NY', 'Y', 'DIST-NE-01'),
    ('NY-NYC-002', 'New York Metro South',    'NORTHEAST', 'New York',      'NY', 'Y', 'DIST-NE-01'),
    ('NJ-NWK-001', 'Northern New Jersey',     'NORTHEAST', 'Newark',        'NJ', 'Y', 'DIST-NE-01'),
    ('CT-HRT-001', 'Hartford Metro',          'NORTHEAST', 'Hartford',      'CT', 'Y', 'DIST-NE-01'),
    ('NY-ALB-001', 'Albany Capital Region',   'NORTHEAST', 'Albany',        'NY', 'Y', 'DIST-NE-01'),
    ('MA-BOS-001', 'Greater Boston',          'NORTHEAST', 'Boston',        'MA', 'Y', 'DIST-NE-02'),
    ('MA-BOS-002', 'Boston South Shore',      'NORTHEAST', 'Boston',        'MA', 'Y', 'DIST-NE-02'),
    ('PA-PHL-001', 'Philadelphia Metro',      'NORTHEAST', 'Philadelphia',  'PA', 'Y', 'DIST-NE-02'),
    ('PA-PHL-002', 'Philadelphia Suburbs',    'NORTHEAST', 'Philadelphia',  'PA', 'Y', 'DIST-NE-02'),
    ('RI-PVD-001', 'Providence Metro',        'NORTHEAST', 'Providence',    'RI', 'Y', 'DIST-NE-02'),
    ('FL-MIA-001', 'Miami Dade',              'SOUTHEAST', 'Miami',         'FL', 'Y', 'DIST-SE-01'),
    ('FL-MIA-002', 'Fort Lauderdale',         'SOUTHEAST', 'Fort Lauderdale', 'FL', 'Y', 'DIST-SE-01'),
    ('FL-ORL-001', 'Orlando Metro',           'SOUTHEAST', 'Orlando',       'FL', 'Y', 'DIST-SE-01'),
    ('FL-TPA-001', 'Tampa Bay',               'SOUTHEAST', 'Tampa',         'FL', 'Y', 'DIST-SE-01'),
    ('FL-JAX-001', 'Jacksonville Metro',      'SOUTHEAST', 'Jacksonville',  'FL', 'Y', 'DIST-SE-01'),
    ('GA-ATL-001', 'Atlanta Metro North',     'SOUTHEAST', 'Atlanta',       'GA', 'Y', 'DIST-SE-02'),
    ('GA-ATL-002', 'Atlanta Metro South',     'SOUTHEAST', 'Atlanta',       'GA', 'Y', 'DIST-SE-02'),
    ('NC-CLT-001', 'Charlotte Metro',         'SOUTHEAST', 'Charlotte',     'NC', 'Y', 'DIST-SE-02'),
    ('NC-RDU-001', 'Raleigh-Durham',          'SOUTHEAST', 'Raleigh',       'NC', 'Y', 'DIST-SE-02'),
    ('VA-RIC-001', 'Richmond Metro',          'SOUTHEAST', 'Richmond',      'VA', 'Y', 'DIST-SE-02'),
    ('IL-CHI-001', 'Chicago North',           'MIDWEST',   'Chicago',       'IL', 'Y', 'DIST-MW-01'),
    ('IL-CHI-002', 'Chicago West Suburbs',    'MIDWEST',   'Chicago',       'IL', 'Y', 'DIST-MW-01'),
    ('OH-CLE-001', 'Cleveland Metro',         'MIDWEST',   'Cleveland',     'OH', 'Y', 'DIST-MW-01'),
    ('OH-COL-001', 'Columbus Metro',          'MIDWEST',   'Columbus',      'OH', 'Y', 'DIST-MW-01'),
    ('MI-DET-001', 'Detroit Metro',           'MIDWEST',   'Detroit',       'MI', 'Y', 'DIST-MW-01'),
    ('MN-MSP-001', 'Minneapolis-St Paul',     'MIDWEST',   'Minneapolis',   'MN', 'Y', 'DIST-MW-02'),
    ('WI-MKE-001', 'Milwaukee Metro',         'MIDWEST',   'Milwaukee',     'WI', 'Y', 'DIST-MW-02'),
    ('IN-IND-001', 'Indianapolis Metro',      'MIDWEST',   'Indianapolis',  'IN', 'Y', 'DIST-MW-02'),
    ('MO-STL-001', 'St Louis Metro',          'MIDWEST',   'St Louis',      'MO', 'Y', 'DIST-MW-02'),
    ('MO-KCI-001', 'Kansas City Metro',       'MIDWEST',   'Kansas City',   'MO', 'Y', 'DIST-MW-02'),
    ('CA-LAX-001', 'Los Angeles Metro',       'WEST',      'Los Angeles',   'CA', 'Y', 'DIST-WE-01'),
    ('CA-LAX-002', 'Orange County',           'WEST',      'Irvine',        'CA', 'Y', 'DIST-WE-01'),
    ('CA-SFO-001', 'San Francisco Bay',       'WEST',      'San Francisco', 'CA', 'Y', 'DIST-WE-01'),
    ('CA-SDG-001', 'San Diego Metro',         'WEST',      'San Diego',     'CA', 'Y', 'DIST-WE-01'),
    ('WA-SEA-001', 'Seattle Metro',           'WEST',      'Seattle',       'WA', 'Y', 'DIST-WE-01'),
    ('AZ-PHX-001', 'Phoenix Metro',           'WEST',      'Phoenix',       'AZ', 'Y', 'DIST-WE-02'),
    ('CO-DEN-001', 'Denver Metro',            'WEST',      'Denver',        'CO', 'Y', 'DIST-WE-02'),
    ('OR-PDX-001', 'Portland Metro',          'WEST',      'Portland',      'OR', 'Y', 'DIST-WE-02'),
    ('NV-LAS-001', 'Las Vegas Metro',         'WEST',      'Las Vegas',     'NV', 'Y', 'DIST-WE-02'),
    ('UT-SLC-001', 'Salt Lake City Metro',    'WEST',      'Salt Lake City', 'UT', 'Y', 'DIST-WE-02'),
    ('TX-HOU-001', 'Houston Metro',           'SOUTH',     'Houston',       'TX', 'Y', 'DIST-SO-01'),
    ('TX-DAL-001', 'Dallas-Fort Worth',       'SOUTH',     'Dallas',        'TX', 'Y', 'DIST-SO-01'),
    ('TX-SAT-001', 'San Antonio Metro',       'SOUTH',     'San Antonio',   'TX', 'Y', 'DIST-SO-01'),
    ('TX-AUS-001', 'Austin Metro',            'SOUTH',     'Austin',        'TX', 'Y', 'DIST-SO-01'),
    ('LA-NOR-001', 'New Orleans Metro',       'SOUTH',     'New Orleans',   'LA', 'Y', 'DIST-SO-01'),
    ('LA-NOR-002', 'Baton Rouge Metro',       'SOUTH',     'Baton Rouge',   'LA', 'Y', 'DIST-SO-02'),
    ('TN-NSH-001', 'Nashville Metro',         'SOUTH',     'Nashville',     'TN', 'Y', 'DIST-SO-02'),
    ('TN-MEM-001', 'Memphis Metro',           'SOUTH',     'Memphis',       'TN', 'Y', 'DIST-SO-02'),
    ('AL-BHM-001', 'Birmingham Metro',        'SOUTH',     'Birmingham',    'AL', 'Y', 'DIST-SO-02'),
    ('OK-OKC-001', 'Oklahoma City Metro',     'SOUTH',     'Oklahoma City', 'OK', 'Y', 'DIST-SO-02');

-- SALES_REPS (50 rows)
CREATE OR REPLACE TABLE SF_SOLUTIONS.FIELD_TARGETING.SALES_REPS (
    EMP_ID         VARCHAR(10)  NOT NULL,
    TERR_ID        VARCHAR(20)  NOT NULL,
    FRST_NM        VARCHAR(50)  NOT NULL,
    LAST_NM        VARCHAR(50)  NOT NULL,
    CURR_TITL      VARCHAR(50)  NOT NULL,
    PARENT_TERR_ID VARCHAR(20)  NOT NULL,
    BASE_STT       VARCHAR(2)   NOT NULL,
    IS_ACTIVE      VARCHAR(1)   DEFAULT 'Y',
    HIRE_DT        DATE         NOT NULL
);

INSERT INTO SF_SOLUTIONS.FIELD_TARGETING.SALES_REPS
    (EMP_ID, TERR_ID, FRST_NM, LAST_NM, CURR_TITL, PARENT_TERR_ID, BASE_STT, IS_ACTIVE, HIRE_DT)
VALUES
    ('EMP_001', 'NY-NYC-001', 'Michael',    'Torres',      'Senior Territory Manager',    'DIST-NE-01', 'NY', 'Y', '2020-03-15'),
    ('EMP_002', 'NY-NYC-002', 'Sarah',      'Chen',        'Territory Manager',           'DIST-NE-01', 'NY', 'Y', '2021-06-01'),
    ('EMP_003', 'NJ-NWK-001', 'David',      'Patel',       'Territory Manager',           'DIST-NE-01', 'NJ', 'Y', '2022-01-10'),
    ('EMP_004', 'CT-HRT-001', 'Jennifer',   'Walsh',       'Associate Territory Manager', 'DIST-NE-01', 'CT', 'Y', '2024-02-19'),
    ('EMP_005', 'NY-ALB-001', 'Robert',     'Kim',         'Territory Manager',           'DIST-NE-01', 'NY', 'Y', '2021-09-07'),
    ('EMP_006', 'MA-BOS-001', 'Amanda',     'Rodriguez',   'Senior Territory Manager',    'DIST-NE-02', 'MA', 'Y', '2020-01-06'),
    ('EMP_007', 'MA-BOS-002', 'James',      'O''Brien',    'Territory Manager',           'DIST-NE-02', 'MA', 'Y', '2022-04-18'),
    ('EMP_008', 'PA-PHL-001', 'Lisa',       'Thompson',    'Senior Territory Manager',    'DIST-NE-02', 'PA', 'Y', '2020-05-11'),
    ('EMP_009', 'PA-PHL-002', 'Christopher','Lee',         'Territory Manager',           'DIST-NE-02', 'PA', 'Y', '2023-03-27'),
    ('EMP_010', 'RI-PVD-001', 'Michelle',   'Garcia',      'Associate Territory Manager', 'DIST-NE-02', 'RI', 'Y', '2024-08-12'),
    ('EMP_011', 'FL-MIA-001', 'Daniel',     'Martinez',    'Senior Territory Manager',    'DIST-SE-01', 'FL', 'Y', '2020-02-24'),
    ('EMP_012', 'FL-MIA-002', 'Katherine',  'Scott',       'Territory Manager',           'DIST-SE-01', 'FL', 'Y', '2021-11-15'),
    ('EMP_013', 'FL-ORL-001', 'Andrew',     'Johnson',     'Territory Manager',           'DIST-SE-01', 'FL', 'Y', '2022-07-03'),
    ('EMP_014', 'FL-TPA-001', 'Nicole',     'Williams',    'Territory Manager',           'DIST-SE-01', 'FL', 'Y', '2023-01-09'),
    ('EMP_015', 'FL-JAX-001', 'Ryan',       'Campbell',    'Associate Territory Manager', 'DIST-SE-01', 'FL', 'Y', '2024-05-20'),
    ('EMP_016', 'GA-ATL-001', 'Stephanie',  'Brown',       'Senior Territory Manager',    'DIST-SE-02', 'GA', 'Y', '2020-04-13'),
    ('EMP_017', 'GA-ATL-002', 'Brian',      'Davis',       'Territory Manager',           'DIST-SE-02', 'GA', 'Y', '2021-08-22'),
    ('EMP_018', 'NC-CLT-001', 'Rachel',     'Adams',       'Territory Manager',           'DIST-SE-02', 'NC', 'Y', '2022-10-30'),
    ('EMP_019', 'NC-RDU-001', 'Matthew',    'Wilson',      'Territory Manager',           'DIST-SE-02', 'NC', 'Y', '2023-06-14'),
    ('EMP_020', 'VA-RIC-001', 'Emily',      'Nguyen',      'Associate Territory Manager', 'DIST-SE-02', 'VA', 'Y', '2025-01-06'),
    ('EMP_021', 'IL-CHI-001', 'Kevin',      'Murphy',      'Senior Territory Manager',    'DIST-MW-01', 'IL', 'Y', '2020-06-08'),
    ('EMP_022', 'IL-CHI-002', 'Laura',      'Peterson',    'Territory Manager',           'DIST-MW-01', 'IL', 'Y', '2021-12-01'),
    ('EMP_023', 'OH-CLE-001', 'Jason',      'Taylor',      'Territory Manager',           'DIST-MW-01', 'OH', 'Y', '2022-03-21'),
    ('EMP_024', 'OH-COL-001', 'Megan',      'Anderson',    'Territory Manager',           'DIST-MW-01', 'OH', 'Y', '2023-09-04'),
    ('EMP_025', 'MI-DET-001', 'Patrick',    'Sullivan',    'Associate Territory Manager', 'DIST-MW-01', 'MI', 'Y', '2024-11-18'),
    ('EMP_026', 'MN-MSP-001', 'Christina',  'Larsen',      'Senior Territory Manager',    'DIST-MW-02', 'MN', 'Y', '2020-07-27'),
    ('EMP_027', 'WI-MKE-001', 'Jonathan',   'Brooks',      'Territory Manager',           'DIST-MW-02', 'WI', 'Y', '2021-04-05'),
    ('EMP_028', 'IN-IND-001', 'Samantha',   'Clark',       'Territory Manager',           'DIST-MW-02', 'IN', 'Y', '2022-08-16'),
    ('EMP_029', 'MO-STL-001', 'Tyler',      'Morgan',      'Territory Manager',           'DIST-MW-02', 'MO', 'Y', '2023-02-28'),
    ('EMP_030', 'MO-KCI-001', 'Allison',    'Harper',      'Associate Territory Manager', 'DIST-MW-02', 'MO', 'Y', '2024-06-10'),
    ('EMP_031', 'CA-LAX-001', 'Derek',      'Ramirez',     'Senior Territory Manager',    'DIST-WE-01', 'CA', 'Y', '2020-08-19'),
    ('EMP_032', 'CA-LAX-002', 'Victoria',   'Chang',       'Territory Manager',           'DIST-WE-01', 'CA', 'Y', '2021-02-14'),
    ('EMP_033', 'CA-SFO-001', 'Nathan',     'Goldstein',   'Senior Territory Manager',    'DIST-WE-01', 'CA', 'Y', '2020-10-05'),
    ('EMP_034', 'CA-SDG-001', 'Heather',    'Nakamura',    'Territory Manager',           'DIST-WE-01', 'CA', 'Y', '2022-05-23'),
    ('EMP_035', 'WA-SEA-001', 'Brandon',    'Kowalski',    'Territory Manager',           'DIST-WE-01', 'WA', 'Y', '2023-04-17'),
    ('EMP_036', 'AZ-PHX-001', 'Courtney',   'Rivera',      'Senior Territory Manager',    'DIST-WE-02', 'AZ', 'Y', '2020-11-30'),
    ('EMP_037', 'CO-DEN-001', 'Eric',       'Johansson',   'Territory Manager',           'DIST-WE-02', 'CO', 'Y', '2021-07-12'),
    ('EMP_038', 'OR-PDX-001', 'Hannah',     'Fischer',     'Territory Manager',           'DIST-WE-02', 'OR', 'Y', '2022-12-08'),
    ('EMP_039', 'NV-LAS-001', 'Marcus',     'Bennett',     'Associate Territory Manager', 'DIST-WE-02', 'NV', 'Y', '2024-03-25'),
    ('EMP_040', 'UT-SLC-001', 'Olivia',     'Sandoval',    'Territory Manager',           'DIST-WE-02', 'UT', 'Y', '2023-08-07'),
    ('EMP_041', 'TX-HOU-001', 'Gregory',    'Owens',       'Senior Territory Manager',    'DIST-SO-01', 'TX', 'Y', '2020-09-14'),
    ('EMP_042', 'TX-DAL-001', 'Angela',     'Foster',      'Senior Territory Manager',    'DIST-SO-01', 'TX', 'Y', '2020-12-21'),
    ('EMP_043', 'TX-SAT-001', 'William',    'Reyes',       'Territory Manager',           'DIST-SO-01', 'TX', 'Y', '2021-10-03'),
    ('EMP_044', 'TX-AUS-001', 'Diana',      'Hoffman',     'Territory Manager',           'DIST-SO-01', 'TX', 'Y', '2022-06-19'),
    ('EMP_045', 'LA-NOR-001', 'Raymond',    'Thibodeaux',  'Territory Manager',           'DIST-SO-01', 'LA', 'Y', '2023-05-08'),
    ('EMP_046', 'LA-NOR-002', 'Natalie',    'Boudreaux',   'Territory Manager',           'DIST-SO-02', 'LA', 'Y', '2022-09-26'),
    ('EMP_047', 'TN-NSH-001', 'Adam',       'Whitfield',   'Territory Manager',           'DIST-SO-02', 'TN', 'Y', '2023-07-15'),
    ('EMP_048', 'TN-MEM-001', 'Christina',  'Ingram',      'Associate Territory Manager', 'DIST-SO-02', 'TN', 'Y', '2024-10-01'),
    ('EMP_049', 'AL-BHM-001', 'Douglas',    'Chambers',    'Territory Manager',           'DIST-SO-02', 'AL', 'Y', '2023-11-20'),
    ('EMP_050', 'OK-OKC-001', 'Rebecca',    'Thornton',    'Associate Territory Manager', 'DIST-SO-02', 'OK', 'Y', '2025-02-03');

-- REP_TERRITORY_DIM (50 rows)
CREATE OR REPLACE TABLE SF_SOLUTIONS.FIELD_TARGETING.REP_TERRITORY_DIM (
    EMP_ID    VARCHAR(10)  NOT NULL,
    TERR_ID   VARCHAR(20)  NOT NULL,
    FULL_NM   VARCHAR(100) NOT NULL,
    IS_ACTIVE VARCHAR(1)   DEFAULT 'Y',
    EFF_DT    DATE         NOT NULL,
    END_DT    DATE         NOT NULL
);

INSERT INTO SF_SOLUTIONS.FIELD_TARGETING.REP_TERRITORY_DIM
    (EMP_ID, TERR_ID, FULL_NM, IS_ACTIVE, EFF_DT, END_DT)
VALUES
    ('EMP_001', 'NY-NYC-001', 'Michael Torres',     'Y', '2025-01-01', '9999-12-31'),
    ('EMP_002', 'NY-NYC-002', 'Sarah Chen',         'Y', '2025-01-01', '9999-12-31'),
    ('EMP_003', 'NJ-NWK-001', 'David Patel',        'Y', '2025-01-01', '9999-12-31'),
    ('EMP_004', 'CT-HRT-001', 'Jennifer Walsh',     'Y', '2025-01-01', '9999-12-31'),
    ('EMP_005', 'NY-ALB-001', 'Robert Kim',         'Y', '2025-01-01', '9999-12-31'),
    ('EMP_006', 'MA-BOS-001', 'Amanda Rodriguez',   'Y', '2025-01-01', '9999-12-31'),
    ('EMP_007', 'MA-BOS-002', 'James O''Brien',     'Y', '2025-01-01', '9999-12-31'),
    ('EMP_008', 'PA-PHL-001', 'Lisa Thompson',      'Y', '2025-01-01', '9999-12-31'),
    ('EMP_009', 'PA-PHL-002', 'Christopher Lee',    'Y', '2025-01-01', '9999-12-31'),
    ('EMP_010', 'RI-PVD-001', 'Michelle Garcia',    'Y', '2025-01-01', '9999-12-31'),
    ('EMP_011', 'FL-MIA-001', 'Daniel Martinez',    'Y', '2025-01-01', '9999-12-31'),
    ('EMP_012', 'FL-MIA-002', 'Katherine Scott',    'Y', '2025-01-01', '9999-12-31'),
    ('EMP_013', 'FL-ORL-001', 'Andrew Johnson',     'Y', '2025-01-01', '9999-12-31'),
    ('EMP_014', 'FL-TPA-001', 'Nicole Williams',    'Y', '2025-01-01', '9999-12-31'),
    ('EMP_015', 'FL-JAX-001', 'Ryan Campbell',      'Y', '2025-01-01', '9999-12-31'),
    ('EMP_016', 'GA-ATL-001', 'Stephanie Brown',    'Y', '2025-01-01', '9999-12-31'),
    ('EMP_017', 'GA-ATL-002', 'Brian Davis',        'Y', '2025-01-01', '9999-12-31'),
    ('EMP_018', 'NC-CLT-001', 'Rachel Adams',       'Y', '2025-01-01', '9999-12-31'),
    ('EMP_019', 'NC-RDU-001', 'Matthew Wilson',     'Y', '2025-01-01', '9999-12-31'),
    ('EMP_020', 'VA-RIC-001', 'Emily Nguyen',       'Y', '2025-01-01', '9999-12-31'),
    ('EMP_021', 'IL-CHI-001', 'Kevin Murphy',       'Y', '2025-01-01', '9999-12-31'),
    ('EMP_022', 'IL-CHI-002', 'Laura Peterson',     'Y', '2025-01-01', '9999-12-31'),
    ('EMP_023', 'OH-CLE-001', 'Jason Taylor',       'Y', '2025-01-01', '9999-12-31'),
    ('EMP_024', 'OH-COL-001', 'Megan Anderson',     'Y', '2025-01-01', '9999-12-31'),
    ('EMP_025', 'MI-DET-001', 'Patrick Sullivan',   'Y', '2025-01-01', '9999-12-31'),
    ('EMP_026', 'MN-MSP-001', 'Christina Larsen',   'Y', '2025-01-01', '9999-12-31'),
    ('EMP_027', 'WI-MKE-001', 'Jonathan Brooks',    'Y', '2025-01-01', '9999-12-31'),
    ('EMP_028', 'IN-IND-001', 'Samantha Clark',     'Y', '2025-01-01', '9999-12-31'),
    ('EMP_029', 'MO-STL-001', 'Tyler Morgan',       'Y', '2025-01-01', '9999-12-31'),
    ('EMP_030', 'MO-KCI-001', 'Allison Harper',     'Y', '2025-01-01', '9999-12-31'),
    ('EMP_031', 'CA-LAX-001', 'Derek Ramirez',      'Y', '2025-01-01', '9999-12-31'),
    ('EMP_032', 'CA-LAX-002', 'Victoria Chang',     'Y', '2025-01-01', '9999-12-31'),
    ('EMP_033', 'CA-SFO-001', 'Nathan Goldstein',   'Y', '2025-01-01', '9999-12-31'),
    ('EMP_034', 'CA-SDG-001', 'Heather Nakamura',   'Y', '2025-01-01', '9999-12-31'),
    ('EMP_035', 'WA-SEA-001', 'Brandon Kowalski',   'Y', '2025-01-01', '9999-12-31'),
    ('EMP_036', 'AZ-PHX-001', 'Courtney Rivera',    'Y', '2025-01-01', '9999-12-31'),
    ('EMP_037', 'CO-DEN-001', 'Eric Johansson',     'Y', '2025-01-01', '9999-12-31'),
    ('EMP_038', 'OR-PDX-001', 'Hannah Fischer',     'Y', '2025-01-01', '9999-12-31'),
    ('EMP_039', 'NV-LAS-001', 'Marcus Bennett',     'Y', '2025-01-01', '9999-12-31'),
    ('EMP_040', 'UT-SLC-001', 'Olivia Sandoval',    'Y', '2025-01-01', '9999-12-31'),
    ('EMP_041', 'TX-HOU-001', 'Gregory Owens',      'Y', '2025-01-01', '9999-12-31'),
    ('EMP_042', 'TX-DAL-001', 'Angela Foster',      'Y', '2025-01-01', '9999-12-31'),
    ('EMP_043', 'TX-SAT-001', 'William Reyes',      'Y', '2025-01-01', '9999-12-31'),
    ('EMP_044', 'TX-AUS-001', 'Diana Hoffman',      'Y', '2025-01-01', '9999-12-31'),
    ('EMP_045', 'LA-NOR-001', 'Raymond Thibodeaux', 'Y', '2025-01-01', '9999-12-31'),
    ('EMP_046', 'LA-NOR-002', 'Natalie Boudreaux',  'Y', '2025-01-01', '9999-12-31'),
    ('EMP_047', 'TN-NSH-001', 'Adam Whitfield',     'Y', '2025-01-01', '9999-12-31'),
    ('EMP_048', 'TN-MEM-001', 'Christina Ingram',   'Y', '2025-01-01', '9999-12-31'),
    ('EMP_049', 'AL-BHM-001', 'Douglas Chambers',   'Y', '2025-01-01', '9999-12-31'),
    ('EMP_050', 'OK-OKC-001', 'Rebecca Thornton',   'Y', '2025-01-01', '9999-12-31');

-- =============================================================================
-- SECTION 3: Promo Materials Catalog (DDL + 24 seed rows)
-- =============================================================================

CREATE OR REPLACE TABLE SF_SOLUTIONS.FIELD_TARGETING.PROMO_MATERIALS_CATALOG (
    MATERIAL_ID       VARCHAR(10)  NOT NULL PRIMARY KEY,
    MATERIAL_NAME     VARCHAR(200) NOT NULL,
    MATERIAL_TYPE     VARCHAR(30)  NOT NULL,
    INDICATION        VARCHAR(20)  NOT NULL,
    PRODUCT_CD        VARCHAR(10)  NOT NULL DEFAULT 'ZNX',
    APPROVAL_STATUS   VARCHAR(20)  NOT NULL,
    APPROVAL_DATE     DATE         NOT NULL,
    EXPIRY_DATE       DATE,
    VERSION           VARCHAR(10)  NOT NULL,
    CONTENT_ID        VARCHAR(30)  NOT NULL,
    TARGET_AUDIENCE   VARCHAR(30)  NOT NULL,
    KEY_MESSAGE       VARCHAR(500),
    CLINICAL_STUDY_REF VARCHAR(50),
    LIFECYCLE_STAGE   VARCHAR(20)  NOT NULL
);

INSERT INTO SF_SOLUTIONS.FIELD_TARGETING.PROMO_MATERIALS_CATALOG
    (MATERIAL_ID, MATERIAL_NAME, MATERIAL_TYPE, INDICATION, PRODUCT_CD,
     APPROVAL_STATUS, APPROVAL_DATE, EXPIRY_DATE, VERSION, CONTENT_ID,
     TARGET_AUDIENCE, KEY_MESSAGE, CLINICAL_STUDY_REF, LIFECYCLE_STAGE)
VALUES
    ('MAT_001', 'Zenixar SKIN90 Superiority Detail Aid', 'Detail Aid', 'PsO', 'ZNX', 'Approved', '2025-06-15', '2026-12-31', 'v2.1', 'DOC-2025-00142', 'Dermatologist', 'Zenixar delivers SKIN90 in 62% of patients at Week 16.', 'VERTEX-1', 'Active'),
    ('MAT_002', 'Zenixar TARGET-A MOA Detail Aid', 'Detail Aid', 'PsO', 'ZNX', 'Approved', '2025-04-10', '2026-12-31', 'v1.3', 'DOC-2025-00098', 'General', 'Zenixar selectively targets TARGET-A with high-affinity binding.', 'VERTEX-1', 'Active'),
    ('MAT_003', 'Zenixar Head-to-Head vs Competitor-A Detail Aid', 'Detail Aid', 'PsO', 'ZNX', 'Approved', '2025-09-01', '2027-06-30', 'v1.0', 'DOC-2025-00287', 'Dermatologist', 'Superior SKIN90 response vs Competitor-A at Week 52.', 'APEX-PsO', 'Active'),
    ('MAT_004', 'Zenixar Dosing & Administration Detail Aid', 'Detail Aid', 'PsO', 'ZNX', 'Approved', '2025-03-20', '2026-12-31', 'v2.0', 'DOC-2025-00076', 'General', 'Simple SC dosing: 300mg at Weeks 0-4 then monthly maintenance.', NULL, 'Active'),
    ('MAT_005', 'Patient Outcomes Summary Leave-Behind', 'Leave-Behind', 'PsO', 'ZNX', 'Approved', '2025-05-22', '2026-12-31', 'v1.2', 'DOC-2025-00131', 'General', '78% of patients achieve clear or almost clear skin within 6 months.', 'VERTEX-2', 'Active'),
    ('MAT_006', 'TARGET-A Science Simplified Leave-Behind', 'Leave-Behind', 'PsO', 'ZNX', 'Approved', '2025-07-08', '2027-06-30', 'v1.0', 'DOC-2025-00195', 'General', 'Understanding TARGET-A: the key cytokine driving plaque formation.', NULL, 'Active'),
    ('MAT_007', 'Zenixar Insurance & Access Guide', 'Leave-Behind', 'General', 'ZNX', 'Approved', '2025-08-14', '2027-06-30', 'v1.1', 'DOC-2025-00234', 'General', 'Zenixar is covered on 85% of commercial plans with Tier 2 status.', NULL, 'Active'),
    ('MAT_008', 'VERTEX-1 Pivotal Trial Reprint', 'Reprint', 'PsO', 'ZNX', 'Approved', '2025-02-01', '2026-12-31', 'v1.0', 'DOC-2025-00045', 'Dermatologist', 'Phase 3 RCT demonstrating Zenixar efficacy and safety.', 'VERTEX-1', 'Active'),
    ('MAT_009', 'VERTEX-2 Long-Term Extension Reprint', 'Reprint', 'PsO', 'ZNX', 'Approved', '2025-10-15', '2027-06-30', 'v1.0', 'DOC-2025-00312', 'General', 'Sustained SKIN90 through 3 years with consistent safety profile.', 'VERTEX-2', 'Active'),
    ('MAT_010', 'Real-World Evidence Analysis Reprint', 'Reprint', 'PsO', 'ZNX', 'Expired', '2024-06-01', '2025-06-30', 'v1.0', 'DOC-2024-00189', 'Dermatologist', 'Multi-center retrospective analysis of Zenixar outcomes.', NULL, 'Retired'),
    ('MAT_011', 'Zenixar Patient Quick-Start Guide', 'Patient Brochure', 'PsO', 'ZNX', 'Approved', '2025-04-01', '2026-12-31', 'v2.0', 'DOC-2025-00089', 'General', 'Step-by-step guide for patients starting Zenixar in first 16 weeks.', NULL, 'Active'),
    ('MAT_012', 'Self-Injection Technique Guide', 'Patient Brochure', 'General', 'ZNX', 'Approved', '2025-03-15', '2026-12-31', 'v1.4', 'DOC-2025-00071', 'General', 'Illustrated guide for subcutaneous self-injection.', NULL, 'Active'),
    ('MAT_013_B', 'Living Well with Psoriasis Brochure', 'Patient Brochure', 'PsO', 'ZNX', 'Expired', '2024-03-10', '2025-03-31', 'v1.0', 'DOC-2024-00062', 'General', 'Holistic approach to managing plaque psoriasis.', NULL, 'Retired'),
    ('MAT_013', 'Zenixar Starter Kit (2x300mg)', 'Sample Kit', 'PsO', 'ZNX', 'Approved', '2025-01-15', '2026-12-31', 'v1.0', 'DOC-2025-00022', 'General', 'Two-dose starter kit with autoinjector pens for loading doses.', NULL, 'Active'),
    ('MAT_014', 'Zenixar Bridge Kit (1x300mg)', 'Sample Kit', 'PsO', 'ZNX', 'Approved', '2025-01-15', '2026-12-31', 'v1.0', 'DOC-2025-00023', 'General', 'Single-dose bridge supply for patients awaiting insurance auth.', NULL, 'Active'),
    ('MAT_015', 'KOL Presentation: Zenixar Clinical Evidence', 'Speaker Deck', 'PsO', 'ZNX', 'Approved', '2025-08-01', '2027-06-30', 'v1.2', 'DOC-2025-00215', 'Dermatologist', 'Comprehensive clinical evidence for peer-to-peer speaker programs.', 'VERTEX-1', 'Active'),
    ('MAT_016', 'Dermatology Congress Slide Set', 'Speaker Deck', 'PsO', 'ZNX', 'Approved', '2025-09-20', '2027-06-30', 'v1.0', 'DOC-2025-00298', 'Dermatologist', 'Conference-ready presentation covering ZENITH program data.', 'VERTEX-2', 'Active'),
    ('MAT_017', 'Rheumatology Symposium Deck: PsA Crossover', 'Speaker Deck', 'PsA', 'ZNX', 'Under Review', '2026-01-10', NULL, 'v0.9', 'DOC-2026-00015', 'Rheumatologist', 'Emerging data on Zenixar efficacy in psoriatic arthritis.', NULL, 'Draft'),
    ('MAT_018', 'Zenixar iPad Interactive Detail', 'Digital Aid', 'PsO', 'ZNX', 'Approved', '2025-06-01', '2026-12-31', 'v2.0', 'DOC-2025-00155', 'Dermatologist', 'Interactive tablet presentation with animated MOA.', 'VERTEX-1', 'Active'),
    ('MAT_019', 'MOA Video Module (3-min)', 'Digital Aid', 'PsO', 'ZNX', 'Approved', '2025-05-10', '2026-12-31', 'v1.1', 'DOC-2025-00125', 'General', 'Short-form animated video explaining TARGET-A inhibition MOA.', NULL, 'Active'),
    ('MAT_020', 'Interactive Dosing Calculator', 'Digital Aid', 'PsO', 'ZNX', 'Approved', '2025-07-25', '2027-06-30', 'v1.0', 'DOC-2025-00208', 'General', 'Weight-based dosing tool with loading and maintenance schedule.', NULL, 'Active'),
    ('MAT_021', 'Patient Testimonial: Clear Skin Journey', 'Video', 'PsO', 'ZNX', 'Approved', '2025-09-05', '2027-06-30', 'v1.0', 'DOC-2025-00265', 'General', 'Real patient achieving clear skin with Zenixar after biologic switch.', NULL, 'Active'),
    ('MAT_022', 'Zenixar MOA Animation (Full)', 'Video', 'PsO', 'ZNX', 'Approved', '2025-04-20', '2026-12-31', 'v1.2', 'DOC-2025-00095', 'Dermatologist', 'Detailed 5-minute animation of TARGET-A pathway.', NULL, 'Active'),
    ('MAT_023', 'Formulary Decision Maker Dossier', 'Leave-Behind', 'PsO', 'ZNX', 'Approved', '2025-10-01', '2027-06-30', 'v1.0', 'DOC-2025-00305', 'General', 'Managed-care dossier summarizing clinical and economic outcomes.', 'VERTEX-1', 'Active'),
    ('MAT_024', 'Zenixar Safety Profile Summary', 'Detail Aid', 'General', 'ZNX', 'Approved', '2025-11-15', '2027-06-30', 'v1.0', 'DOC-2025-00341', 'General', 'Integrated safety analysis across ZENITH program: 3-year pooled.', 'VERTEX-2', 'Active');

-- =============================================================================
-- SECTION 4: Derived Tables (created after data.sql is loaded)
-- =============================================================================

-- CALL_NOTES_RAW — populated from CALL_ACTIVITY after data.sql runs
CREATE OR REPLACE TABLE SF_SOLUTIONS.FIELD_TARGETING.CALL_NOTES_RAW (
    MDM_ID               VARCHAR,
    CALL_DATE            DATE,
    TERR_ID              VARCHAR,
    NOTE_TEXT            VARCHAR,
    TEMPLATE_DISPOSITION VARCHAR
);

-- CALL_NOTES_ENRICHED — populated from CALL_NOTES_RAW
CREATE OR REPLACE TABLE SF_SOLUTIONS.FIELD_TARGETING.CALL_NOTES_ENRICHED (
    MDM_ID              VARCHAR,
    CALL_DATE           DATE,
    TERR_ID             VARCHAR,
    NOTE_TEXT           VARCHAR,
    SENTIMENT_SCORE     FLOAT,
    DISPOSITION         VARCHAR,
    KEY_SIGNALS         VARIANT,
    MATERIALS_PRESENTED VARIANT
);

-- CALL_MATERIAL_USAGE — populated from CALL_ACTIVITY after data.sql runs
CREATE OR REPLACE TABLE SF_SOLUTIONS.FIELD_TARGETING.CALL_MATERIAL_USAGE (
    USAGE_ID    NUMBER AUTOINCREMENT START 1 INCREMENT 1,
    CALL_ID     VARCHAR(20)  NOT NULL,
    MDM_ID      VARCHAR(20)  NOT NULL,
    MATERIAL_ID VARCHAR(10)  NOT NULL,
    USAGE_TYPE  VARCHAR(20)  NOT NULL,
    REACTION    VARCHAR(20)  NOT NULL,
    TERR_ID     VARCHAR(20),
    CALL_DATE   DATE,
    REP_ID      VARCHAR(20)
);

-- =============================================================================
-- SECTION 5: Views
-- =============================================================================

CREATE OR REPLACE VIEW SF_SOLUTIONS.FIELD_TARGETING.MATERIAL_EFFECTIVENESS AS
WITH usage_stats AS (
    SELECT
        cmu.MATERIAL_ID,
        COUNT(*) AS TOTAL_USES,
        COUNT(DISTINCT cmu.MDM_ID) AS UNIQUE_HCPS,
        ROUND(SUM(CASE WHEN cmu.REACTION = 'Positive' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 1) AS PCT_POSITIVE_REACTION,
        ROUND(SUM(CASE WHEN cmu.REACTION = 'Negative' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 1) AS PCT_NEGATIVE_REACTION
    FROM SF_SOLUTIONS.FIELD_TARGETING.CALL_MATERIAL_USAGE cmu
    GROUP BY cmu.MATERIAL_ID
),
sentiment_by_material AS (
    SELECT
        cmu.MATERIAL_ID,
        ROUND(AVG(cne.SENTIMENT_SCORE), 3) AS AVG_SENTIMENT_POST_USE
    FROM SF_SOLUTIONS.FIELD_TARGETING.CALL_MATERIAL_USAGE cmu
    INNER JOIN SF_SOLUTIONS.FIELD_TARGETING.CALL_NOTES_ENRICHED cne
        ON cmu.MDM_ID = cne.MDM_ID AND cmu.CALL_DATE = cne.CALL_DATE
    GROUP BY cmu.MATERIAL_ID
),
conversion_by_material AS (
    SELECT
        cmu.MATERIAL_ID,
        ROUND(
            COUNT(DISTINCT CASE WHEN cne.DISPOSITION = 'conversion_ready' THEN cmu.MDM_ID END) * 100.0
            / NULLIF(COUNT(DISTINCT cmu.MDM_ID), 0), 1
        ) AS CONVERSION_READY_RATE
    FROM SF_SOLUTIONS.FIELD_TARGETING.CALL_MATERIAL_USAGE cmu
    LEFT JOIN SF_SOLUTIONS.FIELD_TARGETING.CALL_NOTES_ENRICHED cne
        ON cmu.MDM_ID = cne.MDM_ID
    GROUP BY cmu.MATERIAL_ID
)
SELECT
    pmc.MATERIAL_ID,
    pmc.MATERIAL_NAME,
    pmc.MATERIAL_TYPE,
    us.TOTAL_USES,
    us.UNIQUE_HCPS,
    us.PCT_POSITIVE_REACTION,
    us.PCT_NEGATIVE_REACTION,
    sbm.AVG_SENTIMENT_POST_USE,
    cbm.CONVERSION_READY_RATE
FROM SF_SOLUTIONS.FIELD_TARGETING.PROMO_MATERIALS_CATALOG pmc
LEFT JOIN usage_stats us ON pmc.MATERIAL_ID = us.MATERIAL_ID
LEFT JOIN sentiment_by_material sbm ON pmc.MATERIAL_ID = sbm.MATERIAL_ID
LEFT JOIN conversion_by_material cbm ON pmc.MATERIAL_ID = cbm.MATERIAL_ID
WHERE pmc.LIFECYCLE_STAGE = 'Active';

-- =============================================================================
-- SECTION 6: Stage for Streamlit
-- =============================================================================

CREATE STAGE IF NOT EXISTS SF_SOLUTIONS.FIELD_TARGETING.STREAMLIT_STAGE
    DIRECTORY = (ENABLE = TRUE);
