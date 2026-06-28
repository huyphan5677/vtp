from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils.common import with_config


@with_config("rules.yaml")
def transform_success_order_all_months(
    df: pd.DataFrame, column_name: str, config=None
) -> pd.DataFrame:
    """Trong X tháng gần nhất, tháng nào cũng có đơn phát thành công (>=1).

    Args:
        df (pd.DataFrame): Bảng chứa dữ liệu giao dịch.
        column_name (str): Tên cột chứa doanh thu.
        config (dict): Config từ rules.yaml.

    Returns:
        pd.DataFrame: Bảng chứa dữ liệu.
    """
    rule_config = config.get("success_order_all_months", {})
    months_window = rule_config.get("months_window")

    temp_df = df.copy()
    temp_df["month"] = pd.to_datetime(temp_df["month"], format="%Y%m")
    temp_df["month"] = temp_df["month"].dt.to_period("M")

    max_month = temp_df["month"].max()
    min_month = max_month - months_window + 1

    print(f"Tính toán rule từ {min_month} đến {max_month}")

    # Filter X tháng gần nhất
    temp_df = temp_df[temp_df["month"].between(min_month, max_month)]

    # Mask: tháng có đơn thành công
    temp_df["has_success"] = temp_df[column_name] >= 1

    # Aggregate
    df_result = (
        temp_df
        .groupby("cus_id")
        .agg(
            all_months_have_success=(
                "has_success",
                "all",
            ),  # tất cả tháng đều True
            month_count=("month", "count"),  # số tháng có data
        )
        .reset_index()
    )

    # Rule: phải đủ tháng + tất cả đều có đơn
    df_result["success_order_all_months"] = np.where(
        (df_result["all_months_have_success"])
        & (df_result["month_count"] == months_window),
        1,
        0,
    )

    return df_result[["cus_id", "success_order_all_months"]]
