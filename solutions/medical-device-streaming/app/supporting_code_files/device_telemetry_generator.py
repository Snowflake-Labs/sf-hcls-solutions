#!/usr/bin/env python3
"""
Device Telemetry Generator
=========================

Generates realistic device telemetry data for operational monitoring:
- Hardware health (battery, temperature, CPU, memory)
- Connectivity status and performance
- Maintenance alerts and scheduling
- Error conditions and warnings
- Performance metrics and utilization
"""

import numpy as np
import pandas as pd
import logging
import random
from datetime import datetime, timedelta
from typing import Optional
from supporting_code_files.config import TelemetryConfig, MedicalDeviceConfig
import uuid
import threading
import time
import pytz

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeviceTelemetryGenerator:
    """
    Generates realistic device telemetry data for operational monitoring.
    Simulates various operational scenarios and device health conditions.
    """
    
    # Class-level timestamp management for globally unique timestamps
    _global_timestamp_lock = threading.Lock()
    _global_last_timestamp = None
    _global_microsecond_counter = 0
    
    def __init__(self, telemetry_config: TelemetryConfig = None, device_config: MedicalDeviceConfig = None):
        self.telemetry_config = telemetry_config or TelemetryConfig()
        self.device_config = device_config or MedicalDeviceConfig()
        
        # Device state tracking
        self.device_states = {}
        self.alert_history = {}
        
        # Operational scenarios
        self.scenarios = {
            'NORMAL': {'weight': 0.7, 'description': 'Normal operation'},
            'HIGH_LOAD': {'weight': 0.15, 'description': 'High patient load period'},
            'MAINTENANCE': {'weight': 0.05, 'description': 'Maintenance window'},
            'NETWORK_ISSUES': {'weight': 0.1, 'description': 'Network connectivity problems'}
        }
        
        logger.info("Device Telemetry Generator initialized")
    
    def _get_unique_timestamp(self) -> datetime:
        """
        Generate realistic timestamps for telemetry records.
        Always generates timestamps slightly in the past to match clinical data approach.
        Ensures timestamps are always < current time (no future timestamps).
        """
        with DeviceTelemetryGenerator._global_timestamp_lock:
            # TIMEZONE-NEUTRAL: Always use UTC regardless of local system timezone
            import pytz
            current_time = datetime.now(pytz.UTC)
            
            # If this is the first timestamp or we need to reset
            if DeviceTelemetryGenerator._global_last_timestamp is None:
                DeviceTelemetryGenerator._global_microsecond_counter = 0
                DeviceTelemetryGenerator._global_last_timestamp = current_time
            else:
                # Calculate time elapsed since last call
                time_elapsed = (current_time - DeviceTelemetryGenerator._global_last_timestamp).total_seconds()
                
                # If significant real time has passed (> 1 second), reset counter
                if time_elapsed >= 1.0:
                    DeviceTelemetryGenerator._global_microsecond_counter = 0
                else:
                    # Increment counter for rapid successive calls
                    DeviceTelemetryGenerator._global_microsecond_counter += 1
            
            # Always generate timestamp slightly in the past to avoid any future timestamps
            # Use 100ms intervals for successive records, starting from 100ms ago
            offset_ms = (DeviceTelemetryGenerator._global_microsecond_counter + 1) * 100
            offset_ms = min(offset_ms, 10000)  # Cap at 10 seconds in the past
            
            # Generate timestamp that is always in the past
            timestamp = current_time - timedelta(milliseconds=offset_ms)
            DeviceTelemetryGenerator._global_last_timestamp = current_time
            
            return timestamp
    
    def initialize_device_state(self, device_id: str, device_type: str, facility_id: str = None) -> dict:
        """Initialize device state for telemetry tracking"""
        if device_id not in self.device_states:
            self.device_states[device_id] = {
                'device_id': device_id,
                'device_type': device_type,
                'facility_id': facility_id or f"FACILITY_{random.randint(1,3)}",
                'room_id': f"ROOM_{random.randint(101,350)}",
                
                # Hardware state - More realistic initial battery levels
                'battery_level': random.randint(65, 95),  # Start with more varied, realistic levels
                'battery_temperature': np.random.uniform(20, 30),  # Celsius
                'charging_status': random.choice(['CHARGING', 'DISCHARGING', 'FULL']),
                'temperature': np.random.uniform(25, 35),  # Device temperature
                'cpu_usage': np.random.uniform(20, 40),  # %
                'memory_usage': np.random.uniform(30, 50),  # %
                'storage_usage': np.random.uniform(40, 60),  # %
                
                # Connectivity state
                'connection_status': 'CONNECTED',
                'signal_strength': random.randint(-40, -20),  # dBm
                'data_transmission_rate': np.random.uniform(10, 50),  # MB/s
                'packet_loss_rate': np.random.uniform(0, 0.5),  # %
                'latency_ms': random.randint(10, 50),
                
                # Operational state
                'uptime_hours': np.random.uniform(100, 1000),
                'total_data_collected_mb': np.random.uniform(1000, 10000),
                'successful_transmissions': random.randint(10000, 50000),
                'failed_transmissions': random.randint(0, 100),
                
                # Maintenance state
                            'last_maintenance': datetime.now(pytz.UTC) - timedelta(days=random.randint(1, 90)),
            'next_maintenance_due': datetime.now(pytz.UTC) + timedelta(days=random.randint(30, 180)),
                'calibration_status': 'CALIBRATED',
                'last_calibration': datetime.now(pytz.UTC) - timedelta(days=random.randint(1, 30)),
                
                # Firmware and compliance
                'firmware_version': f"v{random.randint(2,4)}.{random.randint(0,9)}.{random.randint(0,9)}",
                'last_update': datetime.now(pytz.UTC) - timedelta(days=random.randint(1, 60)),
                'compliance_status': 'COMPLIANT',
                
                # State tracking
                'session_id': None,
                'current_patient_id': None,
                'last_telemetry_update': datetime.now(pytz.UTC),
                'degradation_factors': {},  # Track wear and tear
                'alert_cooldowns': {}  # Prevent alert spam
            }
            
            self.alert_history[device_id] = []
        
        return self.device_states[device_id]
    
    def update_device_state(self, device_id: str, scenario: str = 'NORMAL') -> dict:
        """Update device state based on operational scenario"""
        if device_id not in self.device_states:
            logger.error(f"Device {device_id} not initialized")
            return {}
        
        state = self.device_states[device_id]
        
        # Time since last update
        time_delta = (datetime.now(pytz.UTC) - state['last_telemetry_update']).total_seconds()
        
        # Ensure minimum time delta to force value changes even in rapid succession
        # This simulates that telemetry readings are taken at intervals, not instantaneously
        MIN_TIME_DELTA = 30.0  # Simulate 30 seconds between readings minimum
        if time_delta < MIN_TIME_DELTA:
            time_delta = MIN_TIME_DELTA
        
        # Update based on scenario
        if scenario == 'NORMAL':
            self._update_normal_operation(state, time_delta)
        elif scenario == 'HIGH_LOAD':
            self._update_high_load_operation(state, time_delta)
        elif scenario == 'MAINTENANCE':
            self._update_maintenance_mode(state, time_delta)
        elif scenario == 'NETWORK_ISSUES':
            self._update_network_issues(state, time_delta)
        
        # Apply gradual degradation
        self._apply_device_degradation(state, time_delta)
        
        # Update timestamp
        state['last_telemetry_update'] = datetime.now(pytz.UTC)
        
        return state
    
    def _update_normal_operation(self, state: dict, time_delta: float):
        """Update state for normal operation with enhanced variations for dashboard visibility"""
        # Realistic battery management with auto-charging at low levels
        BATTERY_LOW_THRESHOLD = 25  # Start charging when battery drops below this
        BATTERY_HIGH_THRESHOLD = 90  # Stop charging when battery reaches this
        
        # Auto-manage charging status based on battery level
        if state['battery_level'] <= BATTERY_LOW_THRESHOLD:
            state['charging_status'] = 'CHARGING'  # Auto-start charging when low
        elif state['battery_level'] >= BATTERY_HIGH_THRESHOLD and state['charging_status'] == 'CHARGING':
            state['charging_status'] = random.choice(['DISCHARGING', 'FULL'])  # Stop charging when high
        
        # Enhanced battery discharge/charge with realistic behavior
        if state['charging_status'] != 'CHARGING':
            # Realistic discharge rates
            discharge_rate = 1.5 if state['current_patient_id'] else 0.5  # %/hour
            state['battery_level'] = max(20, state['battery_level'] - (discharge_rate * time_delta / 3600))
            
            # Small random battery fluctuations for realism
            battery_fluctuation = np.random.uniform(-0.5, 0.2)  # Smaller, more realistic fluctuation
            state['battery_level'] = np.clip(state['battery_level'] + battery_fluctuation, 20, 100)
        else:
            # Charging increases battery
            charge_rate = 15.0  # %/hour (faster charging)
            state['battery_level'] = min(100, state['battery_level'] + (charge_rate * time_delta / 3600))
            
            # Small fluctuation during charging
            charge_fluctuation = np.random.uniform(-0.1, 0.3)
            state['battery_level'] = np.clip(state['battery_level'] + charge_fluctuation, 20, 100)
        
        # Enhanced CPU/memory variations (more dramatic for visibility)
        state['cpu_usage'] = np.clip(state['cpu_usage'] + np.random.normal(0, 8), 10, 70)  # Increased variation
        state['memory_usage'] = np.clip(state['memory_usage'] + np.random.normal(0, 6), 20, 80)  # Increased variation
        
        # Enhanced temperature variations (more noticeable changes)
        ambient_temp = np.random.uniform(20, 32)  # Wider range
        load_factor = (state['cpu_usage'] / 100) * 12  # Increased impact
        state['temperature'] = ambient_temp + load_factor + np.random.uniform(-3, 3)  # Wider random range
        
        # Enhanced signal strength variations (more noticeable for dashboard)
        signal_change = np.random.randint(-12, 12)  # Even wider range of change
        state['signal_strength'] = np.clip(state['signal_strength'] + signal_change, -80, -10)
        
        # Network performance with more variation
        state['latency_ms'] = max(10, state['latency_ms'] + np.random.randint(-15, 15))  # Increased variation
        state['packet_loss_rate'] = max(0, min(2, state['packet_loss_rate'] + np.random.uniform(-0.3, 0.3)))
        
        # Randomly change charging status occasionally
        if np.random.random() < 0.05:  # 5% chance to change charging status
            state['charging_status'] = random.choice(['CHARGING', 'DISCHARGING', 'FULL'])
        
        # Data accumulation
        if state['current_patient_id']:
            data_rate = np.random.uniform(0.5, 2.0)  # MB/minute
            state['total_data_collected_mb'] += data_rate * (time_delta / 60)
            state['successful_transmissions'] += random.randint(0, 5)
    
    def _update_high_load_operation(self, state: dict, time_delta: float):
        """Update state for high load operation"""
        # Higher resource usage
        state['cpu_usage'] = np.clip(state['cpu_usage'] + np.random.normal(10, 5), 40, 95)
        state['memory_usage'] = np.clip(state['memory_usage'] + np.random.normal(15, 5), 50, 95)
        
        # Auto-manage charging at low battery levels
        if state['battery_level'] <= 25:
            state['charging_status'] = 'CHARGING'  # Force charging when critically low
        
        # Faster battery drain during high load
        if state['charging_status'] != 'CHARGING':
            discharge_rate = 3.0  # %/hour (faster drain under load)
            state['battery_level'] = max(20, state['battery_level'] - (discharge_rate * time_delta / 3600))
        else:
            # Slower charging during high load
            charge_rate = 8.0  # %/hour (slower charging under load)
            state['battery_level'] = min(100, state['battery_level'] + (charge_rate * time_delta / 3600))
        
        # Higher temperature due to load
        state['temperature'] += np.random.uniform(2, 5)
        
        # Network congestion effects
        state['latency_ms'] = min(200, state['latency_ms'] + random.randint(5, 20))
        state['packet_loss_rate'] = min(5, state['packet_loss_rate'] + np.random.uniform(0.1, 0.5))
        state['data_transmission_rate'] = max(5, state['data_transmission_rate'] - np.random.uniform(0, 10))
        
        # More data generation
        if state['current_patient_id']:
            data_rate = np.random.uniform(3.0, 8.0)  # MB/minute
            state['total_data_collected_mb'] += data_rate * (time_delta / 60)
            state['successful_transmissions'] += random.randint(5, 15)
            state['failed_transmissions'] += random.randint(0, 2)
    
    def _update_maintenance_mode(self, state: dict, time_delta: float):
        """Update state for maintenance mode"""
        # Lower activity
        state['cpu_usage'] = np.clip(state['cpu_usage'] - 10, 5, 30)
        state['memory_usage'] = np.clip(state['memory_usage'] - 10, 10, 40)
        
        # Potentially offline
        if random.random() < 0.3:
            state['connection_status'] = 'DISCONNECTED'
        else:
            state['connection_status'] = 'CONNECTED'
        
        # No patient data generation
        state['current_patient_id'] = None
        
        # Temperature stable
        state['temperature'] = np.clip(state['temperature'] - 2, 20, 30)
    
    def _update_network_issues(self, state: dict, time_delta: float):
        """Update state for network connectivity issues"""
        # Connection instability
        connection_states = ['CONNECTED', 'UNSTABLE', 'DISCONNECTED']
        state['connection_status'] = random.choice(connection_states)
        
        # Poor network metrics
        state['signal_strength'] = min(-20, state['signal_strength'] - random.randint(5, 15))
        state['latency_ms'] = min(500, state['latency_ms'] + random.randint(20, 100))
        state['packet_loss_rate'] = min(10, state['packet_loss_rate'] + np.random.uniform(1, 3))
        state['data_transmission_rate'] = max(1, state['data_transmission_rate'] - np.random.uniform(5, 20))
        
        # More transmission failures
        if state['current_patient_id']:
            state['failed_transmissions'] += random.randint(2, 8)
    
    def _apply_device_degradation(self, state: dict, time_delta: float):
        """Apply gradual device degradation over time"""
        device_age_days = (datetime.now(pytz.UTC) - state['last_maintenance']).days
        
        # Battery degradation (but maintain minimum threshold)
        if device_age_days > 365:  # After 1 year
            battery_degradation = (device_age_days - 365) * 0.01  # 1% per year
            state['battery_level'] = max(20, state['battery_level'] - battery_degradation * (time_delta / 86400))
        
        # Calibration drift
        if (datetime.now(pytz.UTC) - state['last_calibration']).days > 30:
            if random.random() < 0.01:  # 1% chance per update
                state['calibration_status'] = 'NEEDS_CALIBRATION'
        
        # Storage usage growth
        state['storage_usage'] = min(95, state['storage_usage'] + np.random.uniform(0, 0.1))
    
    def generate_alerts(self, device_id: str, state: dict) -> list[dict]:
        """Generate alerts based on device state"""
        alerts = []
        current_time = datetime.now(pytz.UTC)
        
        # Check alert cooldowns
        cooldowns = state.get('alert_cooldowns', {})
        
        # Battery alerts
        if state['battery_level'] <= self.telemetry_config.BATTERY_CRITICAL_THRESHOLD:
            if 'BATTERY_CRITICAL' not in cooldowns or cooldowns['BATTERY_CRITICAL'] < current_time:
                alerts.append({
                    'alert_type': 'BATTERY_CRITICAL',
                    'alert_severity': 'CRITICAL',
                    'alert_message': f"Device {device_id} battery critically low: {state['battery_level']:.1f}%",
                    'timestamp': current_time
                })
                cooldowns['BATTERY_CRITICAL'] = current_time + timedelta(minutes=30)
        
        elif state['battery_level'] <= self.telemetry_config.BATTERY_LOW_THRESHOLD:
            if 'BATTERY_LOW' not in cooldowns or cooldowns['BATTERY_LOW'] < current_time:
                alerts.append({
                    'alert_type': 'BATTERY_LOW',
                    'alert_severity': 'WARNING',
                    'alert_message': f"Device {device_id} battery low: {state['battery_level']:.1f}%",
                    'timestamp': current_time
                })
                cooldowns['BATTERY_LOW'] = current_time + timedelta(minutes=60)
        
        # Performance alerts
        if state['cpu_usage'] > self.telemetry_config.CPU_HIGH_THRESHOLD:
            if 'CPU_HIGH' not in cooldowns or cooldowns['CPU_HIGH'] < current_time:
                alerts.append({
                    'alert_type': 'CPU_HIGH',
                    'alert_severity': 'WARNING',
                    'alert_message': f"Device {device_id} CPU usage high: {state['cpu_usage']:.1f}%",
                    'timestamp': current_time
                })
                cooldowns['CPU_HIGH'] = current_time + timedelta(minutes=15)
        
        if state['memory_usage'] > self.telemetry_config.MEMORY_HIGH_THRESHOLD:
            if 'MEMORY_HIGH' not in cooldowns or cooldowns['MEMORY_HIGH'] < current_time:
                alerts.append({
                    'alert_type': 'MEMORY_HIGH',
                    'alert_severity': 'WARNING',
                    'alert_message': f"Device {device_id} memory usage high: {state['memory_usage']:.1f}%",
                    'timestamp': current_time
                })
                cooldowns['MEMORY_HIGH'] = current_time + timedelta(minutes=15)
        
        # Temperature alerts
        if state['temperature'] > self.telemetry_config.TEMPERATURE_HIGH_THRESHOLD:
            if 'TEMPERATURE_HIGH' not in cooldowns or cooldowns['TEMPERATURE_HIGH'] < current_time:
                alerts.append({
                    'alert_type': 'TEMPERATURE_HIGH',
                    'alert_severity': 'ERROR',
                    'alert_message': f"Device {device_id} temperature high: {state['temperature']:.1f}°C",
                    'timestamp': current_time
                })
                cooldowns['TEMPERATURE_HIGH'] = current_time + timedelta(minutes=20)
        
        # Connectivity alerts
        if state['connection_status'] == 'DISCONNECTED':
            if 'CONNECTIVITY_LOST' not in cooldowns or cooldowns['CONNECTIVITY_LOST'] < current_time:
                alerts.append({
                    'alert_type': 'CONNECTIVITY_LOST',
                    'alert_severity': 'ERROR',
                    'alert_message': f"Device {device_id} lost network connectivity",
                    'timestamp': current_time
                })
                cooldowns['CONNECTIVITY_LOST'] = current_time + timedelta(minutes=10)
        
        elif state['connection_status'] == 'UNSTABLE':
            if 'CONNECTIVITY_UNSTABLE' not in cooldowns or cooldowns['CONNECTIVITY_UNSTABLE'] < current_time:
                alerts.append({
                    'alert_type': 'CONNECTIVITY_UNSTABLE',
                    'alert_severity': 'WARNING',
                    'alert_message': f"Device {device_id} network connection unstable",
                    'timestamp': current_time
                })
                cooldowns['CONNECTIVITY_UNSTABLE'] = current_time + timedelta(minutes=20)
        
        # Maintenance alerts
        if state['next_maintenance_due'] <= current_time:
            if 'MAINTENANCE_OVERDUE' not in cooldowns or cooldowns['MAINTENANCE_OVERDUE'] < current_time:
                alerts.append({
                    'alert_type': 'MAINTENANCE_OVERDUE',
                    'alert_severity': 'WARNING',
                    'alert_message': f"Device {device_id} maintenance overdue",
                    'timestamp': current_time
                })
                cooldowns['MAINTENANCE_OVERDUE'] = current_time + timedelta(hours=24)
        
        elif (state['next_maintenance_due'] - current_time).days <= 7:
            if 'MAINTENANCE_DUE' not in cooldowns or cooldowns['MAINTENANCE_DUE'] < current_time:
                alerts.append({
                    'alert_type': 'MAINTENANCE_DUE',
                    'alert_severity': 'INFO',
                    'alert_message': f"Device {device_id} maintenance due in {(state['next_maintenance_due'] - current_time).days} days",
                    'timestamp': current_time
                })
                cooldowns['MAINTENANCE_DUE'] = current_time + timedelta(hours=48)
        
        # Calibration alerts
        if state['calibration_status'] == 'NEEDS_CALIBRATION':
            if 'CALIBRATION_NEEDED' not in cooldowns or cooldowns['CALIBRATION_NEEDED'] < current_time:
                alerts.append({
                    'alert_type': 'CALIBRATION_NEEDED',
                    'alert_severity': 'WARNING',
                    'alert_message': f"Device {device_id} requires calibration",
                    'timestamp': current_time
                })
                cooldowns['CALIBRATION_NEEDED'] = current_time + timedelta(hours=12)
        
        # Update cooldowns
        state['alert_cooldowns'] = cooldowns
        
        return alerts
    
    def generate_telemetry_record(self, device_id: str, device_type: str, scenario: str = 'NORMAL', 
                                session_id: str = None) -> dict:
        """Generate a single telemetry record"""
        
        # Initialize device if needed
        if device_id not in self.device_states:
            self.initialize_device_state(device_id, device_type)
        
        # Update state
        state = self.update_device_state(device_id, scenario)
        
        # Assign session if provided
        if session_id:
            state['session_id'] = session_id
        
        # Generate alerts
        alerts = self.generate_alerts(device_id, state)
        
        # Select primary alert for this record
        primary_alert = alerts[0] if alerts else None
        
        # Build telemetry record with unique timestamp using Python 3.9 dict merge
        unique_timestamp = self._get_unique_timestamp()
        
        # Base identification data
        base_record = {
            'timestamp': unique_timestamp,
            'device_id': device_id,
            'device_type': device_type,
            'session_id': state.get('session_id'),
            'facility_id': state['facility_id'],
            'room_id': state['room_id'],
        }
        
        # Hardware health data
        hardware_data = {
            'battery_level': round(state['battery_level'], 1),  # Keep decimal for more accurate display
            'battery_temperature': round(state['battery_temperature'], 1),
            'charging_status': state['charging_status'],
            'connection_status': state['connection_status'],
            'signal_strength': state['signal_strength'],
            'data_transmission_rate': round(state['data_transmission_rate'], 2),
            'packet_loss_rate': round(state['packet_loss_rate'], 3),
            'latency_ms': state['latency_ms'],
        }
        
        # System performance data
        performance_data = {
            'cpu_usage': round(state['cpu_usage'], 1),
            'memory_usage': round(state['memory_usage'], 1),
            'storage_usage': round(state['storage_usage'], 1),
            'temperature': round(state['temperature'], 1),
        }
        
        # Status and maintenance data
        status_data = {
            'sensor_connectivity': self._generate_sensor_connectivity(device_type),
            'calibration_status': state['calibration_status'],
            'last_calibration_timestamp': state['last_calibration'],
            'maintenance_status': self._determine_maintenance_status(state),
            'next_maintenance_date': state['next_maintenance_due'],
            'error_codes': self._generate_error_codes(state, alerts),
            'warning_codes': self._generate_warning_codes(state, alerts),
        }
        
        # Alert and operational data
        operational_data = {
            'alert_type': primary_alert['alert_type'] if primary_alert else None,
            'alert_severity': primary_alert['alert_severity'] if primary_alert else None,
            'alert_message': primary_alert['alert_message'] if primary_alert else None,
            'uptime_hours': round(state['uptime_hours'], 1),
            'total_data_collected_mb': round(state['total_data_collected_mb'], 2),
            'successful_transmissions': state['successful_transmissions'],
            'failed_transmissions': state['failed_transmissions'],
        }
        
        # Compliance data
        compliance_data = {
            'firmware_version': state['firmware_version'],
            'last_update_timestamp': state['last_update'],
            'compliance_status': state['compliance_status'],
            'audit_trail': self._generate_audit_trail(device_id, scenario)
        }
        
        # Python 3.9 dict merge operators for cleaner code
        record = base_record | hardware_data | performance_data | status_data | operational_data | compliance_data
        
        # Store alerts in history
        if alerts:
            if device_id not in self.alert_history:
                self.alert_history[device_id] = []
            self.alert_history[device_id].extend(alerts)
            
            # Optimize: Only cleanup alert history every 100 records to reduce processing overhead
            if not hasattr(self, '_cleanup_counters'):
                self._cleanup_counters = {}
            
            if device_id not in self._cleanup_counters:
                self._cleanup_counters[device_id] = 0
            
            self._cleanup_counters[device_id] += 1
            
            # Cleanup only every 100 records for this device
            if self._cleanup_counters[device_id] % 100 == 0:
                cutoff_time = datetime.now(pytz.UTC) - timedelta(hours=24)
                old_count = len(self.alert_history[device_id])
                self.alert_history[device_id] = [
                    alert for alert in self.alert_history[device_id]
                    if alert['timestamp'] > cutoff_time
                ]
                new_count = len(self.alert_history[device_id])
                if old_count != new_count:
                    logger.debug(f"Cleaned {device_id} alert history: {old_count} -> {new_count} alerts")
        
        return record
    
    def _generate_sensor_connectivity(self, device_type: str) -> dict:
        """Generate sensor connectivity status for device type"""
        connectivity = {}
        
        if device_type == 'ECG':
            for lead in ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']:
                connectivity[f'lead_{lead}'] = random.choice(['CONNECTED', 'LOOSE', 'DISCONNECTED'])
        elif device_type == 'EDA':
            for i in range(1, 4):
                connectivity[f'electrode_{i}'] = random.choice(['CONNECTED', 'LOOSE', 'DISCONNECTED'])
        elif device_type == 'PPG':
            connectivity['sensor'] = random.choice(['CONNECTED', 'LOOSE', 'DISCONNECTED'])
        
        return connectivity
    
    def _determine_maintenance_status(self, state: dict) -> str:
        """Determine maintenance status based on device state"""
        days_until_maintenance = (state['next_maintenance_due'] - datetime.now(pytz.UTC)).days
        
        if days_until_maintenance < 0:
            return 'MAINTENANCE_OVERDUE'
        elif days_until_maintenance <= 7:
            return 'MAINTENANCE_DUE'
        else:
            return 'OPERATIONAL'
    
    def _generate_error_codes(self, state: dict, alerts: list[dict]) -> list[str]:
        """Generate error codes based on state and alerts"""
        error_codes = []
        
        for alert in alerts:
            if alert['alert_severity'] in ['ERROR', 'CRITICAL']:
                error_codes.append(f"ERR_{alert['alert_type']}")
        
        # Random system errors
        if random.random() < 0.05:  # 5% chance
            error_codes.append(f"ERR_SYS_{random.randint(1000, 9999)}")
        
        return error_codes
    
    def _generate_warning_codes(self, state: dict, alerts: list[dict]) -> list[str]:
        """Generate warning codes based on state and alerts"""
        warning_codes = []
        
        for alert in alerts:
            if alert['alert_severity'] == 'WARNING':
                warning_codes.append(f"WARN_{alert['alert_type']}")
        
        return warning_codes
    
    def _generate_audit_trail(self, device_id: str, scenario: str) -> dict:
        """Generate audit trail information"""
        return {
            'last_access': datetime.now(pytz.UTC).isoformat(),
            'access_method': 'TELEMETRY_UPDATE',
            'scenario': scenario,
            'system_user': 'SYSTEM',
            'session_uuid': str(uuid.uuid4())
        }
    
    def generate_batch_telemetry(self, device_ids: list[str], device_types: dict[str, str], 
                                scenario: str = 'NORMAL', batch_size: int = 50) -> pd.DataFrame:
        """Generate batch of telemetry records for multiple devices"""
        records = []
        
        for _ in range(batch_size):
            device_id = random.choice(device_ids)
            device_type = device_types.get(device_id, 'UNKNOWN')
            
            record = self.generate_telemetry_record(device_id, device_type, scenario)
            records.append(record)
        
        return pd.DataFrame(records)
    
    def get_device_states(self) -> dict:
        """Get current device states"""
        return self.device_states
    
    def get_alert_history(self, device_id: str = None) -> dict | list:
        """Get alert history for device(s)"""
        if device_id:
            return self.alert_history.get(device_id, [])
        return self.alert_history

def main():
    """Test the device telemetry generator"""
    generator = DeviceTelemetryGenerator()
    
    print("🔧 Device Telemetry Generator Test")
    print("=" * 50)
    
    # Test devices
    test_devices = {
        'ECG_001': 'ECG',
        'EDA_001': 'EDA',
        'PPG_001': 'PPG'
    }
    
    print(f"Testing telemetry generation for {len(test_devices)} devices")
    
    # Generate telemetry data
    for scenario in ['NORMAL', 'HIGH_LOAD', 'NETWORK_ISSUES']:
        print(f"\n--- {scenario} Scenario ---")
        
        batch_data = generator.generate_batch_telemetry(
            device_ids=list(test_devices.keys()),
            device_types=test_devices,
            scenario=scenario,
            batch_size=10
        )
        
        print(f"Generated {len(batch_data)} telemetry records")
        print(f"Alert types: {batch_data['alert_type'].value_counts().to_dict()}")
        print(f"Average CPU usage: {batch_data['cpu_usage'].mean():.1f}%")
        print(f"Average battery level: {batch_data['battery_level'].mean():.1f}%")
    
    print("\n✅ Device telemetry generator test completed!")

if __name__ == "__main__":
    main() 