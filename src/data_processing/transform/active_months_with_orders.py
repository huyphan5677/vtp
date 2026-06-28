from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils.common import with_config


@with_config("rules.yaml")
def transform_total_success_order(
    df: pd.DataFrame, column_name: str, config=None
) -> pd.DataFrame:
    """Xử lý cột tong_tien.

    -> trả về bảng total_success_order với 3 cột: cus_id và total_success_order, score
    """
    temp_df = df.copy()
    temp_df["month"] = pd.to_datetime(
        temp_df["month"], format="%Y%m"
    ).dt.to_period("M")

    # Xác định khoảng thời gian đang xét trong data
    max_month = temp_df["month"].max()
    min_month = temp_df["month"].min()

    time_we_consider = int(
        config.get("total_success_order").get("min", 12)
    )  # Số tháng tối thiểu để xét tổng doanh thu

    min_month = max_month - time_we_consider + 1

    # Lọc dữ liệu trong khung thời gian ta xét
    valid_df = temp_df[temp_df["month"].between(min_month, max_month)].copy()
    df_total_success_order = (
        valid_df.groupby("cus_id").agg({column_name: "sum"}).reset_index()
    )

    df_total_success_order["score_4"] = np.round(
        (df_total_success_order[column_name] / 1000000).clip(1, 9999)
    ).astype(int)
    df_total_success_order["score_4"] = df_total_success_order["score_4"].apply(
        lambda x: f"{x:04d}"
    )
    return df_total_success_order[["cus_id", "score_4"]]
