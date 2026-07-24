from __future__ import annotations

import pandas as pd
import ast

from src.utils.common import month_date_range
from src.utils.minio_client import (
    save_to_minio,
    extract_data_by_date,
)

# Giới hạn timestamp hợp lệ, ví dụ: 1e12 tương ứng với ngày 1/1/2050
MAX_TIMESTAMP = 1e12


def transform_age_by_day(
    date: str,
    day_prefix: str,
    raw_day_prefix: str,
    day_partition_key: str,
) -> pd.DataFrame:
    """Giai đoạn ngày: đọc raw ngày `date` từ MinIO, tính tuổi từ ngày sinh,
    lưu xuống {day_prefix}/daily/date={date}/

    -> trả về dữ liệu ngày đã làm sạch, 2 cột: cus_id, age_years
    """
    # 1, Đọc dữ liệu raw theo ngày
    raw_df = extract_data_by_date(
        date, prefix=raw_day_prefix, day_partition_key=day_partition_key
    )

    # 2, Làm sạch dữ liệu: chỉ giữ cus_id, ngay_sinh; bỏ dòng cus_id null;
    #    tính tuổi (age_years) từ ngày sinh
    clean_df = raw_df[["cus_id", "ngay_sinh"]].copy()
    clean_df = clean_df.dropna(subset=["cus_id"])
    # Chuẩn hóa cus_id
    clean_df["cus_id"] = clean_df["cus_id"].apply(
    lambda x: ast.literal_eval(x).get("member0")
    if isinstance(x, str) and x.startswith("{")
    else (x.get("member0") if isinstance(x, dict) else x)
)
    clean_df["cus_id"] = (
    clean_df["cus_id"]
    .astype(float)
    .astype(int)
    .astype(str)
)
    dob = pd.to_numeric(clean_df["ngay_sinh"], errors="coerce")
    dob = dob.apply(lambda x: x if x < MAX_TIMESTAMP else None)
    dob = pd.to_datetime(dob, unit="ms", errors="coerce")

    ref_date  = pd.to_datetime(date)
    clean_df["age_years"] = (ref_date - dob).dt.days / 365.25
    clean_df = clean_df[["cus_id", "age_years"]]

    # 3, Lưu dữ liệu đã làm sạch xuống MinIO
    save_to_minio(
        clean_df,
        object_name=f"{day_prefix}/{day_partition_key}={date}/data.parquet",
    )
    return clean_df


def transform_age_latest(
    month: str,
    day_prefix: str,
    month_prefix: str,
    day_partition_key: str,
    month_partition_key: str,
) -> pd.DataFrame:

    # lấy ngày cuối tháng
    latest_date = month_date_range(month)[1]

    # đọc snapshot age mới nhất
    day_df = extract_data_by_date(
        latest_date,
        prefix=day_prefix,
        day_partition_key=day_partition_key,
    )

    # output feature
    result_df = day_df[
        [
            "cus_id",
            "age_years"
        ]
    ].rename(
        columns={
            "age_years": "nam_tuoi"
        }
    )

    save_to_minio(
        result_df,
        object_name=f"{month_prefix}/{month_partition_key}={month}/data.parquet",
    )


    return result_df