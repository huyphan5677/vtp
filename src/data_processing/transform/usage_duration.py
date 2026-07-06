from __future__ import annotations

import pandas as pd

from src.utils.common import load_config, month_date_range
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

    day_prefix, raw_day_prefix, day_partition_key đều lấy từ features.yaml.

    -> trả về dữ liệu ngày đã làm sạch, 2 cột: cus_id, so_thang_hdong
    """
    raw_df = extract_data_by_date(
        date, prefix=raw_day_prefix, day_partition_key=day_partition_key
    )

    clean_df = raw_df[["cus_id", "so_thang_hdong"]].copy()
    clean_df = clean_df.dropna(subset=["cus_id"])
    clean_df["cus_id"] = clean_df["cus_id"].astype(str)
    clean_df["month"] = date[:6]

    save_to_minio(
        clean_df,
        object_name=f"{day_prefix}/{day_partition_key}={date}/data.parquet",
    )
    return clean_df


def transform_usage_duration_lxm(
    month: str,
    months_window: int,
    day_prefix: str,
    month_prefix: str,
    day_partition_key: str,
    month_partition_key: str,
) -> pd.DataFrame:
    """Giai đoạn tháng (có window): tự load `months_window` tháng dữ liệu
    ngày đã clean (`day_prefix`), lấy max `so_thang_hdong` theo cus_id,
    tạo signal thô `usage_duration_months` và `behavior_score`, rồi tự lưu
    xuống `month_prefix`.

    Lưu ý: transform chỉ tạo signal, ngưỡng sẽ được xử lý ở tầng filter sau.

    -> trả về bảng gồm cus_id, usage_duration_months, behavior_score
    """
    rules_cfg = load_config("rules.yaml")
    min_months = rules_cfg.get("usage_duration_months", {}).get("min", 4)

    start_month = (pd.Period(month, freq="M") - months_window + 1).strftime(
        "%Y%m"
    )
    start_date = month_date_range(start_month)[0]
    end_date = month_date_range(month)[1]

    day_df = extract_data_by_range(
        start_date,
        end_date,
        prefix=day_prefix,
        day_partition_key=day_partition_key,
    )

    result_df = (
        day_df.groupby("cus_id", as_index=False)["so_thang_hdong"]
        .max()
        .rename(columns={"so_thang_hdong": "usage_duration_months"})
    )

    result_df["behavior_score"] = result_df["usage_duration_months"].apply(
        lambda x: "00"
        if pd.isna(x) or x < min_months
        else "01"
        if x <= 6
        else "02"
        if x <= 12
        else "03"
        if x <= 18
        else "04"
    )

    save_to_minio(
        result_df,
        object_name=f"{month_prefix}/{month_partition_key}={month}/data.parquet",
    )
    return result_df
