import os
from pathlib import Path

# dinh nghĩa thư mục gốc
ROOT_DIR = Path(__file__).parent.parent

# định nghĩa data nguồn
DAY_DIR_PATH = f"/opt/airflow/data/data_hitech_day"
# DAY_DIR_PATH = f"/data/ftpuser/data/ftpuser/data/data_hitech_day"

MONTH_DIR_PATH = f"/opt/airflow/dags/vtp/src/data/hitech_month"
# MONTH_DIR_PATH = f"/data/ftpuser/data/ftpuser/data/data_hitech_month"

# định nghĩa folder xuất ra
OUTPUT_DAY_DIR_PATH = f"{ROOT_DIR}/data/clean/hitech_day"
# OUTPUT_MONTH_DIR_PATH = f"{ROOT_DIR}/data/clean/hitech_month"

# định nghĩa folder nguồn
# định nghĩa folder xuất ra khi tính toán các chỉ số theo tháng
OUTPUT_GROUPBY_DIR_PATH = f"{ROOT_DIR}/data/clean/groupby_data"

# config path
CONFIG_PATH = f"{ROOT_DIR}/config"