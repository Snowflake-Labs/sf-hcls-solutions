#!/usr/bin/env python3
"""
Medical Device Streaming Control Dashboard
==========================================
Python 3.11+ Required for Optimal Performance

Streamlit application for controlling and monitoring medical device data streaming.
Provides real-time control over the dual streaming system and monitors record counts
in target Snowflake tables.

Python 3.11+ Enhancements:
- 10-60% performance improvements for real-time dashboard updates
- Enhanced error messages for better debugging
- Improved string processing with removeprefix/removesuffix methods
- Better type hints with built-in generic types
- Optimized memory usage for concurrent data visualization
- Faster data processing and chart rendering
"""

import streamlit as st
import pandas as pd
import time
import threading
from datetime import datetime, timedelta
import sys
import os
import signal
import subprocess
import plotly.graph_objects as go
import logging
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import json
import pytz

# Project modules - using absolute imports to supporting_code_files package

from supporting_code_files.stream_controller import StreamController
from supporting_code_files.database_monitor import DatabaseMonitor
from supporting_code_files.config_handler import StreamlitConfig

# Page configuration
st.set_page_config(
    page_title="Medical Device Streaming Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

class StreamingDashboard:
    def __init__(self):
        self.config = StreamlitConfig()
        self.stream_controller = StreamController()
        self.db_monitor = DatabaseMonitor()
        self.logger = logging.getLogger(__name__)
        
        # Initialize session state
        if 'streaming_active' not in st.session_state:
            st.session_state.streaming_active = False
        if 'stream_stats' not in st.session_state:
            st.session_state.stream_stats = {}
        if 'last_refresh' not in st.session_state:
            st.session_state.last_refresh = datetime.now(pytz.UTC)
        if 'confirm_reset' not in st.session_state:
            st.session_state.confirm_reset = False
        # New session state variables for tracking streaming history
        if 'last_streaming_stopped_time' not in st.session_state:
            st.session_state.last_streaming_stopped_time = None
        if 'streaming_ever_started' not in st.session_state:
            st.session_state.streaming_ever_started = False
        # Message management for auto-clearing
        if 'temp_messages' not in st.session_state:
            st.session_state.temp_messages = []
        if 'last_message_clear' not in st.session_state:
            st.session_state.last_message_clear = datetime.now(pytz.UTC)

    def add_temp_message(self, message_type: str, message: str, duration: int = 10):
        """Add a temporary message that will auto-clear after specified seconds"""
        timestamp = datetime.now(pytz.UTC)
        st.session_state.temp_messages.append({
            'type': message_type,  # 'success', 'info', 'warning', 'error'
            'message': message,
            'timestamp': timestamp,
            'duration': duration
        })
        
    def show_temp_messages(self):
        """Display and manage temporary messages"""
        current_time = datetime.now(pytz.UTC)
        
        # Filter out expired messages
        active_messages = []
        for msg in st.session_state.temp_messages:
            time_elapsed = (current_time - msg['timestamp']).total_seconds()
            if time_elapsed < msg['duration']:
                active_messages.append(msg)
        
        # Update session state with only active messages
        st.session_state.temp_messages = active_messages
        
        # Display active messages
        for msg in active_messages:
            time_left = msg['duration'] - (current_time - msg['timestamp']).total_seconds()
            if msg['type'] == 'success':
                st.success(f"{msg['message']} ⏰ ({time_left:.0f}s)")
            elif msg['type'] == 'info':
                st.info(f"{msg['message']} ⏰ ({time_left:.0f}s)")
            elif msg['type'] == 'warning':
                st.warning(f"{msg['message']} ⏰ ({time_left:.0f}s)")
            elif msg['type'] == 'error':
                st.error(f"{msg['message']} ⏰ ({time_left:.0f}s)")

    def clear_all_temp_messages(self):
        """Clear all temporary messages immediately"""
        st.session_state.temp_messages = []

    def _render_time_ticker(self):
        """Render real-time clock showing local and UTC time"""
        now_local = datetime.now()
        now_utc = datetime.now(pytz.UTC)
        
        # Format times for display
        local_time = now_local.strftime("%H:%M:%S")
        utc_time = now_utc.strftime("%H:%M:%S")
        
        # Show local time with timezone
        local_tz = now_local.astimezone().tzinfo.tzname(now_local)
        
        st.metric(
            "🕐 Current Time", 
            local_time,
            delta=f"UTC: {utc_time}",
            help=f"Local time ({local_tz}) and UTC time for chart timestamp comparison"
        )

    def render_header(self):
        """Render the dashboard header"""
        st.title("🏥 Medical Device Streaming Dashboard")
        st.markdown("---")
        
        # Always sync streaming status to ensure accurate display
        # This prevents stale status information
        current_time = datetime.now(pytz.UTC)
        last_sync = getattr(st.session_state, 'last_sync_time', datetime.min.replace(tzinfo=pytz.UTC))
        time_since_sync = (current_time - last_sync).total_seconds()
        
        # Sync every 2 seconds to keep status current, or immediately after startup
        if time_since_sync >= 2 or last_sync == datetime.min:
            self._sync_streaming_status()
            st.session_state.last_sync_time = current_time
        
        # Use 4 columns to include the time ticker
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Streaming Status", 
                     "🟢 ACTIVE" if st.session_state.get('streaming_active', False) else "🔴 STOPPED")
        with col2:
            if (st.session_state.get('streaming_active', False) and 
                st.session_state.get('streaming_start_time') is not None):
                elapsed = datetime.now(pytz.UTC) - st.session_state.streaming_start_time
                st.metric("Stream Uptime", f"{elapsed.total_seconds():.0f}s")
            else:
                st.metric("Stream Uptime", "0s")
        with col3:
            # Show when streaming was last updated (stopped or started)
            if st.session_state.get('streaming_ever_started', False) and st.session_state.get('last_streaming_stopped_time'):
                # Show when streaming last stopped
                last_updated_text = st.session_state.last_streaming_stopped_time.strftime("%H:%M:%S")
            elif st.session_state.get('streaming_active', False) and st.session_state.get('streaming_start_time'):
                # Currently streaming - show when it started
                last_updated_text = st.session_state.streaming_start_time.strftime("%H:%M:%S")
            else:
                # Never streamed in this session
                last_updated_text = "N/A"
            
            st.metric("Last Stream Updated", last_updated_text)
        with col4:
            # Real-time clock showing local and UTC time
            self._render_time_ticker()

    def render_control_panel(self):
        """Render the streaming control panel"""
        # Force clear sidebar to prevent cached elements from auto-refresh
        st.sidebar.empty()
        st.sidebar.header("🎛️ Streaming Controls")
        
        # Show temporary messages in sidebar
        with st.sidebar:
            self.show_temp_messages()
        
        # Use the same sync timing as header to avoid duplicate syncs
        # The header sync will handle the timing logic
        
        # Fixed configuration - 5 patients, continuous streaming, normal scenario
        patient_count = 5  # Static number of patients
        duration = None  # Continuous streaming
        scenario = "NORMAL"  # Always normal scenario

        # Control buttons
        st.sidebar.markdown("### 🚀 Stream Control")
        
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            if st.button("▶️ Start Stream", 
                        disabled=st.session_state.get('streaming_active', False),
                        type="primary",
                        key="start_stream_main"):
                self.start_streaming(patient_count, duration, scenario)
        
        with col2:
            if st.button("⏹️ Stop Stream", 
                        disabled=not st.session_state.get('streaming_active', False),
                        type="secondary",
                        key="stop_stream_main"):
                self.stop_streaming()
        
        # Auto-refresh settings - always available
        st.sidebar.markdown("### 🔄 Refresh Settings")
        auto_refresh = st.sidebar.checkbox(
            "Auto Refresh",
            value=st.session_state.get("auto_refresh_main", False),
            key="auto_refresh_main",
        )
        
        # If auto-refresh is turned off, immediately reset last_refresh to prevent pending refreshes
        # Use session state directly to get the current checkbox value
        if not st.session_state.get("auto_refresh_main", False) and 'last_refresh' in st.session_state:
            st.session_state.last_refresh = datetime.now(pytz.UTC)
        
        refresh_interval = st.sidebar.slider(
            "Refresh Interval (seconds)",
            1,
            30,
            st.session_state.get("refresh_interval", 5),
            key="refresh_interval_main",
        )
        
        # Store refresh interval in session state for other components to access
        st.session_state.refresh_interval = refresh_interval
        
        # Emergency controls - use structured layout like Start/Stop buttons
        st.sidebar.markdown("### 🚨 Emergency Controls")
        
        # Put emergency buttons in a structured container
        emergency_col = st.sidebar.columns(1)[0]
        with emergency_col:
            # Force stop all streaming processes button (preserves Streamlit dashboards)
            if st.button("⚠️ Force Stop ALL Medical Streaming",
                        help="COMPREHENSIVE EMERGENCY STOP: Immediately terminates BOTH internal Streamlit streaming AND all external medical device processes from ANY version directory (V0, V1, V11_9, V12_0, etc.). Preserves Streamlit dashboards. Stops: active streaming sessions, streaming demos, generators, dual stream managers, snowpipe clients, and any other medical device processes.",
                        type="secondary",
                        key="force_stop_all_streaming"):
                self.force_stop_all_streaming_processes()
            
            # Database reset button
            if st.button("🔥 Reset Medical Device Data",
                        help="Truncate all clinical and telemetry tables in Snowflake. This action cannot be undone.",
                        type="secondary",
                        key="reset_medical_data_main"):
                self.reset_database_tables()
        
        return refresh_interval

    def render_patient_health_panel(self):
        """Render patient health monitoring panel with clinical insights"""
        st.header("🩺 Clinical Data Monitoring")

        # Control Panel
        control_cols = st.columns(2)
        
        with control_cols[0]:
            # Get available patients from database
            available_patients = self._get_available_patients()
            
            # Add refresh button for patient list
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_patient = st.selectbox(
                    "Patient Filter",
                    available_patients,
                    index=0,
                    help="Select a specific patient to view their individual vital signs data. Patient list loaded from Snowflake database."
                )
            with col2:
                if st.button("🔄", help="Refresh patient list from database", key="refresh_patients"):
                    # Clear cached patient list to force refresh
                    if 'available_patients' in st.session_state:
                        del st.session_state.available_patients
                    if 'patient_ids_raw' in st.session_state:
                        del st.session_state.patient_ids_raw
                    st.rerun()
        
        with control_cols[1]:
            selected_time_range = st.selectbox(
                "Time Range",
                ["Last 5 Minutes", "Last 1 Hour", "Last 24 Hours", "Custom Range"],
                index=0,  # Default to "Last 5 Minutes" for real-time monitoring
                help="Select time range - 'Last 5 Minutes' shows real-time streaming data with 5-second resolution"
            )
        
        # Store selected time range in session state
        st.session_state.selected_time_range = selected_time_range
        
        # Show database status and data source information
        self._show_data_source_status()

        # Generate unified timestamp architecture for perfect medical synchronization
        reference_timestamp = datetime.now(pytz.UTC)
        
        # Generate the exact same X-axis timestamps for ALL charts to ensure perfect synchronization
        # This approach ensures all vital signs charts show identical X-axis timestamps
        unified_timestamps = []
        if "5 Minutes" in selected_time_range:
            # For 5-minute view: 30 data points, 10 seconds apart (10-second resolution)
            for i in range(30):
                timestamp = reference_timestamp - timedelta(seconds=(29-i)*10)
                unified_timestamps.append(timestamp)
        elif "1 Minute" in selected_time_range:
            # For 1-minute view: 60 data points, 1 second apart
            for i in range(60):
                timestamp = reference_timestamp - timedelta(seconds=59-i)
                unified_timestamps.append(timestamp)
        elif "1 Hour" in selected_time_range:
            # For 1-hour view: 60 data points, 1 minute apart
            for i in range(60):
                timestamp = reference_timestamp - timedelta(minutes=59-i)
                unified_timestamps.append(timestamp)
        elif "24 Hours" in selected_time_range:
            # For 24-hour view: 60 data points, 24 minutes apart
            for i in range(60):
                timestamp = reference_timestamp - timedelta(minutes=(59-i)*24)
                unified_timestamps.append(timestamp)
        else:
            # Default to 1-minute intervals
            for i in range(60):
                timestamp = reference_timestamp - timedelta(seconds=59-i)
                unified_timestamps.append(timestamp)
        
        # Render ECG Waveform Chart first using the unified timestamps
        self._render_ecg_waveform_chart(selected_patient, selected_time_range, reference_timestamp, unified_timestamps)
        st.markdown("---")
        
        # Get vital data for the selected patient using the SAME unified timestamps
        vital_data = self._get_patient_vital_data_synchronized(selected_patient, selected_time_range, reference_timestamp, unified_timestamps)
        
        # Three Vital Signs Cards - Arranged Vertically for Better Readability

    
        # ECG Card - Full Width
        st.markdown("#### 💓 ECG (Heart Rate)")
        self._render_vital_sign_card("ECG", "💓", "Heart Rate", vital_data["ecg"], "bpm", 60, 100)
        
        st.markdown("---")
        
        # EDA Card - Full Width
        st.markdown("#### 😰 EDA (Stress Level)")
        self._render_vital_sign_card("EDA", "😰", "Stress Level", vital_data["eda"], "μS", 1.0, 3.0)
        
        st.markdown("---")
        
        # PPG Card - Full Width
        st.markdown("#### 🫀 PPG (SpO2)")
        self._render_vital_sign_card("PPG", "🫀", "SpO2", vital_data["ppg"], "%", 95, 100, is_spo2=True)
        
        # Patient Health Summary
        st.markdown("---")
        self._render_patient_health_summary(selected_time_range, vital_data)
        
        # Legend
        st.markdown("---")
        self._render_clinical_legend()
        
    def _render_ecg_waveform_chart(self, patient: str, time_range: str, reference_timestamp, unified_timestamps):
        """Render the real-time ECG waveform chart with median-smoothed Lead II data from Snowflake."""
        
        # Header
        st.markdown("#### 📈 Real-Time ECG Waveform (Lead II) - Median-Smoothed Data from Snowflake")
        
        # Set default behavior (always show stats, never show quality markers)
        show_quality = False
        show_stats = True
        
        patient_id = self._convert_patient_selection_to_id(patient)
        

        
        # Fetch median-smoothed waveform data using same timestamp approach as vital signs
        waveform_data = self.db_monitor.get_ecg_waveform_data(time_range, patient_id, reference_timestamp=reference_timestamp)
        
        if not waveform_data:
            # Create an empty chart using UNIFIED axis configuration
            fig = go.Figure()
            fig.add_annotation(
                text="No real-time ECG waveform data available.<br>Start streaming to see the waveform.",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(color="gray", size=14)
            )
            
            # Use the SAME unified axis configuration as vital signs charts
            axis_config = self._get_unified_axis_configuration(time_range)
            
            fig.update_layout(
                height=300,
                plot_bgcolor='black',
                paper_bgcolor='black',
                xaxis=dict(
                    showgrid=True,
                    gridcolor='rgba(0, 255, 0, 0.2)',
                    tickformat=axis_config['tickformat'],
                    dtick=axis_config['dtick'],
                    tickangle=axis_config['tickangle'],
                    showticklabels=True,
                    title=axis_config['title'],
                    range=[axis_config['x_min'], axis_config['x_max']],  # Same range as vital signs
                    type='date',
                    visible=True  # Make axis visible
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor='rgba(0, 255, 0, 0.2)',
                    zeroline=True,
                    zerolinecolor='rgba(0, 255, 0, 0.4)',
                    title="Amplitude (mV)",
                    visible=True  # Make axis visible
                ),
                font=dict(color='#00ff00')
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            return

        # Prepare data for Plotly - median-smoothed Lead II data
        df = pd.DataFrame(waveform_data)
        df['TIMESTAMP_VAL'] = pd.to_datetime(df['TIMESTAMP_VAL'])
        
        # Calculate median-smoothed data statistics
        total_points = len(df)
        avg_signal_quality = df['SIGNAL_QUALITY'].mean() if total_points > 0 else 0
        
        # Display statistics if enabled - median-smoothed data
        if show_stats and total_points > 0:
            stat_col1, stat_col2 = st.columns(2)
            with stat_col1:
                st.metric("Aggregated Data Points", total_points)
            with stat_col2:
                st.metric("Signal Quality", f"{avg_signal_quality:.2f}", delta="High" if avg_signal_quality > 0.8 else "Medium")

        # Create Plotly figure
        fig = go.Figure()

        # Single trace with median-smoothed ECG Lead II data
        fig.add_trace(go.Scatter(
            x=df["TIMESTAMP_VAL"],
            y=df["ECG_SIGNAL"],
            mode='lines+markers' if show_quality else 'lines',
            line=dict(color='#00ff00', width=2),
            marker=dict(color='#00ff00', size=3) if show_quality else None,
            name='Median-Smoothed ECG Waveform (Lead II)',
            hovertemplate=(
                "<b>Full UTC Timestamp:</b> %{x|%Y-%m-%d %H:%M:%S.%L}<br>" +
                "<b>ECG Signal:</b> %{y:.4f} mV<br>" +
                "<b>Data Quality:</b> Median-Smoothed Lead II from Snowflake<extra></extra>"
            )
        ))

        # Use the SAME unified axis configuration as vital signs charts (PREVENTS INCONSISTENCY)
        axis_config = self._get_unified_axis_configuration(time_range)
        
        # Update layout to mimic a medical monitor with enhanced information and FIXED x-axis range
        fig.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis_title=None,
            yaxis_title="Amplitude (mV)",
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(0, 255, 0, 0.2)',
                tickformat=axis_config['tickformat'],
                dtick=axis_config['dtick'],  # IDENTICAL tick interval as vital signs
                tickangle=axis_config['tickangle'],
                showticklabels=True,
                title=axis_config['title'],
                range=[axis_config['x_min'], axis_config['x_max']],  # IDENTICAL range as vital signs
                type='date'  # Ensure proper datetime handling
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(0, 255, 0, 0.2)',
                zeroline=True,
                zerolinecolor='rgba(0, 255, 0, 0.4)'
            ),
            plot_bgcolor='black',
            paper_bgcolor='black',
            font=dict(color='#00ff00'),
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(0,0,0,0.5)",
                bordercolor="rgba(0,255,0,0.5)",
                borderwidth=1
            ) if show_quality else None,
            showlegend=show_quality
        )
        
        # Add annotation for raw data info
        if total_points > 0:
            fig.add_annotation(
                text=f"📊 Median-Smoothed ECG Data from Snowflake<br>{total_points} aggregated data points",
                xref="paper", yref="paper",
                x=0.98, y=0.02,
                showarrow=False,
                font=dict(color="rgba(0, 255, 0, 0.7)", size=10),
                bgcolor="rgba(0,0,0,0.7)",
                bordercolor="rgba(0,255,0,0.3)",
                borderwidth=1
            )
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        # Add description of how ECG waveform data is plotted
        with st.expander("📊 How ECG Waveform Data is Plotted", expanded=False):
            st.markdown("""
            **Real-Time ECG Waveform Visualization:**
            - **Data Source**: Lead II ECG signal data from Snowflake database (base signal × 1.2 + noise)
            - **Processing Applied**: Median aggregation in time buckets to preserve cardiac rhythm while filtering artifacts
            - **Sampling Rate**: Original high-frequency medical device sampling (100-250 Hz after optimization)
            - **Display Method**: Median-smoothed data points connected with continuous green lines (medical monitor style)
            - **Time Synchronization**: Uses unified timestamp configuration to ensure consistency with vital signs charts
            - **Medical Accuracy**: Shows clinically-relevant waveform with noise reduction for clear rhythm visualization
            - **Quality Indicators**: Signal quality metadata displayed when "Show Quality" is enabled
            - **Hospital-Grade Styling**: Black background with green phosphor-style display mimicking professional ECG monitors
            """)
            st.caption("💡 This approach ensures medical professionals see clear cardiac rhythms with noise reduction while preserving authentic waveform characteristics.")




    def _get_patient_vital_data_synchronized(self, patient, time_range, reference_timestamp, unified_timestamps):
        """Get patient vital sign data EXCLUSIVELY from Snowflake database with synchronized timestamps"""
        try:
            # Use the provided reference timestamp for ALL queries to ensure synchronization
            # This ensures ECG waveform, ECG vitals, EDA vitals, and PPG vitals all show the same time window
            
            # For minute and 5-minute views during streaming, get real-time data
            if "5 Minutes" in time_range or "1 Minute" in time_range:
                return self._get_minute_vital_data(patient, time_range, reference_timestamp, unified_timestamps)
            # For longer time ranges, get historical data from Snowflake
            return self._get_historical_vital_data(patient, time_range, reference_timestamp, unified_timestamps)
        except Exception as e:
            st.error(f"❌ Database Error: {str(e)}")
            st.warning("🔌 Please ensure Snowflake connection is active and tables contain data")
            # Return empty data structure instead of simulated data
            return {
                "ecg": {"values": np.array([]), "times": np.array([]), "timestamps": [], "average": 0, "unit": "seconds"},
                "eda": {"values": np.array([]), "times": np.array([]), "timestamps": [], "average": 0, "unit": "seconds"},
                "ppg": {"values": np.array([]), "times": np.array([]), "timestamps": [], "average": 0, "unit": "seconds"}
            }
    
    def _get_minute_vital_data(self, patient, time_range, reference_timestamp, unified_timestamps):
        """Get vital data for specified time range directly from Snowflake with synchronized timestamp - DATABASE ONLY"""
        try:
            # Convert patient selection to proper patient_id format
            patient_id = self._convert_patient_selection_to_id(patient)
            
            # Get median-aggregated data points from Snowflake for clean medical visualization
            # Uses artifact-resistant median averaging while preserving physiological trends
            
            # Determine optimal data point limit based on time range
            if "5 Minutes" in time_range:
                data_limit = 30  # 30 median points for 5-minute view (10-second buckets)
            else:
                data_limit = 60  # 60 median points for other time ranges
            
            ecg_data = self.db_monitor.get_raw_vital_data_points(
                schema=self.config.snowflake_config.CLINICAL_SCHEMA,
                table_name='ECG_DATA_FLATTENED',
                time_range=time_range,  # Use actual selected time range for consistency
                limit=data_limit,  # Optimized for median aggregation buckets
                patient_id=patient_id,
                reference_timestamp=reference_timestamp,
                unified_timestamps=unified_timestamps
            )
            eda_data = self.db_monitor.get_raw_vital_data_points(
                schema=self.config.snowflake_config.CLINICAL_SCHEMA,
                table_name='EDA_DATA_FLATTENED', 
                time_range=time_range,  # Use actual selected time range for consistency
                limit=data_limit,
                patient_id=patient_id,
                reference_timestamp=reference_timestamp,
                unified_timestamps=unified_timestamps
            )
            ppg_data = self.db_monitor.get_raw_vital_data_points(
                schema=self.config.snowflake_config.CLINICAL_SCHEMA,
                table_name='PPG_DATA_FLATTENED',
                time_range=time_range,  # Use actual selected time range for consistency 
                limit=data_limit,
                patient_id=patient_id,
                reference_timestamp=reference_timestamp,
                unified_timestamps=unified_timestamps
            )
            
            # Process data and map to unified timestamps for perfect synchronization across all charts
            ecg_result = self._process_raw_data_with_actual_timestamps(ecg_data, 'ECG', unified_timestamps)
            eda_result = self._process_raw_data_with_actual_timestamps(eda_data, 'EDA', unified_timestamps)
            ppg_result = self._process_raw_data_with_actual_timestamps(ppg_data, 'PPG', unified_timestamps)
            
            # When streaming is active, we get fresher data from the database automatically
            # NO random variations - all data comes from Snowflake!
            
            # Calculate averages only if we have data
            ecg_avg = np.mean(ecg_result['values']) if len(ecg_result['values']) > 0 else 0
            eda_avg = np.mean(eda_result['values']) if len(eda_result['values']) > 0 else 0
            ppg_avg = np.mean(ppg_result['values']) if len(ppg_result['values']) > 0 else 0
            
            return {
                "ecg": {"values": ecg_result['values'], "times": ecg_result['times'], 
                       "timestamps": ecg_result['timestamps'], "average": ecg_avg, "unit": "seconds"},
                "eda": {"values": eda_result['values'], "times": eda_result['times'],
                       "timestamps": eda_result['timestamps'], "average": eda_avg, "unit": "seconds"},
                "ppg": {"values": ppg_result['values'], "times": ppg_result['times'],
                       "timestamps": ppg_result['timestamps'], "average": ppg_avg, "unit": "seconds"}
            }
            
        except Exception as e:
            st.error(f"❌ Database connection failed for minute data: {str(e)}")
            # Return empty structure - no fallback simulation
            return {
                "ecg": {"values": np.array([]), "times": np.array([]), "timestamps": [], "average": 0, "unit": "seconds"},
                "eda": {"values": np.array([]), "times": np.array([]), "timestamps": [], "average": 0, "unit": "seconds"},
                "ppg": {"values": np.array([]), "times": np.array([]), "timestamps": [], "average": 0, "unit": "seconds"}
            }
    
    def _get_historical_vital_data(self, patient, time_range, reference_timestamp, unified_timestamps):
        """Get historical vital data from Snowflake with synchronized timestamp - DATABASE ONLY"""
        try:
            # Convert patient selection to proper patient_id format
            patient_id = self._convert_patient_selection_to_id(patient)
            
            # Get median-aggregated data points from Snowflake for clean historical visualization
            # Uses artifact-resistant median averaging while preserving physiological trends
            
            # Determine optimal data point limit based on time range
            if "5 Minutes" in time_range:
                data_limit = 30  # 30 median points for 5-minute view (10-second buckets)
            else:
                data_limit = 60  # 60 median points for other time ranges
            
            ecg_data = self.db_monitor.get_raw_vital_data_points(
                schema=self.config.snowflake_config.CLINICAL_SCHEMA,
                table_name='ECG_DATA_FLATTENED',
                time_range=time_range,
                limit=data_limit,  # Optimized for median aggregation buckets
                patient_id=patient_id,
                reference_timestamp=reference_timestamp,
                unified_timestamps=unified_timestamps
            )
            eda_data = self.db_monitor.get_raw_vital_data_points(
                schema=self.config.snowflake_config.CLINICAL_SCHEMA,
                table_name='EDA_DATA_FLATTENED',
                time_range=time_range,
                limit=data_limit,
                patient_id=patient_id,
                reference_timestamp=reference_timestamp,
                unified_timestamps=unified_timestamps
            )
            ppg_data = self.db_monitor.get_raw_vital_data_points(
                schema=self.config.snowflake_config.CLINICAL_SCHEMA,
                table_name='PPG_DATA_FLATTENED',
                time_range=time_range,
                limit=data_limit,
                patient_id=patient_id,
                reference_timestamp=reference_timestamp,
                unified_timestamps=unified_timestamps
            )
            
            # Process data and map to unified timestamps for perfect synchronization across all charts
            ecg_result = self._process_raw_data_with_actual_timestamps(ecg_data, 'ECG', unified_timestamps)
            eda_result = self._process_raw_data_with_actual_timestamps(eda_data, 'EDA', unified_timestamps)
            ppg_result = self._process_raw_data_with_actual_timestamps(ppg_data, 'PPG', unified_timestamps)
            
            # Determine time unit
            time_unit = "hours" if "Hour" in time_range else "minutes"
            
            # Calculate averages only if we have data
            ecg_avg = np.mean(ecg_result['values']) if len(ecg_result['values']) > 0 else 0
            eda_avg = np.mean(eda_result['values']) if len(eda_result['values']) > 0 else 0
            ppg_avg = np.mean(ppg_result['values']) if len(ppg_result['values']) > 0 else 0
            
            return {
                "ecg": {"values": ecg_result['values'], "times": ecg_result['times'],
                       "timestamps": ecg_result['timestamps'], "average": ecg_avg, "unit": time_unit},
                "eda": {"values": eda_result['values'], "times": eda_result['times'],
                       "timestamps": eda_result['timestamps'], "average": eda_avg, "unit": time_unit},
                "ppg": {"values": ppg_result['values'], "times": ppg_result['times'],
                       "timestamps": ppg_result['timestamps'], "average": ppg_avg, "unit": time_unit}
            }
            
        except Exception as e:
            st.error(f"❌ Database connection failed for historical data: {str(e)}")
            # Return empty structure - no fallback simulation
            time_unit = "hours" if "Hour" in time_range else "minutes"
            return {
                "ecg": {"values": np.array([]), "times": np.array([]), "timestamps": [], "average": 0, "unit": time_unit},
                "eda": {"values": np.array([]), "times": np.array([]), "timestamps": [], "average": 0, "unit": time_unit},
                "ppg": {"values": np.array([]), "times": np.array([]), "timestamps": [], "average": 0, "unit": time_unit}
            }
    
    def _process_raw_data_with_actual_timestamps(self, data: list, signal_type: str, unified_timestamps: list) -> dict:
        """
        Process RAW individual data points using ONLY actual values and timestamps from database.
        NO interpolation, NO sampling, NO artificial timestamps - only real medical measurements plotted 
        at their actual timestamps from Snowflake.
        
        Args:
            data: Raw individual data points from database (NOT aggregated)
            signal_type: Type of signal ('ECG', 'EDA', 'PPG')
            unified_timestamps: IGNORED - we use actual timestamps only
            
        Returns:
            dict: Processed data with ONLY actual values and timestamps from Snowflake
        """
        if not data:
            # Return empty data structure - NO fake data
            return {
                "values": np.array([]),  # Empty - no fake data
                "times": np.array([]),   # Empty - not used 
                "timestamps": [],        # Empty - no fake timestamps
                "average": 0,
                "unit": self._get_signal_unit(signal_type)
            }
        
        # Get the actual RAW data values and timestamps from database  
        db_values = []
        db_timestamps = []
        
        for record in data:
            if isinstance(record, dict):
                # Extract RAW value (NOT aggregated) - use the actual value from database query
                value = record.get('RAW_VALUE', 0)
                if value is not None and value != 0:  # Only include actual measurements
                    db_values.append(float(value))
                    
                    # Extract actual timestamp from individual data point
                    timestamp_str = record.get('TIMESTAMP_VAL', record.get('timestamp_val', record.get('timestamp')))
                    if timestamp_str:
                        # Convert string timestamp to datetime for proper x-axis plotting
                        if isinstance(timestamp_str, str):
                            try:
                                from datetime import datetime
                                # Parse the timestamp string to datetime object
                                timestamp_dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                db_timestamps.append(timestamp_dt)
                            except:
                                # Fallback: use string directly
                                db_timestamps.append(timestamp_str)
                        else:
                            # Already a datetime object
                            db_timestamps.append(timestamp_str)
        
        if not db_values or not db_timestamps:
            # Return empty data - NO fake data
            return {
                "values": np.array([]),
                "times": np.array([]),  # Not used
                "timestamps": [],
                "average": 0,
                "unit": self._get_signal_unit(signal_type)
            }
        
        # Sort data by timestamp to ensure proper chronological order
        combined = list(zip(db_timestamps, db_values))
        combined.sort(key=lambda x: x[0])  # Sort by timestamp
        
        if combined:
            sorted_timestamps, sorted_values = zip(*combined)
            actual_timestamps = list(sorted_timestamps)
            actual_values = np.array(sorted_values)
        else:
            actual_timestamps = []
            actual_values = np.array([])
        
        # Calculate average of actual values only
        average_value = np.mean(actual_values) if len(actual_values) > 0 else 0
            
        return {
            "values": actual_values,        # Only actual values from Snowflake
            "times": np.array([]),          # Not used - x-axis uses timestamps directly
            "timestamps": actual_timestamps, # Actual timestamps from database for x-axis
            "average": average_value,
            "unit": self._get_signal_unit(signal_type)
        }

    def _get_signal_unit(self, signal_type: str) -> str:
        """Get the unit for a signal type"""
        units = {
            'ECG': 'bpm',
            'EDA': 'μS', 
            'PPG': '%'
        }
        return units.get(signal_type, 'units')

    def _process_aggregated_data(self, db_records, vital_type):
        """Process aggregated database records into chart-ready format - DATABASE ONLY"""
        if not db_records:
            # NO RANDOM GENERATION - Show clear "No Data" status
            st.warning(f"⚠️ No {vital_type} data available in Snowflake for selected time range")
            # Return empty arrays to indicate no data
            return {
                'values': np.array([]),
                'times': np.array([]),
                'timestamps': []
            }
        
        # Extract data from database records ONLY
        values = []
        timestamps = []
        times = []
        
        # Sort records by time_bucket (newest first)
        sorted_records = sorted(db_records, key=lambda x: x.get('TIME_BUCKET', ''), reverse=True)
        
        for i, record in enumerate(sorted_records):
            # Get averaged value from database (no fallbacks to defaults)
            avg_val = record.get('AVG_VALUE')
            if avg_val is not None:
                values.append(float(avg_val))
                
                # Get timestamp from database
                timestamp = record.get('TIME_BUCKET') or record.get('PERIOD_START', '')
                timestamps.append(timestamp)
                
                # Calculate relative time (seconds/minutes/hours ago)
                times.append((i + 1) * 10)  # 10, 20, 30, etc.
        
        # Only return data if we have actual database records
        if not values:
            st.error(f"❌ No valid {vital_type} values found in database records")
            return {
                'values': np.array([]),
                'times': np.array([]),
                'timestamps': []
            }
        
        return {
            'values': np.array(values),
            'times': np.array(times),
            'timestamps': timestamps
        }
    
    # ALL RANDOM GENERATION METHODS REMOVED - PURE DATABASE APPROACH
    # Previously contained: _generate_realistic_historical_pattern, _get_realistic_variation, _get_simulated_vital_data
    # All data now comes exclusively from Snowflake via get_aggregated_vital_data()
    
    def _render_vital_sign_card(self, vital_type, emoji, name, data, unit, lower_limit, upper_limit, is_spo2=False):
        """Render individual vital sign card with clinical chart"""
        
        # Calculate time range label
        time_range = st.session_state.get('selected_time_range', 'Last 24 Hours')
        if "10 seconds" in time_range:
            range_label = "10-Second Average"
        elif "5 Minutes" in time_range:
            range_label = "5-Minute Average"
        elif "1 Minute" in time_range:
            range_label = "1-Minute Average"
        elif "24 Hour" in time_range:
            range_label = "24-Hour Average"
        elif "6 Hour" in time_range:
            range_label = "6-Hour Average"
        elif "1 Hour" in time_range:
            range_label = "1-Hour Average"
        else:
            range_label = "Average"
        
        # Current average and status
        avg_value = data["average"]
        
        # Check if we have actual data (not just zeros from empty database)
        has_data = len(data.get("values", [])) > 0 and any(v != 0 for v in data.get("values", []))
        
        if not has_data:
            # No data available - show appropriate message
            status = "⚠️ NO DATA"
            status_color = "off"
            value_display = "N/A"
        else:
            # We have actual data - determine status based on vital type
            if is_spo2:
                # PPG/SpO2: Only concerned about low values
                if avg_value >= 95:
                    status = "✅ NORMAL"
                    status_color = "normal"
                elif avg_value >= 90:
                    status = "⚠️ ELEVATED"
                    status_color = "off"
                else:
                    status = "🔴 CRITICAL"
                    status_color = "inverse"
            else:
                # ECG/EDA: Concerned about both high and low values
                if lower_limit <= avg_value <= upper_limit:
                    status = "✅ NORMAL"
                    status_color = "normal"
                elif avg_value > upper_limit:
                    status = "⚠️ ELEVATED"
                    status_color = "off"
                else:  # avg_value < lower_limit
                    status = "🔴 CRITICAL"
                    status_color = "inverse"
            value_display = f"{avg_value:.1f} {unit}"
        
        # Display average and status in columns for better layout
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.metric(f"{range_label}", value_display)
        with col2:
            # Normal range info
            if is_spo2:
                st.caption(f"Normal Range: {lower_limit}-{upper_limit}{unit}")
            else:
                st.caption(f"Normal Range: {lower_limit}-{upper_limit} {unit}")
        with col3:
            st.markdown(f"**{status}**")
        
        # Create clinical chart
        fig = self._create_clinical_chart(vital_type, data, unit, lower_limit, upper_limit, is_spo2, time_range)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        # Add description of how vital signs data is plotted
        with st.expander(f"📊 How {vital_type} Data is Plotted", expanded=False):
            st.markdown(f"""
            **Medical-Grade {vital_type} Visualization:**
            - **Data Processing**: Median averaging within time buckets to filter sensor artifacts and noise
            - **Clinical Accuracy**: Represents "typical" physiological values per time window (artifact-resistant)
            - **Normal Range Indicators**: Dashed red lines show clinical normal limits for immediate assessment
            - **Time Synchronization**: Unified axis configuration ensures consistency across all vital sign charts
            - **Professional Display**: Clean trend lines matching hospital monitor standards
            - **Quality Filtering**: Eliminates sensor glitches, electrical interference, and movement artifacts
            - **Hover Details**: Full UTC timestamps and precise values available on hover
            """)
            if is_spo2:
                st.caption("💡 SpO2 charts show optimal target (100%) and critical lower threshold for oxygen saturation monitoring.")
            else:
                st.caption("💡 This median-based approach provides clinically meaningful trends while filtering out non-physiological noise.")

    def _get_time_axis_label(self, time_range: str) -> str:
        """Get appropriate x-axis time label based on selected time range"""
        if "5 Minutes" in time_range:
            return "Time (seconds ago)"
        elif "1 Minute" in time_range:
            return "Time (seconds ago)"
        elif "1 Hour" in time_range:
            return "Time (minutes ago)"
        elif "24 Hour" in time_range:
            return "Time (hours ago)"
        else:
            return "Time"
    
    # REMOVED: _get_dynamic_tick_settings() method - replaced by _get_unified_axis_configuration()
    # This ensures there's only ONE centralized logic for all axis configurations

    def _get_unified_axis_configuration(self, time_range: str) -> dict:
        """
        Get complete unified axis configuration including time calculations and tick settings.
        
        This ensures ECG waveform and vital signs charts use IDENTICAL axis configurations
        by calculating time ranges and tick settings once and reusing the same values.
        
        Designed to prevent data clustering by matching medical device sampling frequencies:
        - ECG: 250-500Hz (2-4ms intervals)
        - EDA/PPG: 100-250Hz (4-10ms intervals)
        """
        from datetime import datetime, timedelta
        import pytz
        
        # Calculate time range ONCE - both charts will use these exact same values
        current_time = datetime.now(pytz.UTC)
        
        if "5 Minutes" in time_range:
            x_min = current_time - timedelta(minutes=5)
            x_max = current_time
            tick_config = {
                'dtick': 10000,  # 10 seconds = 10000ms (10-second ticks for full 5-minute span)
                'tickformat': '%H:%M:%S',  # Show time with seconds (HH:MM:SS)
                'tickangle': 45,
                'title': "Time (UTC) - Last 5 Minutes from System Time (10-second resolution)"
            }
        elif "1 Minute" in time_range:
            x_min = current_time - timedelta(minutes=1)
            x_max = current_time
            tick_config = {
                'dtick': 5000,  # 5 seconds = 5000ms (optimal for high-frequency medical data)
                'tickformat': '%H:%M:%S',  # Show time with seconds (HH:MM:SS)
                'tickangle': 45,
                'title': "Time (UTC) - Last 1 Minute from System Time"
            }
        elif "1 Hour" in time_range:
            x_min = current_time - timedelta(hours=1)
            x_max = current_time
            tick_config = {
                'dtick': 300000,  # 5 minutes = 300000ms
                'tickformat': '%H:%M',  # Show hours and minutes (HH:MM)
                'tickangle': 45,
                'title': "Time (UTC) - Last 1 Hour from System Time"
            }
        elif "24 Hour" in time_range:
            x_min = current_time - timedelta(hours=24)
            x_max = current_time
            tick_config = {
                'dtick': 7200000,  # 2 hours = 7200000ms
                'tickformat': '%m/%d %H:00',  # Show date and hour (MM/DD HH:00)
                'tickangle': 45,
                'title': "Date & Time (UTC) - Last 24 Hours from System Time"
            }
        else:
            # Custom range or fallback
            x_min = current_time - timedelta(hours=1)
            x_max = current_time
            tick_config = {
                'dtick': None,
                'tickformat': '%Y-%m-%d %H:%M:%S',
                'tickangle': 45,
                'title': "Timestamp (UTC)"
            }
        
        # Return complete configuration that both charts will use identically
        return {
            'x_min': x_min,
            'x_max': x_max,
            'current_time': current_time,
            **tick_config  # Unpack tick settings
        }

    def _create_clinical_chart(self, vital_type, data, unit, lower_limit, upper_limit, is_spo2=False, time_range="Last 24 Hours"):
        """Create clinical chart with database data - handles empty data gracefully"""
        
        # Handle empty data from database or all-zero data (no actual measurements)
        has_actual_data = len(data["values"]) > 0 and any(v != 0 for v in data["values"])
        if not has_actual_data:
            # Create empty chart with clear message BUT with proper 10-minute axis configuration
            fig = go.Figure()
            fig.add_annotation(
                text=f"No {vital_type} data available in Snowflake<br>Start streaming or check database connection",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="gray")
            )
            
            # Use the SAME unified axis configuration as ECG chart (PREVENTS INCONSISTENCY)
            axis_config = self._get_unified_axis_configuration(time_range)
            
            fig.update_layout(
                height=400,
                margin=dict(l=10, r=10, t=10, b=30),
                showlegend=False,
                xaxis=dict(
                    title=axis_config['title'], 
                    showgrid=True, 
                    gridcolor='lightgray',
                    tickformat=axis_config['tickformat'],
                    dtick=axis_config['dtick'],  # IDENTICAL tick intervals as ECG
                    tickangle=axis_config['tickangle'],
                    range=[axis_config['x_min'], axis_config['x_max']],  # IDENTICAL range as ECG
                    type='date'  # Ensure proper datetime handling
                ),
                yaxis=dict(title=f"{vital_type} ({unit})", showgrid=True, gridcolor='lightgray'),
                plot_bgcolor='white'
            )
            return fig
        
        # Create chart with actual database data
        fig = go.Figure()
        
        # Normal range backgrounds
        if not is_spo2:
            # Standard vital signs (ECG, EDA) - show both upper and lower limits
            fig.add_hline(y=upper_limit, line_dash="dash", line_color="red", 
                         annotation_text=f"Upper Normal ({upper_limit})", annotation_position="bottom right")
            fig.add_hline(y=lower_limit, line_dash="dash", line_color="red", 
                         annotation_text=f"Lower Normal ({lower_limit})", annotation_position="top right")
        else:
            # SpO2 - only show lower limit and optimal target
            fig.add_hline(y=100, line_dash="dash", line_color="green", 
                         annotation_text="Optimal Target (100%)", annotation_position="bottom right")
            fig.add_hline(y=lower_limit, line_dash="dash", line_color="red", 
                         annotation_text=f"Lower Normal ({lower_limit}%)", annotation_position="top right")
        
        # Add trend line with data points - using full timestamps on x-axis
        fig.add_trace(go.Scatter(
            x=data.get("timestamps", data["times"]),  # Use full timestamps instead of relative times
            y=data["values"],
            mode='lines+markers',
            line=dict(color='rgb(29, 78, 216)', width=3),
            marker=dict(size=8, color='rgb(29, 78, 216)', symbol='circle'),
            name='Vital Readings',
            hovertemplate=(
                "<b>%{text}</b><br>" +
                "📅 Full Timestamp: %{x|%Y-%m-%d %H:%M:%S.%L}<br>" +
                "📊 Value: %{y:.1f} " + unit + "<br>" +
                "<extra></extra>"  # Removes the trace box
            ),
            text=[f"{vital_type} Reading" for _ in data["values"]]
        ))
        
        # Use the SAME unified axis configuration as ECG chart (ENSURES CONSISTENCY)
        axis_config = self._get_unified_axis_configuration(time_range)
        
        # Update layout with FIXED x-axis range to prevent clustering
        fig.update_layout(
            height=400,  # Increased from 250 for better readability with wider charts
            margin=dict(l=10, r=10, t=10, b=30),
            showlegend=False,
            xaxis=dict(
                title=axis_config['title'], 
                showgrid=True, 
                gridcolor='lightgray',
                tickformat=axis_config['tickformat'],
                dtick=axis_config['dtick'],  # IDENTICAL tick interval as ECG
                tickangle=axis_config['tickangle'],
                range=[axis_config['x_min'], axis_config['x_max']],  # IDENTICAL range as ECG
                type='date'  # Ensure proper datetime handling
            ),
            yaxis=dict(title=f"{vital_type} ({unit})", showgrid=True, gridcolor='lightgray'),
            plot_bgcolor='white',
            hovermode='closest'  # Ensure hover works properly
        )
        
        return fig
    
    def _render_patient_health_summary(self, time_range, vital_data):
        """Render 24-hour patient health summary"""
        st.subheader("📊 24-Hour Clinical Data Summary")
        
        # Note about time range and zones
        st.caption(
            f"**Note:** Average values and labels automatically update based on selected time range "
            f"(e.g., \"1-Hour Average: 74 bpm\" when \"Last 1 Hour\" is selected). "
            f"Background zones indicate clinical significance: "
            f"🟢 Normal (between limits), 🟡 Caution (approaching limits), 🔴 Critical (beyond limits)."
        )
        
        # Summary cards
        summary_cols = st.columns(4)
        
        with summary_cols[0]:
            st.markdown("#### 📈 Overall Trend")
            # Generate trend analysis from actual database data
            ecg_avg = vital_data["ecg"]["average"]
            eda_avg = vital_data["eda"]["average"]
            ppg_avg = vital_data["ppg"]["average"]
            
            if ecg_avg > 0 and eda_avg > 0 and ppg_avg > 0:
                if eda_avg > 2.5:
                    trend_text = f"Elevated stress levels detected (EDA: {eda_avg:.1f} μS). Heart rate stable at {ecg_avg:.1f} bpm."
                elif ecg_avg > 90:
                    trend_text = f"Elevated heart rate detected ({ecg_avg:.1f} bpm). Monitor for sustained elevation."
                elif ppg_avg < 95:
                    trend_text = f"SpO2 below optimal range ({ppg_avg:.1f}%). Consider oxygen assessment."
                else:
                    trend_text = f"All vitals within normal ranges. ECG: {ecg_avg:.1f} bpm, SpO2: {ppg_avg:.1f}%."
            else:
                trend_text = "⚠️ Insufficient data for trend analysis. Start streaming for real-time insights."
            st.write(trend_text)
        
        with summary_cols[1]:
            st.markdown("#### 🚨 Alerts Generated")
            # Generate alerts based on actual vital data
            alerts = []
            if ecg_avg > 100:
                alerts.append("ECG elevated (>100 bpm)")
            elif ecg_avg < 60 and ecg_avg > 0:
                alerts.append("ECG low (<60 bpm)")
            
            if eda_avg > 3.0:
                alerts.append("EDA critically high (>3.0 μS)")
            elif eda_avg < 1.0 and eda_avg > 0:
                alerts.append("EDA below normal (<1.0 μS)")
                
            if ppg_avg < 95 and ppg_avg > 0:
                alerts.append("SpO2 low (<95%)")
            
            if alerts:
                alert_text = f"{len(alerts)} active alert{'s' if len(alerts) > 1 else ''}: " + ", ".join(alerts)
            elif ecg_avg > 0 or eda_avg > 0 or ppg_avg > 0:
                alert_text = "No active alerts - all parameters normal"
            else:
                alert_text = "⚠️ No data available for alert monitoring"
            st.write(alert_text)
        
        with summary_cols[2]:
            st.markdown("#### 📋 Health Status")
            # Determine health status from actual data
            if ecg_avg > 0 and eda_avg > 0 and ppg_avg > 0:
                critical_count = 0
                if ecg_avg > 100 or ecg_avg < 60:
                    critical_count += 1
                if eda_avg > 3.0 or eda_avg < 1.0:
                    critical_count += 1
                if ppg_avg < 95:
                    critical_count += 1
                
                if critical_count == 0:
                    status_text = "✅ STABLE - All parameters within normal ranges"
                elif critical_count == 1:
                    status_text = "⚠️ CAUTION - One parameter requires attention"
                else:
                    status_text = "🔴 CRITICAL - Multiple parameters outside normal ranges"
            else:
                status_text = "⚠️ UNKNOWN - Insufficient data for health assessment"
            st.write(status_text)
        
        with summary_cols[3]:
            st.markdown("#### 🎯 Recommendations")
            # Generate recommendations based on actual data
            recommendations = []
            if eda_avg > 2.5:
                recommendations.append("Consider stress reduction techniques")
            if ecg_avg > 90:
                recommendations.append("Monitor cardiac activity closely")
            if ppg_avg < 96:
                recommendations.append("Assess respiratory function")
            
            if recommendations:
                rec_text = "; ".join(recommendations) + "."
            elif ecg_avg > 0 or eda_avg > 0 or ppg_avg > 0:
                rec_text = "Continue routine monitoring - all parameters stable."
            else:
                rec_text = "⚠️ Start data streaming for personalized recommendations."
            st.write(rec_text)

    def _render_clinical_legend(self):
        """Render comprehensive clinical legend"""
        st.subheader("📖 Chart Legend")
        
        legend_cols = st.columns(7)
        
        legend_items = [
            ("🟢 Normal Zone (Between Normal Limits)", "normal"),
            ("🟡 Caution Zone (Approaching Limits)", "caution"),
            ("🔴 Critical Zone (Beyond Normal Limits)", "critical"),
            ("● Data Points", "data"),
            ("— Vital Readings Trend Line", "trend"),
            ("- - - Upper Normal Limit", "upper"),
            ("- - - Lower Normal Limit", "lower")
        ]
        
        for i, (label, _) in enumerate(legend_items):
            with legend_cols[i % 7]:
                st.caption(label)




    def render_device_health_panel(self):
        """Render simplified device health monitoring dashboard as a clean table."""
        st.header("📟 Device Health Monitoring")
        st.caption("Essential device health metrics for each medical monitoring device")
        
        try:
            # Fetch latest telemetry data per device using proper GROUP BY SQL logic
            recent_records = self.db_monitor.get_latest_telemetry_per_device(
                self.db_monitor.config.TELEMETRY_SCHEMA,
                self.db_monitor.config.TELEMETRY_TABLE
            )
            
            if not recent_records:
                st.info("💡 No telemetry data available. Start streaming to see device health insights.")
                return
                
            # Parse and organize device data
            device_metrics = self._process_device_telemetry(recent_records)
            
            if not device_metrics:
                st.info("💡 Unable to parse device telemetry data. Check data format.")
                return
            
            # Render device health table
            self._render_device_health_table(device_metrics)
            
        except Exception as e:
            st.error(f"Failed to load device health data: {e}")
            st.info("💡 Ensure streaming is active and Snowflake connection is available.")

    def start_streaming(self, patient_count: int, duration: int = None, scenario: str = "NORMAL"):
        """Start the streaming process - supports continuous streaming when duration is None"""
        try:
            # Clear any existing messages when starting
            self.clear_all_temp_messages()
            
            # Show starting message
            streaming_mode = "continuous" if duration is None else f"{duration} seconds"
            with st.spinner(f"🚀 Starting {streaming_mode} streaming..."):
                success = self.stream_controller.start_streaming(
                    patient_count=patient_count,
                    duration=duration,  # None for continuous streaming
                    scenario=scenario
                )
            
            if success:
                # Immediately set session state to active
                st.session_state.streaming_active = True
                st.session_state.streaming_start_time = datetime.now(pytz.UTC)
                st.session_state.streaming_duration = duration  # None for continuous, or specific duration
                st.session_state.streaming_ever_started = True  # Mark that streaming has started at least once
                
                # Store thread references for precise stopping
                st.session_state.streaming_thread_id = None
                if hasattr(self.stream_controller, 'streaming_thread') and self.stream_controller.streaming_thread:
                    st.session_state.streaming_thread_id = self.stream_controller.streaming_thread.ident
                    st.session_state.streaming_thread_ref = self.stream_controller.streaming_thread
                
                # Store stream manager reference for cleanup
                if hasattr(self.stream_controller, 'stream_manager'):
                    st.session_state.stream_manager_ref = self.stream_controller.stream_manager
                
                # Verify the controller state is also set
                if hasattr(self.stream_controller, 'streaming_active'):
                    self.stream_controller.streaming_active = True
                
                # Add temporary success message that auto-clears
                if duration is None:
                    self.add_temp_message('success', f"✅ Continuous streaming started with {patient_count} patients!", duration=8)
                else:
                    self.add_temp_message('success', f"✅ Streaming started with {patient_count} patients for {duration} seconds!", duration=8)
                
                # Remove st.rerun() to avoid interfering with auto-refresh timing
                # UI will update naturally on next refresh cycle
            else:
                self.add_temp_message('error', "❌ Failed to start streaming. Check logs for details.", duration=10)
                st.session_state.streaming_active = False
                
        except Exception as e:
            self.add_temp_message('error', f"❌ Error starting stream: {str(e)}", duration=12)
            st.session_state.streaming_active = False

    def stop_streaming(self):
        """Stop streaming using stored thread references - PRECISE TARGETING"""
        try:
            # Clear any existing messages when stopping
            self.clear_all_temp_messages()
            
            self.add_temp_message('info', "⏹️ Stopping streaming processes...", duration=5)
            stopped_components = []
            
            # Method 1: Stop using stored thread references (PRECISE)
            try:
                # Stop the main streaming thread if we have a reference
                if (hasattr(st.session_state, 'streaming_thread_ref') and 
                    st.session_state.streaming_thread_ref and 
                    st.session_state.streaming_thread_ref.is_alive()):
                    
                    # First try graceful shutdown via stream manager
                    if hasattr(st.session_state, 'stream_manager_ref') and st.session_state.stream_manager_ref:
                        st.session_state.stream_manager_ref.streaming_active = False
                        st.session_state.stream_manager_ref.stop_streaming()
                        stopped_components.append("Stream Manager")
                    
                    # NO SLEEP - Immediate stop for maximum responsiveness
                    import time
                    # time.sleep(2)  # Removed for instant stop
                    
                    # If still alive, force stop (Note: Python threads can't be forcefully killed)
                    if st.session_state.streaming_thread_ref.is_alive():
                        stopped_components.append("Thread marked for stop")
                    else:
                        stopped_components.append("Streaming Thread")
                        
            except Exception as e:
                self.add_temp_message('warning', f"⚠️ Error stopping thread: {str(e)}", duration=8)
            
            # Method 2: Standard controller stop
            try:
                self.stream_controller.stop_streaming()
                stopped_components.append("Stream Controller")
            except Exception as e:
                self.add_temp_message('warning', f"⚠️ Controller stop failed: {str(e)}", duration=8)
            
            # Method 3: Force reset all streaming states
            try:
                # Reset controller states
                self.stream_controller.streaming_active = False
                self.stream_controller.start_time = None
                self.stream_controller.streaming_thread = None
                
                # Reset stream manager if we have reference
                if hasattr(st.session_state, 'stream_manager_ref') and st.session_state.stream_manager_ref:
                    st.session_state.stream_manager_ref.streaming_active = False
                    try:
                        st.session_state.stream_manager_ref.stop_streaming()
                    except:
                        pass  # May already be stopped
                
                # Reset dual stream manager states in controller
                if hasattr(self.stream_controller, 'stream_manager') and self.stream_controller.stream_manager:
                    self.stream_controller.stream_manager.streaming_active = False
                    try:
                        self.stream_controller.stream_manager.stop_streaming()
                    except:
                        pass
                
                stopped_components.append("All State Variables")
                
            except Exception as e:
                self.add_temp_message('warning', f"⚠️ Error resetting states: {str(e)}", duration=8)
            
            # Method 4: Clean up session state thread references
            try:
                if hasattr(st.session_state, 'streaming_thread_ref'):
                    delattr(st.session_state, 'streaming_thread_ref')
                if hasattr(st.session_state, 'streaming_thread_id'):
                    delattr(st.session_state, 'streaming_thread_id')
                if hasattr(st.session_state, 'stream_manager_ref'):
                    delattr(st.session_state, 'stream_manager_ref')
                stopped_components.append("Session State References")
                
            except Exception as e:
                self.add_temp_message('warning', f"⚠️ Error cleaning session state: {str(e)}", duration=8)
            
            # Update session state
            st.session_state.streaming_active = False
            st.session_state.last_streaming_stopped_time = datetime.now(pytz.UTC)
            
            # Show what was stopped - single clean message
            if stopped_components:
                component_list = ", ".join(stopped_components)
                self.add_temp_message('success', f"✅ Stopped {len(stopped_components)} components: {component_list}", duration=10)
            else:
                self.add_temp_message('warning', "⚠️ No active components found to stop", duration=8)
            
            # Remove st.rerun() to avoid interfering with auto-refresh timing
            # Streamlit will naturally refresh when button is clicked
            
        except Exception as e:
            self.add_temp_message('error', f"❌ Error stopping stream: {str(e)}", duration=12)
            # Ensure session state is reset even if stop fails
            st.session_state.streaming_active = False
            st.session_state.last_streaming_stopped_time = datetime.now(pytz.UTC)


    def force_stop_all_streaming_processes(self):
        """Force stop all medical device streaming processes system-wide from ANY version"""
        import subprocess
        import signal
        import logging
        
        logger = logging.getLogger(__name__)
        logger.warning("Emergency force stop initiated by user - targeting ALL versions")
        
        success_count = 0
        total_processes = 0
        error_messages = []
        
        # Comprehensive list of patterns to catch ALL streaming processes from any version
        process_patterns = [
            # Core streaming script patterns (version-agnostic due to -f flag)
            'medical_device_generator.py', 
            'device_telemetry_generator.py',
            'dual_stream_manager.py',
            'snowpipe_streaming_client.py',
            
            # Version-specific directory patterns to ensure coverage
            'V[0-9]*/.*medical_device',  # Catch V0/, V1/, V10/, V11_9/, V12_0/, etc.
            'V[0-9]*/.*streaming',       # Any streaming processes in version dirs
            'V[0-9]*/.*dual_stream',     # Dual stream managers from any version
            'V[0-9]*/.*snowpipe',        # Snowpipe clients from any version
            
            # Additional safety patterns for edge cases
            'Medical_Device_Streaming_Data.*medical_device',
            'Medical_Device_Streaming_Data.*streaming',
            'Medical_Device_Streaming_Data.*dual_stream',
            'Medical_Device_Streaming_Data.*snowpipe',
            
            # Legacy naming variations that might exist
            'ecg_streaming_demo.py',
            'high_performance_demo.py',
        ]
        
        with st.spinner("🚨 Force stopping ALL streaming processes from ANY version..."):
            # STEP 1: Stop internal Streamlit streaming first
            try:
                logger.info("Stopping internal Streamlit streaming...")
                
                # Call the regular stop streaming logic to properly clean up internal state
                self.stop_streaming()
                success_count += 1
                logger.info("Successfully stopped internal Streamlit streaming")
                
            except Exception as e:
                error_msg = f"Error stopping internal streaming: {str(e)}"
                error_messages.append(error_msg)
                logger.error(error_msg)
            
            # STEP 2: Kill external streaming processes
            for pattern in process_patterns:
                try:
                    # Use pkill to find and kill processes by name pattern
                    result = subprocess.run(
                        ['pkill', '-f', pattern],
                        capture_output=True,
                        text=True
                    )
                    
                    # Check if any processes were killed (pkill returns 0 if processes found)
                    if result.returncode == 0:
                        success_count += 1
                        logger.info(f"Successfully killed processes matching: {pattern}")
                    
                    total_processes += 1
                    
                except Exception as e:
                    error_msg = f"Error killing {pattern}: {str(e)}"
                    error_messages.append(error_msg)
                    logger.error(error_msg)
            
            # STEP 3: Additional comprehensive cleanup - kill any remaining processes in project directory
            # but exclude Streamlit processes explicitly
            try:
                result = subprocess.run([
                    'pkill', '-f', 
                    'Medical_Device_Streaming_Data(?!.*streamlit)(?!.*run_streamlit)'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    success_count += 1
                    logger.info("Successfully killed remaining Medical_Device_Streaming_Data processes (excluding Streamlit)")
                    
            except Exception as e:
                error_messages.append(f"Error in comprehensive cleanup: {str(e)}")
                logger.error(f"Error in comprehensive cleanup: {str(e)}")
            
            # Note: Internal Streamlit streaming stopped first, external processes cleaned up after
        
        # Update session state to reflect stopped streaming
        st.session_state.streaming_active = False
        st.session_state.last_streaming_stopped_time = datetime.now(pytz.UTC)
        
        # Show results
        if error_messages:
            st.warning(f"⚠️ Medical streaming force stop completed with some issues:\n" + "\n".join(error_messages))
            logger.warning("Medical streaming force stop completed with errors")
        else:
            st.success("✅ ALL medical device streaming (internal + external) from ALL versions have been force stopped successfully! (Streamlit dashboards preserved)")
            logger.info("Medical streaming force stop completed successfully - internal Streamlit streaming and all external versions targeted")
        
        self.add_temp_message('success', '🚨 Emergency stop executed - Internal streaming + ALL external processes from ALL versions terminated (dashboards preserved)', 15)
        
        # Wait a moment then refresh to update UI state
        time.sleep(1)
        st.rerun()
    
    def reset_database_tables(self):
        """Handle the database reset action by setting a confirmation flag."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("User initiated database reset. Asking for confirmation.")
        st.session_state.confirm_reset = True
        st.rerun()

    def _ask_for_reset_confirmation(self):
        """Display a confirmation dialog for resetting the database."""
        st.warning("**⚠️ Are you sure you want to reset all medical device data?**")
        st.write("This will truncate all clinical and telemetry tables in Snowflake. This action cannot be undone.")
        
        col1, col2, col3 = st.columns([1.5, 1, 4])
        with col1:
            if st.button("✅ Yes, reset data", type="primary", key="confirm_reset_yes"):
                with st.spinner("Truncating tables... This might take a moment."):
                    success, message = self.db_monitor.truncate_all_tables()
                
                if success:
                    st.success("✅ All tables have been successfully reset.")
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info("All medical device data tables were truncated by user.")
                    
                    # Clear patient filter cache since all patient data has been deleted
                    if 'available_patients' in st.session_state:
                        del st.session_state.available_patients
                    if 'patient_ids_raw' in st.session_state:
                        del st.session_state.patient_ids_raw
                    
                    # Clear any cached data that might be outdated after reset
                    if 'stream_stats' in st.session_state:
                        st.session_state.stream_stats = {}
                    
                    self.add_temp_message('info', '🔄 Patient filter refreshed - database is now empty', 10)
                else:
                    st.error(f"🔥 Failed to reset tables: {message}")
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to truncate tables: {message}")
                
                st.session_state.confirm_reset = False
                time.sleep(3) # Give user time to see the message
                st.rerun()

        with col2:
            if st.button("❌ Cancel", key="confirm_reset_cancel"):
                import logging
                logger = logging.getLogger(__name__)
                logger.info("User cancelled database reset.")
                st.session_state.confirm_reset = False
                st.rerun()

    def _sync_streaming_status(self):
        """Synchronize dashboard session state with actual streaming controller state"""
        try:
            # Get current session state
            current_session_state = st.session_state.get('streaming_active', False)
            
            # Check controller state - this should be the authoritative source
            controller_active = self.stream_controller.is_streaming_active()
            
            # Check if the streaming thread is still alive
            thread_active = (hasattr(self.stream_controller, 'streaming_thread') and 
                           self.stream_controller.streaming_thread is not None and 
                           self.stream_controller.streaming_thread.is_alive())
            
            # Check for external system processes (fallback)
            system_active = self._check_system_streaming_processes()
            
            # Trust the stream controller's assessment of dual manager state
            dual_manager_active = controller_active  # StreamController should know its own state
            
            # Smart streaming state logic - trust the session state more during startup
            # Check if we recently started streaming (within last 30 seconds)
            recently_started = False
            time_since_start = 0
            if hasattr(st.session_state, 'streaming_start_time'):
                time_since_start = (datetime.now(pytz.UTC) - st.session_state.streaming_start_time).total_seconds()
                recently_started = time_since_start < 30
            
            # Check if streaming might have completed naturally
            streaming_duration = getattr(st.session_state, 'streaming_duration', 300)
            # Ensure streaming_duration is not None (fallback to 300 seconds)
            if streaming_duration is None:
                streaming_duration = 300
            likely_completed = (time_since_start >= streaming_duration * 0.95)  # Within 95% of expected duration
            
            # Determine streaming state with improved logic
            if system_active:
                # External process detected - definitely active
                actual_streaming_active = True
            elif current_session_state and recently_started:
                # If we recently started streaming, trust the session state for a grace period
                # This prevents the sync from interfering with startup
                actual_streaming_active = True
            elif controller_active or thread_active or dual_manager_active:
                # Controller, thread, or dual manager indicates active streaming
                actual_streaming_active = True
            elif current_session_state and likely_completed:
                # If streaming likely completed naturally, keep showing as active briefly
                # This prevents premature "STOPPED" status when streaming finished successfully
                actual_streaming_active = True
            else:
                # No evidence of active streaming
                actual_streaming_active = False
            
            # Update session state only if there's a clear change needed
            previous_state = current_session_state
            
            # Only update if we have strong evidence the state should change
            if actual_streaming_active != previous_state:
                # Double-check before making state changes
                if not actual_streaming_active and previous_state:
                    # Before stopping, do additional verification
                    # Check if we can detect any sign of active streaming
                    additional_evidence_active = False
                    
                    try:
                        # Use StreamController as the authoritative source for streaming state
                        # This is more reliable than direct dual_stream_manager access
                        controller_says_active = self.stream_controller.is_streaming_active()
                        if controller_says_active:
                            additional_evidence_active = True
                                
                        # Also check if we're still within reasonable time bounds
                        if time_since_start < streaming_duration * 1.1:  # Allow 10% buffer
                            additional_evidence_active = True
                            
                    except Exception:
                        pass
                    
                    # Only stop if we have very strong evidence AND no additional evidence of activity
                    strong_evidence_stopped = (
                        not controller_active and 
                        not thread_active and 
                        not system_active and 
                        not dual_manager_active and
                        not recently_started and
                        not additional_evidence_active
                    )
                    
                    if strong_evidence_stopped:
                        st.session_state.streaming_active = False
                        st.session_state.last_streaming_stopped_time = datetime.now(pytz.UTC)  # Record when streaming stopped
                        # Show appropriate message based on completion status
                        if likely_completed:
                            st.success("🎉 Streaming completed successfully after running for full duration!")
                        else:
                            st.info("✅ Streaming stopped.")
                elif actual_streaming_active and not previous_state:
                    # Starting: Trust the positive indicators
                    st.session_state.streaming_active = True
                    if system_active and not (controller_active or thread_active):
                        st.info("ℹ️ External streaming process detected. Dashboard synchronized.")
                    else:
                        st.success("🟢 Streaming is now active!")
            
            # Debug information (can be enabled for troubleshooting)
            debug_mode = False  # Set to True for debugging
            if debug_mode:
                st.write(f"🔍 Debug - Controller: {controller_active}, Thread: {thread_active}, DualManager: {dual_manager_active}, System: {system_active}")
                st.write(f"🔍 Debug - RecentStart: {recently_started}, TimeElapsed: {time_since_start:.1f}s, Duration: {streaming_duration}s, LikelyCompleted: {likely_completed}")
                st.write(f"🔍 Debug - Session: {current_session_state}, Final: {st.session_state.streaming_active}")
                    
        except Exception as e:
            # On error, be conservative - don't change state unless we're sure
            st.error(f"❌ Error checking streaming status: {str(e)}")
    
    def _check_system_streaming_processes(self) -> bool:
        """Check if any medical device streaming processes are running on the system"""
        try:
            # Use StreamController as primary source - it should know if its processes are active
            if self.stream_controller.is_streaming_active():
                return True
            
            # Fallback: Check system processes
            import subprocess
            result = subprocess.run(
                ['ps', 'aux'], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            # Look for streaming-related processes (broader search)
            for line in result.stdout.split('\n'):
                if any(keyword in line for keyword in [
                    'dual_stream_manager',
                    'snowpipe_streaming'
                ]) and 'python' in line:
                    return True
            return False
            
        except Exception:
            # If we can't check, return False
            return False

    def _show_data_source_status(self):
        """Show comprehensive data source status and database connectivity information"""
        # Check database connectivity
        try:
            # Test database connection
            test_records = self.db_monitor.get_table_record_counts()
            db_connected = True
            total_records = sum(test_records.values()) if test_records else 0
        except Exception as e:
            db_connected = False
            total_records = 0
            
        # Create status columns
        status_col1, status_col2 = st.columns(2)
        
        with status_col1:
            if db_connected:
                st.success("🟢 **Snowflake Connected**")
                st.caption(f"📊 Total records: {total_records:,}")
            else:
                st.error("🔴 **Snowflake Disconnected**")
                st.caption("Using fallback data")
                
        with status_col2:
            if st.session_state.streaming_active:
                st.success("🔴 **LIVE Streaming**")
                st.caption("📡 Real-time data from database")
            else:
                st.info("⏸️ **Historical Data**")
                st.caption("📚 Static data from database")
        
        # Show detailed data source information
        with st.expander("📋 Data Source Details", expanded=False):
            st.markdown("### 🏗️ Architecture Overview")
            
            if db_connected:
                st.markdown("""
                **✅ All Dashboard Data Sources:**
                - 💓 **ECG Data**: `CLINICAL.ECG_DATA` table in Snowflake
                - 😰 **EDA Data**: `CLINICAL.EDA_DATA` table in Snowflake  
                - 🫀 **PPG Data**: `CLINICAL.PPG_DATA` table in Snowflake
                - 📈 **Aggregations**: Real-time calculations from database records
                - ⏱️ **Timestamps**: Actual database timestamps with proper precision
                
                **🚫 NO Simulated Data:**
                - Zero random value generation
                - No fallback simulations 
                - Empty charts displayed when no database data available
                - All metrics calculated from actual Snowflake records
                """)
                
                if st.session_state.streaming_active:
                    st.markdown("""
                    **🔴 LIVE Streaming Process:**
                    1. 🏥 Medical device generators create patient data
                    2. 📡 Snowpipe Streaming Client writes to Snowflake
                    3. 🔄 Dashboard queries latest aggregated data  
                    4. 📊 Charts display real database values (100% authentic)
                    """)
                else:
                    st.markdown("""
                    **📚 Historical Data Mode:**
                    - Charts show aggregated historical data from Snowflake
                    - Zero simulated or random values
                    - All timestamps reflect actual database records
                    - Empty charts shown if no data in database
                    """)
            else:
                st.warning("""
                **⚠️ Database Connection Issues:**
                - Dashboard will show "No Data Available" messages
                - NO fallback to simulated data (pure database approach)
                - Connect to Snowflake to see real medical device data
                - Check configuration and network connectivity
                """)
            
            # Show current time range info  
            selected_range = st.session_state.get('selected_time_range', 'Last 5 Minutes')
            st.markdown(f"**🕐 Current View**: `{selected_range}` - All data from Snowflake database")
            
        # Additional info if streaming is active with short time ranges
        current_time_range = st.session_state.get('selected_time_range', '')
        if "10 seconds" in current_time_range or "5 Minutes" in current_time_range or "1 Minute" in current_time_range:
            if st.session_state.streaming_active:
                st.info("🔄 **Live Mode**: Charts update with latest data from Snowflake every refresh")

    def _get_available_patients(self):
        """Get list of available patients from Snowflake database with caching"""
        # Use session state to cache patient list to avoid repeated database queries
        if 'available_patients' not in st.session_state:
            try:
                # Get distinct patient IDs from database
                patient_ids = self.db_monitor.get_distinct_patient_ids()
                
                if patient_ids:
                    # Convert database patient IDs to display format
                    # e.g., "PATIENT_001" -> "Patient 001"
                    display_patients = []
                    for patient_id in patient_ids:
                        if patient_id.startswith("PATIENT_"):
                            # Extract number and format for display using Python 3.9 removeprefix
                            patient_num = patient_id.removeprefix("PATIENT_")
                            display_patients.append(f"Patient {patient_num}")
                        else:
                            # Use patient ID as-is if not in expected format
                            display_patients.append(patient_id)
                    
                    # Cache the results
                    st.session_state.available_patients = sorted(display_patients)
                    st.session_state.patient_ids_raw = patient_ids
                    
                    self.logger.info(f"Loaded {len(patient_ids)} patients from database: {patient_ids[:5]}...")
                else:
                    # Fallback to default if no patients found in database
                    st.session_state.available_patients = ["No patients found - database is empty"]
                    st.session_state.patient_ids_raw = []
                    self.logger.warning("No patient IDs found in database, using fallback options")
                    
            except Exception as e:
                # Fallback to hardcoded list if database query fails
                self.logger.error(f"Failed to load patients from database: {str(e)}")
                st.session_state.available_patients = [
                    "Patient 001", "Patient 002", "Patient 003", "Patient 004", "Patient 005",
                    "Patient 006", "Patient 007", "Patient 008", "Patient 009", "Patient 010"
                ]
                st.session_state.patient_ids_raw = []
        
        return st.session_state.available_patients

    def _convert_patient_selection_to_id(self, patient_selection):
        """Convert patient selection from dropdown to proper patient_id format"""
        if not patient_selection or patient_selection in ["No patients found in database", "No patients found - database is empty"]:
            return None  # No patient filtering
        
        # Convert "Patient 001" to "PATIENT_001"
        if "Patient " in patient_selection:
            patient_number = patient_selection.replace("Patient ", "").strip()
            return f"PATIENT_{patient_number}"
        
        # If already in PATIENT_XXX format, return as is
        if patient_selection.startswith("PATIENT_"):
            return patient_selection
            
        return None

    def _process_device_telemetry(self, recent_records: list) -> dict:
        """Process device telemetry data - simplified for fast loading"""
        device_metrics = {}
        
        # Process all records to find the most recent for each device
        for record in recent_records:
            try:
                data = json.loads(record.get('DATA', '{}'))
                device_id = data.get('device_id')
                record_timestamp = record.get('TIMESTAMP_VAL')
                
                if not device_id or not record_timestamp:
                    continue
                
                # Store the most recent data per device (compare timestamps)
                if device_id not in device_metrics:
                    device_metrics[device_id] = {
                        'device_type': data.get('device_type', 'Unknown'),
                        'latest_data': data,
                        'timestamp': record_timestamp
                    }
                else:
                    # Update if this record is more recent
                    existing_timestamp = device_metrics[device_id]['timestamp']
                    if record_timestamp > existing_timestamp:
                        device_metrics[device_id] = {
                            'device_type': data.get('device_type', 'Unknown'),
                            'latest_data': data,
                            'timestamp': record_timestamp
                        }
                
            except Exception:
                continue
        
        return device_metrics

    def _render_device_health_table(self, device_metrics: dict):
        """Render device health as a clean table - simplified for fast loading"""
        if not device_metrics:
            st.info("No device metrics to display")
            return
        
        # Create data for table - simplified with only current values
        table_data = []
        
        for device_id, metrics in device_metrics.items():
            latest = metrics['latest_data']
            
            # Get current values only - no status calculations for speed
            battery = latest.get('battery_level', 0)
            signal = latest.get('signal_strength', 0)
            temp = latest.get('temperature', 0)
            cpu = latest.get('cpu_usage', 0)
            connection = latest.get('connection_status', 'UNKNOWN')
            uptime = latest.get('uptime_hours', 0)
            
            # Add row to table - raw values only for speed
            table_data.append({
                'Device': f"{device_id} ({metrics['device_type']})",
                'Battery': f"{battery:.0f}%",
                'Signal': f"{signal:.0f} dBm",
                'Temperature': f"{temp:.1f}°C",
                'CPU': f"{cpu:.1f}%",
                'Connection': connection,
                'Uptime': f"{uptime:.1f}h"
            })
        
        # Quick summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Devices", len(device_metrics))
        with col2:
            connected = sum(1 for _, m in device_metrics.items() 
                           if m['latest_data'].get('connection_status') == 'CONNECTED')
            st.metric("Connected", connected)
        with col3:
            avg_battery = np.mean([m['latest_data'].get('battery_level', 0) for m in device_metrics.values()])
            st.metric("Avg Battery", f"{avg_battery:.0f}%")
        
        st.markdown("---")
        
        # Use current UTC time for 'as of' timestamp (do not derive from data)
        as_of_text = datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S.%f UTC')

        # Display ultra-fast simple table without DataFrame
        st.markdown(f"### 📋 Current Device Status (Last available readings as of: `{as_of_text}`)")
        
        # Create simple HTML table for maximum speed
        table_html = "<table style='width:100%'><tr><th>Device</th><th>Battery</th><th>Signal</th><th>Temp</th><th>CPU</th><th>Connection</th><th>Uptime</th></tr>"
        
        for row in table_data:
            table_html += f"""<tr>
                <td>{row['Device']}</td>
                <td>{row['Battery']}</td>
                <td>{row['Signal']}</td>
                <td>{row['Temperature']}</td>
                <td>{row['CPU']}</td>
                <td>{row['Connection']}</td>
                <td>{row['Uptime']}</td>
            </tr>"""
        
        table_html += "</table>"
        st.markdown(table_html, unsafe_allow_html=True)
        
        # Note about data source - show appropriate message based on streaming status
        # Force synchronization before checking streaming status
        try:
            # Explicitly sync streaming status first
            self._sync_streaming_status()
            
            # Now check the synchronized session state
            streaming_active = st.session_state.get('streaming_active', False)
            
            if streaming_active:
                refresh_interval = st.session_state.get('refresh_interval', 5)
                st.caption(f"💡 Live data from telemetry stream - refreshes every {refresh_interval} seconds")
            else:
                st.caption("💡 Data from database")
        except Exception as e:
            # Fallback to static message if there's any error
            st.caption("💡 Data from database")
    
    def render_patient_insights_panel(self):
        """Render Patient Health Insights panel with demographics and latest vital signs"""
        st.header("👤 Patient Health Insights")
        st.markdown("Select a patient to view their demographics and latest vital statistics.")
        
        try:
            # Get available patients with demographics
            patients_df = self._get_patients_with_demographics()
            
            if patients_df.empty:
                st.warning("⚠️ No patients with vital signs data found. Please ensure streaming is active and data is available.")
                return
            
            # Patient selection dropdown
            patient_options = {}
            for _, row in patients_df.iterrows():
                patient_display = f"{row['FIRST']} {row['LAST']} (ID: {row['PATIENT_ID']})"
                patient_options[patient_display] = row['PATIENT_ID']
            
            selected_patient_display = st.selectbox(
                "🔍 Select Patient:",
                options=list(patient_options.keys()),
                key="patient_selector"
            )
            
            if selected_patient_display:
                selected_patient_id = patient_options[selected_patient_display]
                patient_info = patients_df[patients_df['PATIENT_ID'] == selected_patient_id].iloc[0]
                
                # Display patient demographics
                st.markdown("### 📋 Patient Demographics")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("👤 Name", f"{patient_info['FIRST']} {patient_info['LAST']}")
                    
                with col2:
                    age = patient_info['CALCULATED_AGE']
                    st.metric("🎂 Age", f"{age} years")
                    
                with col3:
                    st.metric("⚧️ Gender", patient_info['GENDER'])
                    
                with col4:
                    st.metric("🌍 Race", patient_info['RACE'])
                
                col5, col6 = st.columns(2)
                with col5:
                    st.metric("🏛️ Ethnicity", patient_info['ETHNICITY'])
                with col6:
                    st.metric("📅 Birth Date", patient_info['BIRTHDATE'].strftime('%Y-%m-%d'))
                
                st.markdown("---")
                
                # Get and display latest vital signs
                vital_signs_df = self._get_patient_latest_vitals(selected_patient_id)
                
                if not vital_signs_df.empty:
                    latest_record = vital_signs_df.iloc[0]
                    timestamp = latest_record['TIMESTAMP_SEC']
                    
                    # Highlight timestamp
                    st.markdown("### 🩺 Latest Vital Signs")
                    st.markdown(f"**⏰ Last available readings as of: `{timestamp}`**")
                    st.markdown("")
                    
                    # Display vital signs in a clean table
                    vital_signs_data = []
                    
                    # Helper function to format timestamp info
                    def format_source_info(source_timestamp, age_seconds):
                        if pd.notna(source_timestamp) and pd.notna(age_seconds):
                            if age_seconds == 0:
                                return " (real-time)"
                            else:
                                # Format the source timestamp with full date and time
                                source_datetime = pd.to_datetime(source_timestamp).strftime('%Y-%m-%d %H:%M:%S')
                                return f" (last reading received at {source_datetime})"
                        return ""
                    
                    # ECG Data
                    if pd.notna(latest_record['ECG_HEART_RATE']):
                        source_info = format_source_info(
                            latest_record.get('ECG_SOURCE_TIMESTAMP'),
                            latest_record.get('ECG_AGE_SECONDS')
                        )
                        vital_signs_data.append({
                            "Measurement": "❤️ Heart Rate (ECG)",
                            "Value": f"{latest_record['ECG_HEART_RATE']:.0f} BPM{source_info}",
                            "Status": self._get_heart_rate_status(latest_record['ECG_HEART_RATE'])
                        })
                    
                    # Stress Level
                    if pd.notna(latest_record['STRESS_LEVEL']):
                        source_info = format_source_info(
                            latest_record.get('EDA_SOURCE_TIMESTAMP'),
                            latest_record.get('EDA_AGE_SECONDS')
                        )
                        vital_signs_data.append({
                            "Measurement": "😰 Stress Level (EDA)",
                            "Value": f"{latest_record['STRESS_LEVEL']:.2f}{source_info}",
                            "Status": self._get_stress_status(latest_record['STRESS_LEVEL'])
                        })
                    
                    # Blood Oxygen
                    if pd.notna(latest_record['SPO2']):
                        source_info = format_source_info(
                            latest_record.get('PPG_SOURCE_TIMESTAMP'),
                            latest_record.get('PPG_AGE_SECONDS')
                        )
                        vital_signs_data.append({
                            "Measurement": "🫁 Blood Oxygen (SpO2)",
                            "Value": f"{latest_record['SPO2']:.1f}%{source_info}",
                            "Status": self._get_spo2_status(latest_record['SPO2'])
                        })
                    
                    # Blood Pressure
                    if pd.notna(latest_record['SYSTOLIC_BP']) and pd.notna(latest_record['DIASTOLIC_BP']):
                        source_info = format_source_info(
                            latest_record.get('PPG_SOURCE_TIMESTAMP'),
                            latest_record.get('PPG_AGE_SECONDS')
                        )
                        vital_signs_data.append({
                            "Measurement": "🩸 Blood Pressure",
                            "Value": f"{latest_record['SYSTOLIC_BP']:.0f}/{latest_record['DIASTOLIC_BP']:.0f} mmHg{source_info}",
                            "Status": self._get_bp_status(latest_record['SYSTOLIC_BP'], latest_record['DIASTOLIC_BP'])
                        })
                    
                    if vital_signs_data:
                        vital_signs_table = pd.DataFrame(vital_signs_data)
                        
                        # Color-code the table based on status with black text for visibility
                        def highlight_status(row):
                            if row['Status'] in ['🔴 High', '🔴 Critical', '🔴 Low']:
                                return ['background-color: #ffe6e6; color: black'] * len(row)
                            elif row['Status'] in ['🟡 Elevated', '🟡 Moderate']:
                                return ['background-color: #fff3cd; color: black'] * len(row)
                            else:
                                return ['background-color: #d4edda; color: black'] * len(row)
                        
                        styled_table = vital_signs_table.style.apply(highlight_status, axis=1)
                        st.dataframe(styled_table, use_container_width=True, hide_index=True)
                        
                    else:
                        st.warning(f"⚠️ No vital signs data available for {patient_info['FIRST']} {patient_info['LAST']} at the latest timestamp.")
                else:
                    st.warning(f"⚠️ No vital signs data found for patient {patient_info['FIRST']} {patient_info['LAST']}.")
            
        except Exception as e:
            self.logger.error(f"Error in patient insights panel: {str(e)}")
            st.error(f"Unable to load patient insights: {str(e)}")
    
    def _get_patients_with_demographics(self):
        """Get patients who have both vital signs and demographic data"""
        try:
            # Use dynamic database and schema references from config
            marketplace_db = self.config.snowflake_config.MARKETPLACE_DATABASE
            marketplace_schema = self.config.snowflake_config.MARKETPLACE_SCHEMA
            marketplace_table = self.config.snowflake_config.MARKETPLACE_PATIENTS_TABLE
            clinical_db = self.config.snowflake_config.DATABASE
            clinical_schema = self.config.snowflake_config.CLINICAL_SCHEMA
            
            query = f"""
            SELECT DISTINCT
                v.PATIENT_ID,
                p.FIRST,
                p.LAST,
                p.GENDER,
                p.RACE,
                p.ETHNICITY,
                p.BIRTHDATE,
                DATEDIFF('year', p.BIRTHDATE, CURRENT_DATE()) as CALCULATED_AGE,
                COUNT(v.PATIENT_ID) as VITAL_RECORDS
            FROM {clinical_db}.{clinical_schema}.PATIENT_VITAL_SIGNS v
            INNER JOIN {marketplace_db}.{marketplace_schema}.{marketplace_table} p
                ON CAST(v.PATIENT_ID AS STRING) = CAST(p.PATIENT_ID AS STRING)
            GROUP BY v.PATIENT_ID, p.FIRST, p.LAST, p.GENDER, p.RACE, p.ETHNICITY, p.BIRTHDATE
            ORDER BY p.FIRST, p.LAST
            """
            
            return self.db_monitor._execute_query(query)
            
        except Exception as e:
            self.logger.error(f"Error getting patients with demographics: {str(e)}")
            return pd.DataFrame()
    
    def _get_patient_latest_vitals(self, patient_id):
        """Get the latest vital signs for a specific patient including source timestamps"""
        try:
            query = f"""
            SELECT 
                PATIENT_ID,
                TIMESTAMP_SEC,
                ECG_HEART_RATE,
                ECG_SOURCE_TIMESTAMP,
                ECG_AGE_SECONDS,
                STRESS_LEVEL,
                EDA_SOURCE_TIMESTAMP,
                EDA_AGE_SECONDS,
                SPO2,
                PPG_SOURCE_TIMESTAMP,
                PPG_AGE_SECONDS,
                SYSTOLIC_BP,
                DIASTOLIC_BP,
                AROUSAL_LEVEL,
                PULSE_WAVE_VELOCITY,
                ARTERIAL_STIFFNESS
            FROM MEDICAL_DEVICE_CLINICAL_DATA.PATIENT_VITAL_SIGNS
            WHERE PATIENT_ID = '{patient_id}'
            ORDER BY TIMESTAMP_SEC DESC
            LIMIT 1
            """
            
            return self.db_monitor._execute_query(query)
            
        except Exception as e:
            self.logger.error(f"Error getting latest vitals for patient {patient_id}: {str(e)}")
            return pd.DataFrame()
    
    def _get_heart_rate_status(self, heart_rate):
        """Get heart rate status with color coding"""
        if pd.isna(heart_rate):
            return "⚪ N/A"
        elif heart_rate > 100:
            return "🔴 High"
        elif heart_rate < 60:
            return "🔴 Low"
        elif heart_rate > 90:
            return "🟡 Elevated"
        else:
            return "🟢 Normal"
    
    def _get_stress_status(self, stress_level):
        """Get stress level status with color coding"""
        if pd.isna(stress_level):
            return "⚪ N/A"
        elif stress_level > 0.8:
            return "🔴 Critical"
        elif stress_level > 0.6:
            return "🔴 High"
        elif stress_level > 0.4:
            return "🟡 Moderate"
        else:
            return "🟢 Normal"
    
    def _get_spo2_status(self, spo2):
        """Get SpO2 status with color coding"""
        if pd.isna(spo2):
            return "⚪ N/A"
        elif spo2 < 95:
            return "🔴 Low"
        elif spo2 < 97:
            return "🟡 Moderate"
        else:
            return "🟢 Normal"
    
    def _get_bp_status(self, systolic, diastolic):
        """Get blood pressure status with color coding"""
        if pd.isna(systolic) or pd.isna(diastolic):
            return "⚪ N/A"
        elif systolic > 140 or diastolic > 90:
            return "🔴 High"
        elif systolic < 90 or diastolic < 60:
            return "🔴 Low"
        elif systolic > 130 or diastolic > 85:
            return "🟡 Elevated"
        else:
            return "🟢 Normal"

    def run(self):
        """Main dashboard run method"""
        # Render header
        self.render_header()
        
        # Check if we need to show the confirmation dialog
        if st.session_state.get('confirm_reset', False):
            # Clear sidebar to prevent cached elements
            with st.sidebar:
                st.empty()
            # Clear main content area to prevent cached elements
            main_container = st.container()
            with main_container:
                st.empty()
            self._ask_for_reset_confirmation()
        else:
            # Render control panel (sidebar)
            refresh_interval = self.render_control_panel()
            
            # Main content area
            tab1, tab2, tab3 = st.tabs(["🩺 Clinical Data Monitoring", "📟 Device Health Monitoring", "👤 Patient Health Insights"])
            
            with tab1:
                try:
                    self.render_patient_health_panel()
                except Exception as e:
                    self.logger.error(f"Error rendering patient health panel: {str(e)}")
                    st.error("Unable to load patient health data. Please try refreshing the page.")
            
            with tab2:
                try:
                    self.render_device_health_panel()
                except Exception as e:
                    self.logger.error(f"Error rendering device health panel: {str(e)}")
                    st.error("Unable to load device health data. Please try refreshing the page.")
            
            with tab3:
                try:
                    self.render_patient_insights_panel()
                except Exception as e:
                    self.logger.error(f"Error rendering patient insights panel: {str(e)}")
                    st.error("Unable to load patient insights data. Please try refreshing the page.")
            
            # Auto-refresh functionality (improved non-blocking)
            # Use session state directly to get the current checkbox value
            if st.session_state.get("auto_refresh_main", False):
                current_time = datetime.now(pytz.UTC)
                last_refresh = st.session_state.get('last_refresh', datetime.min.replace(tzinfo=pytz.UTC))
                time_since_refresh = (current_time - last_refresh).total_seconds()
                
                # Only refresh if enough time has passed AND auto-refresh is still enabled
                if time_since_refresh >= refresh_interval:
                    # Double-check that auto-refresh is still enabled before rerunning
                    if st.session_state.get("auto_refresh_main", False):
                        st.session_state.last_refresh = current_time
                        
                        # Clear patient filter cache during auto-refresh to ensure fresh data
                        # This ensures patient list updates regardless of streaming status
                        if 'available_patients' in st.session_state:
                            del st.session_state.available_patients
                        if 'patient_ids_raw' in st.session_state:
                            del st.session_state.patient_ids_raw
                        
                        st.rerun()

# Main application
if __name__ == "__main__":
    dashboard = StreamingDashboard()
    dashboard.run() 