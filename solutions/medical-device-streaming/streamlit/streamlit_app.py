"""Medical Device Streaming Dashboard — Streamlit in Snowflake (SiS) Version.

Read-only dashboard for monitoring medical device data stored in SF_SOLUTIONS.
Queries flattened views for ECG, EDA, PPG vital signs and device telemetry.
"""

import plotly.graph_objects as go
import streamlit as st
from snowflake.snowpark.context import get_active_session

session = get_active_session()

st.set_page_config(page_title="Medical Device Monitor", page_icon="🏥", layout="wide")
st.title("🏥 Medical Device Streaming Monitor")
st.markdown("Real-time clinical and telemetry data from Snowpipe Streaming")
st.markdown("---")

CLINICAL_SCHEMA = "SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL"
TELEMETRY_SCHEMA = "SF_SOLUTIONS.MEDICAL_DEVICE_TELEMETRY"


def get_patient_list():
    """Get list of patients with data."""
    df = session.sql(f"""
        SELECT DISTINCT PATIENT_ID
        FROM {CLINICAL_SCHEMA}.ECG_DATA
        ORDER BY PATIENT_ID
        LIMIT 50
    """).to_pandas()
    if df.empty:
        return []
    return df["PATIENT_ID"].tolist()


def get_ecg_data(patient_id, minutes=5):
    """Get recent ECG data for a patient."""
    return session.sql(f"""
        SELECT
            TIMESTAMP_VAL,
            HEART_RATE::FLOAT AS HEART_RATE,
            RHYTHM_CLASSIFICATION,
            SIGNAL_QUALITY::FLOAT AS SIGNAL_QUALITY,
            QT_INTERVAL::FLOAT AS QT_INTERVAL,
            ST_ELEVATION::FLOAT AS ST_ELEVATION
        FROM {CLINICAL_SCHEMA}.ECG_DATA_FLATTENED
        WHERE PATIENT_ID = '{patient_id}'
          AND TIMESTAMP_VAL >= DATEADD(MINUTE, -{minutes}, CURRENT_TIMESTAMP())
        ORDER BY TIMESTAMP_VAL DESC
        LIMIT 100
    """).to_pandas()


def get_eda_data(patient_id, minutes=5):
    """Get recent EDA data for a patient."""
    return session.sql(f"""
        SELECT
            TIMESTAMP_VAL,
            STRESS_LEVEL::FLOAT AS STRESS_LEVEL,
            AROUSAL_LEVEL::FLOAT AS AROUSAL_LEVEL,
            SKIN_CONDUCTANCE_LEVEL::FLOAT AS SKIN_CONDUCTANCE_LEVEL,
            EMOTIONAL_VALENCE,
            SIGNAL_QUALITY::FLOAT AS SIGNAL_QUALITY
        FROM {CLINICAL_SCHEMA}.EDA_DATA_FLATTENED
        WHERE PATIENT_ID = '{patient_id}'
          AND TIMESTAMP_VAL >= DATEADD(MINUTE, -{minutes}, CURRENT_TIMESTAMP())
        ORDER BY TIMESTAMP_VAL DESC
        LIMIT 100
    """).to_pandas()


def get_ppg_data(patient_id, minutes=5):
    """Get recent PPG data for a patient."""
    return session.sql(f"""
        SELECT
            TIMESTAMP_VAL,
            SPO2::FLOAT AS SPO2,
            HEART_RATE::FLOAT AS HEART_RATE,
            SYSTOLIC_BP::FLOAT AS SYSTOLIC_BP,
            DIASTOLIC_BP::FLOAT AS DIASTOLIC_BP,
            PERFUSION_INDEX::FLOAT AS PERFUSION_INDEX,
            SIGNAL_QUALITY::FLOAT AS SIGNAL_QUALITY
        FROM {CLINICAL_SCHEMA}.PPG_DATA_FLATTENED
        WHERE PATIENT_ID = '{patient_id}'
          AND TIMESTAMP_VAL >= DATEADD(MINUTE, -{minutes}, CURRENT_TIMESTAMP())
        ORDER BY TIMESTAMP_VAL DESC
        LIMIT 100
    """).to_pandas()


def get_telemetry_data(minutes=5):
    """Get recent device telemetry."""
    return session.sql(f"""
        SELECT
            TIMESTAMP_VAL,
            DEVICE_ID,
            DEVICE_TYPE,
            BATTERY_LEVEL::FLOAT AS BATTERY_LEVEL,
            SIGNAL_STRENGTH::FLOAT AS SIGNAL_STRENGTH,
            CONNECTION_STATUS,
            LATENCY_MS::FLOAT AS LATENCY_MS,
            CPU_USAGE::FLOAT AS CPU_USAGE,
            TEMPERATURE::FLOAT AS TEMPERATURE
        FROM {TELEMETRY_SCHEMA}.DEVICE_TELEMETRY_FLATTENED
        WHERE TIMESTAMP_VAL >= DATEADD(MINUTE, -{minutes}, CURRENT_TIMESTAMP())
        ORDER BY TIMESTAMP_VAL DESC
        LIMIT 200
    """).to_pandas()


def get_record_counts():
    """Get row counts for all tables."""
    return session.sql("""
        SELECT TABLE_SCHEMA, TABLE_NAME, ROW_COUNT
        FROM SF_SOLUTIONS.INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA IN ('MEDICAL_DEVICE_CLINICAL', 'MEDICAL_DEVICE_TELEMETRY')
          AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    """).to_pandas()


# Sidebar
st.sidebar.header("Settings")
time_range = st.sidebar.selectbox("Time Range", [5, 15, 30, 60], index=0, format_func=lambda x: f"Last {x} minutes")

patients = get_patient_list()
if patients:
    selected_patient = st.sidebar.selectbox("Patient", patients)
else:
    st.sidebar.warning("No patient data found. Start the streaming client to populate data.")
    selected_patient = None

# Table counts overview
st.sidebar.markdown("---")
st.sidebar.markdown("### Data Volume")
counts_df = get_record_counts()
if not counts_df.empty:
    for _, row in counts_df.iterrows():
        st.sidebar.metric(f"{row['TABLE_NAME']}", f"{int(row['ROW_COUNT']):,} rows")
else:
    st.sidebar.info("Tables are empty")

# Main content
if selected_patient:
    # ECG Section
    st.header("💓 ECG — Heart Activity")
    ecg_df = get_ecg_data(selected_patient, time_range)
    if not ecg_df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Heart Rate", f"{ecg_df['HEART_RATE'].iloc[0]:.0f} bpm")
        col2.metric("Rhythm", ecg_df["RHYTHM_CLASSIFICATION"].iloc[0])
        col3.metric("Signal Quality", f"{ecg_df['SIGNAL_QUALITY'].iloc[0]:.2f}")

        fig = go.Figure(
            data=[
                go.Scatter(
                    x=ecg_df["TIMESTAMP_VAL"].tolist(),
                    y=ecg_df["HEART_RATE"].tolist(),
                    mode="lines+markers",
                    line=dict(color="#1f77b4", width=2),
                    marker=dict(size=4),
                )
            ]
        )
        fig.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="Upper Normal")
        fig.add_hline(y=60, line_dash="dash", line_color="red", annotation_text="Lower Normal")
        fig.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="Time",
            yaxis_title="Heart Rate (bpm)",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No ECG data available for selected time range.")

    st.markdown("---")

    # EDA Section
    st.header("😰 EDA — Stress Monitoring")
    eda_df = get_eda_data(selected_patient, time_range)
    if not eda_df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Stress Level", f"{eda_df['STRESS_LEVEL'].iloc[0]:.2f} μS")
        col2.metric("Arousal", f"{eda_df['AROUSAL_LEVEL'].iloc[0]:.2f}")
        col3.metric("Emotional State", eda_df["EMOTIONAL_VALENCE"].iloc[0])

        fig = go.Figure(
            data=[
                go.Scatter(
                    x=eda_df["TIMESTAMP_VAL"].tolist(),
                    y=eda_df["STRESS_LEVEL"].tolist(),
                    mode="lines+markers",
                    line=dict(color="#ff7f0e", width=2),
                    marker=dict(size=4),
                )
            ]
        )
        fig.add_hline(y=3.0, line_dash="dash", line_color="red", annotation_text="High Stress")
        fig.add_hline(y=1.0, line_dash="dash", line_color="green", annotation_text="Low Stress")
        fig.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="Time",
            yaxis_title="Stress Level (μS)",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No EDA data available for selected time range.")

    st.markdown("---")

    # PPG Section
    st.header("🫀 PPG — Oxygen & Blood Pressure")
    ppg_df = get_ppg_data(selected_patient, time_range)
    if not ppg_df.empty:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("SpO2", f"{ppg_df['SPO2'].iloc[0]:.1f}%")
        col2.metric("Heart Rate", f"{ppg_df['HEART_RATE'].iloc[0]:.0f} bpm")
        col3.metric("Systolic BP", f"{ppg_df['SYSTOLIC_BP'].iloc[0]:.0f} mmHg")
        col4.metric("Diastolic BP", f"{ppg_df['DIASTOLIC_BP'].iloc[0]:.0f} mmHg")

        fig = go.Figure(
            data=[
                go.Scatter(
                    x=ppg_df["TIMESTAMP_VAL"].tolist(),
                    y=ppg_df["SPO2"].tolist(),
                    mode="lines+markers",
                    line=dict(color="#2ca02c", width=2),
                    marker=dict(size=4),
                )
            ]
        )
        fig.add_hline(y=95, line_dash="dash", line_color="red", annotation_text="Lower Normal")
        fig.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="Time",
            yaxis_title="SpO2 (%)",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No PPG data available for selected time range.")

    st.markdown("---")

# Device Telemetry Section (always shown)
st.header("📟 Device Telemetry")
telemetry_df = get_telemetry_data(time_range)
if not telemetry_df.empty:
    st.dataframe(
        telemetry_df[
            [
                "DEVICE_ID",
                "DEVICE_TYPE",
                "BATTERY_LEVEL",
                "SIGNAL_STRENGTH",
                "CONNECTION_STATUS",
                "LATENCY_MS",
                "CPU_USAGE",
                "TEMPERATURE",
            ]
        ],
    )
else:
    st.info("No telemetry data available. Start the streaming client to populate data.")
