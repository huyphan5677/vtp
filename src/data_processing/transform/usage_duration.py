from __future__ import annotations

import pandas as pd
import ast

from src.utils.common import month_date_range
from src.utils.minio_client import (
    save_to_minio,
    extract_data_by_date,
)

def transform_usage_duration_by_day(
    date: str,
    day_prefix: str,
    raw_day_prefix: str,
    day_partition_key: str,
) -> pd.DataFrame:
    """Giai đoạn ngày: đọc raw ngày `date` từ MinIO, chuẩn bị input cho rule
    usage_duration, lưu xuống `day_prefix`/`day_partition_key`={date}/.

    -> trả về dữ liệu ngày đã làm sạch, 2 cột: cus_id, usage_months
    """
    raw_df = extract_data_by_date(
        date, prefix=raw_day_prefix, day_partition_key=day_partition_key
    )

    clean_df = raw_df[["cus_id", "ngay_hoptac"]].copy()
    clean_df = clean_df.dropna(subset=["cus_id"])
    clean_df = clean_df.dropna(subset=["ngay_hoptac"])
    clean_df["cus_id"] = clean_df["cus_id"].apply(
    lambda x: ast.literal_eval(x).get("member0")
    if isinstance(x, str) and x.startswith("{")
    else (x.get("member0") if isinstance(x, dict) else x))

    clean_df["cus_id"] = (
    clean_df["cus_id"]
    .astype(float)
    .astype(int)
    .astype(str))

    # =================
    # usage_months
    # =================
    hop_tac = pd.to_datetime(clean_df["ngay_hoptac"],format="%d/%m/%Y",errors="coerce")
    today = pd.Timestamp.today()

    clean_df["usage_months"] = ((today - hop_tac).dt.days / 30.44)

    clean_df = clean_df[["cus_id","usage_months"]]


    save_to_minio(
        clean_df,
        object_name=f"{day_prefix}/{day_partition_key}={date}/data.parquet",
    )
    return clean_df


def transform_usage_latest(
    month: str,
    day_prefix: str,
    month_prefix: str,
    day_partition_key: str,
    month_partition_key: str,
) -> pd.DataFrame:
    """
    Lấy usage hiện tại và nhóm thời gian hoạt động.

    Output:
        cus_id,
        f_usage_months,
        f_usage_duration_group
    """

    # 1. lấy ngày cuối tháng
    latest_date = month_date_range(month)[1]

    # 2. đọc snapshot cuối tháng
    day_df = extract_data_by_date(
        latest_date,
        prefix=day_prefix,
        day_partition_key=day_partition_key,
    )

    result_df = day_df[
        [
            "cus_id",
            "usage_months",
        ]
    ].copy()

    # rename feature
    result_df = result_df.rename(
        columns={
            "usage_months": "f_usage_months"
        }
    )

    # 3. tạo nhóm duration
    bins = [
        -float("inf"),
        4,
        6,
        12,
        18,
        float("inf"),
    ]

    labels = [
        "00",
        "01",
        "02",
        "03",
        "04",
    ]

    result_df["f_usage_duration_group"] = pd.cut(
        result_df["f_usage_months"],
        bins=bins,
        labels=labels,
        right=True,
    )

    # 4. lưu chung
    save_to_minio(
        result_df,
        object_name=f"{month_prefix}/{month_partition_key}={month}/data.parquet",
    )

    return result_df