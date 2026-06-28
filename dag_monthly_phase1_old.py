from __future__ import annotations

import os
import logging
import pathlib
import subprocess
from datetime import datetime, timedelta

import pytz
from airflow import DAG
from airflow.models.param import Param
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.standard.operators.empty import EmptyOperator


logger = logging.getLogger(__name__)

TIMEZONE = pytz.timezone("Asia/Ho_Chi_Minh")
DAG_NAME = "DAG_MONTHLY_PHASE1"
SCHEDULE = "30 7 1 * *"
DAG_ARGS = {
    "start_date": datetime(2024, 12, 1),
    "retries": 3,
    "retry_delay": timedelta(minutes=10),
}


log_check_interval = 30
first_day_of_month = datetime.now(TIMEZONE).replace(day=1)

# Params
dt_to = (first_day_of_month - timedelta(days=1)).strftime("%Y%m%d")
dt_from = dt_to[:6] + "01"

run_mode = "prod"
overwrite = "false"
params = {
    "dt_from": Param(dt_from),
    "dt_to": Param(dt_to),
    "run_mode": Param(run_mode, enum=["prod", "backtest", "dev"]),
    "skip_dags": Param(""),
    "overwrite": Param(overwrite, enum=["false", "true"]),
}


def extract_run_configs(run_configs, **kwargs):
    # fix undefined param
    logger.info("Extracting run configs: %s", run_configs)
    run_configs["dt_from"] = str(dt_from)
    run_configs["dt_to"] = str(dt_to)
    run_configs["run_mode"] = run_mode
    run_configs["skip_dags"] = ""
    run_configs["overwrite"] = overwrite

    logger.info("Run configs after extraction: %s", run_configs)

    kwargs["ti"].xcom_push(key="run_configs", value=run_configs)


def update_repo(
    target_dir: str = "/opt/airflow/dags/vtp",
    repo_url: str = "http://gitea:3000/gitea/vtp.git",
    branch: str = "master",
    **kwargs,
):
    if pathlib.Path(os.path.join(target_dir, ".git")).is_dir():
        logger.info("Reset, pull")
        subprocess.run(
            ["git", "-C", target_dir, "reset", "--hard", f"origin/{branch}"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", target_dir, "pull", "origin", branch],
            check=True,
        )
    else:
        logger.info("Clone")
        subprocess.run(
            ["git", "clone", "-b", branch, repo_url, target_dir],
            check=True,
        )


# Run DAG
with DAG(
    DAG_NAME,
    default_args=DAG_ARGS,
    catchup=False,
    render_template_as_native_obj=True,
    schedule=SCHEDULE,
    max_active_runs=1,
    params=params,
) as dag:
    input_arg = "--dt_from {{params.dt_from}} --dt_to {{params.dt_to}} --run_mode {{params.run_mode}} --skip_dags {{params.skip_dags}} --overwrite {{params.overwrite}}"

    start_node = EmptyOperator(
        task_id="start",
    )

    end_node = EmptyOperator(
        task_id="end",
    )

    extract_config = PythonOperator(
        task_id="extract_config",
        python_callable=extract_run_configs,
        op_kwargs={
            "run_configs": {
                "dt_from": "{{ dag_run.conf.get('dt_from', dt_from) }}",
                "dt_to": "{{ dag_run.conf.get('dt_to', dt_to) }}",
                "run_mode": "{{ dag_run.conf.get('run_mode', run_mode) }}",
                "skip_dags": "{{ dag_run.conf.get('skip_dags', '') }}",
                "overwrite": "{{ dag_run.conf.get('overwrite', overwrite) }}",
            }
        },
    )

    update_code = PythonOperator(
        task_id="update_code", python_callable=update_repo
    )

    pipeline_day = BashOperator(
        task_id="pipeline_day",
        bash_command=(
            "export PYTHONPATH=/opt/airflow/dags/vtp:${PYTHONPATH}; "
            f"{os.environ['SPARK_HOME']}/bin/spark-submit --master spark://master:7077 /opt/airflow/dags/vtp/src/scripts/pipeline_day/pipeline_day.py {input_arg}"
        ),
    )

    groupby_data = BashOperator(
        task_id="groupby_data",
        bash_command=(
            "export PYTHONPATH=/opt/airflow/dags/vtp:${PYTHONPATH}; "
            f"{os.environ['SPARK_HOME']}/bin/spark-submit --master spark://master:7077 /opt/airflow/dags/vtp/src/scripts/group_data_monthly/grouping_data.py {input_arg}"
        ),
    )

    main_scoring = BashOperator(
        task_id="main_scoring",
        bash_command=(
            "export PYTHONPATH=/opt/airflow/dags/vtp:${PYTHONPATH}; "
            f"{os.environ['SPARK_HOME']}/bin/spark-submit --master spark://master:7077 /opt/airflow/dags/vtp/src/scripts/scoring/main_scoring.py {input_arg}"
        ),
    )

    # Define dependencies
    (
        start_node
        >> extract_config
        >> pipeline_day
        >> groupby_data
        >> main_scoring
        >> end_node
    )
