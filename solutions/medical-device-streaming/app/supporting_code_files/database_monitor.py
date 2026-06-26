#!/usr/bin/env python3
"""
Database Monitor
================

Monitors Snowflake database tables to retrieve record counts and statistics
for the Streamlit dashboard.
"""

import sys
import os
import logging
from typing import Dict, Optional
import snowflake.connector
import pandas as pd
from datetime import datetime, timedelta

# Project modules are now in the same directory - no path manipulation needed

from supporting_code_files.config import SnowflakeConfig

class DatabaseMonitor:
    """
    Monitors Snowflake database tables for record counts and statistics.
    """
    
    def __init__(self):
        self.config = SnowflakeConfig()
        self.logger = logging.getLogger(__name__)
        self._connection = None
        
    def _get_connection(self) -> snowflake.connector.SnowflakeConnection:
        """
        Get or create a Snowflake connection.
        
        Returns:
            SnowflakeConnection: Active connection to Snowflake
        """
        try:
            # Check if connection exists and is still valid
            if self._connection and not self._connection.is_closed():
                return self._connection
            
            # Create new connection
            connection_params = {
                'account': self.config.ACCOUNT,
                'user': self.config.USER,
                'database': self.config.DATABASE,
                'warehouse': self.config.WAREHOUSE,
                'role': self.config.ROLE
            }
            
            # Add JWT authentication using private key
            if self.config.PRIVATE_KEY_PATH:
                private_key = self._load_private_key()
                connection_params['private_key'] = private_key
            else:
                raise Exception("SNOWFLAKE_PRIVATE_KEY_PATH not configured. Private key authentication is required.")
            
            self._connection = snowflake.connector.connect(**connection_params)
            self.logger.info("✅ Database connection established")
            return self._connection
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Snowflake: {str(e)}")
            raise
    
    def _load_private_key(self):
        """Load private key for authentication"""
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.serialization import load_pem_private_key
            
            with open(self.config.PRIVATE_KEY_PATH, 'rb') as key_file:
                private_key = load_pem_private_key(
                    key_file.read(),
                    password=None  # Assuming no password
                )
            return private_key
        except Exception as e:
            self.logger.error(f"Failed to load private key: {str(e)}")
            raise
    
    def _execute_query(self, query: str):
        """Execute a SQL query and return results as pandas DataFrame"""
        try:
            import pandas as pd
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(query)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            cursor.close()
            
            # Return as pandas DataFrame
            return pd.DataFrame(results, columns=columns)
            
        except Exception as e:
            self.logger.error(f"Failed to execute query: {str(e)}")
            import pandas as pd
            return pd.DataFrame()
    
    def get_table_record_counts(self) -> Dict[str, int]:
        """
        Get record counts for all monitored tables.
        
        Returns:
            Dict[str, int]: Dictionary with table names as keys and record counts as values
        """
        record_counts = {}
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Define tables to monitor
            tables_to_monitor = [
                # Clinical tables
                (self.config.CLINICAL_SCHEMA, 'ECG_DATA', 'clinical.ECG_DATA'),
                (self.config.CLINICAL_SCHEMA, 'EDA_DATA', 'clinical.EDA_DATA'),
                (self.config.CLINICAL_SCHEMA, 'PPG_DATA', 'clinical.PPG_DATA'),
                (self.config.CLINICAL_SCHEMA, 'PATIENT_SESSIONS', 'clinical.PATIENT_SESSIONS'),
                (self.config.CLINICAL_SCHEMA, 'DEVICE_REGISTRY', 'clinical.DEVICE_REGISTRY'),
                
                # Telemetry table
                (self.config.TELEMETRY_SCHEMA, 'DEVICE_TELEMETRY', 'telemetry.DEVICE_TELEMETRY'),
            ]
            
            for schema, table_name, display_key in tables_to_monitor:
                try:
                    query = f"""
                    SELECT COUNT(*) as record_count 
                    FROM {schema}.{table_name}
                    """
                    
                    cursor.execute(query)
                    result = cursor.fetchone()
                    record_counts[display_key] = result[0] if result else 0
                    
                    self.logger.debug(f"Retrieved count for {display_key}: {record_counts[display_key]}")
                    
                except Exception as e:
                    # If table doesn't exist or query fails, set count to 0
                    self.logger.warning(f"Failed to get count for {display_key}: {str(e)}")
                    record_counts[display_key] = 0
            
            cursor.close()
            self.logger.info(f"Retrieved record counts for {len(record_counts)} tables")
            return record_counts
            
        except Exception as e:
            self.logger.error(f"Error retrieving record counts: {str(e)}")
            return {}

    def get_table_details(self, schema: str, table_name: str) -> Dict:
        """
        Get detailed information about a specific table.
        
        Args:
            schema: Schema name
            table_name: Table name
            
        Returns:
            Dict: Table details including row count, size, last updated
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get table information from INFORMATION_SCHEMA
            query = f"""
            SELECT 
                ROW_COUNT,
                BYTES,
                LAST_ALTERED,
                CREATED
            FROM {self.config.DATABASE}.INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = '{schema}' 
            AND TABLE_NAME = '{table_name}'
            """
            
            cursor.execute(query)
            result = cursor.fetchone()
            
            if result:
                return {
                    'row_count': result[0] or 0,
                    'size_bytes': result[1] or 0,
                    'last_altered': result[2],
                    'created': result[3]
                }
            else:
                return {}
                
        except Exception as e:
            self.logger.error(f"Error getting table details for {schema}.{table_name}: {str(e)}")
            return {}
    
    def get_recent_records(self, schema: str, table_name: str, limit: int = 10) -> list:
        """
        Get recent records from a table.
        
        Args:
            schema: Schema name
            table_name: Table name
            limit: Number of records to retrieve
            
        Returns:
            list: Recent records
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Try to order by timestamp or ingestion_timestamp if available
            timestamp_columns = ['timestamp_val', 'timestamp', 'ingestion_timestamp', 'created_timestamp']
            order_by_clause = ""
            
            # Check which timestamp column exists
            for ts_col in timestamp_columns:
                try:
                    # Check if column exists by trying to select it
                    check_query = f"""
                    SELECT {ts_col} 
                    FROM {schema}.{table_name} 
                    LIMIT 1
                    """
                    cursor.execute(check_query)
                    cursor.fetchone()
                    order_by_clause = f"ORDER BY {ts_col} DESC"
                    break
                except:
                    continue
            
            # Get recent records
            query = f"""
            SELECT * 
            FROM {schema}.{table_name}
            {order_by_clause}
            LIMIT {limit}
            """
            
            cursor.execute(query)
            
            # Get column names
            columns = [desc[0] for desc in cursor.description]
            
            # Fetch results
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            records = []
            for row in rows:
                record = {}
                for i, value in enumerate(row):
                    # Convert datetime objects to strings for JSON serialization
                    if hasattr(value, 'strftime'):
                        record[columns[i]] = value.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        record[columns[i]] = value
                records.append(record)
            
            cursor.close()
            return records
            
        except Exception as e:
            self.logger.error(f"Error getting recent records from {schema}.{table_name}: {str(e)}")
            return []
    
    def get_latest_telemetry_per_device(self, schema: str, table_name: str) -> list:
        """
        Get the most recent telemetry record for each device using proper SQL GROUP BY logic.
        
        Args:
            schema: Schema name
            table_name: Table name
            
        Returns:
            list: Most recent record for each unique device_id
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Find the appropriate timestamp column
            timestamp_columns = ['timestamp_val', 'timestamp', 'ingestion_timestamp', 'created_timestamp']
            timestamp_col = None
            
            for ts_col in timestamp_columns:
                try:
                    check_query = f"SELECT {ts_col} FROM {schema}.{table_name} LIMIT 1"
                    cursor.execute(check_query)
                    cursor.fetchone()
                    timestamp_col = ts_col
                    break
                except:
                    continue
            
            if not timestamp_col:
                self.logger.warning(f"No timestamp column found in {schema}.{table_name}")
                return []
            
            # Use window function to get the most recent record per device
            query = f"""
            WITH latest_per_device AS (
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY JSON_EXTRACT_PATH_TEXT(DATA, 'device_id') 
                           ORDER BY {timestamp_col} DESC
                       ) as rn
                FROM {schema}.{table_name}
                WHERE JSON_EXTRACT_PATH_TEXT(DATA, 'device_id') IS NOT NULL
            )
            SELECT *
            FROM latest_per_device
            WHERE rn = 1
            ORDER BY JSON_EXTRACT_PATH_TEXT(DATA, 'device_id')
            """
            
            self.logger.info(f"Getting latest telemetry per device from {schema}.{table_name}")
            cursor.execute(query)
            
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            records = []
            for row in rows:
                record_dict = dict(zip(columns, row))
                records.append(record_dict)
            
            self.logger.info(f"Retrieved {len(records)} latest telemetry records (one per device)")
            return records
            
        except Exception as e:
            self.logger.error(f"Error getting latest telemetry per device: {str(e)}")
            return []
    
    def get_raw_vital_data_points(self, schema: str, table_name: str, time_range: str, limit: int = 60, patient_id: str = None, reference_timestamp=None, unified_timestamps=None) -> list:
        """
        Get median-aggregated vital sign data points for specified time range.
        Uses medical-grade median averaging to filter artifacts while preserving physiological trends.
        
        Args:
            schema: Schema name (e.g., 'CLINICAL')
            table_name: Table name (e.g., 'ECG_DATA_FLATTENED')
            time_range: Time range ('Last 5 Minutes', 'Last 1 Hour', 'Last 6 Hours', 'Last 24 Hours')
            limit: Number of time buckets to return (30 for 5-minute view, 60 for others)
            patient_id: Specific patient ID to filter by (e.g., 'PATIENT_001')
            reference_timestamp: Reference timestamp for time window calculation
            unified_timestamps: List of exact datetime objects for X-axis synchronization
            
        Returns:
            list: Median-aggregated records with clean trend values (MEDICAL OPTIMIZATION)
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Find timestamp column (try both cases)
            timestamp_col = None
            timestamp_columns = ['TIMESTAMP_VAL', 'timestamp_val', 'TIMESTAMP', 'timestamp', 'INGESTION_TIMESTAMP', 'ingestion_timestamp']
            
            for ts_col in timestamp_columns:
                try:
                    check_query = f"""
                    SELECT {ts_col} 
                    FROM {schema}.{table_name} 
                    LIMIT 1
                    """
                    cursor.execute(check_query)
                    cursor.fetchone()
                    timestamp_col = ts_col
                    self.logger.info(f"Using timestamp column: {timestamp_col} for {schema}.{table_name}")
                    break
                except:
                    continue
            
            if not timestamp_col:
                self.logger.warning(f"No timestamp column found in {schema}.{table_name}")
                return []
            
            # Determine time window for raw data query
            if "10 seconds" in time_range:
                hours_back = 0
                minutes_back = 0
                seconds_back = 10
            elif "5 Minutes" in time_range:
                hours_back = 0
                minutes_back = 5
                seconds_back = 0
            elif "10 Minutes" in time_range:
                hours_back = 0
                minutes_back = 10
                seconds_back = 0
            elif "1 Minute" in time_range:
                hours_back = 0
                minutes_back = 1
                seconds_back = 0
            elif "1 Hour" in time_range:
                hours_back = 1
                minutes_back = 0
                seconds_back = 0
            elif "6 Hour" in time_range:
                hours_back = 6
                minutes_back = 0
                seconds_back = 0
            else:  # 24 Hours
                hours_back = 24
                minutes_back = 0
                seconds_back = 0
            
            # Determine value column based on table name
            value_col = self._get_value_column_for_table(table_name)
            if not value_col:
                self.logger.warning(f"Unknown value column for table {table_name}")
                return []
            
            # Build WHERE clause with proper time bounds
            if reference_timestamp:
                ref_ts_str = reference_timestamp.strftime('%Y-%m-%d %H:%M:%S')
                base_timestamp = f"TO_TIMESTAMP('{ref_ts_str}', 'YYYY-MM-DD HH24:MI:SS')"
            else:
                base_timestamp = "SYSDATE()"
                
            # Create time window
            if seconds_back > 0:
                where_conditions = [
                    f"{timestamp_col} >= DATEADD(second, -{seconds_back}, {base_timestamp})",
                    f"{timestamp_col} <= {base_timestamp}"
                ]
            else:
                where_conditions = [
                    f"{timestamp_col} >= DATEADD(hour, -{hours_back}, DATEADD(minute, -{minutes_back}, {base_timestamp}))",
                    f"{timestamp_col} <= {base_timestamp}"
                ]
            
            # Add patient filter if specified
            if patient_id:
                where_conditions.append(f"patient_id = '{patient_id}'")
            
            where_clause = " AND ".join(where_conditions)
            
            # MEDIAN AGGREGATION QUERY - Medical-grade artifact filtering
            # Create time buckets and calculate median for each interval
            
            # Determine bucket interval and count based on time range
            if "5 Minutes" in time_range:
                bucket_seconds = 10  # 10-second buckets for 5-minute view
                expected_buckets = 30  # 30 buckets total
            elif "1 Minute" in time_range:
                bucket_seconds = 1   # 1-second buckets for 1-minute view  
                expected_buckets = 60
            elif "1 Hour" in time_range:
                bucket_seconds = 60  # 1-minute buckets for 1-hour view
                expected_buckets = 60
            else:
                bucket_seconds = 360  # 6-minute buckets for longer views
                expected_buckets = 60
            
            # MEDIAN AGGREGATION WITH TIME BUCKETS - ONE VALUE PER TIME BUCKET
            query = f"""
            WITH time_buckets AS (
                SELECT 
                    FLOOR(EXTRACT(EPOCH FROM {timestamp_col}) / {bucket_seconds}) * {bucket_seconds} as bucket_start_epoch,
                    TO_TIMESTAMP(FLOOR(EXTRACT(EPOCH FROM {timestamp_col}) / {bucket_seconds}) * {bucket_seconds}) as bucket_timestamp,
                    {value_col} as raw_value
                FROM {schema}.{table_name}
                WHERE {where_clause}
            ),
            median_aggregated AS (
                SELECT 
                    bucket_timestamp as TIMESTAMP_VAL,
                    MEDIAN(raw_value) as RAW_VALUE,
                    COUNT(*) as sample_count
                FROM time_buckets
                GROUP BY bucket_timestamp
                ORDER BY bucket_timestamp DESC
                LIMIT {expected_buckets}
            )
            SELECT 
                TIMESTAMP_VAL,
                ROUND(RAW_VALUE, 4) as RAW_VALUE
            FROM median_aggregated
            ORDER BY TIMESTAMP_VAL DESC
            """
            
            self.logger.info(f"Executing MEDIAN aggregation query for {table_name}: time_range={time_range}, bucket_seconds={bucket_seconds}, expected_buckets={expected_buckets}")
            cursor.execute(query)
            
            # Get column names
            columns = [desc[0] for desc in cursor.description]
            
            # Fetch results
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries with raw values
            records = []
            for row in rows:
                record = {}
                for i, value in enumerate(row):
                    col_name = columns[i]
                    if hasattr(value, 'strftime'):
                        record[col_name] = value.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        record[col_name] = value
                records.append(record)
            
            cursor.close()
            
            if records:
                self.logger.info(f"Retrieved {len(records)} MEDIAN-AGGREGATED data points from {schema}.{table_name} for {time_range}")
            else:
                self.logger.warning(f"No median-aggregated data found in {schema}.{table_name} for {time_range} and patient {patient_id}")
                
            return records
            
        except Exception as e:
            self.logger.error(f"Error getting median-aggregated data from {schema}.{table_name}: {str(e)}")
            return []

    def get_aggregated_vital_data(self, schema: str, table_name: str, time_range: str, limit: int = 6, patient_id: str = None, reference_timestamp=None, unified_timestamps=None) -> list:
        """
        Get aggregated vital sign data for specified time range with proper timestamps.
        Prioritizes the most recent data when streaming is active.
        
        Args:
            schema: Schema name (e.g., 'CLINICAL')
            table_name: Table name (e.g., 'ECG_DATA')
            time_range: Time range ('Last 1 Minute', 'Last 1 Hour', 'Last 6 Hours', 'Last 24 Hours')
            limit: Number of data points to return
            patient_id: Specific patient ID to filter by (e.g., 'PATIENT_001')
            reference_timestamp: Reference timestamp for time window calculation
            unified_timestamps: List of exact datetime objects for X-axis synchronization
            
        Returns:
            list: Aggregated records with timestamps and averaged values
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Find timestamp column FIRST (before defining group_by_format)
            timestamp_col = None
            timestamp_columns = ['timestamp_val', 'timestamp', 'ingestion_timestamp', 'created_timestamp']
            
            for ts_col in timestamp_columns:
                try:
                    check_query = f"""
                    SELECT {ts_col} 
                    FROM {schema}.{table_name} 
                    LIMIT 1
                    """
                    cursor.execute(check_query)
                    cursor.fetchone()
                    timestamp_col = ts_col
                    self.logger.info(f"Using timestamp column: {timestamp_col} for {schema}.{table_name}")
                    break
                except:
                    continue
            
            if not timestamp_col:
                self.logger.warning(f"No timestamp column found in {schema}.{table_name}")
                return []
            
            # NOW determine aggregation interval using the correct timestamp column
            if "10 seconds" in time_range:
                interval_seconds = 1  # 1-second intervals for 10-second view
                hours_back = 0
                minutes_back = 0
                seconds_back = 10
                time_format = '%Y-%m-%d %H:%M:%S'
                group_by_format = f"DATE_TRUNC('second', {timestamp_col})"
            elif "5 Minutes" in time_range:
                interval_seconds = 10  # 10-second intervals for 5-minute view (30 data points total)
                hours_back = 0
                minutes_back = 5
                seconds_back = 0
                time_format = '%Y-%m-%d %H:%M:%S'
                # Group by 10-second intervals: truncate to minute, then add 10-second buckets
                group_by_format = f"DATE_TRUNC('minute', {timestamp_col}) + INTERVAL '10 seconds' * FLOOR(EXTRACT(second FROM {timestamp_col}) / 10)"
            elif "10 Minutes" in time_range:
                interval_seconds = 10  # 10-second intervals for 10-minute view (60 data points total)
                hours_back = 0
                minutes_back = 10
                seconds_back = 0
                time_format = '%Y-%m-%d %H:%M:%S'
                # Group by 10-second intervals: truncate to minute, then add 10-second buckets
                group_by_format = f"DATE_TRUNC('minute', {timestamp_col}) + INTERVAL '10 seconds' * FLOOR(EXTRACT(second FROM {timestamp_col}) / 10)"
            elif "1 Minute" in time_range:
                interval_seconds = 10  # 10-second intervals for 1-minute view
                hours_back = 0
                minutes_back = 1
                seconds_back = 0
                time_format = '%Y-%m-%d %H:%M:%S'
                group_by_format = f"DATE_TRUNC('second', {timestamp_col})"
            elif "1 Hour" in time_range:
                interval_seconds = 600  # 10-minute intervals for 1-hour view
                hours_back = 1
                minutes_back = 0
                seconds_back = 0
                time_format = '%Y-%m-%d %H:%M:%S'
                group_by_format = f"DATE_TRUNC('minute', {timestamp_col})"
            elif "6 Hour" in time_range:
                interval_seconds = 3600  # 1-hour intervals for 6-hour view
                hours_back = 6
                minutes_back = 0
                seconds_back = 0
                time_format = '%Y-%m-%d %H:%M:%S'
                group_by_format = f"DATE_TRUNC('hour', {timestamp_col})"
            else:  # 24 Hours
                interval_seconds = 14400  # 4-hour intervals for 24-hour view
                hours_back = 24
                minutes_back = 0
                seconds_back = 0
                time_format = '%Y-%m-%d %H:%M:%S'
                group_by_format = f"DATE_TRUNC('hour', {timestamp_col})"
            
            # Determine value column based on table name
            value_col = self._get_value_column_for_table(table_name)
            if not value_col:
                self.logger.warning(f"Unknown value column for table {table_name}")
                return []
            
            # Build WHERE clause with patient filtering - support hours, minutes, and seconds
            # CRITICAL: Use reference_timestamp if provided for synchronization, otherwise fall back to SYSDATE()
            # This ensures synchronization across all vital signs queries when reference_timestamp is provided
            if reference_timestamp:
                # Convert Python datetime to Snowflake timestamp string for SQL
                ref_ts_str = reference_timestamp.strftime('%Y-%m-%d %H:%M:%S')
                base_timestamp = f"TO_TIMESTAMP('{ref_ts_str}', 'YYYY-MM-DD HH24:MI:SS')"
            else:
                # For real-time views, use the latest actual data timestamp instead of SYSDATE()
                # This ensures the time window aligns with actual data availability
                if "5 Minutes" in time_range or "1 Minute" in time_range:
                    base_timestamp = f"(SELECT MAX({timestamp_col}) FROM {schema}.{table_name})"
                else:
                    base_timestamp = "SYSDATE()"
                
            # Create proper time window with BOTH lower and upper bounds to prevent future data
            if seconds_back > 0:
                where_conditions = [
                    f"{timestamp_col} >= DATEADD(second, -{seconds_back}, {base_timestamp})",
                    f"{timestamp_col} <= {base_timestamp}"
                ]
            else:
                where_conditions = [
                    f"{timestamp_col} >= DATEADD(hour, -{hours_back}, DATEADD(minute, -{minutes_back}, {base_timestamp}))",
                    f"{timestamp_col} <= {base_timestamp}"
                ]
            
            # Add patient filter if specified
            if patient_id:
                where_conditions.append(f"patient_id = '{patient_id}'")
            
            # TODO: UNIFIED TIMESTAMPS IMPLEMENTATION NEEDED
            # When unified_timestamps is provided, instead of using the current range-based query,
            # we should query for data at the exact timestamps in the unified_timestamps list
            # and interpolate values for those specific time points to ensure perfect X-axis synchronization.
            # For now, using existing range-based logic until full implementation is complete.
            
            where_clause = " AND ".join(where_conditions)
            
            # Build aggregation query with priority on most recent data
            # For streaming scenarios, we want the absolute latest data
            query = f"""
            SELECT 
                {group_by_format} as time_bucket,
                AVG({value_col}) as avg_value,
                COUNT(*) as record_count,
                MIN({timestamp_col}) as period_start,
                MAX({timestamp_col}) as period_end,
                MAX({timestamp_col}) as latest_timestamp
            FROM {schema}.{table_name}
            WHERE {where_clause}
            GROUP BY {group_by_format}
            ORDER BY time_bucket DESC
            LIMIT {limit}
            """
            
            self.logger.info(f"Executing aggregated query for {table_name}: time_range={time_range}, patient_id={patient_id}")
            cursor.execute(query)
            
            # Get column names
            columns = [desc[0] for desc in cursor.description]
            
            # Fetch results
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries with proper timestamp formatting
            records = []
            for row in rows:
                record = {}
                for i, value in enumerate(row):
                    col_name = columns[i]
                    if hasattr(value, 'strftime'):
                        # Format timestamps with appropriate precision
                        record[col_name] = value.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        record[col_name] = value
                records.append(record)
            
            cursor.close()
            
            if records:
                latest_timestamp = records[0].get('LATEST_TIMESTAMP', 'unknown')
                self.logger.info(f"Retrieved {len(records)} aggregated records from {schema}.{table_name} for {time_range}. Latest data: {latest_timestamp}")
            else:
                self.logger.warning(f"No records found in {schema}.{table_name} for {time_range} and patient {patient_id}")
                
            return records
            
        except Exception as e:
            self.logger.error(f"Error getting aggregated data from {schema}.{table_name}: {str(e)}")
            return []
    
    def get_distinct_patient_ids(self) -> list:
        """
        Get distinct patient IDs from all clinical data tables (ECG, EDA, PPG).
        
        Returns:
            list: Sorted list of distinct patient IDs found across all clinical tables
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Tables to check for patient IDs
            clinical_tables = ['ECG_DATA', 'EDA_DATA', 'PPG_DATA', 'ECG_DATA_FLATTENED', 'EDA_DATA_FLATTENED', 'PPG_DATA_FLATTENED']
            all_patient_ids = set()
            
            for table_name in clinical_tables:
                try:
                    # Check if table exists and has patient_id column
                    check_query = f"""
                    SELECT DISTINCT patient_id 
                    FROM {self.config.DATABASE}.{self.config.CLINICAL_SCHEMA}.{table_name}
                    WHERE patient_id IS NOT NULL
                    LIMIT 100
                    """
                    
                    cursor.execute(check_query)
                    rows = cursor.fetchall()
                    
                    # Add patient IDs to set
                    for row in rows:
                        if row[0]:  # Ensure patient_id is not None/empty
                            all_patient_ids.add(row[0])
                    
                    self.logger.info(f"Found {len(rows)} distinct patient IDs in {table_name}")
                    
                except Exception as table_error:
                    # Log but continue - table might not exist or have different structure
                    self.logger.warning(f"Could not query patient IDs from {table_name}: {str(table_error)}")
                    continue
            
            cursor.close()
            
            # Convert to sorted list
            patient_ids = sorted(list(all_patient_ids))
            
            self.logger.info(f"Found {len(patient_ids)} total distinct patient IDs across all clinical tables")
            return patient_ids
            
        except Exception as e:
            self.logger.error(f"Error getting distinct patient IDs: {str(e)}")
            return []
    
    def get_ecg_waveform_data(self, time_range: str, patient_id: Optional[str] = None, limit: int = 500, reference_timestamp=None, unified_timestamps=None) -> list:
        """
        Get median-smoothed ECG signal data points for clean waveform visualization.
        Uses fine-grained median averaging to preserve cardiac rhythm while filtering artifacts.
        
        Args:
            time_range: Time range string (e.g., "Last 5 Minutes", "Last 1 Hour")  
            patient_id: Optional patient ID to filter by
            limit: Max number of smoothed data points to retrieve
            reference_timestamp: Reference timestamp for synchronization with vital signs
            
        Returns:
            list: List of dictionaries containing median-smoothed ECG waveform with preserved cardiac detail
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Determine time window using same logic as vital signs for consistency
            if "5 Minutes" in time_range:
                hours_back = 0
                minutes_back = 5
                seconds_back = 0
            elif "10 Minutes" in time_range:
                hours_back = 0
                minutes_back = 10
                seconds_back = 0
            elif "1 Minute" in time_range:
                hours_back = 0
                minutes_back = 1
                seconds_back = 0
            elif "1 Hour" in time_range:
                hours_back = 1
                minutes_back = 0
                seconds_back = 0
            elif "24 Hour" in time_range:
                hours_back = 24
                minutes_back = 0
                seconds_back = 0
            else:
                # Default to 1 minute
                hours_back = 0
                minutes_back = 1
                seconds_back = 0
            
            # Use reference_timestamp if provided for synchronization, otherwise fall back to SYSDATE()
            if reference_timestamp:
                ref_ts_str = reference_timestamp.strftime('%Y-%m-%d %H:%M:%S')
                base_timestamp = f"TO_TIMESTAMP('{ref_ts_str}', 'YYYY-MM-DD HH24:MI:SS')"
            else:
                base_timestamp = "SYSDATE()"
            
            # Build WHERE clause with proper time bounds (same pattern as vital signs)
            if seconds_back > 0:
                where_conditions = [
                    f"timestamp_val >= DATEADD(second, -{seconds_back}, {base_timestamp})",
                    f"timestamp_val <= {base_timestamp}"
                ]
            else:
                where_conditions = [
                    f"timestamp_val >= DATEADD(hour, -{hours_back}, DATEADD(minute, -{minutes_back}, {base_timestamp}))",
                    f"timestamp_val <= {base_timestamp}"
                ]
            
            # Add patient filter if specified
            if patient_id:
                where_conditions.append(f"patient_id = '{patient_id}'")
            
            where_clause = " AND ".join(where_conditions)
            
            # MEDIAN-SMOOTHED ECG QUERY - Fine-grained buckets to preserve cardiac rhythm
            # Use smaller buckets for ECG to maintain waveform detail while filtering noise
            if "5 Minutes" in time_range:
                bucket_seconds = 1    # 1-second buckets for detailed ECG in 5-minute view
                expected_points = 300 # 300 points for smooth waveform
            elif "1 Minute" in time_range:
                bucket_seconds = 0.2  # 200ms buckets for very detailed ECG  
                expected_points = 300
            elif "1 Hour" in time_range:
                bucket_seconds = 12   # 12-second buckets for 1-hour view
                expected_points = 300
            else:
                bucket_seconds = 30   # 30-second buckets for longer views
                expected_points = 300
            
            # MEDIAN AGGREGATION FOR ECG WITH CARDIAC DETAIL PRESERVATION
            query = f"""
            WITH ecg_time_buckets AS (
                SELECT 
                    FLOOR(EXTRACT(EPOCH FROM timestamp_val) / {bucket_seconds}) * {bucket_seconds} as bucket_start_epoch,
                    TO_TIMESTAMP(FLOOR(EXTRACT(EPOCH FROM timestamp_val) / {bucket_seconds}) * {bucket_seconds}) as bucket_timestamp,
                    lead_ii as raw_ecg_signal,
                    signal_quality
                FROM {self.config.DATABASE}.{self.config.CLINICAL_SCHEMA}.ECG_DATA_FLATTENED
                WHERE {where_clause}
            ),
            median_ecg_smoothed AS (
                SELECT 
                    bucket_timestamp as TIMESTAMP_VAL,
                    MEDIAN(raw_ecg_signal) as ECG_SIGNAL,
                    AVG(signal_quality) as SIGNAL_QUALITY,
                    'median_smoothed' as DATA_QUALITY,
                    COUNT(*) as sample_count
                FROM ecg_time_buckets
                GROUP BY bucket_timestamp
                ORDER BY bucket_timestamp DESC
                LIMIT {expected_points}
            )
            SELECT 
                TIMESTAMP_VAL,
                ROUND(ECG_SIGNAL, 4) as ECG_SIGNAL,
                DATA_QUALITY,
                ROUND(SIGNAL_QUALITY, 2) as SIGNAL_QUALITY
            FROM median_ecg_smoothed
            ORDER BY TIMESTAMP_VAL DESC
            """
            
            self.logger.info(f"Executing MEDIAN-SMOOTHED ECG query (cardiac rhythm preserved) for patient: {patient_id or 'All'}, time_range: {time_range}, bucket_seconds: {bucket_seconds}")
            cursor.execute(query)
            
            columns = [desc[0] for desc in cursor.description]
            records = []
            
            # Convert to list of dictionaries with proper timestamp formatting
            for row in cursor.fetchall():
                record = {}
                for i, value in enumerate(row):
                    col_name = columns[i]
                    if hasattr(value, 'strftime'):
                        record[col_name] = value.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        record[col_name] = value
                records.append(record)
            
            cursor.close()
            
            if records:
                self.logger.info(f"Retrieved {len(records)} MEDIAN-SMOOTHED ECG data points from database for {time_range}")
            else:
                self.logger.warning(f"No median-smoothed ECG data found for {time_range} and patient {patient_id}")
                
            return records
            
        except Exception as e:
            self.logger.error(f"Error getting median-smoothed ECG waveform data: {str(e)}")
            return []





    def _get_value_column_for_table(self, table_name: str) -> str:
        """Get the appropriate value column name for a given table (using flattened view columns)"""
        table_columns = {
            'ECG_DATA_FLATTENED': 'HEART_RATE',
            'EDA_DATA_FLATTENED': 'SKIN_CONDUCTANCE_LEVEL', 
            'PPG_DATA_FLATTENED': 'SPO2'
        }
        return table_columns.get(table_name.upper(), None)
    
    def get_streaming_statistics(self) -> Dict:
        """
        Get streaming-specific statistics from the database.
        
        Returns:
            Dict: Streaming statistics
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            statistics = {}
            
            # Get record counts by time periods (last hour, last day)
            # Use timestamp_val for ECG/EDA/PPG tables, fallback to timestamp for others
            timestamp_col = "timestamp_val"
            time_queries = {
                'last_hour': f"{timestamp_col} >= DATEADD(hour, -1, SYSDATE())",
                'last_day': f"{timestamp_col} >= DATEADD(day, -1, SYSDATE())"
            }
            
            # Check clinical tables
            for device_type, table_name in self.config.DEVICE_TABLES.items():
                statistics[f'{device_type}_stats'] = {}
                
                for period, condition in time_queries.items():
                    try:
                        query = f"""
                        SELECT COUNT(*) 
                        FROM {self.config.DATABASE}.{self.config.CLINICAL_SCHEMA}.{table_name}
                        WHERE {condition}
                        """
                        
                        cursor.execute(query)
                        result = cursor.fetchone()
                        statistics[f'{device_type}_stats'][period] = result[0] if result else 0
                        
                    except Exception as e:
                        self.logger.warning(f"Failed to get {period} stats for {device_type}: {str(e)}")
                        statistics[f'{device_type}_stats'][period] = 0
            
            # Get telemetry statistics
            statistics['telemetry_stats'] = {}
            
            # Detect timestamp column for telemetry table
            telemetry_timestamp_col = None
            timestamp_columns = ['timestamp_val', 'timestamp', 'ingestion_timestamp', 'created_timestamp']
            
            for ts_col in timestamp_columns:
                try:
                    check_query = f"""
                    SELECT {ts_col} 
                    FROM {self.config.DATABASE}.{self.config.TELEMETRY_SCHEMA}.{self.config.TELEMETRY_TABLE} 
                    LIMIT 1
                    """
                    cursor.execute(check_query)
                    cursor.fetchone()
                    telemetry_timestamp_col = ts_col
                    break
                except:
                    continue
            
            if telemetry_timestamp_col:
                telemetry_time_queries = {
                                    'last_hour': f"{telemetry_timestamp_col} >= DATEADD(hour, -1, SYSDATE())",
                'last_day': f"{telemetry_timestamp_col} >= DATEADD(day, -1, SYSDATE())"
                }
                
                for period, condition in telemetry_time_queries.items():
                    try:
                        query = f"""
                        SELECT COUNT(*) 
                        FROM {self.config.DATABASE}.{self.config.TELEMETRY_SCHEMA}.{self.config.TELEMETRY_TABLE}
                        WHERE {condition}
                        """
                        
                        cursor.execute(query)
                        result = cursor.fetchone()
                        statistics['telemetry_stats'][period] = result[0] if result else 0
                        
                    except Exception as e:
                        self.logger.warning(f"Failed to get telemetry {period} stats: {str(e)}")
                        statistics['telemetry_stats'][period] = 0
            else:
                # If no timestamp column found, set stats to 0
                statistics['telemetry_stats']['last_hour'] = 0
                statistics['telemetry_stats']['last_day'] = 0
            
            cursor.close()
            return statistics
            
        except Exception as e:
            self.logger.error(f"Error getting streaming statistics: {str(e)}")
            return {}
    
    def test_connection(self) -> tuple[bool, str]:
        """
        Test the database connection.
        
        Returns:
            tuple: (success, message)
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Simple test query
            cursor.execute("SELECT CURRENT_TIMESTAMP()")
            result = cursor.fetchone()
            
            cursor.close()
            
            if result:
                return True, f"Connection successful. Server time: {result[0]}"
            else:
                return False, "Connection test failed - no result"
                
        except Exception as e:
            return False, f"Connection test failed: {str(e)}"
    
    def close_connection(self):
        """Close the database connection"""
        try:
            if self._connection and not self._connection.is_closed():
                self._connection.close()
                self.logger.info("Database connection closed")
        except Exception as e:
            self.logger.error(f"Error closing connection: {str(e)}")
    
    def __del__(self):
        """Cleanup on object destruction"""
        self.close_connection()

    def truncate_all_tables(self) -> tuple[bool, str]:
        """
        Truncate all clinical and telemetry tables.
        
        Returns:
            tuple: (success, message)
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            tables_to_truncate = [
                (self.config.CLINICAL_SCHEMA, 'ECG_DATA'),
                (self.config.CLINICAL_SCHEMA, 'EDA_DATA'),
                (self.config.CLINICAL_SCHEMA, 'PPG_DATA'),
                (self.config.CLINICAL_SCHEMA, 'PATIENT_SESSIONS'),
                (self.config.CLINICAL_SCHEMA, 'DEVICE_REGISTRY'),
                (self.config.TELEMETRY_SCHEMA, 'DEVICE_TELEMETRY'),
            ]
            
            for schema, table_name in tables_to_truncate:
                try:
                    query = f"TRUNCATE TABLE {schema}.{table_name}"
                    cursor.execute(query)
                    self.logger.info(f"Truncated table: {schema}.{table_name}")
                except Exception as e:
                    self.logger.warning(f"Could not truncate {schema}.{table_name}: {e}")
            
            cursor.close()
            return True, "All tables truncated successfully."
            
        except Exception as e:
            self.logger.error(f"Error truncating tables: {str(e)}")
            return False, f"Failed to truncate tables: {str(e)}"
 