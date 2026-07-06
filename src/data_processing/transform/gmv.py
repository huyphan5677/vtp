from __future__ import annotations

import pandas as pd

from src.utils.common import month_date_range
from src.utils.minio_client import (
    save_to_minio,
    extract_data_by_date,
    extract_data_by_range,
)


def transform_gmv_by_day(
    date: str,
    day_prefix: str,
    raw_day_prefix: str,
    day_partition_key: str,
) -> pd.DataFrame:
    """Giai đoạn ngày: đọc raw ngày `date` từ MinIO, chuẩn bị data cho rule
    gmv, lưu xuống `day_prefix`/`day_partition_key`={date}/.

    day_prefix, raw_day_prefix, day_partition_key đều lấy từ features.yaml.

    -> trả về dữ liệu ngày đã làm sạch, các cột cần cho GMV
    """
    raw_df = extract_data_by_date(
        date, prefix=raw_day_prefix, day_partition_key=day_partition_key
    )

    clean_df = raw_df[
        [
            "cus_id",
            "don_ptc",
            "tong_tien",
            "thu_ho",
            "thuho_tongdon",
            "don_ptc_cod",
            "tongdon_cod",
            "tong_don",
        ]
    ].copy()
    clean_df = clean_df.dropna(subset=["cus_id"])
    clean_df["cus_id"] = clean_df["cus_id"].astype(str)
    clean_df["month"] = date[:6]

    save_to_minio(
        clean_df,
        object_name=f"{day_prefix}/{day_partition_key}={date}/data.parquet",
    )
    return clean_df


def transform_gmv_lxm(
    month: str,
    months_window: int,
    day_prefix: str,
    month_prefix: str,
    day_partition_key: str,
    month_partition_key: str,
) -> pd.DataFrame:
    """Giai đoạn tháng (có window): tự load `months_window` tháng dữ liệu
    ngày đã clean (`day_prefix`), ước tính GMV thô theo cus_id, tạo signal
    `gmv_score`, rồi tự lưu xuống `month_prefix`.

    Lưu ý: transform chỉ tạo signal, ngưỡng và điều kiện pass/fail sẽ được
    xử lý ở tầng filter sau.

    -> trả về bảng gồm cus_id, gmv_score
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

    day_df = day_df[
        [
            "cus_id",
            "month",
            "don_ptc",
            "tong_tien",
            "thu_ho",
            "thuho_tongdon",
            "don_ptc_cod",
            "tongdon_cod",
            "tong_don",
        ]
    ].copy()

    def _estimate_gmv(row: pd.Series) -> float:
        if (row["thu_ho"] > 0) or (row["thuho_tongdon"] > 0):
            avg_don = row["thu_ho"] / row["don_ptc_cod"] if row["don_ptc_cod"] > 0 else row["thu_ho"] / max(row["don_ptc"], 1)
            return row["don_ptc"] * avg_don
        if row["tong_don"] and row["tong_don"] > 0:
            return (row["don_ptc"] * row["tong_tien"] / row["tong_don"])
        return 0.0

    day_df["gmv_value"] = day_df.apply(_estimate_gmv, axis=1)
    result_df = (
        day_df.groupby("cus_id", as_index=False)["gmv_value"]
        .sum()
        .rename(columns={"gmv_value": "gmv_score"})
    )
    result_df["gmv_score"] = (result_df["gmv_score"] / 1_000_000).clip(lower=1, upper=9999)

    save_to_minio(
        result_df,
        object_name=f"{month_prefix}/{month_partition_key}={month}/data.parquet",
    )
    return result_df
