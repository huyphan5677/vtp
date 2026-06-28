from __future__ import annotations

import pandas as pd

from src.utils.minio_client import get_minio_config


def export_data_by_month(df, month) -> None:
    """Xuất dữ liệu groupby theo tháng.

    -> trả về dữ liệu đã được xuất ra
    """
    bucket_name, minio_endpoint, access_key, secret_key = get_minio_config()
    df.to_parquet(
        f"s3://{bucket_name}/groupby_data/month={month}/data_hitech_month.parquet",
        engine="pyarrow",
        storage_options={
            "endpoint_url": f"http://{minio_endpoint}",
            "key": access_key,
            "secret": secret_key,
        },
    )
    print(
        f"Dữ liệu đã được xuất ra s3://{bucket_name}/groupby_data/month={month}/data_hitech_month.parquet"
    )


def group_data_by_month(df) -> pd.DataFrame:
    """Groupby dữ liệu theo tháng.

    -> trả về dữ liệu đã được groupby
    """
    temp_df = df.copy()
    month = str(temp_df["partition_date"].iloc[0])[:6]
    print(f"Bắt đầu xử lý dữ liệu cho tháng {month}")
    groupby_data = (
        temp_df
        .groupby(["cus_id", "ma_tinh_hoatdong_chinh"])
        .agg({
            "tong_tien": "sum",
            "don_ptc": "sum",
            "age_years": "max",
            "usage_duration_months": "max",
            "thuho_tongdon": "sum",
            "don_ptc_cod": "sum",
            # "tong_cuoc_ptc":"sum",
            "tongdon_cod": "sum",
            "thu_ho": "sum",
            "tong_don": "sum",
        })
        .reset_index()
    )
    groupby_data = groupby_data.rename(
        columns={
            "age_years": "nam_tuoi",
            "usage_duration_months": "so_thang_hdong",
        }
    )

    export_data_by_month(groupby_data, month)
    return groupby_data
