# Snowflake HCLS Industry Solutions

**HCLS: Healthcare & Life Sciences**

End-to-end solution accelerators for the Healthcare & Life Sciences industry vertical, built on Snowflake and Cortex Code, showcasing Cortex AI, Snowflake ML, and the modern data platform.

## Requirements

- Snowflake Trial account
- Enterprise edition+
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

---

## Solution Catalog

| # | Solution | Industry | Directory | Key Snowflake Features | Status |
|---|----------|----------|-----------|----------------------|--------|
| 1 | **Clinical Quality and Patient Safety Agent** | Healthcare | `solutions/clinical-quality-agent/` | Snowflake Intelligence, Cortex Agent, Cortex Analyst, Cortex Search (PubMed), Semantic Model | Done |
| 2 | **Medical Device Streaming Platform** | Healthcare | `solutions/medical-device-streaming/` | Snowpipe Streaming (High-Performance), PIPE Objects, ASOF Joins, VARIANT Data, Flattened Views | Done |
| 3 | **HCLS Field Targeting Platform** | Healthcare & Life Sciences | `solutions/field-targeting/` | Cortex AI (SENTIMENT, CLASSIFY_TEXT), Semantic View, Streamlit What-If Dashboard, Rules Engine | Done |

---

## Quick Install (via Cortex Code)

> **TBA** — Plugin install command will be available after public release.

```
$sf-solutions                              # List all available solutions
$sf-solutions hcls                         # Filter by HCLS industry
$sf-solutions:clinical-quality-agent       # Install a solution
$sf-solutions:clinical-quality-agent teardown  # Remove a solution
```

---

## Getting Started

Each solution is self-contained in its own directory with:

```
solutions/<solution-name>/
├── README.md          # Overview, architecture, prerequisites
├── manifest.json      # Solution metadata for the installer
├── NEXT_ACTIONS.md    # Post-install verification steps and example queries
├── scripts/           # SQL setup and teardown scripts
└── streamlit/         # Streamlit app (if applicable)
```

---

## Related Resources

### Web Pages

- [Snowflake ML](https://www.snowflake.com/en/data-cloud/snowflake-ml/) - Integrated set of capabilities for development, MLOps and inference leading with agentic ML
- [Snowflake Notebooks](https://www.snowflake.com/en/data-cloud/notebooks/) - Jupyter-based notebooks in Snowflake Workspaces
- [Cortex Code](https://www.snowflake.com/en/data-cloud/cortex/cortex-code/) - Snowflake's AI native coding agent that boosts ML productivity

### Technical Documentation

- [Cortex Code Documentation](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code) - Getting started with Cortex Code
- [Cortex Code in Snowsight](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-snowsight) - Browser-based experience
- [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli) - Command-line experience
- [Snowflake ML Documentation](https://docs.snowflake.com/en/developer-guide/snowflake-ml/overview) - Official Snowflake ML developer guide
- [Snowflake ML Quickstart](https://quickstarts.snowflake.com/guide/getting-started-with-snowflake-ml/) - Hands-on guides to get started with Snowflake ML
