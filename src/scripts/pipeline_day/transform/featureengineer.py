import pandas as pd


def feature_engineering_date_of_birth(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """
    Xử lý ngày sinh:
    - Thêm cột 'dob' (ngày sinh dạng datetime)
    - Thêm cột 'age_years' (tuổi tính từ ngày sinh)
    
    Parameters:
    df (pd.DataFrame): DataFrame chứa dữ liệu
    column_name (str): Tên cột chứa dữ liệu ngày sinh dạng timestamp
    
    Returns:
    pd.DataFrame: DataFrame đã thêm các cột 'dob' và 'age_years'
    """
    # Giới hạn timestamp hợp lệ, ví dụ: 1e12 tương ứng với ngày 1/1/2050
    MAX_TIMESTAMP = 1e12

    # Chuyển đổi giá trị trong cột thành numeric
    df["dob"] = pd.to_numeric(df[column_name], errors="coerce")
    
    # Loại bỏ những giá trị vượt quá giới hạn timestamp hợp lệ và gán NaN
    df["dob"] = df["dob"].apply(lambda x: x if x < MAX_TIMESTAMP else None)
    
    # Chuyển đổi timestamp thành datetime
    df["dob"] = pd.to_datetime(df["dob"], unit="ms", errors="coerce")
    
    # Tính tuổi (tính theo năm với năm nhuận)
    today = pd.Timestamp.today()
    df["age_years"] = ((today - df["dob"]).dt.days / 365.25)
    
    return df

def feature_engineering_usage_duration(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """
    Xử lý thời gian hợp tác
    -> df có thêm cột: usage_duration_months
    """
    today = pd.Timestamp.today()
    df["usage_duration_months"] = ((today - df[column_name]).dt.days / 30)
    return df

def main_feature_engineering_day(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pipeline xử lý đặc trưng ngày
    -> trả về dữ liệu đặc trưng ngày được xử lý
    """
    df = feature_engineering_date_of_birth(df, "ngay_sinh")
    df = feature_engineering_usage_duration(df, "ngay_hoptac")
    return df