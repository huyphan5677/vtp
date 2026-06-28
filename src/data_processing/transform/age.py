from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils.common import with_config


def feature_engineering_date_of_birth(
    df: pd.DataFrame, column_name: str
) -> pd.DataFrame:
    """Xử lý ngày sinh.

    -> Thêm cột 'dob' (ngày sinh dạng datetime)
    -> Thêm cột 'age_years' (tuổi tính từ ngày sinh)

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
    df["age_years"] = (today - df["dob"]).dt.days / 365.25

    return df


@with_config("rules.yaml")
def transform_nam_tuoi(
    df: pd.DataFrame, column_name: str, config=None
) -> pd.DataFrame:
    """Xử lý cột nam_tuoi.

    -> trả về bảng age với 2 cột: cus_id và age
    """
    # Đọc config
    age_rule = config.get("age", {})
    min_age = age_rule.get("min")
    max_age = age_rule.get("max")

    # Lấy max nam_tuoi
    df_age = df.groupby("cus_id").agg({column_name: "max"}).reset_index()

    # Binning
    df_age["age"] = np.where(
        (df_age[column_name] >= min_age) & (df_age[column_name] <= max_age),
        1,
        0,
    )
    return df_age[["cus_id", "age"]]
