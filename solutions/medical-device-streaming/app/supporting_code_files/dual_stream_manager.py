#!/usr/bin/env python3
"""
Dual Stream Manager
==================

Orchestrates dual streaming of medical device data:
1. Clinical Data Stream: Patient biosignal data to device-specific tables
2. Telemetry Stream: Device operational data to telemetry table

Manages multiple concurrent streams with proper error handling and monitoring.
"""

import threading
import time
import logging
import json
import sys
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytz
import queue
import pandas as pd

# Python 3.11+ enhanced exception handling support
if sys.version_info >= (3, 11):
    # ExceptionGroup is built-in in Python 3.11+
    PYTHON_311_PLUS = True
else:
    # Fallback for older Python versions
    PYTHON_311_PLUS = False

from supporting_code_files.medical_device_generator import MedicalDeviceGenerator
from supporting_code_files.device_telemetry_generator import DeviceTelemetryGenerator
from supporting_code_files.snowpipe_streaming_client import SnowpipeStreamingClient
from supporting_code_files.config import SnowflakeConfig, MedicalDeviceConfig, TelemetryConfig, DemoConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DualStreamManager:
    """
    Manages dual streaming of clinical data and device telemetry.
    Coordinates multiple device generators and streaming clients.
    """
    
    def __init__(self, 
                 snowflake_config: SnowflakeConfig = None,
                 device_config: MedicalDeviceConfig = None,
                 telemetry_config: TelemetryConfig = None,
                 demo_config: DemoConfig = None):
        
        self.snowflake_config = snowflake_config or SnowflakeConfig()
        self.device_config = device_config or MedicalDeviceConfig()
        self.telemetry_config = telemetry_config or TelemetryConfig()
        self.demo_config = demo_config or DemoConfig()
        
        # Initialize generators
        self.device_generator = MedicalDeviceGenerator(self.device_config)
        self.telemetry_generator = DeviceTelemetryGenerator(self.telemetry_config, self.device_config)
        
        # Streaming clients for each device type + telemetry
        self.clinical_clients = {}
        self.telemetry_client = None
        
        # Stream control
        self.streaming_active = False
        self.clinical_threads = {}
        self.telemetry_thread = None
        
        # Data queues for each stream
        self.clinical_queues = {}
        self.telemetry_queue = queue.Queue(maxsize=5000)  # Increased capacity
        
        # Statistics tracking
        self.stats = {
            'clinical_stats': {},
            'telemetry_stats': {
                'batches_sent': 0,
                'records_sent': 0,
                'errors': 0,
                'start_time': None
            },
            'start_time': None,
            'session_info': {}
        }
        
        logger.info("Dual Stream Manager initialized")
        logger.info(f"Python 3.11+ enhanced exception handling: {'enabled' if PYTHON_311_PLUS else 'disabled'}")
    
    def _cleanup_accumulated_stats(self):
        """Clean up accumulated statistics to prevent memory growth"""
        try:
            # Reset error counts that grow indefinitely
            for device_type in self.stats['clinical_stats']:
                if 'errors' in self.stats['clinical_stats'][device_type]:
                    if self.stats['clinical_stats'][device_type]['errors'] > 10000:
                        logger.debug(f"Resetting {device_type} error count from {self.stats['clinical_stats'][device_type]['errors']}")
                        self.stats['clinical_stats'][device_type]['errors'] = 0
            
            # Reset telemetry error count
            if self.stats['telemetry_stats']['errors'] > 10000:
                logger.debug(f"Resetting telemetry error count from {self.stats['telemetry_stats']['errors']}")
                self.stats['telemetry_stats']['errors'] = 0
                
        except Exception as e:
            logger.warning(f"Error during stats cleanup: {str(e)}")
    
    def _cleanup_alert_histories(self):
        """Clean up alert histories from device telemetry generator"""
        try:
            if hasattr(self.telemetry_generator, 'alert_history'):
                # Clean up old alert histories (older than 1 hour)
                cutoff_time = datetime.now(pytz.UTC) - timedelta(hours=1)
                cleaned_devices = 0
                
                for device_id in list(self.telemetry_generator.alert_history.keys()):
                    old_count = len(self.telemetry_generator.alert_history[device_id])
                    self.telemetry_generator.alert_history[device_id] = [
                        alert for alert in self.telemetry_generator.alert_history[device_id]
                        if alert['timestamp'] > cutoff_time
                    ]
                    new_count = len(self.telemetry_generator.alert_history[device_id])
                    if old_count != new_count:
                        cleaned_devices += 1
                
                if cleaned_devices > 0:
                    logger.debug(f"Cleaned alert histories for {cleaned_devices} devices")
                    
        except Exception as e:
            logger.warning(f"Error during alert history cleanup: {str(e)}")
    
    def _handle_streaming_exceptions(self, exceptions: list[Exception]) -> None:
        """
        Python 3.11+ enhanced exception handling for concurrent streaming operations.
        Groups related exceptions and provides better error reporting.
        """
        if not exceptions:
            return
            
        if PYTHON_311_PLUS and len(exceptions) > 1:
            # Use Python 3.11 ExceptionGroup for multiple concurrent exceptions
            streaming_errors = []
            connection_errors = []
            data_errors = []
            
            for exc in exceptions:
                exc_str = str(exc).lower()
                if 'connection' in exc_str or 'network' in exc_str:
                    connection_errors.append(exc)
                elif 'data' in exc_str or 'format' in exc_str:
                    data_errors.append(exc)
                else:
                    streaming_errors.append(exc)
            
            # Group exceptions by type for better error handling
            grouped_exceptions = []
            if streaming_errors:
                grouped_exceptions.append(("Streaming Errors", streaming_errors))
            if connection_errors:
                grouped_exceptions.append(("Connection Errors", connection_errors))  
            if data_errors:
                grouped_exceptions.append(("Data Format Errors", data_errors))
            
            # Log grouped exceptions with enhanced Python 3.11 error formatting
            for error_type, error_list in grouped_exceptions:
                logger.error(f"🚨 {error_type} ({len(error_list)} errors):")
                for i, error in enumerate(error_list, 1):
                    logger.error(f"  {i}. {type(error).__name__}: {error}")
                    
        else:
            # Fallback for single exceptions or older Python versions
            for i, exc in enumerate(exceptions, 1):
                logger.error(f"❌ Streaming error {i}: {type(exc).__name__}: {exc}")
    
    def _clear_clinical_queues(self):
        """Clear all clinical queues to remove old records with potentially duplicate timestamps"""
        logger.info("Clearing clinical queues for fresh streaming session...")
        for device_type, queue_obj in self.clinical_queues.items():
            # Clear the queue by consuming all items
            cleared_count = 0
            try:
                while True:
                    queue_obj.get_nowait()
                    cleared_count += 1
            except queue.Empty:
                pass
            if cleared_count > 0:
                logger.info(f"Cleared {cleared_count} old records from {device_type} queue")
    
    def _initialize_streaming_clients(self) -> bool:
        """Initialize streaming clients for each device type and telemetry with separate pipes"""
        logger.info("Initializing streaming clients with separate pipes...")
        
        try:
            # Initialize clinical data streaming clients (one per device type)
            for device_type in self.device_config.SUPPORTED_DEVICES.keys():
                schema = self.snowflake_config.CLINICAL_SCHEMA
                client = SnowpipeStreamingClient(self.snowflake_config)
                
                # Use device-specific pipe configuration
                pipe_name = self.snowflake_config.get_clinical_pipe_name(device_type)
                channel_name = self.snowflake_config.get_clinical_channel_name(device_type)
                
                client.configure_for_pipe(
                    pipe_name=pipe_name,
                    schema=schema,
                    channel_name=channel_name
                )
                
                self.clinical_clients[device_type] = client
                
                # Initialize device-specific queue sizes based on observed load patterns
                if device_type == 'ECG':
                    queue_size = 1000000  # Extra large for ECG (highest volume + processing complexity)
                elif device_type == 'PPG':
                    queue_size = 500000   # Large for PPG (high volume)
                elif device_type == 'EDA':
                    queue_size = 100000   # Increased for EDA
                else:
                    queue_size = 200000   # Increased default for other devices
                    
                self.clinical_queues[device_type] = queue.Queue(maxsize=queue_size)
                logger.info(f"Initialized {device_type} queue with capacity: {queue_size}")
                self.stats['clinical_stats'][device_type] = {
                    'batches_sent': 0,
                    'records_sent': 0,
                    'errors': 0,
                    'start_time': None
                }
                
                logger.info(f"Initialized {device_type} clinical client for pipe {pipe_name}")

            # Initialize telemetry streaming client  
            self.telemetry_client = SnowpipeStreamingClient(self.snowflake_config)
            telemetry_pipe = self.snowflake_config.TELEMETRY_PIPE
            telemetry_channel = self.snowflake_config.get_telemetry_channel_name()
            
            self.telemetry_client.configure_for_pipe(
                pipe_name=telemetry_pipe,
                schema=self.snowflake_config.TELEMETRY_SCHEMA,
                channel_name=telemetry_channel
            )
            
            logger.info(f"Initialized telemetry client for pipe {telemetry_pipe}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize streaming clients: {str(e)}")
            return False
    
    def create_patient_sessions(self, patient_count: int = None) -> dict:
        """Create patient sessions with device assignments"""
        patient_count = patient_count or self.device_config.DEFAULT_PATIENT_COUNT
        
        logger.info(f"Creating {patient_count} patient sessions...")
        
        patient_profiles = self.device_generator.get_patient_profiles()[:patient_count]
        device_profiles = self.device_generator.get_device_profiles()
        
        sessions = {}
        
        for patient in patient_profiles:
            patient_id = patient['patient_id']
            session_id = patient['session_id']
            
            # Assign devices to patient
            assigned_device_types = []
            assigned_device_ids = []
            
            # Ensure each patient has all three device types for comprehensive testing
            base_devices = ['ECG', 'EDA', 'PPG']
            
            # Assign specific device instances (ensure unique assignment)
            for device_type in base_devices:
                available_devices = [d for d, info in device_profiles.items() 
                                   if info['device_type'] == device_type 
                                   and info['status'] == 'ACTIVE'
                                   and info.get('current_patient_id') is None]  # Not already assigned
                
                assigned_device_id = None
                
                if available_devices:
                    # Use existing available device
                    assigned_device_id = available_devices[0]  # Take first unassigned device
                    
                    # Mark device as assigned to this patient
                    device_profiles[assigned_device_id]['current_patient_id'] = patient_id
                    device_profiles[assigned_device_id]['current_session_id'] = session_id
                    device_profiles[assigned_device_id]['assignment_timestamp'] = datetime.now(pytz.UTC)
                    
                    logger.info(f"Assigned {assigned_device_id} to {patient_id}")
                else:
                    # Create emergency device if needed
                    logger.warning(f"No available {device_type} devices for {patient_id}")
                    assigned_device_id = f"{device_type}_{patient_id}_EMERGENCY"
                    device_profiles[assigned_device_id] = {
                        'device_id': assigned_device_id,
                        'device_type': device_type,
                        'device_model': f"Emergency-{device_type}",
                        'status': 'ACTIVE',
                        'current_patient_id': patient_id,
                        'current_session_id': session_id,
                        'assignment_timestamp': datetime.now(pytz.UTC)
                    }
                    logger.info(f"Created emergency device {assigned_device_id} for {patient_id}")
                
                # Add to assignment lists
                assigned_device_types.append(device_type)
                assigned_device_ids.append(assigned_device_id)
                
                # Initialize device in telemetry generator
                self.telemetry_generator.initialize_device_state(
                    assigned_device_id, device_type, patient.get('facility_id')
                )
            
            sessions[patient_id] = {
                'patient_profile': patient,
                'assigned_device_types': assigned_device_types,
                'assigned_device_ids': assigned_device_ids,
                'session_start_time': datetime.now(pytz.UTC),
                'session_status': 'ACTIVE'
            }
            
            logger.info(f"Created session for {patient_id} with devices: {assigned_device_types}")
        
        self.stats['session_info'] = sessions
        return sessions
    
    def start_clinical_data_streaming(self, sessions: dict, duration: int = None):
        """Start clinical data streaming for all patient sessions - supports continuous streaming when duration is None"""
        logger.info(f"Starting clinical data streaming for {len(sessions)} patients...")
        
        def clinical_stream_worker(device_type: str):
            """Worker thread for clinical data streaming"""
            client = self.clinical_clients[device_type]
            queue_obj = self.clinical_queues[device_type]
            stats = self.stats['clinical_stats'][device_type]
            
            try:
                # Authenticate and setup streaming
                jwt_token = client.authenticate()
                client.discover_ingest_host(jwt_token)
                scoped_token = client.get_scoped_token(jwt_token)
                
                channel_created = client.create_channel(scoped_token)
                if not channel_created:
                    logger.error(f"Failed to create channel for {device_type}")
                    return
                
                stats['start_time'] = datetime.now(pytz.UTC)
                batch_records = []
                last_batch_time = datetime.now(pytz.UTC)  # Track when batch was last sent
                batch_timeout = 0.1  # Send partial batches after 100ms for low-latency streaming
                
                logger.info(f"✅ {device_type} clinical streaming started")
                
                while self.streaming_active:
                    try:
                        # Check queue for data with minimal blocking
                        try:
                            record = queue_obj.get(timeout=0.01)  # 10ms timeout for low-latency streaming
                            batch_records.append(record)
                        except queue.Empty:
                            # Check if we have partial batch that's been waiting too long
                            current_time = datetime.now(pytz.UTC)
                            time_since_last_batch = (current_time - last_batch_time).total_seconds()
                            
                            if batch_records and time_since_last_batch >= batch_timeout:
                                # Send partial batch to prevent data gaps/delays
                                success = client.send_data_batch(batch_records)
                                
                                if success:
                                    stats['batches_sent'] += 1
                                    stats['records_sent'] += len(batch_records)
                                    logger.debug(f"⏰ {device_type} timeout batch sent: {len(batch_records)} records after {time_since_last_batch:.1f}s")
                                else:
                                    stats['errors'] += 1
                                    logger.error(f"❌ {device_type} timeout batch send failed")
                                
                                batch_records = []  # Reset batch
                                last_batch_time = current_time
                            continue
                        
                        # Process batch when full or timeout
                        if len(batch_records) >= self.device_config.CLINICAL_DATA_BATCH_SIZE:
                            success = client.send_data_batch(batch_records)
                            
                            if success:
                                stats['batches_sent'] += 1
                                stats['records_sent'] += len(batch_records)
                                logger.debug(f"✅ {device_type} batch sent: {len(batch_records)} records")
                            else:
                                stats['errors'] += 1
                                logger.error(f"❌ {device_type} batch send failed")
                            
                            batch_records = []  # Reset batch
                            last_batch_time = datetime.now(pytz.UTC)
                            
                        # NO SLEEP - Maximum throughput streaming
                        # Removed all artificial delays for optimal performance
                        
                    except Exception as e:
                        stats['errors'] += 1
                        logger.error(f"{device_type} streaming error: {str(e)}")
                        
                        # Enhanced error recovery with better monitoring
                        current_queue_size = queue_obj.qsize()
                        logger.warning(f"{device_type} queue size: {current_queue_size}, batch size: {len(batch_records)}")
                        
                        # NO SLEEP ERROR RECOVERY - Immediate retry for maximum throughput
                        # Log error but continue immediately without delays
                        logger.warning(f"{device_type} error occurred, continuing immediately for maximum throughput")
                
                # Send any remaining records
                if batch_records:
                    client.send_data_batch(batch_records)
                    stats['batches_sent'] += 1
                    stats['records_sent'] += len(batch_records)
                
                logger.info(f"✅ {device_type} clinical streaming completed")
                
            except Exception as e:
                logger.error(f"Critical error in {device_type} streaming: {str(e)}")
                stats['errors'] += 1
        
        # Start streaming threads for each device type that has assignments
        active_device_types = set()
        for session in sessions.values():
            active_device_types.update(session['assigned_device_types'])
        
        for device_type in active_device_types:
            thread = threading.Thread(
                target=clinical_stream_worker,
                args=(device_type,),
                name=f"clinical_stream_{device_type}"
            )
            thread.daemon = True
            thread.start()
            self.clinical_threads[device_type] = thread
            
            logger.info(f"Started {device_type} clinical streaming thread")
    
    def start_telemetry_streaming(self, sessions: dict, scenario: str = 'NORMAL'):
        """Start device telemetry streaming"""
        logger.info("Starting device telemetry streaming...")
        
        def telemetry_stream_worker():
            """Worker thread for telemetry streaming"""
            try:
                # Authenticate and setup streaming
                jwt_token = self.telemetry_client.authenticate()
                self.telemetry_client.discover_ingest_host(jwt_token)
                scoped_token = self.telemetry_client.get_scoped_token(jwt_token)
                
                channel_created = self.telemetry_client.create_channel(scoped_token)
                if not channel_created:
                    logger.error("Failed to create telemetry channel")
                    return
                
                self.stats['telemetry_stats']['start_time'] = datetime.now(pytz.UTC)
                batch_records = []
                
                # Get all assigned devices
                all_device_ids = []
                device_types = {}
                
                for session in sessions.values():
                    for device_id in session['assigned_device_ids']:
                        all_device_ids.append(device_id)
                        # Find device type from device profiles
                        device_profiles = self.device_generator.get_device_profiles()
                        device_types[device_id] = device_profiles[device_id]['device_type']
                
                logger.info(f"✅ Telemetry streaming started for {len(all_device_ids)} devices")
                
                while self.streaming_active:
                    try:
                        # Generate telemetry data
                        telemetry_batch = self.telemetry_generator.generate_batch_telemetry(
                            device_ids=all_device_ids,
                            device_types=device_types,
                            scenario=scenario,
                            batch_size=self.device_config.TELEMETRY_BATCH_SIZE
                        )
                        
                        if not telemetry_batch.empty:
                            # Convert to records for streaming
                            records = telemetry_batch.to_dict('records')
                            
                            # Send telemetry batch
                            success = self.telemetry_client.send_data_batch(records)
                            
                            if success:
                                self.stats['telemetry_stats']['batches_sent'] += 1
                                self.stats['telemetry_stats']['records_sent'] += len(records)
                                logger.debug(f"Telemetry: Sent batch of {len(records)} records")
                            else:
                                self.stats['telemetry_stats']['errors'] += 1
                                logger.error("Telemetry: Failed to send batch")
                        
                        # NO SLEEP - Maximum telemetry throughput
                        
                    except Exception as e:
                        self.stats['telemetry_stats']['errors'] += 1
                        logger.error(f"Telemetry streaming error: {str(e)}")
                        
                        # NO SLEEP - Immediate retry for maximum telemetry throughput
                        logger.warning("Telemetry error occurred, continuing immediately for maximum throughput")
                
                logger.info("✅ Telemetry streaming completed")
                
            except Exception as e:
                logger.error(f"Critical error in telemetry streaming: {str(e)}")
                self.stats['telemetry_stats']['errors'] += 1
        
        # Start telemetry thread
        self.telemetry_thread = threading.Thread(
            target=telemetry_stream_worker,
            name="telemetry_stream"
        )
        self.telemetry_thread.daemon = True
        self.telemetry_thread.start()
        
        logger.info("Started telemetry streaming thread")
    
    def generate_and_queue_clinical_data(self, sessions: dict, duration: int = None):
        """Generate clinical data and queue for streaming - supports continuous streaming when duration is None"""
        duration_msg = "continuous" if duration is None else f"{duration} seconds"
        logger.info(f"Starting clinical data generation for {duration_msg}...")
        
        def data_generation_worker():
            """Worker thread for clinical data generation"""
            # For continuous streaming (duration=None), run indefinitely until streaming_active becomes False
            # For timed streaming, set end_time
            end_time = None if duration is None else datetime.now(pytz.UTC).timestamp() + duration
            
            generation_cycle_count = 0
            last_cleanup_time = datetime.now(pytz.UTC)
            
            while self.streaming_active:
                # Break if duration is specified and exceeded
                if end_time is not None and datetime.now(pytz.UTC).timestamp() >= end_time:
                    break
                try:
                    for patient_id, session in sessions.items():
                        if session['session_status'] != 'ACTIVE':
                            continue
                        
                        # Generate data for each assigned device type
                        for device_type in session['assigned_device_types']:
                            try:
                                # Generate device data with NeuroKit2 compatibility
                                if device_type == 'ECG':
                                    # Generate ECG data with unique timestamps
                                    data = self.device_generator.generate_ecg_data(
                                        session['patient_profile'],
                                        session['assigned_device_ids'][session['assigned_device_types'].index(device_type)],
                                        duration=self.device_config.CLINICAL_STREAMING_INTERVAL
                                    )

                                elif device_type == 'EDA':
                                    # Generate EDA data with unique timestamps
                                    data = self.device_generator.generate_eda_data(
                                        session['patient_profile'],
                                        session['assigned_device_ids'][session['assigned_device_types'].index(device_type)],
                                        duration=self.device_config.CLINICAL_STREAMING_INTERVAL
                                    )
                                elif device_type == 'PPG':
                                    # Generate PPG data with unique timestamps
                                    data = self.device_generator.generate_ppg_data(
                                        session['patient_profile'],
                                        session['assigned_device_ids'][session['assigned_device_types'].index(device_type)],
                                        duration=self.device_config.CLINICAL_STREAMING_INTERVAL
                                    )

                                else:
                                    continue
                                
                                # Queue records for streaming
                                if not data.empty:
                                    records = data.to_dict('records')
                                    queue_obj = self.clinical_queues[device_type]
                                    
                                    records_queued = 0
                                    records_dropped = 0
                                    
                                    # Implement backpressure control
                                    if queue_obj.qsize() > queue_obj.maxsize * 0.8:
                                        logger.debug(f"{device_type} queue at {queue_obj.qsize()}/{queue_obj.maxsize} capacity - applying backpressure")
                                        time.sleep(0.05)  # 50ms backpressure delay
                                        continue  # Skip this batch to allow queue to drain
                                    
                                    for record in records:
                                        try:
                                            # Try non-blocking put first
                                            queue_obj.put_nowait(record)
                                            records_queued += 1
                                        except queue.Full:
                                            # If queue is full, try with longer timeout for important data
                                            try:
                                                queue_obj.put(record, timeout=0.001)  # 1ms timeout for low-latency streaming
                                                records_queued += 1
                                            except queue.Full:
                                                records_dropped += 1
                                                self.stats['clinical_stats'][device_type]['errors'] += 1
                                                # Only log every 100 dropped records to reduce spam
                                                if self.stats['clinical_stats'][device_type]['errors'] % 100 == 0:
                                                    logger.warning(f"{device_type} queue full, dropped {self.stats['clinical_stats'][device_type]['errors']} records so far")
                                    
                                    # Log batch summary if there were drops
                                    if records_dropped > 0:
                                        logger.debug(f"{device_type} batch: Queued {records_queued}, Dropped {records_dropped} records")
                                
                            except Exception as e:
                                logger.error(f"Error generating {device_type} data for {patient_id}: {str(e)}")
                                self.stats['clinical_stats'][device_type]['errors'] += 1
                                # NO SLEEP - Maximum throughput even on errors
                    
                    # Periodic cleanup to prevent memory growth
                    generation_cycle_count += 1
                    current_time = datetime.now(pytz.UTC)
                    
                    # Cleanup stats and alert histories every 1000 cycles (~10 minutes at 100ms/cycle)
                    if generation_cycle_count % 1000 == 0 or (current_time - last_cleanup_time).total_seconds() > 600:
                        logger.debug(f"Performing periodic cleanup after {generation_cycle_count} cycles")
                        self._cleanup_accumulated_stats()
                        self._cleanup_alert_histories()
                        last_cleanup_time = current_time
                    
                    # Prevent CPU exhaustion with controlled timing
                    time.sleep(0.1)  # 100ms delay between generation cycles
                    
                except Exception as e:
                    logger.error(f"Error in data generation cycle: {str(e)}")
                    # Brief pause after errors to prevent error loops
                    time.sleep(0.2)
            
            logger.info("Clinical data generation completed")
        
        # Start data generation thread
        generation_thread = threading.Thread(
            target=data_generation_worker,
            name="clinical_data_generation"
        )
        generation_thread.daemon = True
        generation_thread.start()
        
        return generation_thread
    
    def start_dual_streaming(self, patient_count: int = None, duration: int = None, scenario: str = 'NORMAL'):
        """Start complete dual streaming demo - supports continuous streaming when duration is None"""
        streaming_mode = "Continuous" if duration is None else f"{duration}s"
        logger.info(f"🏥 Starting Medical Device Dual Streaming Demo ({streaming_mode})")
        logger.info("=" * 60)
        
        try:
            # Initialize
            if not self._initialize_streaming_clients():
                logger.error("Failed to initialize streaming clients")
                return False
            
            # Create patient sessions
            sessions = self.create_patient_sessions(patient_count)
            if not sessions:
                logger.error("Failed to create patient sessions")
                return False
            
            # Start streaming
            self.streaming_active = True
            self.stats['start_time'] = datetime.now(pytz.UTC)
            
            # Clear clinical queues before starting new session
            self._clear_clinical_queues()
            
            # Reset the medical device generator's timestamp state for new session
            from .medical_device_generator import MedicalDeviceGenerator
            MedicalDeviceGenerator.reset_timestamp_state()
            
            # Start both streams
            self.start_clinical_data_streaming(sessions, duration)
            self.start_telemetry_streaming(sessions, scenario)
            
            # Start data generation
            data_thread = self.generate_and_queue_clinical_data(sessions, duration)
            
            logger.info(f"✅ Dual streaming started for {len(sessions)} patients")
            logger.info(f"📊 Clinical devices: {sum(len(s['assigned_device_types']) for s in sessions.values())}")
            logger.info(f"📊 Telemetry devices: {sum(len(s['assigned_device_ids']) for s in sessions.values())}")
            duration_msg = "Continuous (until stopped)" if duration is None else f"{duration} seconds"
            logger.info(f"⏰ Duration: {duration_msg}")
            logger.info(f"🎯 Scenario: {scenario}")
            
            # Monitor streaming
            self.monitor_streaming_progress(duration)
            
            # Wait for completion
            data_thread.join()
            
            # Stop streaming
            self.stop_streaming()
            
            # Print final statistics
            self.print_final_statistics()
            
            return True
            
        except Exception as e:
            logger.error(f"Dual streaming failed: {str(e)}")
            self.stop_streaming()
            return False
    
    def monitor_streaming_progress(self, duration: int = None):
        """Monitor and log streaming progress - supports continuous streaming when duration is None"""
        start_time = datetime.now(pytz.UTC)
        
        # For continuous streaming (duration=None), run until streaming_active becomes False
        # For timed streaming, run until duration is reached
        while self.streaming_active:
            # Break if duration is specified and exceeded
            if duration is not None and (datetime.now(pytz.UTC) - start_time).total_seconds() >= duration:
                break
                
            try:
                # Calculate statistics
                elapsed = int((datetime.now(pytz.UTC) - start_time).total_seconds())
                
                # Clinical stats
                total_clinical_records = sum(stats['records_sent'] for stats in self.stats['clinical_stats'].values())
                total_clinical_batches = sum(stats['batches_sent'] for stats in self.stats['clinical_stats'].values())
                clinical_errors = sum(stats['errors'] for stats in self.stats['clinical_stats'].values())
                
                # Telemetry stats
                telemetry_records = self.stats['telemetry_stats']['records_sent']
                telemetry_batches = self.stats['telemetry_stats']['batches_sent']
                telemetry_errors = self.stats['telemetry_stats']['errors']
                
                # Rates
                clinical_rate = total_clinical_records / elapsed if elapsed > 0 else 0
                telemetry_rate = telemetry_records / elapsed if elapsed > 0 else 0
                
                # Progress message - different for continuous vs timed
                if duration is None:
                    logger.info(f"📊 Continuous streaming: {elapsed}s elapsed")
                else:
                    remaining = max(0, duration - elapsed)
                    logger.info(f"📊 Progress: {elapsed}s elapsed, {remaining}s remaining")
                    
                logger.info(f"   Clinical: {total_clinical_records} records ({clinical_rate:.1f}/sec) - {clinical_errors} errors")
                logger.info(f"   Telemetry: {telemetry_records} records ({telemetry_rate:.1f}/sec) - {telemetry_errors} errors")
                
                # NO SLEEP - Continuous monitoring without delays
                
            except Exception as e:
                logger.error(f"Error in monitoring: {str(e)}")
                # NO SLEEP - Continue monitoring immediately
    
    def stop_streaming(self):
        """Stop all streaming operations"""
        logger.info("Stopping dual streaming...")
        
        self.streaming_active = False
        
        # Wait for threads to complete
        for device_type, thread in self.clinical_threads.items():
            if thread and thread.is_alive():
                thread.join(timeout=10)
                logger.info(f"Stopped {device_type} clinical streaming")
        
        if self.telemetry_thread and self.telemetry_thread.is_alive():
            self.telemetry_thread.join(timeout=10)
            logger.info("Stopped telemetry streaming")
        
        logger.info("✅ All streaming operations stopped")
    
    def print_final_statistics(self):
        """Print comprehensive final statistics"""
        if not self.stats['start_time']:
            return
        
        total_duration = (datetime.now(pytz.UTC) - self.stats['start_time']).total_seconds()
        
        logger.info("\n📊 FINAL DUAL STREAMING STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Total Duration: {total_duration:.1f} seconds")
        
        # Clinical Data Statistics
        logger.info(f"\n🩺 CLINICAL DATA STREAMS:")
        total_clinical_records = 0
        total_clinical_batches = 0
        total_clinical_errors = 0
        
        for device_type, stats in self.stats['clinical_stats'].items():
            if stats['records_sent'] > 0:
                rate = stats['records_sent'] / total_duration if total_duration > 0 else 0
                logger.info(f"   {device_type}: {stats['records_sent']} records ({rate:.1f}/sec) - {stats['errors']} errors")
                total_clinical_records += stats['records_sent']
                total_clinical_batches += stats['batches_sent']
                total_clinical_errors += stats['errors']
        
        clinical_rate = total_clinical_records / total_duration if total_duration > 0 else 0
        logger.info(f"   TOTAL CLINICAL: {total_clinical_records} records ({clinical_rate:.1f}/sec)")
        
        # Telemetry Statistics
        logger.info(f"\n🔧 TELEMETRY DATA STREAM:")
        telemetry_stats = self.stats['telemetry_stats']
        telemetry_rate = telemetry_stats['records_sent'] / total_duration if total_duration > 0 else 0
        logger.info(f"   Records: {telemetry_stats['records_sent']} ({telemetry_rate:.1f}/sec)")
        logger.info(f"   Batches: {telemetry_stats['batches_sent']}")
        logger.info(f"   Errors: {telemetry_stats['errors']}")
        
        # Overall Statistics
        total_records = total_clinical_records + telemetry_stats['records_sent']
        total_batches = total_clinical_batches + telemetry_stats['batches_sent']
        total_errors = total_clinical_errors + telemetry_stats['errors']
        overall_rate = total_records / total_duration if total_duration > 0 else 0
        
        logger.info(f"\n🎯 OVERALL PERFORMANCE:")
        logger.info(f"   Total Records: {total_records}")
        logger.info(f"   Total Batches: {total_batches}")
        logger.info(f"   Overall Rate: {overall_rate:.1f} records/second")
        logger.info(f"   Error Rate: {(total_errors/total_records*100):.2f}%" if total_records > 0 else "   Error Rate: 0%")
        logger.info(f"   Success Rate: {((total_records-total_errors)/total_records*100):.2f}%" if total_records > 0 else "   Success Rate: 100%")
        
        logger.info("=" * 60)

def main():
    """Test the dual stream manager"""
    manager = DualStreamManager()
    
    print("🏥 Dual Stream Manager Test")
    print("=" * 50)
    
    # Run a short test streaming session
    success = manager.start_dual_streaming(
        patient_count=3,
        duration=60,  # 1 minute test
        scenario='NORMAL'
    )
    
    if success:
        print("\n✅ Dual streaming test completed successfully!")
    else:
        print("\n❌ Dual streaming test failed!")

if __name__ == "__main__":
    main() 