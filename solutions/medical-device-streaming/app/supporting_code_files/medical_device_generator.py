#!/usr/bin/env python3
"""
Multi-Device Medical Generator using NeuroKit2
==============================================
Python 3.11+ Optimized for Enhanced Performance

Generates realistic biosignal data for medical device types.

Currently Active Device Types:
- ECG: Electrocardiography (Heart activity)
- EDA: Electrodermal Activity (Stress/arousal)
- PPG: Photoplethysmography (Blood flow)

Focus on active device types: ECG, EDA, and PPG for real-time medical monitoring.

Python 3.11+ Enhancements:
- 10-60% performance improvements from CPython optimizations
- Enhanced error messages with precise source locations
- Faster dictionary operations and list comprehensions
- Improved memory efficiency for large-scale data generation
"""

import neurokit2 as nk
import numpy as np
import pandas as pd
import logging
import uuid
import json
import os
from datetime import datetime, timedelta
from typing import Generator, Optional
from supporting_code_files.config import MedicalDeviceConfig
import random
import pytz

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MedicalDeviceGenerator:
    """
    Unified generator for multiple medical device types using NeuroKit2.
    Generates realistic biosignal data with patient-specific conditions and device characteristics.
    """
    
    # Class-level timestamp management for unique timestamps across all generators
    _global_base_time = None
    _global_timestamp_offset = 0
    _global_timestamp_lock = None
    
    def __init__(self, config: MedicalDeviceConfig = None):
        """Initialize the medical device generator with configuration"""
        self.config = config or MedicalDeviceConfig()
        
        # Initialize global base time and lock once for the entire session (TIMEZONE-NEUTRAL)
        if MedicalDeviceGenerator._global_base_time is None:
            import pytz
            MedicalDeviceGenerator._global_base_time = datetime.now(pytz.UTC)
        
        # Initialize class-level lock for thread-safe timestamp generation
        if MedicalDeviceGenerator._global_timestamp_lock is None:
            import threading
            MedicalDeviceGenerator._global_timestamp_lock = threading.Lock()
        
        # Load device profiles
        self.device_profiles = self._load_device_profiles()
        
        # Initialize NeuroKit2 if available
        try:
            import neurokit2 as nk
            self.nk = nk
            logger.info("NeuroKit2 initialized successfully")
        except ImportError:
            logger.warning("NeuroKit2 not available. Using synthetic data generation.")
            self.nk = None
        self.patient_profiles = self._load_patient_profiles()
        logger.info(f"Initialized Medical Device Generator with {len(self.device_profiles)} device profiles")
    
    def _load_device_profiles(self) -> dict:
        """Load device profiles from configuration"""
        device_profiles = {}
        
        # Ensure we have enough devices for all patients (with buffer)
        patient_count = self.config.DEFAULT_PATIENT_COUNT
        devices_per_type = max(patient_count + 2, 5)  # At least patient_count + buffer
        
        for device_type, config in self.config.SUPPORTED_DEVICES.items():
            # Create sufficient device instances per type
            for i in range(devices_per_type):  # Enough devices for all patients
                device_id = f"{device_type}_{str(i+1).zfill(3)}"
                # Use Python 3.9 dictionary merge operator for cleaner code
                base_device_info = {
                    'device_id': device_id,
                    'device_type': device_type,
                    'device_model': f"{config['name']}-Pro-{random.choice(['X1', 'X2', 'Z3'])}",
                    'firmware_version': f"v{random.randint(2,4)}.{random.randint(0,9)}.{random.randint(0,9)}",
                    'sampling_rate': random.choice(config['sampling_rates']),
                    'facility_id': f"FACILITY_{random.randint(1,3)}",
                    'room_id': f"ROOM_{random.randint(101,350)}",
                    'status': 'ACTIVE',
                }
                maintenance_info = {
                    'last_maintenance': datetime.now(pytz.UTC) - timedelta(days=random.randint(1,90)),
                    'next_maintenance': datetime.now(pytz.UTC) + timedelta(days=random.randint(30,180))
                }
                # Python 3.9 dict merge operator
                device_profiles[device_id] = base_device_info | maintenance_info
        
        return device_profiles
    
    def _load_patient_profiles(self) -> list[dict]:
        """Load patient profiles with medical conditions"""
        try:
            # Try to load from existing config
            config_path = 'supporting_code_files/patients.json'
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    patient_config = json.load(f)
                profiles = patient_config['patient_profiles']['standard_set'][:self.config.DEFAULT_PATIENT_COUNT]
            else:
                profiles = self._get_fallback_patient_profiles()
            
            # Enhance profiles with device assignments
            for i, profile in enumerate(profiles):
                profile['session_id'] = f"SESSION_{str(i+1).zfill(3)}_{datetime.now(pytz.UTC).strftime('%Y%m%d_%H%M%S')}"
                profile['facility_id'] = f"FACILITY_{random.randint(1,3)}"
                profile['room_id'] = f"ROOM_{random.randint(101,350)}"
                profile['session_start_time'] = datetime.now(pytz.UTC)
                profile['attending_physician'] = f"Dr. {random.choice(['Smith', 'Johnson', 'Williams', 'Brown', 'Davis'])}"
                profile['clinical_priority'] = random.choice(['ROUTINE', 'URGENT', 'CRITICAL'])
                
                # Skip device assignment during initialization - will be handled by DualStreamManager
                # profile['assigned_devices'] = self._assign_devices_to_patient(profile)
                profile['assigned_devices'] = []  # Empty list, will be populated during session creation
            
            return profiles
            
        except Exception as e:
            logger.error(f"Failed to load patient profiles: {str(e)}")
            return self._get_fallback_patient_profiles()
    
    def _get_fallback_patient_profiles(self) -> list[dict]:
        """Fallback patient profiles if loading fails - matches patients.json exactly"""
        return [
            {
                'patient_id': '1229701',
                'condition': 'NORMAL',
                'heart_rate': 72,
                'stress_level': 0.3
            },
            {
                'patient_id': '1229702', 
                'condition': 'HIGH_STRESS',
                'heart_rate': 85,
                'stress_level': 0.6
            },
            {
                'patient_id': '1229704',
                'condition': 'TACHYCARDIA',
                'heart_rate': 110,
                'stress_level': 0.4
            },
            {
                'patient_id': '1229709',
                'condition': 'BRADYCARDIA',
                'heart_rate': 55,
                'stress_level': 0.2
            },
            {
                'patient_id': '1229737',
                'condition': 'NORMAL_ATHLETE',
                'heart_rate': 60,
                'stress_level': 0.1
            }
        ]
    
    def _assign_devices_to_patient(self, patient_profile: dict) -> list[str]:
        """Get devices already assigned to this patient (from dual_stream_manager)"""
        patient_id = patient_profile.get('patient_id', 'UNKNOWN')
        
        # Find devices already assigned to this patient by dual_stream_manager
        assigned_devices = []
        for device_id, device_info in self.device_profiles.items():
            if device_info.get('current_patient_id') == patient_id:
                assigned_devices.append(device_id)
        
        # If no devices assigned yet, fall back to base devices (shouldn't happen with proper flow)
        if not assigned_devices:
            logger.warning(f"No devices found for {patient_id}, using fallback assignment")
            # Use unique device assignment based on patient ID for fallback
            device_types_needed = ['ECG', 'EDA', 'PPG']
            
            # Extract patient number for unique assignment
            patient_number = 1  # default
            if patient_id.startswith('PATIENT_'):
                # Handle old PATIENT_001 format (fallback compatibility)
                try:
                    patient_number = int(patient_id.split('_')[1])
                except (IndexError, ValueError):
                    patient_number = 1
            else:
                # Handle new numeric patient IDs (1229701, 1229702, etc.)
                # Map specific patient IDs to sequential numbers for consistent device assignment
                patient_id_mapping = {
                    '1229701': 1,
                    '1229702': 2, 
                    '1229704': 3,
                    '1229709': 4,
                    '1229737': 5
                }
                patient_number = patient_id_mapping.get(patient_id, hash(patient_id) % 100 + 1)
            
            for device_type in device_types_needed:
                available = [d for d, info in self.device_profiles.items() 
                           if info['device_type'] == device_type and info.get('current_patient_id') is None]
                if available:
                    # Use patient number to select unique device (with wraparound)
                    device_index = (patient_number - 1) % len(available)
                    selected_device = available[device_index]
                    assigned_devices.append(selected_device)
                    # Mark as temporarily assigned to prevent other patients from using it
                    self.device_profiles[selected_device]['current_patient_id'] = patient_id
        
        # Ensure we don't exceed available devices and have some variety
        available_devices = list(self.device_profiles.keys())
        final_devices = []
        
        for device_id in assigned_devices:
            if device_id in available_devices and device_id not in final_devices:
                final_devices.append(device_id)
        
        # Add random devices if needed to reach target count
        target_count = min(self.config.DEVICES_PER_PATIENT, len(available_devices))
        while len(final_devices) < target_count:
            random_device = random.choice(available_devices)
            if random_device not in final_devices:
                final_devices.append(random_device)
        
        return final_devices[:target_count]
    
    def generate_ecg_data(self, patient_profile: dict, device_id: str, duration: float = 10.0) -> pd.DataFrame:
        """Generate ECG data using NeuroKit2"""
        try:
            device_info = self.device_profiles[device_id]
            sampling_rate = int(device_info['sampling_rate'])  # Ensure integer
            heart_rate = int(patient_profile.get('heart_rate', 75))  # Ensure integer
            condition = patient_profile.get('condition', 'NORMAL')
            
            # OPTIMIZED FOR REAL-TIME STREAMING WITH MAXIMUM THROUGHPUT
            requested_duration = max(0.001, min(float(duration), 30.0))  # Support 1ms intervals for optimal latency
            heart_rate = max(60, min(heart_rate, 120))  # Clamp heart rate between 60-120 bpm for stability
            sampling_rate = max(100, min(sampling_rate, 250))  # Aligned with PPG sampling rate for optimal real-time performance
            
            # For real-time streaming: generate adequate samples even for microsecond intervals
            # Minimum 2 samples per batch - aligned with EDA/PPG for performance parity
            min_batch_samples = 2  # Minimum batch size for real-time streaming (matches EDA/PPG)
            samples_needed = max(min_batch_samples, int(requested_duration * sampling_rate))
            nk_duration = max(1, int(samples_needed / sampling_rate) + 1)  # Duration to generate enough samples
            
            # Generate base ECG signal - NeuroKit2 requires integer parameters
            # Simplified error handling like EDA/PPG for better real-time performance
            ecg_signal = nk.ecg_simulate(
                duration=nk_duration,  # Use viable duration for NeuroKit2
                sampling_rate=sampling_rate,
                heart_rate=heart_rate,
                noise=0.01
            )
            
            # Apply condition-specific modifications
            if condition == 'ATRIAL_FIBRILLATION':
                # Add irregular rhythm
                ecg_signal = self._add_afib_artifacts(ecg_signal, sampling_rate)
            elif condition == 'TACHYCARDIA':
                # Increase heart rate
                heart_rate = min(heart_rate * 1.3, 150)
            elif condition == 'BRADYCARDIA':
                # Decrease heart rate
                heart_rate = max(heart_rate * 0.7, 40)
            
            # Truncate signal to requested duration for real-time streaming
            if len(ecg_signal) > samples_needed:
                ecg_signal = ecg_signal[:samples_needed]
            
            # Create 12-lead ECG data with unique timestamps
            timestamps = self._get_unique_timestamps(len(ecg_signal), sampling_rate)
            
            # Generate 12-lead data with realistic relationships
            data = []
            for i, timestamp in enumerate(timestamps):
                record = {
                    'timestamp': timestamp,
                    'device_id': device_id,
                    'session_id': patient_profile['session_id'],
                    'patient_id': patient_profile['patient_id'],
                    'heart_rate': heart_rate + random.randint(-5, 5),
                    'rr_intervals': [],  # Would calculate from peaks
                    'lead_I': ecg_signal[i] + np.random.normal(0, 0.01),
                    'lead_II': ecg_signal[i] * 1.2 + np.random.normal(0, 0.01),
                    'lead_III': ecg_signal[i] * 0.8 + np.random.normal(0, 0.01),
                    'lead_aVR': -ecg_signal[i] * 0.5 + np.random.normal(0, 0.01),
                    'lead_aVL': ecg_signal[i] * 0.6 + np.random.normal(0, 0.01),
                    'lead_aVF': ecg_signal[i] * 0.9 + np.random.normal(0, 0.01),
                    'lead_V1': ecg_signal[i] * 0.7 + np.random.normal(0, 0.01),
                    'lead_V2': ecg_signal[i] * 1.1 + np.random.normal(0, 0.01),
                    'lead_V3': ecg_signal[i] * 1.3 + np.random.normal(0, 0.01),
                    'lead_V4': ecg_signal[i] * 1.5 + np.random.normal(0, 0.01),
                    'lead_V5': ecg_signal[i] * 1.2 + np.random.normal(0, 0.01),
                    'lead_V6': ecg_signal[i] * 0.9 + np.random.normal(0, 0.01),
                    'rhythm_classification': self._classify_rhythm(condition),
                    'st_elevation': np.random.normal(0, 0.1),
                    'qt_interval': random.randint(350, 450),
                    'signal_quality': max(0.7, min(1.0, np.random.normal(0.9, 0.1))),
                    'artifacts_detected': random.random() < 0.05,
                    'noise_level': np.random.uniform(0.01, 0.03)
                }
                data.append(record)
            
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"Error generating ECG data: {str(e)}")
            return pd.DataFrame()


    
    def generate_eda_data(self, patient_profile: dict, device_id: str, duration: float = 10.0) -> pd.DataFrame:
        """Generate EDA data using NeuroKit2"""
        try:
            device_info = self.device_profiles[device_id]
            sampling_rate = int(device_info['sampling_rate'])  # Ensure integer
            stress_level = patient_profile.get('stress_level', 0.5)
            condition = patient_profile.get('condition', 'NORMAL')
            
            # OPTIMIZED FOR REAL-TIME STREAMING WITH MAXIMUM THROUGHPUT
            requested_duration = max(0.001, min(float(duration), 30.0))  # Support 1ms intervals for optimal latency
            sampling_rate = max(64, min(sampling_rate, 1000))  # Higher frequency for real-time EDA streaming
            
            # For real-time streaming: generate adequate samples even for microsecond intervals
            # Minimum 2 samples per batch for EDA real-time flow
            min_batch_samples = 2  # Minimum batch size for real-time EDA streaming
            samples_needed = max(min_batch_samples, int(requested_duration * sampling_rate))
            nk_duration = max(1, int(samples_needed / sampling_rate) + 1)  # Duration to generate enough samples
            
            # Generate EDA signal with SCR peaks - NeuroKit2 requires integer parameters
            scr_number = min(4 if 'STRESS' in condition else 2, nk_duration)  # Limit SCR peaks to generation duration
            eda_signal = nk.eda_simulate(
                duration=nk_duration,  # Use viable duration for NeuroKit2
                sampling_rate=sampling_rate,
                scr_number=max(1, scr_number),  # At least 1 SCR
                drift=0.01
            )
            
            # Truncate signal to requested duration for real-time streaming
            if len(eda_signal) > samples_needed:
                eda_signal = eda_signal[:samples_needed]
            
            # Generate unique timestamps for EDA data
            timestamps = self._get_unique_timestamps(len(eda_signal), sampling_rate)
            
            data = []
            for i, timestamp in enumerate(timestamps):
                # Base conductance level affected by stress
                base_scl = 5.0 + (stress_level * 10.0)  # μS
                scr_amplitude = stress_level * 2.0
                
                record = {
                    'timestamp': timestamp,
                    'device_id': device_id,
                    'session_id': patient_profile['session_id'],
                    'patient_id': patient_profile['patient_id'],
                    'skin_conductance_level': base_scl + eda_signal[i],
                    'skin_conductance_response': scr_amplitude * abs(eda_signal[i]),
                    'arousal_level': min(1.0, stress_level + np.random.uniform(-0.1, 0.1)),
                    'stress_indicator': stress_level,
                    'emotional_valence': self._determine_emotional_valence(condition, stress_level),
                    'scr_peaks_detected': random.randint(0, 2),
                    'peak_amplitude': scr_amplitude * np.random.uniform(0.5, 1.5),
                    'rise_time_ms': random.randint(1000, 3000),
                    'half_recovery_time_ms': random.randint(2000, 8000),
                    'signal_quality': max(0.7, min(1.0, np.random.normal(0.85, 0.1))),
                    'temperature_compensation': True
                }
                data.append(record)
            
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"Error generating EDA data: {str(e)}")
            return pd.DataFrame()
    
    def generate_ppg_data(self, patient_profile: dict, device_id: str, duration: float = 10.0) -> pd.DataFrame:
        """Generate PPG data using NeuroKit2"""
        try:
            device_info = self.device_profiles[device_id]
            sampling_rate = int(device_info['sampling_rate'])  # Ensure integer
            heart_rate = int(patient_profile.get('heart_rate', 75))  # Ensure integer
            condition = patient_profile.get('condition', 'NORMAL')
            
            # OPTIMIZED FOR REAL-TIME STREAMING WITH MAXIMUM THROUGHPUT
            requested_duration = max(0.001, min(float(duration), 30.0))  # Support 1ms intervals for optimal latency
            heart_rate = max(60, min(heart_rate, 120))  # Clamp heart rate for stability
            sampling_rate = max(100, min(sampling_rate, 250))  # High-frequency PPG sampling for real-time streaming
            
            # For real-time streaming: generate adequate samples even for microsecond intervals
            # Minimum 2 samples per batch for PPG real-time flow
            min_batch_samples = 2  # Minimum batch size for real-time PPG streaming
            samples_needed = max(min_batch_samples, int(requested_duration * sampling_rate))
            nk_duration = max(2, int(samples_needed / sampling_rate) + 1)  # PPG needs minimum 2 seconds duration
            
            ppg_signal = nk.ppg_simulate(
                duration=nk_duration,  # Use viable minimum duration for NeuroKit2
                sampling_rate=sampling_rate,
                heart_rate=heart_rate
            )
            
            # Truncate signal to requested duration for real-time streaming
            if len(ppg_signal) > samples_needed:
                ppg_signal = ppg_signal[:samples_needed]
            
            # Generate unique timestamps for PPG data
            timestamps = self._get_unique_timestamps(len(ppg_signal), sampling_rate)
            
            data = []
            for i, timestamp in enumerate(timestamps):
                # SpO2 affected by condition
                spo2_base = 98 if condition == 'NORMAL' else 94
                spo2 = spo2_base + np.random.uniform(-2, 2)
                
                record = {
                    'timestamp': timestamp,
                    'device_id': device_id,
                    'session_id': patient_profile['session_id'],
                    'patient_id': patient_profile['patient_id'],
                    'raw_ppg_signal': ppg_signal[i],
                    'heart_rate': heart_rate + random.randint(-3, 3),
                    'systolic_peak': ppg_signal[i] * np.random.uniform(0.8, 1.2),
                    'diastolic_notch': ppg_signal[i] * np.random.uniform(0.3, 0.6),
                    'pulse_wave_velocity': np.random.uniform(4, 8),  # m/s
                    'spo2': max(85, min(100, spo2)),
                    'perfusion_index': np.random.uniform(0.5, 5.0),
                    'arterial_stiffness': np.random.uniform(6, 12),
                    'blood_pressure_estimate': {
                        'systolic': random.randint(110, 140),
                        'diastolic': random.randint(70, 90)
                    },
                    'signal_quality': max(0.7, min(1.0, np.random.normal(0.9, 0.1))),
                    'motion_artifacts': random.random() < 0.05
                }
                data.append(record)
            
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"Error generating PPG data: {str(e)}")
            return pd.DataFrame()


    
    # Helper methods for condition-specific modifications
    def _add_afib_artifacts(self, signal: np.ndarray, sampling_rate: int) -> np.ndarray:
        """Add atrial fibrillation artifacts to ECG signal"""
        # Add irregular rhythm variations
        for i in range(len(signal)):
            if random.random() < 0.1:  # 10% chance of irregularity
                signal[i] += np.random.normal(0, 0.2)
        return signal
    
    def _classify_rhythm(self, condition: str) -> str:
        """Classify heart rhythm based on condition"""
        if condition == 'ATRIAL_FIBRILLATION':
            return 'ATRIAL_FIBRILLATION'
        elif condition == 'TACHYCARDIA':
            return 'SINUS_TACHYCARDIA'
        elif condition == 'BRADYCARDIA':
            return 'SINUS_BRADYCARDIA'
        else:
            return 'NORMAL_SINUS_RHYTHM'
    

    def _determine_emotional_valence(self, condition: str, stress_level: float) -> str:
        """Determine emotional valence from condition and stress"""
        if stress_level > 0.7:
            return 'NEGATIVE'
        elif stress_level < 0.3:
            return 'POSITIVE'
        else:
            return 'NEUTRAL'
    

    def generate_patient_session_data(self, patient_id: str, device_types: list[str], duration: float = 10.0) -> dict[str, pd.DataFrame]:
        """Generate data for all assigned devices for a patient session"""
        patient_profile = next((p for p in self.patient_profiles if p['patient_id'] == patient_id), None)
        if not patient_profile:
            logger.error(f"Patient {patient_id} not found")
            return {}
        
        session_data = {}
        
        for device_type in device_types:
            # Find available device of this type
            available_devices = [d for d in self.device_profiles.keys() if d.startswith(device_type)]
            if not available_devices:
                logger.warning(f"No {device_type} devices available")
                continue
            
            device_id = random.choice(available_devices)
            
            # Generate data based on device type
            if device_type == 'ECG':
                data = self.generate_ecg_data(patient_profile, device_id, duration)

            elif device_type == 'EDA':
                data = self.generate_eda_data(patient_profile, device_id, duration)
            elif device_type == 'PPG':
                data = self.generate_ppg_data(patient_profile, device_id, duration)

            else:
                logger.warning(f"Unknown device type: {device_type}")
                continue
            
            if not data.empty:
                session_data[device_type] = data
        
        return session_data
    
    def get_patient_profiles(self) -> list[dict]:
        """Get list of patient profiles"""
        return self.patient_profiles
    
    def get_device_profiles(self) -> dict:
        """Get dictionary of device profiles"""
        return self.device_profiles

    def _get_unique_timestamps(self, periods: int, sampling_rate: int) -> pd.DatetimeIndex:
        """
        Generate timestamps for streaming data using ACTUAL real-time stamps.
        For true streaming, timestamps should reflect when data actually enters the system.
        """
        import pytz
        from datetime import timedelta
        
        # Validate inputs to prevent errors
        periods = max(1, int(periods))
        sampling_rate = max(1, min(int(sampling_rate), 10000))  # Cap at 10kHz
        
        # For streaming data, use CURRENT time as the base (not future times)
        current_time = datetime.now(pytz.UTC)
        
        # Calculate time interval in microseconds (minimum 100us = 10kHz max)
        interval_us = max(100, int(1_000_000 / sampling_rate))
        
        # For real streaming: generate timestamps BACKWARDS from current time
        # This ensures all timestamps are <= current time (no future data)
        # Most recent data point gets current time, older points get earlier times
        timestamps = []
        for i in range(periods):
            # Generate timestamps going backwards in time from current moment
            offset_us = (periods - 1 - i) * interval_us
            timestamp = current_time - timedelta(microseconds=offset_us)
            timestamps.append(timestamp)
        
        # Convert to pandas DatetimeIndex
        try:
            timestamps = pd.DatetimeIndex(timestamps)
        except Exception as e:
            logger.error(f"Error creating timestamp index: {e}")
            # Fallback: simple range ending at current time
            timestamps = pd.date_range(
                end=current_time,
                periods=periods,
                freq=f'{interval_us}us'
            )
        
        logger.debug(f"Generated {periods} timestamps from {timestamps[0]} to {timestamps[-1]}")
        return timestamps
    
    @classmethod
    def reset_timestamp_state(cls):
        """
        Reset timestamp state - no longer needed with real-time timestamp generation.
        Kept for compatibility with existing code.
        """
        import threading
        with cls._global_timestamp_lock if cls._global_timestamp_lock else threading.Lock():
            import pytz
            cls._global_base_time = datetime.now(pytz.UTC)
            cls._global_timestamp_offset = 0
            logger.info(f"Timestamp state reset (now using real-time generation). Current time: {cls._global_base_time}")

def main():
    """Test the medical device generator"""
    generator = MedicalDeviceGenerator()
    
    print("🏥 Medical Device Generator Test")
    print("=" * 50)
    
    # Test generation for first patient
    patient = generator.get_patient_profiles()[0]
    print(f"Testing data generation for {patient['patient_id']}")
    
    # Generate data for active device types
    device_types = ['ECG', 'EDA', 'PPG']
    session_data = generator.generate_patient_session_data(
        patient['patient_id'], 
        device_types, 
        duration=5.0
    )
    
    for device_type, data in session_data.items():
        print(f"\n{device_type} Data: {len(data)} records generated")
        print(data.head(2))
    
    print("\n✅ Medical device generator test completed!")

if __name__ == "__main__":
    main() 