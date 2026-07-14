# Snowflake HCLS Industry Solutions

**HCLS: Healthcare & Life Sciences**

End-to-end solution accelerators for the Healthcare & Life Sciences industry vertical, built on Snowflake and Cortex Code, showcasing Cortex AI, Snowflake ML, and the modern data platform.

---

## Solution Catalog

| # | Solution | Industry | Directory | Key Snowflake Features | Status |
|---|----------|----------|-----------|----------------------|--------|
| 1 | **Clinical Quality and Patient Safety Agent** | Healthcare | `solutions/clinical-quality-agent/` | Snowflake Intelligence, Cortex Agent, Cortex Analyst, Cortex Search (PubMed), Semantic Model | ✅ Done |
| 2 | **Medical Device Streaming Platform** | Healthcare | `solutions/medical-device-streaming/` | Snowpipe Streaming (High-Performance), PIPE Objects, ASOF Joins, VARIANT Data, Flattened Views | ✅ Done |

---

## Quick Install (via Cortex Code)

Solutions are installed via the `$sf-solutions` skill in [snowflake-ai-kit](https://github.com/Snowflake-Labs/snowflake-ai-kit):

```bash
# Install the snowflake-ai-kit plugin (includes sf-solutions skill)
cortex skill add github:Snowflake-Labs/snowflake-ai-kit
```

Then in a Cortex Code session, run a solution by name:

```
$sf-solutions:clinical-quality-agent
$sf-solutions:clinical-quality-agent teardown
```

---

## Getting Started

Each solution is self-contained in its own directory with:

```
solutions/<solution-name>/
├── README.md          # Overview, architecture, prerequisites
├── manifest.json      # Solution metadata for the installer
├── scripts/           # SQL setup and teardown scripts
├── NEXT_ACTIONS.md    # Post-install guidance
└── data/              # Sample data generation scripts (if applicable)
```

## Prerequisites

- Snowflake account (Enterprise edition recommended)
- Appropriate role with CREATE DATABASE / SCHEMA privileges
- Warehouse (default: `COMPUTE_WH`)

---

## Developers

If you're contributing new solutions to this repository, use the `add-solution` skill
from [sf-solutions](https://github.com/Snowflake-Labs/sf-solutions) to convert
existing repos into the standard format.

```bash
git clone https://github.com/Snowflake-Labs/sf-hcls-solutions.git
cd sf-hcls-solutions
cortex
```

Then invoke:
```
$add-solution ../my-existing-solution-repo
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
