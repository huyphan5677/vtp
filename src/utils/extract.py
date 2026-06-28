from __future__ import annotations

import pandas as pd

from src.config.data_path import DAY_DIR_PATH
from src.utils.minio_client import get_minio_config


def extract_day_data(date: str) -> pd.DataFrame:
    """Lấy dữ liệu ngày từ file parquet local.

    -> trả về dữ liệu ngày được lấy từ file parquet

    Raises:
        ValueError: Nếu ngày tháng không hợp lệ
    """
    if date is None:
        raise ValueError("Ngày tháng là bắt buộc trong cấu hình")

    try:
        data = pd.read_parquet(f"{DAY_DIR_PATH}/partition={date}")
    except:
        data = pd.read_parquet(f"{DAY_DIR_PATH}/{date}")

    return data


def extract_data_by_date(start_date, end_date) -> pd.DataFrame:
    """Lấy dữ liệu từ file parquet.

    -> trả về dữ liệu được lấy từ file parquet
    """
    start_date = int(start_date)
    end_date = int(end_date)

    filters = []
    if start_date:
        filters.append(("partition_date", ">=", start_date))
    if end_date:
        filters.append(("partition_date", "<=", end_date))

    bucket_name, minio_endpoint, access_key, secret_key = get_minio_config()

    df = pd.read_parquet(
        f"s3://{bucket_name}/hitech_day/",
        engine="pyarrow",
        filters=filters,
        storage_options={
            "endpoint_url": f"http://{minio_endpoint}",
            "key": access_key,
            "secret": secret_key,
        },
    )

    return df


def extract_scoring_data(scoring_month: str) -> pd.DataFrame:
    """Lấy dữ liệu scoring từ minio.

    -> trả về dữ liệu scoring

    Notes: Cần dữ liệu ít nhất 12 tháng trước thời điểm scoring
    """
    # Rule base cần dữ liệu ít nhất 12 tháng trước thời điểm scoring
    scoring_date = pd.to_datetime(scoring_month + "01")

    start_date = scoring_date - pd.DateOffset(months=12)
    end_date = scoring_date - pd.DateOffset(months=1)

    # Đổi lại dữ liệu để filter
    start_date_int = int(start_date.strftime("%Y%m"))
    end_date_int = int(end_date.strftime("%Y%m"))

    print(f"Xét dữ liệu từ tháng {start_date_int} đến tháng {end_date_int}")
    bucket_name, minio_endpoint, access_key, secret_key = get_minio_config()
    df = pd.read_parquet(
        f"s3://{bucket_name}/groupby_data/",
        engine="pyarrow",
        filters=[
            ("month", ">=", start_date_int),
            ("month", "<=", end_date_int),
        ],
        storage_options={
            "endpoint_url": f"http://{minio_endpoint}",
            "key": access_key,
            "secret": secret_key,
        },
    )

    return df
