from __future__ import annotations

import pandas as pd

from src.utils.common import month_date_range
from src.utils.minio_client import (
    save_to_minio,
    extract_data_by_date,
    extract_data_by_range,
)


def transform_sales_region_by_day(
    date: str,
    day_prefix: str,
    raw_day_prefix: str,
    day_partition_key: str,
) -> pd.DataFrame:
    """Giai đoạn ngày: đọc raw ngày `date` từ MinIO, chuẩn bị input cho rule
    sales_region, lưu xuống `day_prefix`/`day_partition_key`={date}/.

    day_prefix, raw_day_prefix, day_partition_key đều lấy từ features.yaml.

    -> trả về dữ liệu ngày đã làm sạch, 2 cột: cus_id, sale_region
    """
    raw_df = extract_data_by_date(
        date, prefix=raw_day_prefix, day_partition_key=day_partition_key
    )

    clean_df = raw_df[["cus_id", "ma_tinh_hoatdong_chinh"]].copy()
    clean_df = clean_df.rename(columns={"ma_tinh_hoatdong_chinh": "sale_region"})
    clean_df = clean_df.dropna(subset=["cus_id"])
    clean_df["cus_id"] = (
    clean_df["cus_id"].dropna()
    .apply(lambda x: x.get("member0") if isinstance(x, dict) else x)
    .astype(str)
)

    save_to_minio(
        clean_df,
        object_name=f"{day_prefix}/{day_partition_key}={date}/data.parquet",
    )
    return clean_df


def transform_sales_region_lxm(
    month: str,
    months_window: int,
    day_prefix: str,
    month_prefix: str,
    day_partition_key: str,
    month_partition_key: str
) -> pd.DataFrame:
    """Giai đoạn tháng (có window): tự load `months_window` tháng dữ liệu
    ngày đã clean (`day_prefix`), lấy bản ghi cuối cùng theo cus_id,
    tạo signal `sales_region_value` cho tỉnh hợp lệ, rồi tự lưu xuống
    `month_prefix`.

    -> trả về bảng gồm cus_id, f_sale_region_l{months_window}m
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

    region_df = day_df[["cus_id", day_partition_key, "sale_region"]].copy()
    region_df["sale_region"] = region_df["sale_region"].astype(str)

    # Lấy bản ghi mới nhất
    result_df = (
        region_df
        .sort_values(day_partition_key, ascending=False)
        .groupby("cus_id", as_index=False)
        .first()
    )

    region_col = f"f_sale_region_l{months_window}m"

    result_df = result_df[["cus_id", region_col]]


    save_to_minio(
        result_df,
        object_name=f"{month_prefix}/{month_partition_key}={month}/data.parquet",
    )
    return result_df
