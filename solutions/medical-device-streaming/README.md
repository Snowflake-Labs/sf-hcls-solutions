# Medical Device Streaming Platform

Real-time medical device data streaming platform demonstrating Snowflake's High-Performance Snowpipe Streaming architecture for ECG, EDA, and PPG biosignal data with live analytics.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Medical Devices (ECG, EDA, PPG)                                │
│  └── Python Client (NeuroKit2 simulation)                       │
└─────────────────┬───────────────────────────────────────────────┘
                  │ REST API (JWT Auth)
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  Snowflake High-Performance Snowpipe Streaming                  │
│  ┌────────────────────┐    ┌────────────────────────────┐       │
│  │ PIPE Objects        │    │ DATA_SOURCE(TYPE=STREAMING)│       │
│  │ - ECG_STREAMING     │    │ In-flight transformations  │       │
│  │ - EDA_STREAMING     │    │ Pre-clustering support     │       │
│  │ - PPG_STREAMING     │    │ Throughput-based billing   │       │
│  │ - TELEMETRY         │    └────────────────────────────┘       │
│  └────────┬───────────┘                                         │
│           ▼                                                      │
│  ┌─────────────────────────────────────────────────────┐        │
│  │ SF_SOLUTIONS.MEDICAL_DEVICE_CLINICAL                 │        │
│  │  Tables: ECG_DATA, EDA_DATA, PPG_DATA (VARIANT)     │        │
│  │  Views:  *_FLATTENED (structured columns)            │        │
│  │  View:   PATIENT_VITAL_SIGNS (ASOF join, 5-min)     │        │
│  ├─────────────────────────────────────────────────────┤        │
│  │ SF_SOLUTIONS.MEDICAL_DEVICE_TELEMETRY                │        │
│  │  Table:  DEVICE_TELEMETRY (VARIANT)                  │        │
│  │  View:   DEVICE_TELEMETRY_FLATTENED                  │        │
│  └─────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

## Key Snowflake Features Demonstrated

| Feature | Usage |
|---------|-------|
| **Snowpipe Streaming (High-Performance)** | Real-time data ingestion via PIPE objects with REST API |
| **PIPE Objects** | Centralized data processing definitions with in-flight transformations |
| **VARIANT Data Type** | Semi-structured JSON storage for flexible biosignal schemas |
| **ASOF Joins** | Forward-fill propagation for consolidated vital signs view |
| **Flattened Views** | Efficient SQL access to nested JSON fields |
| **Dual-Schema Architecture** | Separation of clinical and telemetry data streams |

## What Gets Created

### Schema: MEDICAL_DEVICE_CLINICAL

| Object | Type | Description |
|--------|------|-------------|
| PATIENT_SESSIONS | Table | Patient monitoring session management |
| DEVICE_REGISTRY | Table | Device inventory and assignment tracking |
| ECG_DATA | Table | Raw electrocardiography VARIANT data |
| EDA_DATA | Table | Raw electrodermal activity VARIANT data |
| PPG_DATA | Table | Raw photoplethysmography VARIANT data |
| ECG_STREAMING_PIPE | Pipe | Snowpipe Streaming for ECG ingestion |
| EDA_STREAMING_PIPE | Pipe | Snowpipe Streaming for EDA ingestion |
| PPG_STREAMING_PIPE | Pipe | Snowpipe Streaming for PPG ingestion |
| ECG_DATA_FLATTENED | View | Structured ECG metrics (heart rate, leads, rhythm) |
| EDA_DATA_FLATTENED | View | Structured EDA metrics (stress, conductance) |
| PPG_DATA_FLATTENED | View | Structured PPG metrics (SpO2, blood pressure) |
| PATIENT_VITAL_SIGNS | View | Consolidated 5-min real-time view with ASOF joins |

### Schema: MEDICAL_DEVICE_TELEMETRY

| Object | Type | Description |
|--------|------|-------------|
| DEVICE_TELEMETRY | Table | Raw device health/connectivity VARIANT data |
| TELEMETRY_STREAMING_PIPE | Pipe | Snowpipe Streaming for telemetry ingestion |
| DEVICE_TELEMETRY_FLATTENED | View | Structured telemetry (battery, signal, latency) |

## Prerequisites

- Snowflake account (Trial or Enterprise)
- ACCOUNTADMIN role
- Optional: [Synthetic Healthcare Data - Clinical and Claims](https://app.snowflake.com/marketplace/listing/GZSTZL7M0Q6/) (free Marketplace dataset for patient demographics)

## Optional: Live Streaming Demo

The `app/` directory contains a Python client that generates realistic biosignal data using NeuroKit2 and streams it to Snowflake via the REST API. See NEXT_ACTIONS.md for setup instructions.

**Additional requirements for the streaming demo:**
- Python 3.11+
- RSA key pair for JWT authentication
- AWS-based Snowflake account with high-performance streaming preview
