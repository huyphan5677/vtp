from __future__ import annotations

import os
import logging
import pathlib
import subprocess
from datetime import datetime, timedelta

import pytz
import yaml
from airflow import DAG
from airflow.models.param import Param
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.standard.operators.empty import EmptyOperator


logger = logging.getLogger(__name__)

TIMEZONE = pytz.timezone("Asia/Ho_Chi_Minh")
DAG_NAME = "DAG_MONTHLY_PHASE_1"
# Chạy hàng ngày: mỗi ngày xử lý dữ liệu của
# đúng ngày đó; khi gặp ngày đầu tháng, giai đoạn tháng tự tính cho tháng
# liền trước (xem run_feature_range/_months_to_score trong run.py).
SCHEDULE = "30 7 * * *"
DAG_ARGS = {
    "start_date": datetime(2024, 12, 1),
    "retries": 3,
    "retry_delay": timedelta(minutes=10),
}


log_check_interval = 30

# Params: mặc định xử lý đúng ngày hôm nay (dt_from == dt_to). Truyền
# dag_run.conf với dt_from/dt_to khác nhau để backfill 1 khoảng ngày dài
# hơn — giai đoạn tháng sẽ tự tính cho mọi tháng liền trước ngày-đầu-tháng
# rơi trong khoảng đó.
today_str = datetime.now(TIMEZONE).strftime("%Y%m%d")
dt_from = today_str
dt_to = today_str

run_mode = "prod"
overwrite = "false"
params = {
    "dt_from": Param(dt_from),
    "dt_to": Param(dt_to),
    "scoring_month": None,
    "run_mode": Param(run_mode, enum=["prod", "backtest", "dev"]),
    "skip_dags": Param(""),
    "overwrite": Param(overwrite, enum=["false", "true"]),
}


def extract_run_configs(run_configs, **kwargs):
    # fix undefined param
    logger.info("Extracting run configs: %s", run_configs)
    run_configs["dt_from"] = str(dt_from)
    run_configs["dt_to"] = str(dt_to)
    run_configs["scoring_month"] = None
    run_configs["run_mode"] = run_mode
    run_configs["skip_dags"] = ""
    run_configs["overwrite"] = overwrite

    logger.info("Run configs after extraction: %s", run_configs)
    kwargs["ti"].xcom_push(key="run_configs", value=run_configs)


def _load_features_config() -> list[dict]:
    """Đọc danh sách feature từ src/config/features.yaml.

    Đọc trực tiếp bằng yaml (không import package src.*) để không phụ thuộc
    vào PYTHONPATH của repo lúc Airflow parse DAG file.
    """
    features_config_path = (
        pathlib.Path(__file__).parent / "src" / "config" / "features.yaml"
    )
    with features_config_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config["features"]


def _load_feature_names() -> list[str]:
    return [feature["name"] for feature in _load_features_config()]


def _load_day_features() -> list[str]:
    """Danh sách day_feature duy nhất (giai đoạn ngày).

    Nhiều rule instance (name) có thể dùng chung 1 day_feature (ví dụ
    order_l3m/order_l6m dùng chung "order") nên chỉ cần chạy 1 task/day_feature.
    """
    seen = []
    for feature in _load_features_config():
        if feature["day_feature"] not in seen:
            seen.append(feature["day_feature"])
    return seen


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
                "scoring_month": "{{ dag_run.conf.get('scoring_month', None) }}",
                "run_mode": "{{ dag_run.conf.get('run_mode', run_mode) }}",
                "skip_dags": "{{ dag_run.conf.get('skip_dags', '') }}",
                "overwrite": "{{ dag_run.conf.get('overwrite', overwrite) }}",
            }
        },
    )

    update_code = PythonOperator(
        task_id="update_code", python_callable=update_repo
    )

    # Giai đoạn ngày: mỗi day_feature tự đọc raw từng ngày trong
    # [dt_from, dt_to] từ MinIO, tự làm sạch, tự lưu — chạy song song,
    # độc lập nhau.
    day_arg = "--dt_from {{ params.dt_from }} --dt_to {{ params.dt_to }}"
    run_feature_days = BashOperator.partial(
        task_id="run_feature_day",
        retries=2,
    ).expand(
        bash_command=[
            (
                "export PYTHONPATH=/opt/airflow/dags/vtp:${PYTHONPATH}; "
                "python /opt/airflow/dags/vtp/src/data_processing/run.py "
                f"--mode feature_day --day_feature {day_feature} {day_arg}"
            )
            for day_feature in _load_day_features()
        ]
    )

    # Giai đoạn tháng (có window): với mỗi ngày-đầu-tháng rơi trong
    # [dt_from, dt_to], tự tính cho tháng liền trước (run_feature_range tự
    # tìm — xem _months_to_score trong run.py). Đa số ngày trong tháng sẽ
    # không có tháng nào cần tính (no-op).
    run_features = BashOperator.partial(
        task_id="run_feature",
        retries=2,
    ).expand(
        bash_command=[
            (
                "export PYTHONPATH=/opt/airflow/dags/vtp:${PYTHONPATH}; "
                "python /opt/airflow/dags/vtp/src/data_processing/run.py "
                f"--mode feature --feature_name {feature_name} {day_arg}"
            )
            for feature_name in _load_feature_names()
        ]
    )

    # Ghép kết quả tất cả feature lại theo cus_id cho MỌI tháng cần tính
    # trong [dt_from, dt_to] (danh sách tháng giống run_feature ở trên) —
    # chỉ 1 task (không song song theo feature, vì cần đợi TẤT CẢ feature
    # của tháng đó xong trước khi ghép).
    merge_months = BashOperator(
        task_id="merge_months",
        bash_command=(
            "export PYTHONPATH=/opt/airflow/dags/vtp:${PYTHONPATH}; "
            "python /opt/airflow/dags/vtp/src/data_processing/run.py "
            f"--mode merge {day_arg}"
        ),
    )

    # Define dependencies
    (
        start_node
        >> extract_config
        >> run_feature_days
        >> run_features
        >> merge_months
        >> end_node
    )
