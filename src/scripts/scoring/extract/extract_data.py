import pandas as pd
from src.scripts.utils.minio_client import get_minio_config


def extract_scoring_data(scoring_month):
    """
    Lấy dữ liệu scoring
    -> trả về dữ liệu scoring
    """
    
    # Rule base cần dữ liệu ít nhất 12 tháng trước thời điểm scoringƯ
    scoring_date = pd.to_datetime(scoring_month + "01")
    
    start_date = scoring_date - pd.DateOffset(months=12)   
    end_date = scoring_date - pd.DateOffset(months=1)
    
    # Đổi lại dữ liệu để filter
    start_date = int(start_date.strftime("%Y%m"))
    end_date = int(end_date.strftime("%Y%m"))

    print(f"Xét dữ liệu từ tháng {start_date} đến tháng {end_date}")

    bucket_name, minio_endpoint, access_key, secret_key = get_minio_config()
    
    df = pd.read_parquet(
        f"s3://{bucket_name}/groupby_data/",
        engine="pyarrow",
        filters=[("month", ">=", start_date), ("month", "<=", end_date)],
        storage_options={
            "endpoint_url": f"http://{minio_endpoint}",
            "key": access_key,
            "secret": secret_key,
        }
    )

    return df