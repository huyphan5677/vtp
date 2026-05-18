from src.scripts.utils.minio_client import get_minio_client
from src.scripts.utils.load_config import load_config
import pandas as pd
import io


def load_clean_data_to_minio(folder_name: str, date: str, data: pd.DataFrame):
    """
    Xuất dữ liệu đã xử lý ra MinIO dưới dạng parquet
    
    Args:
        folder_name: Tên thư mục lưu trữ dữ liệu (ví dụ: hitech_day, hitech_month, groupby_data)
        date: Ngày dữ liệu (format: YYYY-MM-DD)
        data: DataFrame chứa dữ liệu đã xử lý
    """
    config = load_config("connect.yaml")
    minio_config = config.get("minio", {})
    bucket_name = minio_config.get("bucket", "clean")
    
    client = get_minio_client()
    
    try:
        client.head_bucket(Bucket=bucket_name)
    except:
        client.create_bucket(Bucket=bucket_name)
    
    parquet_buffer = io.BytesIO()
    data.to_parquet(parquet_buffer, index=False)
    parquet_buffer.seek(0)
    
    object_name = f"{folder_name}/partition_date={date}/data_hitech_day_processed.parquet"
    
    client.put_object(
        Bucket=bucket_name,
        Key=object_name,
        Body=parquet_buffer,
        ContentType="application/octet-stream"
    )
    
    # print(client.list_buckets())

