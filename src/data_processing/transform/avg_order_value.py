from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils.bining import binning_data
from src.utils.common import with_config


@with_config("rules.yaml")
def transform_avg_success_order_value_per_month(
    df: pd.DataFrame, column_name: str, config=None
) -> pd.DataFrame:
    """Xử lý cột tong_tien.

    -> trả về bảng avg_success_order_value_per_month với 3 cột: cus_id, month
    (đếm số tháng hđ),tong_tien (Trung bình) và avg_success_order_value_per_month
    """
    # Đọc config
    months_window = config.get("avg_success_order_value_per_month", {}).get(
        "months_window"
    )
    min_avg_success_order = config.get(
        "avg_success_order_value_per_month", {}
    ).get("min")

    # Đầu tiên cần lấy ra tháng cao nhất
    temp_df = df.copy()

    temp_df["month"] = pd.to_datetime(temp_df["month"], format="%Y%m")
    temp_df["month"] = temp_df["month"].dt.to_period("M")
    max_month = temp_df["month"].max()

    # Chỉ trích xuất X tháng gần nhất
    min_month = (
        max_month - months_window + 1
    )  # Phải cộng 1 vì như này: ví dụ tháng 12 thì phải trích xuất 6 tháng gần
    # nhất từ tháng 7 đến tháng 12

    print(
        "Tính toán avg_success_order_value_per_month xét từ tháng",
        min_month,
        "đến tháng",
        max_month,
    )

    # Tính tổng tiền ở tất cả chi nhánh và tháng hoạt động
    df_avg_success_order_value_per_month = (
        temp_df[temp_df["month"].between(min_month, max_month)]
        .groupby("cus_id")
        .agg({column_name: "sum", "month": "nunique"})
        .reset_index()
    )

    # Tính trung bình tiền theo tháng
    df_avg_success_order_value_per_month[
        "avg_success_order_value_per_month"
    ] = (
        df_avg_success_order_value_per_month[column_name]
        / df_avg_success_order_value_per_month["month"]
    )

    # Hơn nữa nếu số tháng ghi nhận được từ khách hàng < 6 tháng thì trả về 0
    df_avg_success_order_value_per_month[
        "avg_success_order_value_per_month"
    ] = np.where(
        (
            df_avg_success_order_value_per_month[
                "avg_success_order_value_per_month"
            ]
            >= min_avg_success_order
        )
        & (df_avg_success_order_value_per_month["month"] == months_window),
        1,
        0,
    )

    # Tính điểm score_2
    df_avg_success_order_value_per_month["score_2"] = binning_data(
        df_avg_success_order_value_per_month, column_name, 20
    ) + df_avg_success_order_value_per_month[
        "avg_success_order_value_per_month"
    ].astype("str")

    # Trả về bảng avg_success_order_value_per_month với 3 cột: cus_id,
    # avg_success_order_value_per_month, score_2
    return df_avg_success_order_value_per_month[
        ["cus_id", "avg_success_order_value_per_month", "score_2"]
    ]


@with_config("rules.yaml")
def transform_total_success_order_value_per_month(
    df: pd.DataFrame, column_name: str, config=None
) -> pd.DataFrame:
    """Xử lý cột tong_tien.

    -> trả về bảng total_success_order_value_per_month với 3 cột: cus_id, month
    (đếm số tháng hđ),tong_tien (Tối thiểu) và total_success_order_value_per_month
    """
    # Đọc config
    months_window = config.get("total_success_order_value_per_month", {}).get(
        "months_window"
    )
    min_total_success_order = config.get(
        "total_success_order_value_per_month", {}
    ).get("min")

    # Đầu tiên cần lấy ra tháng cao nhất
    temp_df = df.copy()
    temp_df["month"] = pd.to_datetime(temp_df["month"], format="%Y%m")
    temp_df["month"] = temp_df["month"].dt.to_period("M")
    max_month = temp_df["month"].max()

    # Chỉ trích xuất X tháng gần nhất
    min_month = (
        max_month - months_window + 1
    )  # phải cộng 1 vì như này: ví dụ tháng
    # 12 thì phải trích xuất 6 tháng gần nhất từ tháng 7 đến tháng 12

    print(
        "Tính toán total_success_order_value_per_month xét từ tháng",
        min_month,
        "đến tháng",
        max_month,
    )
    valid_data_range = temp_df[temp_df["month"].between(min_month, max_month)]

    # Tính tổng tiền theo tháng ở tất cả chi nhánh
    total_success_order_value_per_month = (
        valid_data_range
        .groupby(["cus_id", "month"])
        .agg({column_name: "sum"})
        .reset_index()
    )

    # Tính doanh thu thấp nhất theo tháng và số tháng hoạt động
    result = (
        total_success_order_value_per_month
        .groupby("cus_id")
        .agg(
            min_value_per_month=(column_name, "min"),
            active_months=("month", "nunique"),
        )
        .reset_index()
    )

    # Tạo cột is_success: Nêu có tháng nào có tổng giá trị đơn hàng thành công < 3tr trả về 0 nếu không trả về 1
    # Hơn nữa nếu số tháng ghi nhận được từ khách hàng < 6 tháng thì trả về 0
    result["total_success_order_value_per_month"] = np.where(
        (result["min_value_per_month"] >= min_total_success_order)
        & (result["active_months"] == months_window),
        1,
        0,
    )
    result["score_3"] = result["total_success_order_value_per_month"].astype(
        "str"
    )

    # Trả về bảng total_success_order_value_per_month với 3 cột: cus_id,
    # total_success_order_value_per_month, score_3
    return result[["cus_id", "total_success_order_value_per_month", "score_3"]]
