import pandas as pd
from src.scripts.utils.parse_id import parse_cus_id

### Xử lý từng cột riêng lẻ
def preprocessing_date_of_birth(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """
    Xử lý ngày sinh của khách hàng
    -> trả về ngày sinh được làm sạch
    """
    # chuyển các số < 0 thành None
    df[column_name] = df[column_name].fillna("0").astype(int)
    df[column_name] = df[column_name].where(df[column_name] > 0, None)
    
    # # drop những dòng null trong cột ngay_sinh
    # df = df.dropna(subset=[column_name])
    
    return df

def clean_cus_id(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """
    Xử lý cột cus_id của khách hàng
    -> trả về cột cus_id được làm sạch
    """
    # chuyển cột cus_id từ string sang dict
    # df[column_name] = df[column_name].apply(parse_cus_id)
    
    # nếu không có dạng: {"member0": <value>, "member1": <value>} thì biến thành None
    # df[column_name] = df[column_name].apply(lambda x: x.get("member0") if isinstance(x, dict) else None)
    # df = df.dropna(subset=[column_name])
    
    # bỏ .0 ở cusid đi
    df[column_name] = df[column_name].astype(str)
        # .str.replace(r'\.0$', '', regex=True)
    
    return df

def preprocessing_usage_duration(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """
    Xử lý ngày hợp tác
    -> trả về ngày hợp tác được làm sạch
    """
    # drop những dòng null trong cột ngay_hoptac
    df = df.dropna(subset=[column_name])
    
    # chuyển cột ngay_hoptac từ string sang datetime dạng: ngày/tháng/năm
    df[column_name] = pd.to_datetime(df[column_name], format="%d/%m/%Y", errors="coerce")
    
    # với những dòng bị format không được, MCNA gợi ý chuyển dữ liệu này sang vùng lỗi
    # nhưng trước hết thì để đơn giản ở data mẫu, chúng tôi sẽ chỉ đơn giản xóa nó đi
    df = df.dropna(subset=[column_name])
    
    return df

def preprocessing_tong_tien(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """
    Xử lý số tiền đơn thành công (doanh thu merchant)
    -> trả về số tiền giao dịch được làm sạch
    """
    # drop những dòng null trong cột số tiền giao dịch
    df = df.dropna(subset=[column_name])

    df[column_name] = df[column_name].astype(float)    
    
    # # Bỏ những dòng có số tiền < 0 # nhung don nay la don hoan
    # df[column_name] = df[column_name].where(df[column_name] > 0, None)
     
    df = df.dropna(subset=[column_name])
    
    return df

def preprocessing_don_ptc(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """
    Xử lý số đơn thành công
    -> trả về số đơn thành công được làm sạch
    """
    # drop những dòng null trong cột số đơn thành công
    df = df.dropna(subset=[column_name])
    
    df[column_name] = df[column_name].astype(int)
    df[column_name] = df[column_name].where(df[column_name] > 0, None)
    
    df = df.dropna(subset=[column_name])
    return df

### Hàm chính sử dụng để xử lý các cột
def main_pipeline_day(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pipeline xử lý dữ liệu ngày
    -> trả về dữ liệu ngày được xử lý
    """
    df = clean_cus_id(df, "cus_id")
    df = preprocessing_date_of_birth(df, "ngay_sinh")
    df = preprocessing_usage_duration(df, "ngay_hoptac")
    # df = preprocessing_tong_tien(df, "tong_tien")
    df = preprocessing_don_ptc(df, "don_ptc")
    # df = preprocessing_don_ptc(df, "don_ptc_cod")
    # df = preprocessing_tong_tien(df, "tong_cuoc_ptc")
    
    return df