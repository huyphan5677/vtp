from __future__ import annotations

import pandas as pd

from src.utils.common import month_date_range
from src.utils.minio_client import (
    save_to_minio,
    extract_data_by_date,
    extract_data_by_range,
)


def transform_success_order_by_day(
    date: str,
    day_prefix: str,
    raw_day_prefix: str,
    day_partition_key: str,
) -> pd.DataFrame:
    """Giai đoạn ngày: đọc raw ngày `date` từ MinIO, chuẩn bị input cho rule
    success_order_all_months, lưu xuống `day_prefix`/`day_partition_key`={date}/.

    day_prefix, raw_day_prefix, day_partition_key đều lấy từ features.yaml.

    -> trả về dữ liệu ngày đã làm sạch, 2 cột: cus_id, don_ptc
    """
    raw_df = extract_data_by_date(
        date, prefix=raw_day_prefix, day_partition_key=day_partition_key
    )

    clean_df = raw_df[["cus_id", "don_ptc"]].copy()
    clean_df = clean_df.dropna(subset=["cus_id"])
    clean_df["cus_id"] = clean_df["cus_id"].astype(str)
    clean_df["month"] = date[:6]

    save_to_minio(
        clean_df,
        object_name=f"{day_prefix}/{day_partition_key}={date}/data.parquet",
    )
    return clean_df


def transform_success_order_lxm(
    month: str,
    months_window: int,
    day_prefix: str,
    month_prefix: str,
    day_partition_key: str,
    month_partition_key: str,
) -> pd.DataFrame:
    """Giai đoạn tháng (có window): tự load `months_window` tháng dữ liệu
    ngày đã clean (`day_prefix`), lấy các tháng gần nhất theo cus_id,
    tạo các cột signal thô `success_order_1_month`, `success_order_2_month`,
    ... để tầng filter sau có thể đánh pass/fail.

    Lưu ý: transform chỉ tạo signal, ngưỡng/pattern sẽ được xử lý ở tầng
    filter sau.

    -> trả về bảng gồm cus_id và các cột signal theo từng tháng gần nhất
    """
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

    day_df = day_df[["cus_id", "month", "don_ptc"]].copy()
    day_df["don_ptc"] = pd.to_numeric(day_df["don_ptc"], errors="coerce")

    recent = day_df.sort_values(["cus_id", "month"], ascending=[True, True])

    result = []
    for _, customer in recent.groupby("cus_id"):
        months = customer["month"].astype(str).unique()[-months_window:]
        row = {"cus_id": customer["cus_id"].iloc[0]}
        for idx, m in enumerate(months, start=1):
            sub = customer[customer["month"].astype(str) == m]
            row[f"success_order_{idx}_month"] = int((sub["don_ptc"] >= 1).any())
        result.append(row)

    result_df = pd.DataFrame(result)

    save_to_minio(
        result_df,
        object_name=f"{month_prefix}/{month_partition_key}={month}/data.parquet",
    )
    return result_df
