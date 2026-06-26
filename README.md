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

Install any solution using the Cortex Code plugin:

```bash
# Permanent install (copies plugin to cache — survives restarts)
cortex plugin install https://github.com/Snowflake-Labs/sf-hcls-solutions.git

# Or load locally during development (reads directly from disk, always up-to-date)
cortex --plugin-dir ./plugins/cortex-code
```

> **Note:** `cortex plugin install` copies the plugin into a local cache. If you add new skills later, you must `cortex plugin uninstall sf-hcls-solutions && cortex plugin install ...` to refresh. During development, use `--plugin-dir` instead — it always reads the latest files from disk without caching.

Then in a Cortex Code session, run a solution by name:

```
$sf-hcls-solutions:<solution-name>
```

Example:
```
$sf-hcls-solutions:clinical-quality-agent
$sf-hcls-solutions:clinical-quality-agent teardown
```

## Quick Install (via Claude Code)

```bash
# Add the marketplace
claude plugin marketplace add https://github.com/Snowflake-Labs/sf-hcls-solutions.git --path plugins/claude-code

# Or load locally during development
claude --plugin-dir ./plugins/claude-code
```

Then in a Claude Code session, run a solution by name:
```
/sf-hcls-solutions:clinical-quality-agent
```

---

## Getting Started

Each solution is self-contained in its own directory with:

```
solutions/<solution-name>/
├── README.md          # Overview, architecture, prerequisites
├── manifest.json      # Solution metadata for the installer
├── scripts/           # SQL setup and teardown scripts
└── data/              # Sample data generation scripts (if applicable)
```

## Prerequisites

- Snowflake account (Enterprise edition recommended)
- Appropriate role with CREATE DATABASE / SCHEMA privileges
- Warehouse (default: `COMPUTE_WH`)

---

## Developers for Plugin

If you're contributing new solutions to this repository, use the `add-solution` skill to convert existing repos into the standard plugin format.

### Setup

Clone the repo and run Cortex Code from within it:

```bash
git clone https://github.com/Snowflake-Labs/sf-hcls-solutions.git
cd sf-hcls-solutions
cortex
```

### Convert an Existing Solution

In the Cortex Code session, invoke the add-solution skill with the path to the source repo:

```
$add-solution ../my-existing-solution-repo
```

This will:
1. Analyze the source repo (detect SQL-only, Python-only, or hybrid)
2. Extract all DDL into `scripts/setup.sql` and `scripts/teardown.sql`
3. Generate `manifest.json` and `README.md`
4. Create plugin skills for both Cortex Code and Claude Code
5. Audit for credentials and Snowflake internal info
6. Validate with linters (sqruff, ruff, markdownlint)

### Available Developer Skills

| Skill | Invocation | Purpose |
|-------|-----------|---------|
| add-solution | `$add-solution <path>` | Convert an existing repo into plugin format |
| list | `$sf-hcls-solutions:list` | List all registered solutions |

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
