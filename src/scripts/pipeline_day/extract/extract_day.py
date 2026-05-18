import pandas as pd
from src.config.data_path import DAY_DIR_PATH

def extract_day_data(date):
    """
    Lấy dữ liệu ngày từ file parquet
    -> trả về dữ liệu ngày được lấy từ file parquet
    """
    if date is None:
        raise ValueError("Ngày tháng là bắt buộc trong cấu hình")
    
    if not isinstance(date, str):
        date = str(date)
    
    try:
        data = pd.read_parquet(f"{DAY_DIR_PATH}/partition={date}")
    except:
        data = pd.read_parquet(f"{DAY_DIR_PATH}/{date}")

    return data
