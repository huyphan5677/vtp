from __future__ import annotations

import io

import boto3
import pandas as pd
import pickle

from botocore.exceptions import ClientError
from src.utils.common import load_config


def get_minio_config() -> tuple[str, str, str, str]:
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


def get_minio_client() -> boto3.client:
    """Tạo kết nối đến MinIO server."""
    _, minio_endpoint, access_key, secret_key = get_minio_config()

    return boto3.client(
        "s3",
        endpoint_url=f"http://{minio_endpoint}",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
    )


def save_to_minio(df: pd.DataFrame, object_name: str) -> bool:
    """Lưu DataFrame lên MinIO dưới dạng parquet.

    Args:
        df: DataFrame cần upload.
        object_name: Đường dẫn đầy đủ (prefix + tên file) trên MinIO, ví dụ
            "clean/order/day/partition_date=20251201/data.parquet".

    Returns:
        bool: True nếu upload thành công.

    Raises:
        Exception: Nếu có lỗi khi upload dữ liệu lên MinIO.
    """
    try:
        bucket_name, _, _, _ = get_minio_config()
        client = get_minio_client()

        try:
            client.head_bucket(Bucket=bucket_name)
        except Exception:
            client.create_bucket(Bucket=bucket_name)
            print(f"Đã tạo bucket: {bucket_name}")

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


def read_minio_parquet(
    prefix: str, filters: list | None = None
) -> pd.DataFrame:
    """Đọc parquet từ MinIO theo prefix (tự thêm bucket + credentials).

    Args:
        prefix: Thư mục (không tính bucket) chứa dữ liệu, ví dụ
            "raw/hitech_day/partition_date=20251201" hoặc "clean/order/day".
        filters: Pyarrow filters (ví dụ lọc theo cột partition).
    """
    bucket_name, minio_endpoint, access_key, secret_key = get_minio_config()

    return pd.read_parquet(
        f"s3://{bucket_name}/{prefix}/",
        engine="pyarrow",
        filters=filters,
        storage_options={
            "endpoint_url": f"http://{minio_endpoint}",
            "key": access_key,
            "secret": secret_key,
        },
    )


def extract_data_by_date(
    date: str, prefix: str, day_partition_key: str
) -> pd.DataFrame:
    """Lấy dữ liệu raw của 1 ngày từ MinIO.

    Args:
        date: Ngày cần lấy, định dạng 'YYYYMMDD'.
        prefix: Thư mục (không tính bucket) chứa dữ liệu theo ngày.
        day_partition_key: Tên cột partition theo ngày trong đường dẫn.

    -> trả về dữ liệu ngày `date`
    """
    return read_minio_parquet(f"{prefix}/{day_partition_key}={date}")


def extract_data_by_range(
    start_date: str, end_date: str, prefix: str, day_partition_key: str
) -> pd.DataFrame:
    """Lấy dữ liệu (ghi theo day_partition_key=YYYYMMDD) trong 1 khoảng ngày.

    Args:
        start_date: Ngày bắt đầu, định dạng 'YYYYMMDD'.
        end_date: Ngày kết thúc, định dạng 'YYYYMMDD'.
        prefix: Thư mục (không tính bucket) chứa dữ liệu, ví dụ
            "hitech_day" hoặc "clean/order/day".
        day_partition_key: Tên cột partition theo ngày trong đường dẫn.

    -> trả về dữ liệu được lấy từ file parquet trong khoảng ngày đó
    """
    filters = [
        (day_partition_key, ">=", int(start_date)),
        (day_partition_key, "<=", int(end_date)),
    ]
    return read_minio_parquet(prefix, filters=filters)


def object_exists(object_name: str) -> bool:
    """Kiểm tra object có tồn tại trên MinIO hay không."""
    bucket_name, _, _, _ = get_minio_config()
    client = get_minio_client()

    try:
        client.head_object(Bucket=bucket_name, Key=object_name)
        return True
    except ClientError:
        return False


def save_artifact(obj, object_name: str) -> None:
    """Lưu artifact (pickle) lên MinIO."""
    bucket_name, _, _, _ = get_minio_config()
    client = get_minio_client()

    buffer = io.BytesIO()
    pickle.dump(obj, buffer)
    buffer.seek(0)

    client.put_object(
        Bucket=bucket_name,
        Key=object_name,
        Body=buffer,
    )


def load_artifact(object_name: str):
    """Đọc artifact (pickle) từ MinIO."""
    bucket_name, _, _, _ = get_minio_config()
    client = get_minio_client()

    obj = client.get_object(
        Bucket=bucket_name,
        Key=object_name,
    )

    return pickle.load(obj["Body"])