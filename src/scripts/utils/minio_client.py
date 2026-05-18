import boto3
from src.scripts.utils.load_config import load_config

def get_minio_client():
    """
    Tạo kết nối đến MinIO server
    """
    config = load_config("connect.yaml")
        
    minio_config = config.get("minio", {})
    
    client = boto3.client(
        's3',
        endpoint_url=f"http://{minio_config.get('endpoint', 'localhost:9000')}",
        aws_access_key_id=minio_config.get("access_key"),
        aws_secret_access_key=minio_config.get("secret_key"),
        region_name='us-east-1'
    )
    
    return client

def get_minio_config():
    """
    Lấy cấu hình MinIO
    -> trả về cấu hình MinIO
    """
    try:
        config = load_config("connect.yaml")
        bucket_name = config.get("minio", {}).get("bucket", "clean")
        minio_endpoint = config.get("minio", {}).get("endpoint", "localhost:9000")
        access_key = config.get("minio", {}).get("access_key", "admin")
        secret_key = config.get("minio", {}).get("secret_key", "thethien8a")
        return bucket_name, minio_endpoint, access_key, secret_key
    except Exception as e:
        raise Exception(f"Lỗi khi lấy cấu hình MinIO: {e}")