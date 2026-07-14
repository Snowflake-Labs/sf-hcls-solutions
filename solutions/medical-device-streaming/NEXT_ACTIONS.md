---
description: >
  Show next actions after installing the Medical Device Streaming Platform.
  Guides the user from exploration to running the live demo to production.
  Triggers: what next, next steps, what can I do, how to use this, streaming demo.
---

# Next Actions: Medical Device Streaming Platform

After installation, guide the user through these progressive steps.

> **Note:** The installation includes sample data (`data.sql`) so the Streamlit dashboard
> displays charts immediately. This is static demo data generated via `GENERATOR()`.
> For real-time streaming data that updates continuously, you need to run the Python
> streaming client described in the "Run the Streaming Demo" section below.

## Quick Exploration

1. **Verify the infrastructure:**
   ```sql
   -- List all objects created
   SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
   FROM SF_SOLUTIONS.INFORMATION_SCHEMA.TABLES
   WHERE TABLE_SCHEMA IN ('MEDICAL_DEVICE_CLINICAL', 'MEDICAL_DEVICE_TELEMETRY')
   ORDER BY TABLE_SCHEMA, TABLE_TYPE, TABLE_NAME;

   -- Check streaming pipes
   SHOW PIPES IN SCHEMA SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL;
   SHOW PIPES IN SCHEMA SF_SOLUTIONS.MEDICAL_DEVICE_TELEMETRY;
   ```

2. **Explore the flattened view schemas:**
   ```sql
   -- See what columns are available in the ECG view
   DESCRIBE VIEW SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL.ECG_DATA_FLATTENED;

   -- See the consolidated vital signs view
   DESCRIBE VIEW SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL.PATIENT_VITAL_SIGNS;

   -- See device telemetry fields
   DESCRIBE VIEW SF_SOLUTIONS.MEDICAL_DEVICE_TELEMETRY.DEVICE_TELEMETRY_FLATTENED;
   ```

3. **Query sample data (after streaming some data):**
   ```sql
   -- Latest ECG readings
   SELECT * FROM SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL.ECG_DATA_FLATTENED
   ORDER BY TIMESTAMP_VAL DESC
   LIMIT 10;

   -- Patient vital signs (consolidated real-time view)
   SELECT * FROM SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL.PATIENT_VITAL_SIGNS
   WHERE PATIENT_ID = '1229701'
   ORDER BY TIMESTAMP_SEC DESC
   LIMIT 20;

   -- Device health overview
   SELECT * FROM SF_SOLUTIONS.MEDICAL_DEVICE_TELEMETRY.DEVICE_TELEMETRY_FLATTENED
   ORDER BY TIMESTAMP_VAL DESC
   LIMIT 10;
   ```

## Run the Streaming Demo

The `app/` directory contains a Python client that generates realistic biosignal data.

**Prerequisites:**
- Python 3.11+
- RSA key pair for JWT authentication
- AWS-based Snowflake account with high-performance streaming preview

**Setup steps:**

4. **Generate RSA keys:**
   ```bash
   cd solutions/medical-device-streaming/app/
   openssl genrsa -out rsa_key.p8 2048
   openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub
   ```

5. **Register public key in Snowflake:**
   ```sql
   -- Get the key content (remove header/footer lines)
   -- Then assign to your user:
   ALTER USER <YOUR_USER> SET RSA_PUBLIC_KEY='<public-key-content>';
   ```

6. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your account details
   ```

7. **Install Python dependencies:**
   ```bash
   pip install -r supporting_code_files/requirements.txt
   ```

8. **Run the setup and dashboard:**
   ```bash
   python setup_application.py install
   python run_application.py
   # Access dashboard at http://localhost:8501
   ```

## Connect Real Data

9. **Replace the NeuroKit2 simulator with real device feeds:**
   - Modify `supporting_code_files/medical_device_generator.py` to accept real device input
   - Use the same REST API endpoints and pipe objects
   - Map your device data to the expected JSON schema

10. **Install the Marketplace dataset for demographics:**
    - Search for "Synthetic Healthcare Data - Clinical and Claims" in Snowflake Marketplace
    - Install the free dataset
    - The PATIENT_VITAL_SIGNS view can be extended to join with demographics

11. **Add more device types:**
    - Create new tables following the ECG_DATA pattern (VARIANT + PATIENT_ID + TIMESTAMP_VAL)
    - Create corresponding pipes and flattened views
    - Add new device generators to the Python client

## Production Deployment

12. **Set up monitoring alerts:**
    ```sql
    -- Alert on device disconnections
    CREATE OR REPLACE ALERT SF_SOLUTIONS.MEDICAL_DEVICE_TELEMETRY.DEVICE_DISCONNECT_ALERT
        WAREHOUSE = SF_SOLUTIONS_WH
        SCHEDULE = 'USING CRON */5 * * * * America/Los_Angeles'
        IF (EXISTS (
            SELECT 1
            FROM SF_SOLUTIONS.MEDICAL_DEVICE_TELEMETRY.DEVICE_TELEMETRY_FLATTENED
            WHERE CONNECTION_STATUS = 'DISCONNECTED'
              AND TIMESTAMP_VAL >= DATEADD(MINUTE, -5, CURRENT_TIMESTAMP())
        ))
        THEN
            CALL SYSTEM$SEND_EMAIL(...);
    ```

13. **Create least-privilege roles:**
    ```sql
    CREATE ROLE IF NOT EXISTS MEDICAL_DEVICE_READER;
    GRANT USAGE ON DATABASE SF_SOLUTIONS TO ROLE MEDICAL_DEVICE_READER;
    GRANT USAGE ON SCHEMA SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL TO ROLE MEDICAL_DEVICE_READER;
    GRANT USAGE ON SCHEMA SF_SOLUTIONS.MEDICAL_DEVICE_TELEMETRY TO ROLE MEDICAL_DEVICE_READER;
    GRANT SELECT ON ALL VIEWS IN SCHEMA SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL TO ROLE MEDICAL_DEVICE_READER;
    GRANT SELECT ON ALL VIEWS IN SCHEMA SF_SOLUTIONS.MEDICAL_DEVICE_TELEMETRY TO ROLE MEDICAL_DEVICE_READER;

    CREATE ROLE IF NOT EXISTS MEDICAL_DEVICE_STREAMER;
    GRANT USAGE ON DATABASE SF_SOLUTIONS TO ROLE MEDICAL_DEVICE_STREAMER;
    GRANT USAGE ON SCHEMA SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL TO ROLE MEDICAL_DEVICE_STREAMER;
    GRANT INSERT ON ALL TABLES IN SCHEMA SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL TO ROLE MEDICAL_DEVICE_STREAMER;
    GRANT OPERATE ON ALL PIPES IN SCHEMA SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL TO ROLE MEDICAL_DEVICE_STREAMER;
    ```

14. **Add data retention and clustering:**
    ```sql
    -- Cluster clinical data by patient and time for fast queries
    ALTER TABLE SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL.ECG_DATA
        CLUSTER BY (PATIENT_ID, TIMESTAMP_VAL);

    -- Set retention for compliance
    ALTER TABLE SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL.ECG_DATA
        SET DATA_RETENTION_TIME_IN_DAYS = 90;
    ```

## Summary

| Phase | Actions |
|-------|---------|
| Explore | Verify objects, describe views, query sample data |
| Demo | Generate RSA keys, configure .env, run Python streaming client |
| Real Data | Connect real devices, install Marketplace dataset, add device types |
| Production | Alerts, RBAC, clustering, retention policies |
