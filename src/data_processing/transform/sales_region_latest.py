from __future__ import annotations

import pandas as pd

from src.utils.common import with_config


@with_config("rules.yaml")
def transform_sales_region(
    df: pd.DataFrame, column_name: str, config=None
) -> pd.DataFrame:
    """Xử lý cột sales_region.

    -> trả về bảng sales_region với 2 cột: cus_id và sales_region

    Args:
        df (pd.DataFrame): Bảng chứa dữ liệu giao dịch.
        column_name (str): Tên cột chứa doanh thu.
        config (dict): Config từ rules.yaml.

    Returns:
        pd.DataFrame: Bảng chứa dữ liệu.
    """
    sales_region_rule = config.get("sales_region", {})
    valid_sales_region = sales_region_rule.get("valid", [])

    temp_df = df.copy()
    temp_df["month"] = pd.to_datetime(temp_df["month"], format="%Y%m")
    temp_df["month"] = temp_df["month"].dt.to_period("M")

    # Lấy tháng cuối cùng được ghi nhận của mỗi khách hàng
    newest_month_per_cus = (
        temp_df.groupby("cus_id")["month"].max().reset_index()
    )
    newest_month_per_cus.columns = ["cus_id", "max_month"]

    # Merge để lấy sales_region ghi nhận tại tháng cuối cùng của mỗi khách hàng
    temp_df = temp_df.merge(newest_month_per_cus, on="cus_id")
    current_region_df = temp_df[temp_df["month"] == temp_df["max_month"]][
        ["cus_id", column_name]
    ].drop_duplicates()

    # Kiểm tra khu vực hiện tại có nằm trong danh sách hợp lệ không
    current_region_df["sales_region"] = (
        current_region_df[column_name].isin(valid_sales_region).astype(int)
    )

    # Group by cus_id để kiểm tra thuộc 1 trong 48 tỉnh là được
    result_df = (
        current_region_df.groupby("cus_id")["sales_region"].max().reset_index()
    )

    return result_df
