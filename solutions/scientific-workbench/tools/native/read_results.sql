-- =============================================================================
-- tools/native/read_results.sql
-- Read agent output tables from SCIENTIFIC_WORKBENCH.RESULTS
-- =============================================================================
-- Allows agents to inspect the results they (or other tools) wrote.
-- Validates that the table name is within RESULTS schema to prevent
-- unauthorized reads from other schemas.
-- =============================================================================

CREATE OR REPLACE PROCEDURE SCIENTIFIC_WORKBENCH.CATALOG.READ_RESULTS(
    "TABLE_NAME" VARCHAR,
    "MAX_ROWS"   NUMBER(38,0) DEFAULT 50
)
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'run'
COMMENT = 'TOOL:{"display_name":"Read Results","description":"Read the contents of an output table in SCIENTIFIC_WORKBENCH.RESULTS. Returns up to MAX_ROWS rows as JSON.","domains":"utility","params":{"table_name":"STRING","max_rows":"INT"},"return_type":"VARCHAR","example":"CALL CATALOG.READ_RESULTS(table_name, 50)"}'
EXECUTE AS OWNER
AS
$$
import json, re

ALLOWED_DB_SCHEMA = 'SCIENTIFIC_WORKBENCH.RESULTS'
_SAFE_ID = re.compile(r'^[A-Z][A-Z0-9_]{0,254}$')

def _validate_table(name: str) -> str:
    upper = name.strip().upper().replace('"', '')
    parts = upper.split('.')
    bare = parts[-1] if len(parts) in (1, 3) else ''
    if len(parts) == 3 and '.'.join(parts[:2]) != ALLOWED_DB_SCHEMA:
        raise ValueError(f'table_name must be in {ALLOWED_DB_SCHEMA}')
    if not bare or not _SAFE_ID.match(bare):
        raise ValueError(f'table_name identifier must be uppercase alphanumeric/underscore, got: {name}')
    return f'{ALLOWED_DB_SCHEMA}.{bare}'

def run(session, table_name: str, max_rows: int = 50) -> str:
    fqn = _validate_table(table_name)
    limit = max(1, min(int(max_rows or 50), 500))
    rows = session.sql(f'SELECT * FROM {fqn} LIMIT {limit}').collect()
    if not rows:
        return f'No data found in {fqn}'
    result = [dict(zip([f.name for f in rows[0].__fields__] if hasattr(rows[0], '__fields__') else range(len(rows[0])), r)) for r in rows]
    return json.dumps(result, default=str)[:100000]
$$;

CALL SCIENTIFIC_WORKBENCH.CATALOG.REGISTER_TOOL(
    'read_results', 'Read Results',
    'Read the contents of an output table in SCIENTIFIC_WORKBENCH.RESULTS. Returns rows as JSON.',
    'utility', 'procedure',
    'SCIENTIFIC_WORKBENCH.CATALOG.READ_RESULTS',
    '{"table_name":"STRING","max_rows":"INT"}',
    'VARCHAR',
    'CALL CATALOG.READ_RESULTS(table_name, 50)'
);
