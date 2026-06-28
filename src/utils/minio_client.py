from __future__ import annotations

import io
from datetime import datetime

import boto3
import pandas as pd
from src.utils.load_config import load_config


def get_minio_client() -> boto3.client:
    """Tạo kết nối đến MinIO server."""
    config = load_config("connect.yaml")

    minio_config = config.get("minio", {})

    client = boto3.client(
        "s3",
        endpoint_url=f"http://{minio_config.get('endpoint', 'localhost:9000')}",
        aws_access_key_id=minio_config.get("access_key"),
        aws_secret_access_key=minio_config.get("secret_key"),
        region_name="us-east-1",
    )

    return client


def get_minio_config():
    """Lấy cấu hình MinIO.

    -> trả về cấu hình MinIO

    Raises:
        Exception: Nếu có lỗi khi lấy cấu hình MinIO
    """
    try:
        config = load_config("connect.yaml")
        bucket_name = config.get("minio", {}).get("bucket", "clean")
        minio_endpoint = config.get("minio", {}).get(
            "endpoint", "localhost:9000"
        )
        access_key = config.get("minio", {}).get("access_key", "admin")
        secret_key = config.get("minio", {}).get("secret_key", "thethien8a")
        return bucket_name, minio_endpoint, access_key, secret_key
    except Exception as e:
        raise Exception(f"Lỗi khi lấy cấu hình MinIO: {e}")


def load_clean_data_to_minio(folder_name: str, date: str, data: pd.DataFrame):
    """Xuất dữ liệu đã xử lý ra MinIO dưới dạng parquet.

    Args:
        folder_name: Tên thư mục lưu trữ dữ liệu (ví dụ: hitech_day,
        hitech_month, groupby_data)
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

    object_name = (
        f"{folder_name}/partition_date={date}/data_hitech_day_processed.parquet"
    )

    client.put_object(
        Bucket=bucket_name,
        Key=object_name,
        Body=parquet_buffer,
        ContentType="application/octet-stream",
    )


def load_data_to_minio(
    df: pd.DataFrame, object_name: str = None, scoring_month: str = None
) -> bool:
    """Load DataFrame lên MinIO server.

    Args:
        df: DataFrame cần upload
        object_name: Tên file trên MinIO (nếu không truyền sẽ tự sinh theo timestamp)
        scoring_month: Tháng scoring để đặt tên file (nếu không truyền sẽ dùng timestamp)

    Returns:
        bool: True nếu upload thành công, False nếu thất bại

    Raises:
        Exception: Nếu có lỗi khi upload dữ liệu lên MinIO
    """
    try:
        bucket_name, _, _, _ = get_minio_config()

        client = get_minio_client()

        try:
            client.head_bucket(Bucket=bucket_name)
        except:
            client.create_bucket(Bucket=bucket_name)
            print(f"Đã tạo bucket: {bucket_name}")

        if object_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            object_name = f"scoring/month={scoring_month}/scoring_data_{timestamp}.parquet"

        buffer = io.BytesIO()
        df.to_parquet(buffer, index=False)
        buffer.seek(0)

        client.put_object(
            Bucket=bucket_name,
            Key=object_name,
            Body=buffer,
            ContentType="application/octet-stream",
        )

        print(
            f"Đã upload thành công {len(df)} records lên MinIO: {bucket_name}/{object_name}"
        )
        return True

    except Exception as e:
        print(f"Lỗi khi upload dữ liệu lên MinIO: {e}")
        raise Exception(f"Lỗi khi upload dữ liệu lên MinIO: {e}")
