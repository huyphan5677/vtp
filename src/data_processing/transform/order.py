from __future__ import annotations

import pandas as pd

from src.utils.common import month_date_range
from src.utils.minio_client import (
    save_to_minio,
    extract_data_by_date,
    extract_data_by_range,
)


def transform_order_by_day(
    date: str,
    day_prefix: str,
    raw_day_prefix: str,
    day_partition_key: str,
) -> pd.DataFrame:
    """Giai đoạn ngày: đọc raw ngày `date` từ MinIO, làm sạch, lưu xuống
    `day_prefix`/`day_partition_key`={date}/.

    day_prefix, raw_day_prefix, day_partition_key đều lấy từ features.yaml.

    -> trả về dữ liệu ngày đã làm sạch, 3 cột: cus_id, count, value
    """
    # 1, Đọc dữ liệu raw theo ngày
    raw_df = extract_data_by_date(
        date, prefix=raw_day_prefix, day_partition_key=day_partition_key
    )

    # 2, Làm sạch dữ liệu: chỉ giữ cus_id, don_ptc, tong_tien; bỏ dòng cus_id null;
    #    đổi tên don_ptc -> count, tong_tien -> value
    clean_df = raw_df[["cus_id", "don_ptc", "tong_tien"]].copy()
    clean_df = clean_df.dropna(subset=["cus_id"])
    clean_df["cus_id"] = clean_df["cus_id"].astype(str)
    clean_df = clean_df.rename(
        columns={"don_ptc": "count", "tong_tien": "value"}
    )

    # 3, Lưu dữ liệu đã làm sạch xuống MinIO
    save_to_minio(
        clean_df,
        object_name=f"{day_prefix}/{day_partition_key}={date}/data.parquet",
    )
    return clean_df


def transform_order_lxm(
    month: str,
    months_window: int,
    min_count: float,
    min_value: float,
    day_prefix: str,
    month_prefix: str,
    day_partition_key: str,
    month_partition_key: str,
) -> pd.DataFrame:
    """Giai đoạn tháng (có window): tự load `months_window` tháng dữ liệu
    ngày đã clean (`day_prefix`), tính avg count/value theo cus_id, so với
    ngưỡng min_count/min_value, và tự lưu xuống `month_prefix`.

    Tất cả tham số đều lấy từ features.yaml.

    -> trả về bảng gồm cus_id, f_order_avg_count_l{N}m, f_order_avg_value_l{N}m,
       f_order_count_ok_l{N}m, f_order_value_ok_l{N}m
    """
    # 1, Xác định khoảng ngày cần load: từ đầu tháng (month - months_window + 1)
    #    đến cuối tháng (month)
    start_month = (pd.Period(month, freq="M") - months_window + 1).strftime(
        "%Y%m"
    )
    start_date = month_date_range(start_month)[0]
    end_date = month_date_range(month)[1]

    # 2, Load dữ liệu ngày đã clean
    day_df = extract_data_by_range(
        start_date,
        end_date,
        prefix=day_prefix,
        day_partition_key=day_partition_key,
    )
    day_df["month"] = day_df[day_partition_key].astype(str).str[:6].astype(int)

    # 3, Tính avg count/value theo cus_id, và đánh dấu đạt ngưỡng hay không
    count_col = f"f_order_avg_count_l{months_window}m"
    value_col = f"f_order_avg_value_l{months_window}m"
    count_ok_col = f"f_order_count_ok_l{months_window}m"
    value_ok_col = f"f_order_value_ok_l{months_window}m"

    result_df = (
        day_df
        .groupby("cus_id")
        .agg(
            **{count_col: ("count", "mean"), value_col: ("value", "mean")},
            active_months=("month", "nunique"),
        )
        .reset_index()
    )

    # Đạt ngưỡng chỉ khi >= min VÀ có đủ dữ liệu cả months_window tháng
    has_full_window = result_df["active_months"] == months_window
    result_df[count_ok_col] = (
        (result_df[count_col] >= min_count) & has_full_window
    ).astype(int)
    result_df[value_ok_col] = (
        (result_df[value_col] >= min_value) & has_full_window
    ).astype(int)

    # 4, Chỉ giữ các cột cần thiết
    result_df = result_df[
        ["cus_id", count_col, value_col, count_ok_col, value_ok_col]
    ]

    # 5, Lưu dữ liệu đã làm sạch xuống.
    save_to_minio(
        result_df,
        object_name=f"{month_prefix}/{month_partition_key}={month}/data.parquet",
    )
    return result_df
