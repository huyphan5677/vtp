from __future__ import annotations

import pandas as pd

from src.utils.common import month_date_range
from src.utils.minio_client import (
    save_to_minio,
    extract_data_by_date,
    extract_data_by_range,
)


def transform_usage_duration_by_day(
    date: str,
    day_prefix: str,
    raw_day_prefix: str,
    day_partition_key: str,
) -> pd.DataFrame:
    """Giai đoạn ngày: đọc raw ngày `date` từ MinIO, chuẩn bị input cho rule
    usage_duration, lưu xuống `day_prefix`/`day_partition_key`={date}/.

    -> trả về dữ liệu ngày đã làm sạch, 2 cột: cus_id, so_thang_hdong
    """
    raw_df = extract_data_by_date(
        date, prefix=raw_day_prefix, day_partition_key=day_partition_key
    )

    clean_df = raw_df[["cus_id", "ngay_hoptac"]].copy()
    clean_df = clean_df.dropna(subset=["cus_id"])
    clean_df["cus_id"] = (
        clean_df["cus_id"]
        .apply(
            lambda x:
            x.get("member0")
            if isinstance(x, dict)
            else x
        )
        .astype(str)
    )

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


def transform_usage_lxm(
    month: str,
    months_window: int,
    day_prefix: str,
    month_prefix: str,
    day_partition_key: str,
    month_partition_key: str,
) -> pd.DataFrame:


    start_month = (pd.Period(month, freq="M") - months_window + 1).strftime("%Y%m")

    start_date = month_date_range(start_month)[0]
    end_date = month_date_range(month)[1]


    day_df = extract_data_by_range(
        start_date,
        end_date,
        prefix=day_prefix,
        day_partition_key=day_partition_key,
    )

    usage_col = f"f_usage_duration_l{months_window}m"

    result_df = (
        day_df
        .groupby("cus_id")
        .agg(
            **{
                usage_col:
                (
                    "usage_months",
                    "max"
                )
            }
        )
        .reset_index()
    )


    save_to_minio(
        result_df,
        object_name=
        f"{month_prefix}/{month_partition_key}={month}/data.parquet",
    )

    return result_df

def transform_usage_duration_group_lxm(
    month: str,
    months_window: int,
    day_prefix: str,
    month_prefix: str,
    day_partition_key: str,
    month_partition_key: str,
) -> pd.DataFrame:
    start_month = (pd.Period(month, freq="M") - months_window + 1).strftime("%Y%m")

    start_date = month_date_range(start_month)[0]
    end_date = month_date_range(month)[1]

    day_df = extract_data_by_range(
        start_date,
        end_date,
        prefix=day_prefix,
        day_partition_key=day_partition_key,
    )

    usage_col = f"f_usage_duration_group_l{months_window}m"

    result_df = (
        day_df
        .groupby("cus_id")
        .agg(usage_months=("usage_months", "max"))
        .reset_index()
    )

    result_df["usage_months"] = result_df["usage_months"].astype(int)

    # Tạo nhãn nhóm theo bins
    bins = [-float("inf"), 4, 6, 12, 18, float("inf")]
    labels = ["00", "01", "02", "03", "04"]
    result_df[usage_col] = pd.cut(
        result_df["usage_months"], bins=bins, labels=labels, right=True
    )

    result_df = result_df[["cus_id", usage_col]]

    save_to_minio(
        result_df,
        object_name=f"{month_prefix}/{month_partition_key}={month}/data.parquet",
    )
    return result_df