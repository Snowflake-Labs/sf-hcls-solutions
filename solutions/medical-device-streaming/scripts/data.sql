-- =============================================================================
-- Sample Data: Medical Device Streaming Platform
-- Generates realistic biosignal and telemetry data for dashboard demonstration.
-- Timestamps are relative to CURRENT_TIMESTAMP() so dashboards always show data.
-- =============================================================================

USE ROLE ACCOUNTADMIN;
USE DATABASE SF_SOLUTIONS;
USE WAREHOUSE SF_SOLUTIONS_WH;

-- =============================================================================
-- CLINICAL SCHEMA: ECG, EDA, PPG sample data
-- =============================================================================

USE SCHEMA MEDICAL_DEVICE_CLINICAL;

-- Patient sessions
INSERT INTO PATIENT_SESSIONS (SESSION_ID, PATIENT_ID, FACILITY_ID, ROOM_ID,
    SESSION_START_TIME, SESSION_STATUS, SESSION_TYPE, ATTENDING_PHYSICIAN,
    PRIMARY_CONDITION, CLINICAL_PRIORITY, ACTIVE_DEVICES)
SELECT
    'SESSION-' || LPAD(SEQ4()::VARCHAR, 4, '0'),
    'PATIENT-' || LPAD(MOD(SEQ4(), 5) + 1, 3, '0'),
    'FACILITY-001',
    'ROOM-' || LPAD(MOD(SEQ4(), 10) + 1, 3, '0'),
    DATEADD('HOUR', -SEQ4(), CURRENT_TIMESTAMP())::TIMESTAMP_NTZ,
    CASE MOD(SEQ4(), 3) WHEN 0 THEN 'ACTIVE' WHEN 1 THEN 'ACTIVE' ELSE 'COMPLETED' END,
    CASE MOD(SEQ4(), 4) WHEN 0 THEN 'ICU Monitoring' WHEN 1 THEN 'Post-Surgery'
        WHEN 2 THEN 'Cardiac Assessment' ELSE 'Routine Checkup' END,
    CASE MOD(SEQ4(), 3) WHEN 0 THEN 'Dr. Smith' WHEN 1 THEN 'Dr. Johnson' ELSE 'Dr. Williams' END,
    CASE MOD(SEQ4(), 4) WHEN 0 THEN 'Cardiac Arrhythmia' WHEN 1 THEN 'Hypertension'
        WHEN 2 THEN 'Post-Op Recovery' ELSE 'Respiratory Monitoring' END,
    CASE MOD(SEQ4(), 3) WHEN 0 THEN 'HIGH' WHEN 1 THEN 'MEDIUM' ELSE 'LOW' END,
    ARRAY_CONSTRUCT('ECG-' || LPAD(MOD(SEQ4(), 5) + 1, 3, '0'),
                    'PPG-' || LPAD(MOD(SEQ4(), 5) + 1, 3, '0'))
FROM TABLE(GENERATOR(ROWCOUNT => 10));

-- Device registry
INSERT INTO DEVICE_REGISTRY (DEVICE_ID, DEVICE_TYPE, DEVICE_MODEL, FIRMWARE_VERSION,
    FACILITY_ID, ROOM_ID, CURRENT_PATIENT_ID, STATUS)
SELECT
    CASE MOD(SEQ4(), 3)
        WHEN 0 THEN 'ECG-' || LPAD(SEQ4() + 1, 3, '0')
        WHEN 1 THEN 'EDA-' || LPAD(SEQ4() + 1, 3, '0')
        ELSE 'PPG-' || LPAD(SEQ4() + 1, 3, '0')
    END,
    CASE MOD(SEQ4(), 3) WHEN 0 THEN 'ECG' WHEN 1 THEN 'EDA' ELSE 'PPG' END,
    CASE MOD(SEQ4(), 3) WHEN 0 THEN 'CardioMax Pro' WHEN 1 THEN 'DermaSense Elite' ELSE 'OxiPulse 360' END,
    '2.1.' || MOD(SEQ4(), 5),
    'FACILITY-001',
    'ROOM-' || LPAD(MOD(SEQ4(), 10) + 1, 3, '0'),
    'PATIENT-' || LPAD(MOD(SEQ4(), 5) + 1, 3, '0'),
    'ACTIVE'
FROM TABLE(GENERATOR(ROWCOUNT => 15));

-- ECG data (100 rows, spread over last 30 minutes for 5 patients)
INSERT INTO ECG_DATA (DATA, PATIENT_ID, TIMESTAMP_VAL)
SELECT
    OBJECT_CONSTRUCT(
        'patient_id', 'PATIENT-' || LPAD(MOD(SEQ4(), 5) + 1, 3, '0'),
        'timestamp', DATEADD('SECOND', -SEQ4() * 18, CURRENT_TIMESTAMP())::TIMESTAMP_NTZ,
        'heart_rate', 60 + UNIFORM(0, 40, RANDOM()),
        'lead_I', UNIFORM(-50, 150, RANDOM()) / 100.0,
        'lead_II', UNIFORM(-30, 200, RANDOM()) / 100.0,
        'lead_III', UNIFORM(-80, 120, RANDOM()) / 100.0,
        'lead_V1', UNIFORM(-100, 100, RANDOM()) / 100.0,
        'lead_V2', UNIFORM(-50, 200, RANDOM()) / 100.0,
        'lead_V3', UNIFORM(-50, 250, RANDOM()) / 100.0,
        'lead_V4', UNIFORM(-50, 300, RANDOM()) / 100.0,
        'lead_V5', UNIFORM(-30, 200, RANDOM()) / 100.0,
        'lead_V6', UNIFORM(-30, 150, RANDOM()) / 100.0,
        'rhythm_classification', CASE MOD(SEQ4(), 10)
            WHEN 0 THEN 'Sinus Bradycardia'
            WHEN 1 THEN 'Atrial Fibrillation'
            ELSE 'Normal Sinus Rhythm' END,
        'signal_quality', 0.85 + UNIFORM(0, 15, RANDOM()) / 100.0,
        'qt_interval', 350 + UNIFORM(0, 100, RANDOM()),
        'st_elevation', UNIFORM(-10, 20, RANDOM()) / 100.0,
        'artifacts_detected', CASE WHEN UNIFORM(0, 100, RANDOM()) < 10 THEN TRUE ELSE FALSE END,
        'device_id', 'ECG-' || LPAD(MOD(SEQ4(), 5) + 1, 3, '0'),
        'session_id', 'SESSION-' || LPAD(MOD(SEQ4(), 10), 4, '0')
    )::VARIANT,
    'PATIENT-' || LPAD(MOD(SEQ4(), 5) + 1, 3, '0'),
    DATEADD('SECOND', -SEQ4() * 18, CURRENT_TIMESTAMP())::TIMESTAMP_NTZ
FROM TABLE(GENERATOR(ROWCOUNT => 100));

-- EDA data (100 rows)
INSERT INTO EDA_DATA (DATA, PATIENT_ID, TIMESTAMP_VAL)
SELECT
    OBJECT_CONSTRUCT(
        'patient_id', 'PATIENT-' || LPAD(MOD(SEQ4(), 5) + 1, 3, '0'),
        'timestamp', DATEADD('SECOND', -SEQ4() * 18, CURRENT_TIMESTAMP())::TIMESTAMP_NTZ,
        'stress_indicator', 0.5 + UNIFORM(0, 300, RANDOM()) / 100.0,
        'arousal_level', UNIFORM(10, 90, RANDOM()) / 100.0,
        'skin_conductance_level', 1.0 + UNIFORM(0, 500, RANDOM()) / 100.0,
        'skin_conductance_response', UNIFORM(0, 200, RANDOM()) / 100.0,
        'emotional_valence', CASE MOD(SEQ4(), 5)
            WHEN 0 THEN 'Calm' WHEN 1 THEN 'Neutral' WHEN 2 THEN 'Anxious'
            WHEN 3 THEN 'Stressed' ELSE 'Relaxed' END,
        'signal_quality', 0.80 + UNIFORM(0, 20, RANDOM()) / 100.0,
        'peak_amplitude', UNIFORM(10, 80, RANDOM()) / 100.0,
        'rise_time_ms', 100 + UNIFORM(0, 400, RANDOM()),
        'half_recovery_time_ms', 500 + UNIFORM(0, 2000, RANDOM()),
        'scr_peaks_detected', UNIFORM(0, 5, RANDOM()),
        'temperature_compensation', CASE WHEN UNIFORM(0, 100, RANDOM()) < 80 THEN TRUE ELSE FALSE END,
        'device_id', 'EDA-' || LPAD(MOD(SEQ4(), 5) + 1, 3, '0'),
        'session_id', 'SESSION-' || LPAD(MOD(SEQ4(), 10), 4, '0')
    )::VARIANT,
    'PATIENT-' || LPAD(MOD(SEQ4(), 5) + 1, 3, '0'),
    DATEADD('SECOND', -SEQ4() * 18, CURRENT_TIMESTAMP())::TIMESTAMP_NTZ
FROM TABLE(GENERATOR(ROWCOUNT => 100));

-- PPG data (100 rows)
INSERT INTO PPG_DATA (DATA, PATIENT_ID, TIMESTAMP_VAL)
SELECT
    OBJECT_CONSTRUCT(
        'patient_id', 'PATIENT-' || LPAD(MOD(SEQ4(), 5) + 1, 3, '0'),
        'timestamp', DATEADD('SECOND', -SEQ4() * 18, CURRENT_TIMESTAMP())::TIMESTAMP_NTZ,
        'spo2', 94.0 + UNIFORM(0, 60, RANDOM()) / 10.0,
        'heart_rate', 60 + UNIFORM(0, 40, RANDOM()),
        'blood_pressure_estimate', OBJECT_CONSTRUCT(
            'systolic', 110 + UNIFORM(0, 40, RANDOM()),
            'diastolic', 65 + UNIFORM(0, 25, RANDOM())
        ),
        'pulse_wave_velocity', 5.0 + UNIFORM(0, 40, RANDOM()) / 10.0,
        'arterial_stiffness', UNIFORM(50, 150, RANDOM()) / 100.0,
        'perfusion_index', 0.5 + UNIFORM(0, 150, RANDOM()) / 100.0,
        'signal_quality', 0.82 + UNIFORM(0, 18, RANDOM()) / 100.0,
        'raw_ppg_signal', UNIFORM(-100, 100, RANDOM()) / 100.0,
        'systolic_peak', UNIFORM(50, 150, RANDOM()) / 100.0,
        'diastolic_notch', UNIFORM(20, 80, RANDOM()) / 100.0,
        'motion_artifacts', CASE WHEN UNIFORM(0, 100, RANDOM()) < 15 THEN TRUE ELSE FALSE END,
        'device_id', 'PPG-' || LPAD(MOD(SEQ4(), 5) + 1, 3, '0'),
        'session_id', 'SESSION-' || LPAD(MOD(SEQ4(), 10), 4, '0')
    )::VARIANT,
    'PATIENT-' || LPAD(MOD(SEQ4(), 5) + 1, 3, '0'),
    DATEADD('SECOND', -SEQ4() * 18, CURRENT_TIMESTAMP())::TIMESTAMP_NTZ
FROM TABLE(GENERATOR(ROWCOUNT => 100));

-- =============================================================================
-- TELEMETRY SCHEMA: Device health data
-- =============================================================================

USE SCHEMA MEDICAL_DEVICE_TELEMETRY;

INSERT INTO DEVICE_TELEMETRY (DATA, TIMESTAMP_VAL)
SELECT
    OBJECT_CONSTRUCT(
        'device_id', CASE MOD(SEQ4(), 3)
            WHEN 0 THEN 'ECG-' || LPAD(MOD(SEQ4(), 5) + 1, 3, '0')
            WHEN 1 THEN 'EDA-' || LPAD(MOD(SEQ4(), 5) + 1, 3, '0')
            ELSE 'PPG-' || LPAD(MOD(SEQ4(), 5) + 1, 3, '0')
        END,
        'device_type', CASE MOD(SEQ4(), 3) WHEN 0 THEN 'ECG' WHEN 1 THEN 'EDA' ELSE 'PPG' END,
        'timestamp', DATEADD('SECOND', -SEQ4() * 30, CURRENT_TIMESTAMP())::TIMESTAMP_NTZ,
        'battery_level', 40 + UNIFORM(0, 60, RANDOM()),
        'signal_strength', -30 - UNIFORM(0, 50, RANDOM()),
        'connection_status', CASE WHEN UNIFORM(0, 100, RANDOM()) < 90 THEN 'CONNECTED' ELSE 'INTERMITTENT' END,
        'data_transmission_rate', 800 + UNIFORM(0, 400, RANDOM()),
        'successful_transmissions', 950 + UNIFORM(0, 50, RANDOM()),
        'failed_transmissions', UNIFORM(0, 10, RANDOM()),
        'packet_loss_rate', UNIFORM(0, 30, RANDOM()) / 1000.0,
        'latency_ms', 10 + UNIFORM(0, 40, RANDOM()),
        'cpu_usage', 20 + UNIFORM(0, 50, RANDOM()),
        'memory_usage', 30 + UNIFORM(0, 40, RANDOM()),
        'storage_usage', 10 + UNIFORM(0, 30, RANDOM()),
        'temperature', 35.0 + UNIFORM(0, 80, RANDOM()) / 10.0,
        'uptime_hours', 24 + UNIFORM(0, 200, RANDOM()),
        'maintenance_status', CASE WHEN UNIFORM(0, 100, RANDOM()) < 85 THEN 'OK' ELSE 'DUE_SOON' END,
        'calibration_status', 'CALIBRATED',
        'firmware_version', '2.1.' || MOD(SEQ4(), 5),
        'facility_id', 'FACILITY-001',
        'room_id', 'ROOM-' || LPAD(MOD(SEQ4(), 10) + 1, 3, '0')
    )::VARIANT,
    DATEADD('SECOND', -SEQ4() * 30, CURRENT_TIMESTAMP())::TIMESTAMP_NTZ
FROM TABLE(GENERATOR(ROWCOUNT => 60));
