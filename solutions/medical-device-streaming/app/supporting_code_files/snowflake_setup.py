import sys
import subprocess
import logging
from typing import Optional

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_and_install_dependencies():
    """Check for required packages and install if missing"""
    required_packages = {
        'snowflake-connector-python': 'snowflake.connector',
        'cryptography': 'cryptography',
        'PyJWT': 'jwt',
        'python-dotenv': 'dotenv'
    }
    
    missing_packages = []
    
    logger.info("🔍 Checking Snowflake setup dependencies...")
    
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
            logger.debug(f"✅ {package_name} is installed")
        except ImportError:
            missing_packages.append(package_name)
            logger.warning(f"❌ Missing: {package_name}")
    
    if missing_packages:
        logger.info(f"📦 Installing {len(missing_packages)} missing packages...")
        
        for package in missing_packages:
            try:
                logger.info(f"Installing {package}...")
                subprocess.check_call([
                    sys.executable, '-m', 'pip', 'install', package, '--upgrade'
                ], stdout=subprocess.DEVNULL)
                logger.info(f"✅ Installed {package}")
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ Failed to install {package}: {e}")
                logger.info("💡 Try installing manually:")
                logger.info(f"   pip install {package}")
                return False
    
    logger.info("✅ All Snowflake dependencies are ready")
    return True

# Check dependencies before importing Snowflake modules
if not check_and_install_dependencies():
    logger.error("❌ Dependency check failed. Please install missing packages manually.")
    logger.info("💡 Try running: pip install -r supporting_code_files/requirements.txt")
    sys.exit(1)

# Now safe to import Snowflake modules
try:
    import snowflake.connector
    from supporting_code_files.config import SnowflakeConfig, MedicalDeviceConfig
    logger.info("✅ All core modules imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import required modules: {e}")
    logger.info("💡 Please ensure all dependencies are installed: pip install -r supporting_code_files/requirements.txt")
    sys.exit(1)

class MedicalDeviceSnowflakeSetup:
    """
    Sets up Snowflake database objects for multi-device medical streaming:
    - Database: MEDICAL_DEVICE_DATA
    - Schemas: MEDICAL_DEVICE_CLINICAL_DATA, MEDICAL_DEVICE_TELEMETRY_DATA
    - Device-specific tables for each biosignal type
    - Telemetry tables for device operations
    - PIPE objects for high-performance streaming
    """
    
    def __init__(self, config: SnowflakeConfig = None):
        self.config = config or SnowflakeConfig()
        self.device_config = MedicalDeviceConfig()
        self.connection = None
    
    def connect(self) -> snowflake.connector.SnowflakeConnection:
        """Establish connection to Snowflake with JWT authentication"""
        try:
            # Load private key for JWT authentication
            from supporting_code_files.jwt_utils import load_private_key
            private_key = load_private_key(self.config.PRIVATE_KEY_PATH)
            logger.info(f"🔐 Using JWT authentication with private key: {self.config.PRIVATE_KEY_PATH}")
            
            # Connect using private key authentication (Snowflake connector handles JWT generation internally)
            self.connection = snowflake.connector.connect(
                account=self.config.ACCOUNT,
                user=self.config.USER,
                private_key=private_key,  # Use private key directly
                warehouse=self.config.WAREHOUSE,
                role=self.config.ROLE
            )
            logger.info(f"✅ Successfully connected to Snowflake account: {self.config.ACCOUNT} using JWT authentication")
            return self.connection
        except Exception as e:
            logger.error(f"❌ Failed to connect to Snowflake: {str(e)}")
            logger.error("Make sure you have:")
            logger.error("1. Generated an RSA key pair")
            logger.error("2. Assigned the public key to your Snowflake user")
            logger.error("3. Set SNOWFLAKE_PRIVATE_KEY_PATH in your .env file")
            raise
    
    def execute_sql(self, sql: str, params: Optional[dict] = None) -> list:
        """Execute SQL statement and return results"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"Failed to execute SQL: {str(e)}")
            logger.error(f"SQL: {sql}")
            raise
    
    def create_database_and_schemas(self, replace_existing=False):
        """Create database and schemas for medical device data
        
        Args:
            replace_existing (bool): If True, use CREATE OR REPLACE for complete refresh
        """
        if replace_existing:
            logger.info("Creating database and schemas with REPLACE (full reset)...")
        else:
            logger.info("Creating database and schemas (IF NOT EXISTS)...")
        
        # Create database
        if replace_existing:
            # Full reset approach
            sql = f"CREATE OR REPLACE DATABASE {self.config.DATABASE}"
            logger.info(f"🔄 Replacing database {self.config.DATABASE} (this will drop all existing data!)")
        else:
            # Conservative approach
            sql = f"CREATE DATABASE IF NOT EXISTS {self.config.DATABASE}"
            
        self.execute_sql(sql)
        logger.info(f"Database {self.config.DATABASE} created/verified")
        
        # Use database
        sql = f"USE DATABASE {self.config.DATABASE}"
        self.execute_sql(sql)
        
        # Create schemas
        if replace_existing:
            # Create clinical data schema with replace
            sql = f"CREATE OR REPLACE SCHEMA {self.config.CLINICAL_SCHEMA}"
            self.execute_sql(sql)
            logger.info(f"🔄 Clinical schema {self.config.CLINICAL_SCHEMA} replaced")
            
            # Create telemetry data schema with replace
            sql = f"CREATE OR REPLACE SCHEMA {self.config.TELEMETRY_SCHEMA}"
            self.execute_sql(sql)
            logger.info(f"🔄 Telemetry schema {self.config.TELEMETRY_SCHEMA} replaced")
        else:
            # Create clinical data schema
            sql = f"CREATE SCHEMA IF NOT EXISTS {self.config.CLINICAL_SCHEMA}"
            self.execute_sql(sql)
            logger.info(f"Clinical schema {self.config.CLINICAL_SCHEMA} created/verified")
            
            # Create telemetry data schema
            sql = f"CREATE SCHEMA IF NOT EXISTS {self.config.TELEMETRY_SCHEMA}"
            self.execute_sql(sql)
            logger.info(f"Telemetry schema {self.config.TELEMETRY_SCHEMA} created/verified")
            
        # Grant USAGE permissions on warehouse, database, and schemas (required for streaming)
        self.grant_usage_permissions()
    
    def grant_usage_permissions(self):
        """Grant USAGE permissions on warehouse, database, and schemas (required for Snowpipe Streaming)"""
        logger.info("Granting USAGE permissions for streaming access...")
        
        try:
            # Grant USAGE on WAREHOUSE to both PUBLIC and configured role
            warehouse_grant_public = f"GRANT USAGE ON WAREHOUSE {self.config.WAREHOUSE} TO ROLE PUBLIC"
            self.execute_sql(warehouse_grant_public)
            logger.info(f"✅ Granted USAGE on warehouse {self.config.WAREHOUSE} to PUBLIC role")
            
            if self.config.ROLE != 'PUBLIC':
                warehouse_grant_role = f"GRANT USAGE ON WAREHOUSE {self.config.WAREHOUSE} TO ROLE {self.config.ROLE}"
                self.execute_sql(warehouse_grant_role)
                logger.info(f"✅ Granted USAGE on warehouse {self.config.WAREHOUSE} to {self.config.ROLE} role")
            
            # Grant USAGE on DATABASE to both PUBLIC and configured role
            database_grant_public = f"GRANT USAGE ON DATABASE {self.config.DATABASE} TO ROLE PUBLIC"
            self.execute_sql(database_grant_public)
            logger.info(f"✅ Granted USAGE on database {self.config.DATABASE} to PUBLIC role")
            
            if self.config.ROLE != 'PUBLIC':
                database_grant_role = f"GRANT USAGE ON DATABASE {self.config.DATABASE} TO ROLE {self.config.ROLE}"
                self.execute_sql(database_grant_role)
                logger.info(f"✅ Granted USAGE on database {self.config.DATABASE} to {self.config.ROLE} role")
            
            # Grant USAGE on CLINICAL SCHEMA to both PUBLIC and configured role
            clinical_grant_public = f"GRANT USAGE ON SCHEMA {self.config.DATABASE}.{self.config.CLINICAL_SCHEMA} TO ROLE PUBLIC"
            self.execute_sql(clinical_grant_public)
            logger.info(f"✅ Granted USAGE on clinical schema {self.config.CLINICAL_SCHEMA} to PUBLIC role")
            
            if self.config.ROLE != 'PUBLIC':
                clinical_grant_role = f"GRANT USAGE ON SCHEMA {self.config.DATABASE}.{self.config.CLINICAL_SCHEMA} TO ROLE {self.config.ROLE}"
                self.execute_sql(clinical_grant_role)
                logger.info(f"✅ Granted USAGE on clinical schema {self.config.CLINICAL_SCHEMA} to {self.config.ROLE} role")
            
            # Grant USAGE on TELEMETRY SCHEMA to both PUBLIC and configured role
            telemetry_grant_public = f"GRANT USAGE ON SCHEMA {self.config.DATABASE}.{self.config.TELEMETRY_SCHEMA} TO ROLE PUBLIC"
            self.execute_sql(telemetry_grant_public)
            logger.info(f"✅ Granted USAGE on telemetry schema {self.config.TELEMETRY_SCHEMA} to PUBLIC role")
            
            if self.config.ROLE != 'PUBLIC':
                telemetry_grant_role = f"GRANT USAGE ON SCHEMA {self.config.DATABASE}.{self.config.TELEMETRY_SCHEMA} TO ROLE {self.config.ROLE}"
                self.execute_sql(telemetry_grant_role)
                logger.info(f"✅ Granted USAGE on telemetry schema {self.config.TELEMETRY_SCHEMA} to {self.config.ROLE} role")
                
            logger.info("✅ All USAGE permissions granted successfully!")
            
        except Exception as e:
            logger.error(f"❌ Failed to grant USAGE permissions: {str(e)}")
            # Don't raise - this shouldn't block setup, but will cause streaming issues
            logger.warning("⚠️  Missing USAGE permissions may cause streaming authentication failures")

    def create_patient_management_tables(self):
        """Create patient and session management tables"""
        logger.info("Creating patient management tables...")
        
        # Use clinical schema for patient management
        sql = f"USE SCHEMA {self.config.DATABASE}.{self.config.CLINICAL_SCHEMA}"
        self.execute_sql(sql)
        

        # Create PATIENT_SESSIONS table
        sessions_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.config.PATIENT_SESSIONS_TABLE} (
            session_id VARCHAR(100) PRIMARY KEY,
            patient_id VARCHAR(50) NOT NULL,
            facility_id VARCHAR(50),
            room_id VARCHAR(50),
            
            session_start_time TIMESTAMP_NTZ NOT NULL,
            session_end_time TIMESTAMP_NTZ,
            session_status VARCHAR(20),
            session_type VARCHAR(50),
            
            attending_physician VARCHAR(100),
            primary_condition VARCHAR(100),
            clinical_priority VARCHAR(20),
            
            active_devices ARRAY,
            
            created_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            updated_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
        """
        self.execute_sql(sessions_sql)
        logger.info(f"Table {self.config.PATIENT_SESSIONS_TABLE} created/verified")
        
        # Create DEVICE_REGISTRY table
        registry_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.config.DEVICE_REGISTRY_TABLE} (
            device_id VARCHAR(50) PRIMARY KEY,
            device_type VARCHAR(20) NOT NULL,
            device_model VARCHAR(50),
            firmware_version VARCHAR(20),
            facility_id VARCHAR(50),
            room_id VARCHAR(50),
            
            current_patient_id VARCHAR(50),
            current_session_id VARCHAR(100),
            assignment_timestamp TIMESTAMP_NTZ,
            
            sampling_rates ARRAY,
            supported_features VARIANT,
            
            status VARCHAR(20),
            last_maintenance_date DATE,
            next_maintenance_due DATE,
            
            created_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
        """
        self.execute_sql(registry_sql)
        logger.info(f"Table {self.config.DEVICE_REGISTRY_TABLE} created/verified")
    
    def create_device_specific_tables(self):
        """Create device-specific data tables dynamically based on configuration"""
        logger.info("Creating device-specific data tables...")
        
        sql = f"USE SCHEMA {self.config.DATABASE}.{self.config.CLINICAL_SCHEMA}"
        self.execute_sql(sql)
        
        # Define raw data table schemas for JSON ingestion (matching pipe expectations)
        table_schemas = {
            'ECG': f"""
                    CREATE TABLE IF NOT EXISTS {self.config.DEVICE_TABLES['ECG']} (
            DATA VARIANT NOT NULL,
            PATIENT_ID VARCHAR(50) NOT NULL,
            TIMESTAMP_VAL TIMESTAMP_NTZ NOT NULL,
            load_utc_timestamp TIMESTAMP_NTZ DEFAULT CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP())::TIMESTAMP_NTZ,
            app_ingestion_timestamp TIMESTAMP_NTZ
        )
            """,
            
            'EDA': f"""
            CREATE TABLE IF NOT EXISTS {self.config.DEVICE_TABLES['EDA']} (
                DATA VARIANT NOT NULL,
                PATIENT_ID VARCHAR(50) NOT NULL,
                TIMESTAMP_VAL TIMESTAMP_NTZ NOT NULL,
                load_utc_timestamp TIMESTAMP_NTZ DEFAULT CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP())::TIMESTAMP_NTZ,
                app_ingestion_timestamp TIMESTAMP_NTZ
            )
            """,
            
            'PPG': f"""
            CREATE TABLE IF NOT EXISTS {self.config.DEVICE_TABLES['PPG']} (
                DATA VARIANT NOT NULL,
                PATIENT_ID VARCHAR(50) NOT NULL,
                TIMESTAMP_VAL TIMESTAMP_NTZ NOT NULL,
                load_utc_timestamp TIMESTAMP_NTZ DEFAULT CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP())::TIMESTAMP_NTZ,
                app_ingestion_timestamp TIMESTAMP_NTZ
            )
            """
        }
        
        # Create tables only for configured devices
        for device_type, table_name in self.config.DEVICE_TABLES.items():
            if device_type in table_schemas:
                self.execute_sql(table_schemas[device_type])
                logger.info(f"{device_type} data table created/verified")
                
                # Grant INSERT permissions for streaming
                self.grant_table_insert_permissions(
                    schema=self.config.CLINICAL_SCHEMA,
                    table=table_name,
                    device_type=device_type
                )
            else:
                logger.warning(f"No schema defined for device type: {device_type}")
    
    def create_telemetry_table(self):
        """Create device telemetry table"""
        logger.info("Creating device telemetry table...")
        
        # Use telemetry schema
        sql = f"USE SCHEMA {self.config.DATABASE}.{self.config.TELEMETRY_SCHEMA}"
        self.execute_sql(sql)
        
        telemetry_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.config.TELEMETRY_TABLE} (
            DATA VARIANT NOT NULL,
            TIMESTAMP_VAL TIMESTAMP_NTZ NOT NULL,
            load_utc_timestamp TIMESTAMP_NTZ DEFAULT CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP())::TIMESTAMP_NTZ,
            app_ingestion_timestamp TIMESTAMP_NTZ
        )
        """
        self.execute_sql(telemetry_sql)
        logger.info(f"Device telemetry table created/verified")
        
        # Grant INSERT permissions for streaming
        self.grant_table_insert_permissions(
            schema=self.config.TELEMETRY_SCHEMA,
            table=self.config.TELEMETRY_TABLE,
            device_type="TELEMETRY"
        )
    
    def grant_table_insert_permissions(self, schema: str, table: str, device_type: str):
        """Grant INSERT permissions on tables for Snowpipe Streaming"""
        logger.info(f"Granting INSERT permissions on {schema}.{table}...")
        
        try:
            # Grant INSERT to PUBLIC role (required for Snowpipe Streaming)
            grant_sql = f"GRANT INSERT ON TABLE {self.config.DATABASE}.{schema}.{table} TO ROLE PUBLIC"
            self.execute_sql(grant_sql) 
            logger.info(f"✅ Granted INSERT permission on {schema}.{table} to PUBLIC role")
            
            # Also grant to the configured role if different from PUBLIC
            if self.config.ROLE != 'PUBLIC':
                role_grant_sql = f"GRANT INSERT ON TABLE {self.config.DATABASE}.{schema}.{table} TO ROLE {self.config.ROLE}"
                self.execute_sql(role_grant_sql)
                logger.info(f"✅ Granted INSERT permission on {schema}.{table} to {self.config.ROLE} role")
                
        except Exception as e:
            logger.error(f"❌ Failed to grant INSERT permissions on {schema}.{table}: {str(e)}")
            # Don't raise - this shouldn't block setup, but will cause streaming issues
    
    def create_streaming_pipes(self):
        """Create Snowpipe Streaming PIPE objects for high-performance ingestion"""
        logger.info("Creating Snowpipe Streaming PIPE objects...")
        
        # Use clinical schema for pipe creation
        sql = f"USE SCHEMA {self.config.DATABASE}.{self.config.CLINICAL_SCHEMA}"
        self.execute_sql(sql)
        
        # Create a pipe for each device type
        for device_type, table_name in self.config.DEVICE_TABLES.items():
            pipe_name = self.config.DEVICE_PIPES[device_type]
            
            # Drop pipe if it exists
            drop_sql = f"DROP PIPE IF EXISTS {pipe_name}"
            self.execute_sql(drop_sql)
            
            # Create Snowpipe Streaming pipe with correct syntax including app_ingestion_timestamp
            create_sql = f"""
            CREATE PIPE {pipe_name}
            AS
            COPY INTO {table_name} (DATA, PATIENT_ID, TIMESTAMP_VAL, APP_INGESTION_TIMESTAMP)
            FROM (
                SELECT $1, $1:patient_id, $1:timestamp, $1:app_ingestion_timestamp::TIMESTAMP_NTZ
                FROM TABLE(DATA_SOURCE(TYPE => 'STREAMING'))
            )
            """
            
            self.execute_sql(create_sql)
            logger.info(f"PIPE {pipe_name} created for {device_type} -> {table_name}")
            
            # Grant necessary privileges to both PUBLIC and configured role
            # Grant to PUBLIC role (required for Snowpipe Streaming)
            public_operate_sql = f"GRANT OPERATE ON PIPE {pipe_name} TO ROLE PUBLIC"
            self.execute_sql(public_operate_sql)
            public_monitor_sql = f"GRANT MONITOR ON PIPE {pipe_name} TO ROLE PUBLIC"
            self.execute_sql(public_monitor_sql)
            
            # Also grant to configured role if different from PUBLIC
            if self.config.ROLE != 'PUBLIC':
                grant_sql = f"GRANT OPERATE ON PIPE {pipe_name} TO ROLE {self.config.ROLE}"
                self.execute_sql(grant_sql)
                grant_monitor_sql = f"GRANT MONITOR ON PIPE {pipe_name} TO ROLE {self.config.ROLE}"
                self.execute_sql(grant_monitor_sql)
        
        # Create telemetry pipe
        telemetry_pipe = self.config.TELEMETRY_PIPE
        sql = f"USE SCHEMA {self.config.DATABASE}.{self.config.TELEMETRY_SCHEMA}"
        self.execute_sql(sql)
        
        drop_sql = f"DROP PIPE IF EXISTS {telemetry_pipe}"
        self.execute_sql(drop_sql)
        
        create_sql = f"""
        CREATE PIPE {telemetry_pipe}
        AS
        COPY INTO {self.config.TELEMETRY_TABLE} (DATA, TIMESTAMP_VAL, APP_INGESTION_TIMESTAMP)
        FROM (
            SELECT $1, $1:timestamp, $1:app_ingestion_timestamp::TIMESTAMP_NTZ
            FROM TABLE(DATA_SOURCE(TYPE => 'STREAMING'))
        )
        """
        
        self.execute_sql(create_sql)
        logger.info(f"PIPE {telemetry_pipe} created for telemetry data")
        
        # Grant privileges for telemetry pipe to both PUBLIC and configured role
        # Grant to PUBLIC role (required for Snowpipe Streaming)
        public_operate_sql = f"GRANT OPERATE ON PIPE {telemetry_pipe} TO ROLE PUBLIC"
        self.execute_sql(public_operate_sql)
        public_monitor_sql = f"GRANT MONITOR ON PIPE {telemetry_pipe} TO ROLE PUBLIC"
        self.execute_sql(public_monitor_sql)
        
        # Also grant to configured role if different from PUBLIC
        if self.config.ROLE != 'PUBLIC':
            grant_sql = f"GRANT OPERATE ON PIPE {telemetry_pipe} TO ROLE {self.config.ROLE}"
            self.execute_sql(grant_sql)
            grant_monitor_sql = f"GRANT MONITOR ON PIPE {telemetry_pipe} TO ROLE {self.config.ROLE}"
            self.execute_sql(grant_monitor_sql)
    
    def create_flattened_views(self):
        """Create flattened views that extract key metrics from JSON data into regular columns"""
        logger.info("Creating flattened views for efficient data access...")
        
        # Create ECG flattened view
        logger.info("Creating ECG_DATA_FLATTENED view...")
        sql = f"USE SCHEMA {self.config.DATABASE}.{self.config.CLINICAL_SCHEMA}"
        self.execute_sql(sql)
        
        ecg_view_sql = f"""
        CREATE OR REPLACE VIEW ECG_DATA_FLATTENED AS
        SELECT 
            PATIENT_ID,
            TIMESTAMP_VAL,
            DATA:heart_rate::NUMBER AS HEART_RATE,
            DATA:lead_I::FLOAT AS LEAD_I,
            DATA:lead_II::FLOAT AS LEAD_II,
            DATA:lead_III::FLOAT AS LEAD_III,
            DATA:lead_V1::FLOAT AS LEAD_V1,
            DATA:lead_V2::FLOAT AS LEAD_V2,
            DATA:lead_V3::FLOAT AS LEAD_V3,
            DATA:lead_V4::FLOAT AS LEAD_V4,
            DATA:lead_V5::FLOAT AS LEAD_V5,
            DATA:lead_V6::FLOAT AS LEAD_V6,
            DATA:rhythm_classification::STRING AS RHYTHM_CLASSIFICATION,
            DATA:signal_quality::FLOAT AS SIGNAL_QUALITY,
            DATA:qt_interval::NUMBER AS QT_INTERVAL,
            DATA:st_elevation::FLOAT AS ST_ELEVATION,
            DATA:artifacts_detected::BOOLEAN AS ARTIFACTS_DETECTED,
            DATA:device_id::STRING AS DEVICE_ID,
            DATA:session_id::STRING AS SESSION_ID
        FROM ECG_DATA
        """
        self.execute_sql(ecg_view_sql)
        logger.info("✅ ECG_DATA_FLATTENED view created")
        
        # Create EDA flattened view
        logger.info("Creating EDA_DATA_FLATTENED view...")
        eda_view_sql = f"""
        CREATE OR REPLACE VIEW EDA_DATA_FLATTENED AS
        SELECT 
            PATIENT_ID,
            TIMESTAMP_VAL,
            DATA:stress_indicator::FLOAT AS STRESS_LEVEL,
            DATA:arousal_level::FLOAT AS AROUSAL_LEVEL,
            DATA:skin_conductance_level::FLOAT AS SKIN_CONDUCTANCE_LEVEL,
            DATA:skin_conductance_response::FLOAT AS SKIN_CONDUCTANCE_RESPONSE,
            DATA:emotional_valence::STRING AS EMOTIONAL_VALENCE,
            DATA:signal_quality::FLOAT AS SIGNAL_QUALITY,
            DATA:peak_amplitude::FLOAT AS PEAK_AMPLITUDE,
            DATA:rise_time_ms::NUMBER AS RISE_TIME_MS,
            DATA:half_recovery_time_ms::NUMBER AS HALF_RECOVERY_TIME_MS,
            DATA:scr_peaks_detected::NUMBER AS SCR_PEAKS_DETECTED,
            DATA:temperature_compensation::BOOLEAN AS TEMPERATURE_COMPENSATION,
            DATA:device_id::STRING AS DEVICE_ID,
            DATA:session_id::STRING AS SESSION_ID
        FROM EDA_DATA
        """
        self.execute_sql(eda_view_sql)
        logger.info("✅ EDA_DATA_FLATTENED view created")
        
        # Create PPG flattened view
        logger.info("Creating PPG_DATA_FLATTENED view...")
        ppg_view_sql = f"""
        CREATE OR REPLACE VIEW PPG_DATA_FLATTENED AS
        SELECT 
            PATIENT_ID,
            TIMESTAMP_VAL,
            DATA:spo2::FLOAT AS SPO2,
            DATA:heart_rate::NUMBER AS HEART_RATE,
            DATA:blood_pressure_estimate.systolic::NUMBER AS SYSTOLIC_BP,
            DATA:blood_pressure_estimate.diastolic::NUMBER AS DIASTOLIC_BP,
            DATA:pulse_wave_velocity::FLOAT AS PULSE_WAVE_VELOCITY,
            DATA:arterial_stiffness::FLOAT AS ARTERIAL_STIFFNESS,
            DATA:perfusion_index::FLOAT AS PERFUSION_INDEX, 
            DATA:signal_quality::FLOAT AS SIGNAL_QUALITY,
            DATA:raw_ppg_signal::FLOAT AS RAW_PPG_SIGNAL,
            DATA:systolic_peak::FLOAT AS SYSTOLIC_PEAK,
            DATA:diastolic_notch::FLOAT AS DIASTOLIC_NOTCH,
            DATA:motion_artifacts::BOOLEAN AS MOTION_ARTIFACTS,
            DATA:device_id::STRING AS DEVICE_ID,
            DATA:session_id::STRING AS SESSION_ID
        FROM PPG_DATA
        """
        self.execute_sql(ppg_view_sql)
        logger.info("✅ PPG_DATA_FLATTENED view created")
        
        # Create Device Telemetry flattened view (no PATIENT_ID since it's device-focused)
        logger.info("Creating DEVICE_TELEMETRY_FLATTENED view...")
        sql = f"USE SCHEMA {self.config.DATABASE}.{self.config.TELEMETRY_SCHEMA}"
        self.execute_sql(sql)
        
        telemetry_view_sql = f"""
        CREATE OR REPLACE VIEW DEVICE_TELEMETRY_FLATTENED AS
        SELECT 
            TIMESTAMP_VAL,
            DATA:device_id::STRING AS DEVICE_ID,
            DATA:device_type::STRING AS DEVICE_TYPE,
            DATA:battery_level::NUMBER AS BATTERY_LEVEL,
            DATA:signal_strength::NUMBER AS SIGNAL_STRENGTH,
            DATA:connection_status::STRING AS CONNECTION_STATUS,
            DATA:data_transmission_rate::FLOAT AS DATA_TRANSMISSION_RATE,
            DATA:successful_transmissions::NUMBER AS SUCCESSFUL_TRANSMISSIONS,
            DATA:failed_transmissions::NUMBER AS FAILED_TRANSMISSIONS,
            DATA:packet_loss_rate::FLOAT AS PACKET_LOSS_RATE,
            DATA:latency_ms::NUMBER AS LATENCY_MS,
            DATA:cpu_usage::FLOAT AS CPU_USAGE,
            DATA:memory_usage::FLOAT AS MEMORY_USAGE,
            DATA:storage_usage::FLOAT AS STORAGE_USAGE,
            DATA:temperature::FLOAT AS TEMPERATURE,
            DATA:uptime_hours::FLOAT AS UPTIME_HOURS,
            DATA:maintenance_status::STRING AS MAINTENANCE_STATUS,
            DATA:calibration_status::STRING AS CALIBRATION_STATUS,
            DATA:firmware_version::STRING AS FIRMWARE_VERSION,
            DATA:facility_id::STRING AS FACILITY_ID,
            DATA:room_id::STRING AS ROOM_ID
        FROM DEVICE_TELEMETRY
        """
        self.execute_sql(telemetry_view_sql)
        logger.info("✅ DEVICE_TELEMETRY_FLATTENED view created")
        
        logger.info("✅ All flattened views created successfully!")
        logger.info("Available flattened views:")
        logger.info(f"  - {self.config.CLINICAL_SCHEMA}.ECG_DATA_FLATTENED")
        logger.info(f"  - {self.config.CLINICAL_SCHEMA}.EDA_DATA_FLATTENED")
        logger.info(f"  - {self.config.CLINICAL_SCHEMA}.PPG_DATA_FLATTENED")
        logger.info(f"  - {self.config.TELEMETRY_SCHEMA}.DEVICE_TELEMETRY_FLATTENED")
    
    def create_patient_vital_signs_view(self):
        """Create consolidated PATIENT_VITAL_SIGNS view using ASOF joins for complete patient monitoring"""
        logger.info("Creating PATIENT_VITAL_SIGNS consolidated view...")
        
        # Use clinical schema
        sql = f"USE SCHEMA {self.config.DATABASE}.{self.config.CLINICAL_SCHEMA}"
        self.execute_sql(sql)
        
        # Create the consolidated patient vital signs view
        patient_vital_signs_sql = """
        CREATE OR REPLACE VIEW PATIENT_VITAL_SIGNS AS
        WITH patient_list AS (
            -- Get all patients who have data in any device table
            SELECT DISTINCT PATIENT_ID
            FROM (
                SELECT PATIENT_ID FROM ECG_DATA_FLATTENED
                UNION ALL
                SELECT PATIENT_ID FROM EDA_DATA_FLATTENED  
                UNION ALL
                SELECT PATIENT_ID FROM PPG_DATA_FLATTENED
            )
            WHERE PATIENT_ID IS NOT NULL
        ),
        time_sequence AS (
            -- Generate 300 seconds (5 minutes) ending at current time for real-time view
            -- This captures streaming data as it arrives
            SELECT 
                DATEADD('SECOND', -ROW_NUMBER() OVER (ORDER BY SEQ4()) + 1, 
                       CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP())::TIMESTAMP_NTZ) AS TIMESTAMP_SEC
            FROM TABLE(GENERATOR(ROWCOUNT => 300))
        ),
        time_spine AS (
            -- Create complete 5-minute time spine for each patient (patient x 300 seconds = complete coverage)
            SELECT 
                p.PATIENT_ID,
                t.TIMESTAMP_SEC
            FROM patient_list p
            CROSS JOIN time_sequence t
        )
        SELECT 
            spine.PATIENT_ID,
            spine.TIMESTAMP_SEC,
            
            -- ECG-derived vital signs: Use exact data if available, otherwise propagate
            COALESCE(ecg_exact.HEART_RATE, ecg_propagated.HEART_RATE) AS ECG_HEART_RATE,
            COALESCE(ecg_exact.RHYTHM_CLASSIFICATION, ecg_propagated.RHYTHM_CLASSIFICATION) AS RHYTHM_CLASSIFICATION,
            COALESCE(ecg_exact.QT_INTERVAL, ecg_propagated.QT_INTERVAL) AS QT_INTERVAL,
            COALESCE(ecg_exact.ST_ELEVATION, ecg_propagated.ST_ELEVATION) AS ST_ELEVATION,
            COALESCE(ecg_exact.SIGNAL_QUALITY, ecg_propagated.SIGNAL_QUALITY) AS ECG_SIGNAL_QUALITY,
            COALESCE(ecg_exact.ARTIFACTS_DETECTED, ecg_propagated.ARTIFACTS_DETECTED) AS ECG_ARTIFACTS,
            COALESCE(ecg_exact.DEVICE_ID, ecg_propagated.DEVICE_ID) AS ECG_DEVICE_ID,
            COALESCE(ecg_exact.SESSION_ID, ecg_propagated.SESSION_ID) AS ECG_SESSION_ID,
            
            -- EDA-derived vital signs: Use exact data if available, otherwise propagate
            COALESCE(eda_exact.STRESS_LEVEL, eda_propagated.STRESS_LEVEL) AS STRESS_LEVEL,
            COALESCE(eda_exact.AROUSAL_LEVEL, eda_propagated.AROUSAL_LEVEL) AS AROUSAL_LEVEL,
            COALESCE(eda_exact.SKIN_CONDUCTANCE_LEVEL, eda_propagated.SKIN_CONDUCTANCE_LEVEL) AS SKIN_CONDUCTANCE_LEVEL,
            COALESCE(eda_exact.SKIN_CONDUCTANCE_RESPONSE, eda_propagated.SKIN_CONDUCTANCE_RESPONSE) AS SKIN_CONDUCTANCE_RESPONSE,
            COALESCE(eda_exact.EMOTIONAL_VALENCE, eda_propagated.EMOTIONAL_VALENCE) AS EMOTIONAL_VALENCE,
            COALESCE(eda_exact.SIGNAL_QUALITY, eda_propagated.SIGNAL_QUALITY) AS EDA_SIGNAL_QUALITY,
            COALESCE(eda_exact.DEVICE_ID, eda_propagated.DEVICE_ID) AS EDA_DEVICE_ID,
            COALESCE(eda_exact.SESSION_ID, eda_propagated.SESSION_ID) AS EDA_SESSION_ID,
            
            -- PPG-derived vital signs: Use exact data if available, otherwise propagate
            COALESCE(ppg_exact.SPO2, ppg_propagated.SPO2) AS SPO2,
            COALESCE(ppg_exact.HEART_RATE, ppg_propagated.HEART_RATE) AS PPG_HEART_RATE,
            COALESCE(ppg_exact.SYSTOLIC_BP, ppg_propagated.SYSTOLIC_BP) AS SYSTOLIC_BP,
            COALESCE(ppg_exact.DIASTOLIC_BP, ppg_propagated.DIASTOLIC_BP) AS DIASTOLIC_BP,
            COALESCE(ppg_exact.PULSE_WAVE_VELOCITY, ppg_propagated.PULSE_WAVE_VELOCITY) AS PULSE_WAVE_VELOCITY,
            COALESCE(ppg_exact.ARTERIAL_STIFFNESS, ppg_propagated.ARTERIAL_STIFFNESS) AS ARTERIAL_STIFFNESS,
            COALESCE(ppg_exact.PERFUSION_INDEX, ppg_propagated.PERFUSION_INDEX) AS PERFUSION_INDEX,
            COALESCE(ppg_exact.SIGNAL_QUALITY, ppg_propagated.SIGNAL_QUALITY) AS PPG_SIGNAL_QUALITY,
            COALESCE(ppg_exact.MOTION_ARTIFACTS, ppg_propagated.MOTION_ARTIFACTS) AS PPG_MOTION_ARTIFACTS,
            COALESCE(ppg_exact.DEVICE_ID, ppg_propagated.DEVICE_ID) AS PPG_DEVICE_ID,
            COALESCE(ppg_exact.SESSION_ID, ppg_propagated.SESSION_ID) AS PPG_SESSION_ID,
            
            -- Source timestamps: Show when the actual data was recorded (for propagated values)
            COALESCE(ecg_exact.TIMESTAMP_VAL, ecg_propagated.TIMESTAMP_VAL) AS ECG_SOURCE_TIMESTAMP,
            COALESCE(eda_exact.TIMESTAMP_VAL, eda_propagated.TIMESTAMP_VAL) AS EDA_SOURCE_TIMESTAMP,
            COALESCE(ppg_exact.TIMESTAMP_VAL, ppg_propagated.TIMESTAMP_VAL) AS PPG_SOURCE_TIMESTAMP,
            
            -- Data freshness indicators (seconds since actual reading)
            CASE 
                WHEN ecg_exact.TIMESTAMP_VAL IS NOT NULL THEN 0
                WHEN ecg_propagated.TIMESTAMP_VAL IS NOT NULL THEN 
                    TIMESTAMPDIFF('second', ecg_propagated.TIMESTAMP_VAL, spine.TIMESTAMP_SEC)
                ELSE NULL
            END AS ECG_AGE_SECONDS,
            
            CASE 
                WHEN eda_exact.TIMESTAMP_VAL IS NOT NULL THEN 0
                WHEN eda_propagated.TIMESTAMP_VAL IS NOT NULL THEN 
                    TIMESTAMPDIFF('second', eda_propagated.TIMESTAMP_VAL, spine.TIMESTAMP_SEC)
                ELSE NULL
            END AS EDA_AGE_SECONDS,
            
            CASE 
                WHEN ppg_exact.TIMESTAMP_VAL IS NOT NULL THEN 0
                WHEN ppg_propagated.TIMESTAMP_VAL IS NOT NULL THEN 
                    TIMESTAMPDIFF('second', ppg_propagated.TIMESTAMP_VAL, spine.TIMESTAMP_SEC)
                ELSE NULL
            END AS PPG_AGE_SECONDS

        FROM time_spine spine

        -- EXACT MATCH JOINS: First try to get real data for the exact timestamp
        LEFT JOIN ECG_DATA_FLATTENED ecg_exact
            ON spine.PATIENT_ID = ecg_exact.PATIENT_ID 
            AND spine.TIMESTAMP_SEC = ecg_exact.TIMESTAMP_VAL

        LEFT JOIN EDA_DATA_FLATTENED eda_exact
            ON spine.PATIENT_ID = eda_exact.PATIENT_ID 
            AND spine.TIMESTAMP_SEC = eda_exact.TIMESTAMP_VAL

        LEFT JOIN PPG_DATA_FLATTENED ppg_exact
            ON spine.PATIENT_ID = ppg_exact.PATIENT_ID 
            AND spine.TIMESTAMP_SEC = ppg_exact.TIMESTAMP_VAL

        -- ASOF JOIN FOR PROPAGATION: Only when exact data doesn't exist
        ASOF JOIN ECG_DATA_FLATTENED ecg_propagated
            MATCH_CONDITION(spine.TIMESTAMP_SEC >= ecg_propagated.TIMESTAMP_VAL)
            ON spine.PATIENT_ID = ecg_propagated.PATIENT_ID

        ASOF JOIN EDA_DATA_FLATTENED eda_propagated
            MATCH_CONDITION(spine.TIMESTAMP_SEC >= eda_propagated.TIMESTAMP_VAL)
            ON spine.PATIENT_ID = eda_propagated.PATIENT_ID

        ASOF JOIN PPG_DATA_FLATTENED ppg_propagated
            MATCH_CONDITION(spine.TIMESTAMP_SEC >= ppg_propagated.TIMESTAMP_VAL)
            ON spine.PATIENT_ID = ppg_propagated.PATIENT_ID

        -- Show all rows including those with no data available (NULL values)
        -- This ensures complete 5-minute coverage even when data is not available

        ORDER BY spine.PATIENT_ID, spine.TIMESTAMP_SEC
        """
        
        self.execute_sql(patient_vital_signs_sql)
        logger.info("✅ PATIENT_VITAL_SIGNS consolidated view created")
        logger.info("   Features:")
        logger.info("   - 5-minute real-time window with second-by-second coverage")
        logger.info("   - ASOF joins for data propagation (forward-fill)")
        logger.info("   - Exact matches prioritized over propagated values")
        logger.info("   - Complete coverage even when no data is available")
        logger.info("   - All ECG, EDA, and PPG vital signs consolidated")
    
    def drop_existing_tables(self):
        """Drop existing tables to allow CREATE IF NOT EXISTS to recreate with updated schema"""
        logger.info("🗑️  Dropping existing tables to update schema with UTC timezone conversion...")
        
        # Set database context 
        logger.info(f"📊 Using database: {self.config.DATABASE}")
        self.execute_sql(f"USE DATABASE {self.config.DATABASE}")
        
        # Define tables to drop
        tables_to_drop = [
            # Clinical data tables
            f"{self.config.CLINICAL_SCHEMA}.ECG_DATA",
            f"{self.config.CLINICAL_SCHEMA}.EDA_DATA", 
            f"{self.config.CLINICAL_SCHEMA}.PPG_DATA",
            # Telemetry data table
            f"{self.config.TELEMETRY_SCHEMA}.DEVICE_TELEMETRY"
        ]
        
        # Drop tables
        for table_name in tables_to_drop:
            try:
                logger.info(f"   Dropping {table_name}...")
                drop_sql = f"DROP TABLE IF EXISTS {table_name}"
                self.execute_sql(drop_sql)
                logger.info(f"   ✅ Successfully dropped {table_name}")
            except Exception as e:
                logger.error(f"   ❌ Failed to drop {table_name}: {str(e)}")
                raise
        
        logger.info("🎉 Table drop completed! Tables will be recreated with updated UTC timezone schema.")

    def setup_complete_infrastructure(self, replace_existing=False):
        """Complete setup of Snowflake infrastructure for medical device streaming
        
        Args:
            replace_existing (bool): If True, performs a complete fresh setup with CREATE OR REPLACE
        """
        try:
            self.connect()
            
            if replace_existing:
                logger.info("🚀 Performing COMPLETE FRESH SETUP with CREATE OR REPLACE...")
                logger.warning("⚠️  This will replace all existing database objects and data!")
            
            self.create_database_and_schemas(replace_existing=replace_existing)
            self.create_patient_management_tables()
            self.create_device_specific_tables()
            self.create_telemetry_table()
            
            # Add back the pipe creation (was removed but needed for V1 compatibility)
            self.create_streaming_pipes()
            
            # Create flattened views for efficient data access (these always use CREATE OR REPLACE)
            self.create_flattened_views()
            
            # Create consolidated patient vital signs view (depends on flattened views)
            self.create_patient_vital_signs_view()
            
            setup_type = "FRESH SETUP" if replace_existing else "INCREMENTAL SETUP"
            logger.info(f"✅ Medical device infrastructure {setup_type} completed successfully!")
            logger.info(f"Database: {self.config.DATABASE}")
            logger.info(f"Clinical Schema: {self.config.CLINICAL_SCHEMA}")
            logger.info(f"Telemetry Schema: {self.config.TELEMETRY_SCHEMA}")
            logger.info(f"Device Tables: {list(self.config.DEVICE_TABLES.keys())}")
            logger.info(f"Device Pipes: {list(self.config.DEVICE_PIPES.keys())}")
            logger.info("Using Snowpipe Streaming with PIPE objects (V1 compatible)")
            logger.info("📊 Flattened views created for dashboard efficiency")
            logger.info("🩺 PATIENT_VITAL_SIGNS view created for consolidated monitoring")
            logger.info("   - Real-time 5-minute window with ASOF joins")
            logger.info("   - Complete ECG, EDA, PPG vital sign integration")
            
            if replace_existing:
                logger.info("🎉 Fresh setup complete - all objects recreated from scratch!")
            else:
                logger.info("✅ Incremental setup complete - existing objects preserved")
                
        except Exception as e:
            logger.error(f"❌ Setup failed: {str(e)}")
            raise
        finally:
            if self.connection:
                self.connection.close()
    
    def setup_fresh_infrastructure(self):
        """Convenience method for complete fresh setup with CREATE OR REPLACE"""
        logger.info("🆕 Starting FRESH INFRASTRUCTURE SETUP...")
        return self.setup_complete_infrastructure(replace_existing=True)

def main():
    """Main setup function with support for different setup modes"""
    import sys
    
    # Parse command line arguments
    setup_mode = "normal"
    if len(sys.argv) > 1:
        setup_mode = sys.argv[1]
    
    setup = MedicalDeviceSnowflakeSetup()
    
    try:
        if setup_mode == "drop_tables":
            # Special mode: drop existing tables to allow schema updates
            logger.info("🚀 Running table drop for schema update...")
            setup.connect()
            setup.drop_existing_tables()
            logger.info("✅ Table drop completed successfully!")
            
        elif setup_mode == "fresh" or setup_mode == "--fresh":
            # Fresh setup mode: CREATE OR REPLACE everything
            logger.info("🆕 Running FRESH SETUP with CREATE OR REPLACE...")
            logger.warning("⚠️  This will replace all existing database objects and data!")
            
            # Ask for confirmation unless --force is provided
            if "--force" not in sys.argv:
                response = input("Are you sure you want to proceed? (y/N): ").strip().lower()
                if response != 'y' and response != 'yes':
                    logger.info("❌ Fresh setup cancelled by user")
                    return 1
                    
            setup.setup_fresh_infrastructure()
            
        elif setup_mode == "help" or setup_mode == "--help":
            # Help mode
            print("🏥 Medical Device Snowflake Setup")
            print("=" * 50)
            print("Usage: python snowflake_setup.py [mode]")
            print()
            print("Available modes:")
            print("  (none)      - Normal incremental setup (CREATE IF NOT EXISTS)")
            print("  fresh       - Fresh setup with CREATE OR REPLACE (destructive)")
            print("  drop_tables - Drop existing tables only")
            print("  help        - Show this help message")
            print()
            print("Options:")
            print("  --force     - Skip confirmation prompt for fresh setup")
            print()
            print("Examples:")
            print("  python snowflake_setup.py                # Normal setup")
            print("  python snowflake_setup.py fresh          # Fresh setup with prompt")
            print("  python snowflake_setup.py fresh --force  # Fresh setup without prompt")
            return 0
            
        else:
            # Normal mode: incremental infrastructure setup (default)
            logger.info("🔧 Running NORMAL SETUP (CREATE IF NOT EXISTS)...")
            setup.setup_complete_infrastructure(replace_existing=False)
            
    except KeyboardInterrupt:
        logger.info("❌ Setup cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Setup failed: {str(e)}")
        return 1
    finally:
        if setup.connection:
            setup.connection.close()
            
    return 0

if __name__ == "__main__":
    main() 