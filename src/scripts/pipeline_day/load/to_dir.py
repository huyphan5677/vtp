from src.config.data_path import OUTPUT_DAY_DIR_PATH
import os
import pandas as pd

def load_clean_data_to_dir(date: str, data: pd.DataFrame):
    """
    Xử lý dữ liệu theo ngày,
    xuất ra file parquet dữ liệu được xử lý
    """
    # Tạo thư mục 
    output_dir = f"{OUTPUT_DAY_DIR_PATH}/partition_date={date}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Xuất dữ liệu ra file parquet
    data.to_parquet(f"{output_dir}/data_hitech_day_processed.parquet")
