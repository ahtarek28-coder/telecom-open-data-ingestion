"""
Airflow DAG orchestrating telecom-open-data-ingestion:
fetch World Bank indicators -> fetch FCC complaints (incremental, via
checkpoint) -> load both into DuckDB -> dqcheck.

Same conventions as telecom-cx-analytics-pipeline's DAG: Airflow and this
project's own dependencies (requests, duckdb, dqcheck) live in SEPARATE
venvs (Airflow/dbt-core-style dependency conflicts aside, keeping Airflow's
venv minimal is still good practice), so python is resolved by absolute
path via PIPELINE_VENV_BIN rather than PATH.
"""
import os
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PIPELINE_VENV_BIN = Path(os.environ.get("PIPELINE_VENV_BIN", PROJECT_ROOT / ".venv" / "bin"))
PYTHON_BIN = PIPELINE_VENV_BIN / "python"

# odingest's CLI options (--out, --checkpoint, --db, etc.) default to
# relative paths, meant to be run from the project root -- pin cwd on every
# task rather than relying on Airflow's default task working directory
# (the same relative-path gotcha already hit and fixed in the other DAG).
TASK_CWD = str(PROJECT_ROOT)

with DAG(
    dag_id="telecom_open_data_ingestion",
    description="Fetch real telecom public data (FCC complaints, World Bank indicators) and load into DuckDB",
    schedule="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["telecom", "open-data", "ingestion"],
) as dag:

    fetch_worldbank = BashOperator(
        task_id="fetch_worldbank",
        bash_command=f"{PYTHON_BIN} -m odingest.cli fetch-worldbank",
        cwd=TASK_CWD,
    )

    fetch_fcc_complaints = BashOperator(
        task_id="fetch_fcc_complaints",
        # No --since: resumes from the checkpoint automatically. --max-pages
        # is a safety cap (not a real limit for a caught-up daily run) in
        # case the checkpoint is ever missing/reset and would otherwise try
        # to pull years of backlog in one go.
        bash_command=f"{PYTHON_BIN} -m odingest.cli fetch-fcc-complaints --max-pages 20 --page-size 500",
        cwd=TASK_CWD,
    )

    load_duckdb = BashOperator(
        task_id="load_duckdb",
        bash_command=f"{PYTHON_BIN} -m odingest.cli load-duckdb",
        cwd=TASK_CWD,
    )

    dq_check = BashOperator(
        task_id="dq_check",
        bash_command=f"{PYTHON_BIN} -m dqcheck.cli run --config dq_checks.yml",
        cwd=TASK_CWD,
    )

    [fetch_worldbank, fetch_fcc_complaints] >> load_duckdb >> dq_check
