from __future__ import annotations

import pandas as pd

from src.utils.common import month_date_range
from src.utils.minio_client import (
    save_to_minio,
    extract_data_by_date,
    extract_data_by_range,
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
    lưu xuống `day_prefix`/`day_partition_key`={date}/.

    day_prefix, raw_day_prefix, day_partition_key đều lấy từ features.yaml.

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
    clean_df["cus_id"] = clean_df["cus_id"].astype(str)

    dob = pd.to_numeric(clean_df["ngay_sinh"], errors="coerce")
    dob = dob.apply(lambda x: x if x < MAX_TIMESTAMP else None)
    dob = pd.to_datetime(dob, unit="ms", errors="coerce")

    today = pd.Timestamp.today()
    clean_df["age_years"] = (today - dob).dt.days / 365.25
    clean_df = clean_df[["cus_id", "age_years"]]

    # 3, Lưu dữ liệu đã làm sạch xuống MinIO
    save_to_minio(
        clean_df,
        object_name=f"{day_prefix}/{day_partition_key}={date}/data.parquet",
    )
    return clean_df


def transform_age_lxm(
    month: str,
    months_window: int,
    min_age: float,
    max_age: float,
    day_prefix: str,
    month_prefix: str,
    day_partition_key: str,
    month_partition_key: str,
) -> pd.DataFrame:
    """Giai đoạn tháng (có window): tự load `months_window` tháng dữ liệu
    ngày đã clean (`day_prefix`), lấy tuổi lớn nhất theo cus_id, so với
    khoảng [min_age, max_age], và tự lưu xuống `month_prefix`.

    Tất cả tham số đều lấy từ features.yaml.

    -> trả về bảng gồm cus_id, f_age_l{N}m, f_age_ok_l{N}m
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

    # 3, Lấy tuổi lớn nhất theo cus_id, đánh dấu có nằm trong khoảng hợp lệ
    age_col = f"f_age_l{months_window}m"
    age_ok_col = f"f_age_ok_l{months_window}m"

    result_df = (
        day_df
        .groupby("cus_id")
        .agg(**{age_col: ("age_years", "max")})
        .reset_index()
    )

    result_df[age_ok_col] = (
        (result_df[age_col] >= min_age) & (result_df[age_col] <= max_age)
    ).astype(int)

    # 4, Chỉ giữ các cột cần thiết
    result_df = result_df[["cus_id", age_col, age_ok_col]]

    # 5, Lưu dữ liệu đã làm sạch xuống.
    save_to_minio(
        result_df,
        object_name=f"{month_prefix}/{month_partition_key}={month}/data.parquet",
    )
    return result_df
