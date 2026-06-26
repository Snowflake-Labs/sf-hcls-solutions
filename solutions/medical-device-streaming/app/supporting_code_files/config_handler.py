#!/usr/bin/env python3
"""
Streamlit Configuration Handler
===============================

Manages configuration settings specific to the Streamlit application.
Provides default values and settings for the dashboard interface.
"""

import sys
import os
from typing import Dict, Any

# Project modules - using absolute imports to supporting_code_files package

from supporting_code_files.config import SnowflakeConfig, MedicalDeviceConfig, TelemetryConfig, DemoConfig

class StreamlitConfig:
    """
    Configuration class for Streamlit-specific settings.
    Extends the base configuration with UI-specific defaults and options.
    """
    
    def __init__(self):
        # Initialize base configurations
        self.snowflake_config = SnowflakeConfig()
        self.device_config = MedicalDeviceConfig()
        self.telemetry_config = TelemetryConfig()
        self.demo_config = DemoConfig()
    
    # Dashboard settings
    DASHBOARD_TITLE = "🏥 Medical Device Streaming Dashboard"
    DASHBOARD_ICON = "🏥"
    
    # Default streaming parameters for UI
    DEFAULT_PATIENT_COUNT = 5
    DEFAULT_DURATION = 300  # 5 minutes
    DEFAULT_SCENARIO = 'NORMAL'
    
    # UI refresh settings
    DEFAULT_REFRESH_INTERVAL = 5  # seconds
    MIN_REFRESH_INTERVAL = 1
    MAX_REFRESH_INTERVAL = 30
    
    # Display settings
    MAX_LOG_ENTRIES = 100
    MAX_RECENT_RECORDS = 20
    
    # Color scheme for metrics
    COLORS = {
        'success': '#28a745',
        'warning': '#ffc107', 
        'danger': '#dc3545',
        'info': '#17a2b8',
        'primary': '#007bff'
    }
    
    # Metric thresholds for color coding
    THRESHOLDS = {
        'error_rate_warning': 1.0,  # %
        'error_rate_danger': 5.0,   # %
        'success_rate_warning': 95.0,  # %
        'success_rate_danger': 90.0,   # %
        'records_per_second_low': 100,
        'records_per_second_normal': 500
    }
    
    # Table display configuration
    TABLE_CONFIG = {
        'clinical_tables': ['ECG_DATA', 'EDA_DATA', 'PPG_DATA'],
        'management_tables': ['PATIENT_SESSIONS', 'DEVICE_REGISTRY'],
        'telemetry_tables': ['DEVICE_TELEMETRY']
    }
    
    # Chart and visualization settings
    CHART_CONFIG = {
        'height': 400,
        'width': 800,
        'update_interval': 5,  # seconds
        'max_data_points': 100
    }
    
    @property
    def SUPPORTED_SCENARIOS(self) -> list:
        """Get list of supported streaming scenarios"""
        return ['NORMAL', 'HIGH_LOAD', 'MAINTENANCE', 'NETWORK_ISSUES']
    
    @property
    def SUPPORTED_DEVICES(self) -> Dict[str, str]:
        """Get supported device types with descriptions"""
        return {
            device_type: info['description'] 
            for device_type, info in self.device_config.SUPPORTED_DEVICES.items()
        }
    
    def get_database_info(self) -> Dict[str, str]:
        """Get database connection information for display"""
        return {
            'database': self.snowflake_config.DATABASE,
            'clinical_schema': self.snowflake_config.CLINICAL_SCHEMA,
            'telemetry_schema': self.snowflake_config.TELEMETRY_SCHEMA,
            'account': self.snowflake_config.ACCOUNT,
            'user': self.snowflake_config.USER,
            'warehouse': self.snowflake_config.WAREHOUSE
        }
    
    def get_streaming_config(self) -> Dict[str, Any]:
        """Get streaming configuration for display"""
        return {
            'clinical_batch_size': self.device_config.CLINICAL_DATA_BATCH_SIZE,
            'telemetry_batch_size': self.device_config.TELEMETRY_BATCH_SIZE,
            'clinical_interval': self.device_config.CLINICAL_STREAMING_INTERVAL,
            'telemetry_interval': self.device_config.TELEMETRY_STREAMING_INTERVAL,
            'max_patients': 20,
            'devices_per_patient': self.device_config.DEVICES_PER_PATIENT
        }
    
    def get_table_monitoring_config(self) -> Dict[str, list]:
        """Get table monitoring configuration"""
        return {
            'clinical_tables': [
                {
                    'name': table_name,
                    'display_name': table_name.replace('_DATA', ''),
                    'schema': self.snowflake_config.CLINICAL_SCHEMA,
                    'key': f"clinical.{table_name}"
                }
                for table_name in self.TABLE_CONFIG['clinical_tables']
            ],
            'telemetry_tables': [
                {
                    'name': 'DEVICE_TELEMETRY',
                    'display_name': 'Device Telemetry',
                    'schema': self.snowflake_config.TELEMETRY_SCHEMA,
                    'key': 'telemetry.DEVICE_TELEMETRY'
                }
            ],
            'management_tables': [
                {
                    'name': table_name,
                    'display_name': table_name.replace('_', ' ').title(),
                    'schema': self.snowflake_config.CLINICAL_SCHEMA,
                    'key': f"clinical.{table_name}"
                }
                for table_name in self.TABLE_CONFIG['management_tables']
            ]
        }
    
    def get_metric_color(self, metric_type: str, value: float) -> str:
        """
        Get appropriate color for a metric value based on thresholds.
        
        Args:
            metric_type: Type of metric ('error_rate', 'success_rate', 'records_per_second')
            value: Metric value
            
        Returns:
            str: Color code
        """
        if metric_type == 'error_rate':
            if value >= self.THRESHOLDS['error_rate_danger']:
                return self.COLORS['danger']
            elif value >= self.THRESHOLDS['error_rate_warning']:
                return self.COLORS['warning']
            else:
                return self.COLORS['success']
        
        elif metric_type == 'success_rate':
            if value <= self.THRESHOLDS['success_rate_danger']:
                return self.COLORS['danger']
            elif value <= self.THRESHOLDS['success_rate_warning']:
                return self.COLORS['warning']
            else:
                return self.COLORS['success']
        
        elif metric_type == 'records_per_second':
            if value >= self.THRESHOLDS['records_per_second_normal']:
                return self.COLORS['success']
            elif value >= self.THRESHOLDS['records_per_second_low']:
                return self.COLORS['warning']
            else:
                return self.COLORS['danger']
        
        else:
            return self.COLORS['info']
    
    def get_status_emoji(self, status: str) -> str:
        """Get emoji for status display"""
        status_emojis = {
            'active': '🟢',
            'stopped': '🔴',
            'starting': '🟡',
            'stopping': '🟠',
            'error': '❌',
            'success': '✅',
            'warning': '⚠️',
            'info': 'ℹ️'
        }
        return status_emojis.get(status.lower(), '⚪')
    
    def validate_streaming_params(self, patient_count: int, duration: int, scenario: str) -> tuple[bool, str]:
        """
        Validate streaming parameters.
        
        Args:
            patient_count: Number of patients
            duration: Duration in seconds
            scenario: Scenario name
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if not (1 <= patient_count <= 20):
            return False, "Patient count must be between 1 and 20"
        
        if not (30 <= duration <= 3600):
            return False, "Duration must be between 30 seconds and 1 hour"
        
        if scenario not in self.SUPPORTED_SCENARIOS:
            return False, f"Scenario must be one of: {', '.join(self.SUPPORTED_SCENARIOS)}"
        
        return True, "Parameters are valid"
    
    def get_help_text(self, component: str) -> str:
        """Get help text for UI components"""
        help_texts = {
            'patient_count': "Number of patient sessions to simulate. Each patient can have multiple devices assigned.",
            'duration': "How long to run the streaming demo in seconds. Longer durations generate more data.",
            'scenario': "Operational scenario affects device behavior and telemetry patterns.",
            'auto_refresh': "Automatically refresh the dashboard data while streaming is active.",
            'refresh_interval': "How often to refresh the dashboard data in seconds."
        }
        return help_texts.get(component, "")
    
    def get_page_config(self) -> Dict[str, Any]:
        """Get Streamlit page configuration"""
        return {
            'page_title': self.DASHBOARD_TITLE,
            'page_icon': self.DASHBOARD_ICON,
            'layout': 'wide',
            'initial_sidebar_state': 'expanded'
        } 