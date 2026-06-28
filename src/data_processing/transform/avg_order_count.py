from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils.bining import binning_data
from src.utils.common import with_config


@with_config("rules.yaml")
def transform_avg_success_order_count_per_month(
    df: pd.DataFrame, column_name: str, config=None
) -> pd.DataFrame:
    """Nhận vào cột don_ptc.

    -> trả về bảng avg_success_order_count_per_month với 3 cột: cus_id, month
    (đếm số tháng hđ),don_ptc (Trung bình) và avg_success_order_count_per_month
    """
    # Lấy config
    months_window = config.get("avg_success_order_count_per_month", {}).get(
        "months_window"
    )
    min_avg_success_order_count = config.get(
        "avg_success_order_count_per_month", {}
    ).get("min")

    # Đầu tiên cần lấy ra tháng cao nhất
    temp_df = df.copy()
    temp_df["month"] = pd.to_datetime(temp_df["month"], format="%Y%m")
    temp_df["month"] = temp_df["month"].dt.to_period("M")
    max_month = temp_df["month"].max()

    # Chỉ trích xuất X tháng gần nhất
    min_month = (
        max_month - months_window + 1
    )  # Phải cộng 1 vì như này: ví dụ tháng12 thì phải trích xuất 6 tháng gần
    # nhất từ tháng 7 đến tháng 12

    print(
        "Tính toán avg_success_order_count_per_month xét từ tháng",
        min_month,
        "đến tháng",
        max_month,
    )

    # Xét trong X tháng, số đơn hàng thành công trung bình/tháng >= Y
    # Lưu ý rằng: dữ liệu khách hàng phải đủ 6 tháng thì mới pass rule base
    df_avg_success_order_count = (
        temp_df[temp_df["month"].between(min_month, max_month)]
        .groupby("cus_id")
        .agg({column_name: "mean", "month": "count"})
        .reset_index()
    )
    df_avg_success_order_count["avg_success_order_count_per_month"] = np.where(
        (df_avg_success_order_count[column_name] >= min_avg_success_order_count)
        & (df_avg_success_order_count["month"] == months_window),
        1,
        0,
    )
    df_avg_success_order_count["score_5"] = binning_data(
        df_avg_success_order_count, column_name, 20
    ) + df_avg_success_order_count["avg_success_order_count_per_month"].astype(
        "str"
    )
    return df_avg_success_order_count[
        ["cus_id", "avg_success_order_count_per_month", "score_5"]
    ]
