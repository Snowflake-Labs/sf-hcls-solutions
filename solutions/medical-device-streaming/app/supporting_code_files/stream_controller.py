#!/usr/bin/env python3
"""
Stream Controller
=================

Controls the medical device streaming system from the Streamlit interface.
Provides a clean interface to start/stop streaming and retrieve statistics.
"""

import threading
import logging
import sys
import os
from datetime import datetime
from typing import Dict, Optional
import queue

# Project modules - using absolute imports to supporting_code_files package

from supporting_code_files.dual_stream_manager import DualStreamManager
from supporting_code_files.config import SnowflakeConfig, MedicalDeviceConfig, TelemetryConfig, DemoConfig

class StreamController:
    """
    Controller class for managing streaming operations from Streamlit interface.
    """
    
    def __init__(self):
        # Initialize configurations
        self.snowflake_config = SnowflakeConfig()
        self.device_config = MedicalDeviceConfig()
        self.telemetry_config = TelemetryConfig()
        self.demo_config = DemoConfig()
        
        # Initialize stream manager ONCE (like command line version)
        self.stream_manager = DualStreamManager(
            self.snowflake_config,
            self.device_config,
            self.telemetry_config,
            self.demo_config
        )
        self.streaming_thread = None
        self.streaming_active = False
        
        # Tracking variables
        self.start_time = None
        self.current_config = {}
        
        # Initialize log queue BEFORE setup_logging
        self.log_queue = queue.Queue(maxsize=100)
        
        # Logging setup
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging for the stream controller"""
        # Create a custom handler that captures logs
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Add handler to capture logs for display
        log_handler = QueueLogHandler(self.log_queue)
        log_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        log_handler.setFormatter(formatter)
        
        # Add handler to stream_controller logger
        self.logger.addHandler(log_handler)
        
        # Also add handler to capture logs from other streaming modules
        streaming_modules = [
            'dual_stream_manager',
            'medical_device_generator', 
            'device_telemetry_generator',
            'snowpipe_streaming_client'
        ]
        
        for module_name in streaming_modules:
            module_logger = logging.getLogger(module_name)
            module_logger.setLevel(logging.INFO)
            module_logger.addHandler(log_handler)
    
    def start_streaming(self, patient_count: int = 5, duration: int = None, scenario: str = 'NORMAL') -> bool:
        """
        Start the medical device streaming process.
        
        Args:
            patient_count: Number of patients to simulate
            duration: Duration in seconds (None for continuous streaming)
            scenario: Operational scenario
            
        Returns:
            bool: True if streaming started successfully
        """
        if self.streaming_active:
            self.logger.warning("Streaming is already active")
            return False
        
        try:
            duration_str = "continuous" if duration is None else f"{duration}s"
            self.logger.info(f"Starting streaming: {patient_count} patients, {duration_str}, {scenario}")
            
            # Store current configuration
            self.current_config = {
                'patient_count': patient_count,
                'duration': duration,
                'scenario': scenario
            }
            
            # Start streaming in a separate thread
            self.streaming_thread = threading.Thread(
                target=self._run_streaming,
                args=(patient_count, duration, scenario),
                daemon=True
            )
            
            self.streaming_active = True
            import pytz
            self.start_time = datetime.now(pytz.UTC)
            self.streaming_thread.start()
            
            self.logger.info("✅ Streaming started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start streaming: {str(e)}")
            self.streaming_active = False
            return False
    
    def _run_streaming(self, patient_count: int, duration: int = None, scenario: str = 'NORMAL'):
        """
        Internal method to run the streaming process.
        This runs in a separate thread.
        
        Args:
            duration: Duration in seconds (None for continuous streaming)
        """
        try:
            self.logger.info("Initializing dual streaming...")
            
            # Run the dual streaming
            success = self.stream_manager.start_dual_streaming(
                patient_count=patient_count,
                duration=duration,
                scenario=scenario
            )
            
            if success:
                self.logger.info("✅ Streaming completed successfully")
            else:
                self.logger.error("❌ Streaming failed")
                
        except Exception as e:
            self.logger.error(f"Streaming error: {str(e)}")
        finally:
            # Mark streaming as inactive
            self.streaming_active = False
            self.logger.info("Streaming process finished")
    
    def stop_streaming(self) -> bool:
        """
        Stop the streaming process.
        
        Returns:
            bool: True if stopped successfully
        """
        try:
            if not self.streaming_active:
                self.logger.warning("Streaming is not active")
                return True
            
            self.logger.info("Stopping streaming...")
            
            # Stop the stream manager
            if self.stream_manager:
                self.stream_manager.stop_streaming()
            
            # Mark as inactive
            self.streaming_active = False
            
            # Wait for thread to complete (with timeout)
            if self.streaming_thread and self.streaming_thread.is_alive():
                self.streaming_thread.join(timeout=10)
            
            self.logger.info("✅ Streaming stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping streaming: {str(e)}")
            return False
    
    def get_current_stats(self) -> Dict:
        """
        Get current streaming statistics.
        
        Returns:
            Dict: Current statistics from stream manager
        """
        if not self.stream_manager or not self.streaming_active:
            return {
                'clinical_stats': {},
                'telemetry_stats': {
                    'batches_sent': 0,
                    'records_sent': 0,
                    'errors': 0
                },
                'start_time': None,
                'session_info': {}
            }
        
        try:
            return self.stream_manager.stats.copy()
        except Exception as e:
            self.logger.error(f"Error getting stats: {str(e)}")
            return {}
    
    def is_streaming_active(self) -> bool:
        """Check if streaming is currently active"""
        # Check if thread exists and is alive
        if hasattr(self, 'streaming_thread') and self.streaming_thread is not None:
            thread_alive = self.streaming_thread.is_alive()
            
            # If thread is alive, streaming is definitely active
            if thread_alive:
                if not self.streaming_active:
                    self.streaming_active = True
                    self.logger.info("Updated streaming status: thread detected as running")
                return True
            
            # If thread is dead and we thought we were active, update status
            elif self.streaming_active:
                self.streaming_active = False
                self.logger.info("Updated streaming status: thread completed")
                return False
        
        # Return current status if no thread or thread doesn't exist
        return self.streaming_active
    
    def get_current_config(self) -> Dict:
        """Get current streaming configuration"""
        return self.current_config.copy()
    
    def get_recent_logs(self, max_logs: int = 50) -> list:
        """
        Get recent log messages.
        
        Args:
            max_logs: Maximum number of logs to return
            
        Returns:
            list: Recent log messages
        """
        logs = []
        try:
            # Get logs from queue (non-blocking)
            while not self.log_queue.empty() and len(logs) < max_logs:
                logs.append(self.log_queue.get_nowait())
        except queue.Empty:
            pass
        
        return logs
    
    def check_prerequisites(self) -> tuple[bool, str]:
        """
        Check if system prerequisites are met.
        
        Returns:
            tuple: (success, message)
        """
        try:
            # Check Snowflake configuration
            required_config = [
                self.snowflake_config.ACCOUNT,
                self.snowflake_config.USER,
                self.snowflake_config.DATABASE,
                self.snowflake_config.CLINICAL_SCHEMA,
                self.snowflake_config.TELEMETRY_SCHEMA
            ]
            
            if not all(required_config):
                return False, "Missing required Snowflake configuration parameters"
            
            # Check authentication method
            if not self.snowflake_config.PRIVATE_KEY_PATH:
                return False, "SNOWFLAKE_PRIVATE_KEY_PATH not configured. Private key authentication is required."
            
            return True, "Prerequisites check passed"
            
        except Exception as e:
            return False, f"Prerequisites check failed: {str(e)}"
    
    def get_system_info(self) -> Dict:
        """Get system information for display"""
        return {
            'database': self.snowflake_config.DATABASE,
            'clinical_schema': self.snowflake_config.CLINICAL_SCHEMA,
            'telemetry_schema': self.snowflake_config.TELEMETRY_SCHEMA,
            'supported_devices': list(self.device_config.SUPPORTED_DEVICES.keys()),
            'device_tables': self.snowflake_config.DEVICE_TABLES,
            'telemetry_table': self.snowflake_config.TELEMETRY_TABLE
        }


class QueueLogHandler(logging.Handler):
    """Custom log handler that puts logs into a queue for retrieval"""
    
    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue
    
    def emit(self, record):
        try:
            # Format the log record
            log_entry = self.format(record)
            
            # Add to queue (remove oldest if queue is full)
            try:
                self.log_queue.put_nowait(log_entry)
            except queue.Full:
                # Remove oldest entry and add new one
                try:
                    self.log_queue.get_nowait()
                    self.log_queue.put_nowait(log_entry)
                except queue.Empty:
                    pass
                    
        except Exception:
            # Ignore errors in logging handler
            pass 