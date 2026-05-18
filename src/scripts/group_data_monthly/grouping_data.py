import sys
from datetime import datetime
import pandas as pd
from src.scripts.utils.load_config import load_config
from src.config.data_path import CONFIG_PATH
from src.scripts.utils.minio_client import get_minio_config
from src.scripts.utils import common as utils
from loguru import logger


def extract_data_by_date(start_date, end_date):
    """
    Lấy dữ liệu từ file parquet
    -> trả về dữ liệu được lấy từ file parquet
    """
    start_date = int(start_date)
    end_date = int(end_date)

    filters = []
    if start_date:
        filters.append(("partition_date", ">=", start_date))
    if end_date:
        filters.append(("partition_date", "<=", end_date))

    bucket_name, minio_endpoint, access_key, secret_key = get_minio_config()
    
    df = pd.read_parquet(
        f"s3://{bucket_name}/hitech_day/",
        engine="pyarrow",
        filters=filters,
        storage_options={
            "endpoint_url": f"http://{minio_endpoint}",
            "key": access_key,
            "secret": secret_key,
        }
    )

    return df

def export_data_by_month(df, month):
    """
    Xuất dữ liệu groupby theo tháng
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
        }
    )
    print(f"Dữ liệu đã được xuất ra s3://{bucket_name}/groupby_data/month={month}/data_hitech_month.parquet")

# Hàm thực thi chính
def group_data_by_month(df):
    """
    Groupby dữ liệu theo tháng
    -> trả về dữ liệu đã được groupby
    """
    
    temp_df = df.copy()
    month = str(temp_df["partition_date"].iloc[0])[:6]
    print(month)
    groupby_data = temp_df.groupby(["cus_id", "ma_tinh_hoatdong_chinh"]).agg({
        "tong_tien": "sum",
        "don_ptc": "sum",
        "age_years":"max",
        "usage_duration_months":"max",
        "thuho_tongdon":"sum",
        "don_ptc_cod":"sum",
        # "tong_cuoc_ptc":"sum",
        "tongdon_cod":"sum",
        "thu_ho": "sum",
        "tong_don": "sum",
    }).reset_index()
    groupby_data = groupby_data.rename(columns={"age_years":"nam_tuoi", "usage_duration_months":"so_thang_hdong"})
                
    export_data_by_month(groupby_data, month)
    return groupby_data

if __name__ == "__main__":
    # get arguments
    args_string = " ".join(sys.argv[1:])
    args = utils.process_args_to_dict(args_string)
    start_date = args["dt_from"]
    end_date = args["dt_to"]

    logger.info(f"Start grouping data from {start_date} to {end_date}")

    df = extract_data_by_date(start_date, end_date)
    group_data_by_month(df)