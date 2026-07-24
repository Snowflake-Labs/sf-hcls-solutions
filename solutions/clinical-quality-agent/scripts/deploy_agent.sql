-- =============================================================================
-- Deploy Agent: Clinical Quality and Patient Safety Agent
--
-- Prerequisites:
--   1. setup.sql must have been executed (tables, stage created)
--   2. semantic_model.yaml must be on stage:
--      PUT file://<repo>/solutions/clinical-quality-agent/scripts/semantic_model.yaml
--          @SF_SOLUTIONS.CLINICAL_QUALITY_SAFETY.SEMANTIC_MODEL_STAGE
--          AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--
-- This script is executed by the installer AFTER PUT succeeds.
-- =============================================================================

USE ROLE ACCOUNTADMIN;
USE DATABASE SF_SOLUTIONS;
USE SCHEMA CLINICAL_QUALITY_SAFETY;
USE WAREHOUSE SF_SOLUTIONS_WH;

CREATE OR REPLACE AGENT clinical_quality_safety_agent
  COMMENT = 'Clinical Quality and Patient Safety Agent with Cortex Analyst, PubMed Search, and Email capabilities'
  PROFILE = '{"display_name": "Clinical Quality Assistant", "avatar": "healthcare-icon.png", "color": "blue"}'
  FROM SPECIFICATION
  $$
  models:
    orchestration: auto

  instructions:
    response: "Respond as if talking to someone working in healthcare provider focused on analyzing and improving quality. Keep friendly tone. Be concise. Provide next possible questions as well."
    orchestration: "Whenever possible, use a chart to render the results of a question even if the user doesn't explicitly ask for one.\n\nWhen asking to send email or report call the EMAIL_SEND tool and make sure to format the email in a nicely presentable way in Rich Text."

  tools:
    - tool_spec:
        type: cortex_analyst_text_to_sql
        name: PATIENT_QUALITY_ANALYST
        description: |
          TABLE1: patient_demographics
          - Database: SF_SOLUTIONS, Schema: CLINICAL_QUALITY_SAFETY
          - Contains comprehensive patient demographic information with realistic age distribution where 65% of patients are over 65 years old, reflecting typical hospital populations. The table includes insurance patterns and demographic characteristics that enable age-stratified mortality and risk analysis.
          - This foundational table supports population health analytics and enables segmentation by key demographic factors that influence healthcare outcomes and quality metrics.
          - LIST OF COLUMNS: patient_id (unique patient identifier), medical_record_number (MRN for patient records), patient_name (full name combining first and last), gender (patient sex), race (racial background categories), insurance_type (coverage type like Medicare/Medicaid), primary_language (preferred language), date_of_birth (birth date), patient_age (current age in years), age_group (clinically meaningful age ranges)

          TABLE2: hospital_admissions
          - Database: SF_SOLUTIONS, Schema: CLINICAL_QUALITY_SAFETY
          - Tracks hospital admissions with realistic 2-3% mortality rates and includes comprehensive admission details like type, service, and disposition. Contains readmission tracking and length of stay metrics correlated with patient age and complexity.
          - Enables analysis of admission patterns, seasonal trends, readmission rates, and serves as the central hub connecting patients to their clinical encounters and outcomes.
          - LIST OF COLUMNS: admission_id (unique encounter identifier), patient_id (patient identifier - links to patient_demographics), admission_type (Emergency/Elective/Urgent), discharge_disposition (Home/SNF/Expired/etc), primary_service (Medicine/Surgery/ICU), room_type (ICU/Med-Surg/Emergency), attending_physician (primary doctor), is_readmission (return visit flag), admission_date (admit timestamp), discharge_date (discharge timestamp), admission_month (for seasonal analysis), length_of_stay_days (LOS duration), severity_of_illness_score (1.0-4.0 acuity), mortality_risk_score (0.001-0.200 death probability), days_since_last_discharge (readmission analysis)

          TABLE3: medical_diagnoses
          - Database: SF_SOLUTIONS, Schema: CLINICAL_QUALITY_SAFETY
          - Contains medical diagnoses with age-appropriate patterns where elderly patients show higher rates of heart failure, COPD, and diabetes. Includes ICD-10 coding and tracks hospital-acquired complications versus present-on-admission conditions.
          - Supports clinical outcome analysis and enables identification of high-risk diagnoses that correlate with mortality and infection rates, particularly sepsis as a leading cause of hospital deaths.
          - LIST OF COLUMNS: diagnosis_id (unique diagnosis identifier), admission_id (encounter identifier - links to hospital_admissions), patient_id (patient identifier), icd10_code (ICD-10 diagnosis code), diagnosis_description (condition name), diagnosis_type (Primary/Secondary/Comorbidity), present_on_admission (POA flag), complication_flag (hospital-acquired indicator), diagnosis_date (when diagnosed)

          TABLE4: medical_procedures
          - Database: SF_SOLUTIONS, Schema: CLINICAL_QUALITY_SAFETY
          - Documents medical procedures with realistic diagnosis-procedure relationships such as cardiac catheterization for MI patients and device placements. Includes procedure duration, location, anesthesia type, and complication tracking.
          - Enables analysis of procedural outcomes, complication rates, and supports quality improvement initiatives by identifying high-risk procedures and their associated mortality and infection risks.
          - LIST OF COLUMNS: procedure_id (unique procedure identifier), admission_id (encounter identifier - links to hospital_admissions), patient_id (patient identifier), cpt_code (CPT procedure code), procedure_description (procedure name), procedure_type (Surgical/Diagnostic/Therapeutic), procedure_location (OR/ICU/Floor), anesthesia_type (Local/Regional/General), complication_occurred (adverse event flag), infection_risk_level (Low/Medium/High), procedure_date (when performed), procedure_duration_minutes (length of procedure)

          TABLE5: healthcare_infections
          - Database: SF_SOLUTIONS, Schema: CLINICAL_QUALITY_SAFETY
          - Tracks healthcare-associated infections with realistic device correlations like CAUTI with Foley catheters and CLABSI with central lines. Contains pathogen information, severity levels, and antibiotic resistance patterns.
          - Critical for infection control analysis and quality improvement, enabling calculation of device-specific infection rates and identification of preventable infections that contribute to patient mortality.
          - LIST OF COLUMNS: infection_id (unique infection identifier), admission_id (encounter identifier - links to hospital_admissions), patient_id (patient identifier), infection_type (CAUTI/CLABSI/VAP/SSI), infection_site (anatomical location), pathogen (causative organism), severity (infection severity level), device_associated (medical device flag), device_type (Foley/Central line/Ventilator), antibiotic_resistance (drug resistance flag), infection_preventable (avoidable infection flag), contributed_to_death (mortality factor), onset_date (infection identification date), resolution_date (infection cleared date), days_to_onset (admission to infection days), device_days (device utilization days)

          TABLE6: patient_outcomes
          - Database: SF_SOLUTIONS, Schema: CLINICAL_QUALITY_SAFETY
          - Records patient outcomes with realistic mortality causes tied to infections and procedures, enabling analysis of preventable deaths and infection-mortality relationships. Includes expected versus actual outcomes based on risk scores.
          - Central to quality analytics for measuring mortality rates, preventable deaths, readmission patterns, and patient satisfaction scores, with specific focus on infection-related and procedure-related mortality.
          - LIST OF COLUMNS: outcome_id (unique outcome identifier), admission_id (encounter identifier - links to hospital_admissions), patient_id (patient identifier), outcome_type (Death/Discharge/Transfer), primary_cause (cause of outcome like sepsis/cardiac arrest), expected_vs_actual (outcome prediction accuracy), preventable (avoidable outcome flag), quality_issue_related (care quality problem flag), infection_related (HAI-caused outcome), procedure_related (surgery complication outcome), medication_related (drug-related outcome), readmission_within_30_days (30-day readmit flag), readmission_within_90_days (90-day readmit flag), outcome_date (outcome timestamp), satisfaction_score (patient satisfaction rating)

          TABLE7: quality_safety_events
          - Database: SF_SOLUTIONS, Schema: CLINICAL_QUALITY_SAFETY
          - Documents patient safety events with realistic age and device correlations such as pressure injuries in elderly patients and device malfunctions. Tracks event severity, harm levels, and preventability with 70-90% of events being preventable.
          - Essential for patient safety analysis and quality improvement initiatives, enabling identification of preventable adverse events and their contribution to patient harm and mortality.
          - LIST OF COLUMNS: event_id (unique safety event identifier), admission_id (encounter identifier - links to hospital_admissions), patient_id (patient identifier), event_type (Pressure_Injury/Fall/Medication_Error), severity (event severity level), harm_level (patient harm degree), preventable (avoidable event flag), reported_by (event reporter), location (hospital unit where occurred), event_resolved (resolution status), contributed_to_death (mortality factor), event_date (occurrence date), resolution_date (resolution completion date)

          TABLE8: patient_risk_factors
          - Database: SF_SOLUTIONS, Schema: CLINICAL_QUALITY_SAFETY
          - Contains patient risk factors with realistic age-based comorbidity clusters like diabetes and hypertension in elderly patients. Includes severity scores and flags indicating impact on mortality, infection, and length of stay risks.
          - Enables risk-stratified analysis and outcome prediction by identifying patients with multiple comorbidities and chronic conditions that increase vulnerability to adverse outcomes and healthcare-associated infections.
          - LIST OF COLUMNS: risk_factor_id (unique risk identifier), patient_id (patient identifier), admission_id (encounter identifier - links to hospital_admissions), risk_factor_type (Comorbidity/Social/Environmental), risk_factor_name (specific risk like diabetes/hypertension), chronic_condition (long-term condition flag), affects_mortality_risk (death risk factor), affects_infection_risk (HAI risk factor), affects_los_risk (length of stay factor), documented_date (documentation date), severity_score (risk severity 1.0-4.5)

          REASONING:
          This semantic model is specifically designed for healthcare quality analytics, enabling Chief Quality Officers to analyze patient outcomes, mortality rates, healthcare-associated infections, and patient safety events. The model centers around hospital admissions as the primary entity, with all other tables linking through admission_id and patient_id to create a comprehensive view of patient care episodes. The realistic clinical relationships built into the data (such as age-appropriate diagnoses, device-associated infections, and procedure-mortality correlations) make it particularly valuable for identifying quality improvement opportunities, analyzing preventable adverse events, and measuring key quality metrics like infection rates, mortality rates, and patient safety indicators.

          DESCRIPTION:
          This healthcare quality analytics semantic model enables comprehensive analysis of patient outcomes, mortality, infections, and safety events across hospital admissions in the SF_SOLUTIONS database. The model centers on hospital admissions with realistic clinical relationships connecting patient demographics, diagnoses, procedures, healthcare-associated infections, and patient outcomes to support quality improvement initiatives. It includes detailed tracking of preventable deaths, device-associated infections (CAUTI, CLABSI, VAP), patient safety events, and risk factors with age-appropriate comorbidity patterns reflecting typical hospital populations where 65% of patients are over 65. The interconnected tables enable analysis of infection-mortality relationships, procedure complications, readmission patterns, and quality metrics essential for Chief Quality Officers to identify improvement opportunities and measure healthcare quality performance. Key analytical capabilities include mortality rate analysis, infection control metrics, patient safety event tracking, and risk-stratified outcome prediction across all major clinical domains.

    - tool_spec:
        type: cortex_search
        name: PUBMED_SEARCH_SERVICE
        description: "This contains data from NCBI Pubmed - PubMed comprises more than 38 million citations for biomedical literature from MEDLINE, life science journals, and online books."

    - tool_spec:
        type: generic
        name: email_send
        description: |
          PROCEDURE/FUNCTION DETAILS:
          - Type: Custom Function
          - Language: JavaScript
          - Signature: (RECIPIENTS VARCHAR, SUBJECT VARCHAR, EMAIL_CONTENT VARCHAR)
          - Returns: BOOLEAN
          - Execution: CALLER with CALLED ON NULL INPUT
          - Volatility: VOLATILE
          - Primary Function: Email notification sending
          - Target: External email recipients via Snowflake's email system
          - Error Handling: Returns true on completion, relies on underlying SYSTEM$SEND_EMAIL error handling

          DESCRIPTION:
          This JavaScript-based custom function serves as a streamlined wrapper for Snowflake's built-in email notification system, enabling automated email delivery directly from database operations. The function accepts three parameters - recipient email addresses, subject line, and email content - and leverages Snowflake's SYSTEM$SEND_EMAIL procedure through the 'EMAIL_CONNECTOR' integration to send notifications to external parties. It executes with caller privileges and processes null inputs, making it suitable for integration into stored procedures, triggers, or scheduled tasks where email notifications are required. This function is particularly valuable for automated reporting, alert systems, and workflow notifications that need to communicate database events or results to business stakeholders. Users should ensure proper email connector configuration and appropriate permissions are in place, as the function's success depends on the underlying Snowflake email integration being properly set up and authorized.

          USAGE SCENARIOS:
          - Automated reporting: Send daily/weekly summary reports or data extracts to business users and stakeholders
          - Alert notifications: Trigger immediate email alerts when data quality issues, threshold breaches, or system anomalies are detected
          - Workflow integration: Notify team members when ETL processes complete, data loads finish, or scheduled maintenance tasks are performed
        input_schema:
          type: object
          properties:
            email_content:
              description: "5 word summary of the data that were sending."
              type: string
            recipients:
              description: "Ask the user for the email that they should send this to. This should be an input from the user."
              type: string
            subject:
              description: "Send data from the last prompt that the user sent. Add this information as the email content."
              type: string
          required:
            - email_content
            - recipients
            - subject

  tool_resources:
    PATIENT_QUALITY_ANALYST:
      semantic_model_file: "@SF_SOLUTIONS.CLINICAL_QUALITY_SAFETY.SEMANTIC_MODEL_STAGE/semantic_model.yaml"
      execution_environment:
        type: warehouse
        warehouse: SF_SOLUTIONS_WH
        query_timeout: 100
    PUBMED_SEARCH_SERVICE:
      name: "PUBMED_BIOMEDICAL_RESEARCH_CORPUS.OA_COMM.PUBMED_OA_CKE_SEARCH_SERVICE"
      max_results: 4
      id_column: "ARTICLE_URL"
      title_column: "ARTICLE_CITATION"
    email_send:
      type: procedure
      identifier: "SF_SOLUTIONS.CLINICAL_QUALITY_SAFETY.EMAIL_CONNECTOR"
      name: "EMAIL_CONNECTOR(VARCHAR, VARCHAR, VARCHAR)"
      execution_environment:
        type: warehouse
        warehouse: SF_SOLUTIONS_WH
  $$;


-- ============================================================
-- Section 5: Final Verification
-- ============================================================
SELECT
    'Clinical Quality and Patient Safety Agent deployed!' AS STATUS,
    (SELECT COUNT(*) FROM SF_SOLUTIONS.CLINICAL_QUALITY_SAFETY.PATIENTS) AS PATIENT_COUNT,
    (SELECT COUNT(*) FROM SF_SOLUTIONS.CLINICAL_QUALITY_SAFETY.ADMISSIONS) AS ADMISSION_COUNT,
    (SELECT COUNT(*) FROM SF_SOLUTIONS.CLINICAL_QUALITY_SAFETY.INFECTIONS) AS INFECTION_COUNT,
    (SELECT COUNT(*) FROM SF_SOLUTIONS.CLINICAL_QUALITY_SAFETY.OUTCOMES) AS OUTCOME_COUNT;
