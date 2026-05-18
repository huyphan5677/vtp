import io
import pandas as pd
from datetime import datetime
from src.scripts.utils.minio_client import get_minio_client, get_minio_config


def load_data_to_minio(df: pd.DataFrame, object_name: str = None, scoring_month: str = None) -> bool:
    """
    Load DataFrame lên MinIO server
    
    Args:
        df: DataFrame cần upload
        object_name: Tên file trên MinIO (nếu không truyền sẽ tự sinh theo timestamp)
        scoring_month: Tháng scoring để đặt tên file (nếu không truyền sẽ dùng timestamp)
    
    Returns:
        bool: True nếu upload thành công, False nếu thất bại
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
            ContentType="application/octet-stream"
        )
        
        print(f"Đã upload thành công {len(df)} records lên MinIO: {bucket_name}/{object_name}")
        return True
        
    except Exception as e:
        print(f"Lỗi khi upload dữ liệu lên MinIO: {e}")
        raise Exception(f"Lỗi khi upload dữ liệu lên MinIO: {e}")
