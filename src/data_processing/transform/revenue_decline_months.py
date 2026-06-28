from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils.common import with_config


@with_config("rules.yaml")
def transform_revenue_decline_last_n_months(
    df: pd.DataFrame, column_name: str, config=None
) -> pd.DataFrame:
    """Tiêu chí: giảm doanh thu 6 tháng.

    Logic:
    - Xét 6 tháng gần nhất
    - Đếm số tháng giảm liên tục >=20% so với tháng liền kề
    - Output:
        cus_id
        score_7

    Args:
        df (pd.DataFrame): Bảng chứa dữ liệu giao dịch.
        column_name (str): Tên cột chứa doanh thu.

    Returns:
        pd.DataFrame: Bảng chứa dữ liệu.
    """
    # Đọc config
    rule_config = config.get("revenue_decline_6_months", {})
    months_window = rule_config.get("months_window", 6)
    decline_threshold = rule_config.get("decline_pct", 0.2)

    temp_df = df.copy()
    temp_df["month"] = pd.to_datetime(
        temp_df["month"], format="%Y%m"
    ).dt.to_period("M")

    # Xác định 6 tháng gần nhất
    max_month = temp_df["month"].max()
    min_month = max_month - months_window + 1

    valid_df = temp_df[temp_df["month"].between(min_month, max_month)]

    # Lấp đầy tháng thiếu
    users = valid_df["cus_id"].unique()
    full_months = pd.period_range(min_month, max_month, freq="M")

    index_df = pd.MultiIndex.from_product(
        [users, full_months], names=["cus_id", "month"]
    ).to_frame(index=False)

    merged_df = index_df.merge(valid_df, on=["cus_id", "month"], how="left")
    merged_df[column_name] = merged_df[column_name].fillna(0.0001)

    # Tính % thay đổi so với tháng trước
    merged_df = merged_df.sort_values(["cus_id", "month"])
    merged_df["prev_value"] = merged_df.groupby("cus_id")[column_name].shift(1)
    merged_df = merged_df.dropna(subset=["prev_value"])

    merged_df["ratio"] = merged_df[column_name] / merged_df["prev_value"] - 1

    # Đánh dấu các loại tháng:
    # - is_decline: Tháng GIẢM >= 20% (ratio <= -0.2) → Vi phạm
    # - is_stable_or_up: Tháng KHÔNG giảm quá 20% (ratio > -0.2) → Ổn định/Tăng trưởng
    merged_df["is_decline"] = (merged_df["ratio"] <= -decline_threshold).astype(
        int
    )
    # merged_df["is_stable_or_up"] = (merged_df["ratio"] > -decline_threshold).astype(int)

    # Tính chuỗi GIẢM liên tục
    # Logic: Mỗi khi gặp tháng KHÔNG GIẢM -> tạo nhóm mới (streak_id tăng lên)
    # Các tháng giảm liên tục sẽ có cùng streak_id
    merged_df["decline_streak_id"] = (
        (~merged_df["is_decline"].astype(bool))
        .groupby(merged_df["cus_id"])
        .cumsum()
    )

    merged_df["decline_streak"] = merged_df.groupby([
        "cus_id",
        "decline_streak_id",
    ])["is_decline"].cumsum()

    # # Tính chuỗi ỔN ĐỊNH/TĂNG liên tục (không giảm quá 20%)
    # # Logic: Mỗi khi gặp tháng GIẢM >= 20% -> tạo nhóm mới
    # # Các tháng ổn định/tăng liên tục sẽ có cùng streak_id
    # merged_df["stable_streak_id"] = (
    #     (~merged_df["is_stable_or_up"].astype(bool))
    #     .groupby(merged_df["cus_id"])
    #     .cumsum()
    # )

    # merged_df["stable_streak"] = (
    #     merged_df
    #     .groupby(["cus_id", "stable_streak_id"])["is_stable_or_up"]
    #     .cumsum()
    # )

    # Tổng hợp kết quả
    result_df = merged_df.groupby("cus_id", as_index=False).agg(
        max_decline_streak=("decline_streak", "max"),  # Chuỗi giảm dài nhất
        # max_stable_streak=("stable_streak", "max")         # Chuỗi ổn định/tăng dài nhất (không giảm >=20%)
    )

    # Score 7: dựa trên chuỗi giảm (giới hạn 0-5)
    result_df["score_7"] = (
        result_df["max_decline_streak"].fillna(0).clip(0, 5).astype(str)
    )

    # # Score 8: dựa trên chuỗi ổn định/tăng (giới hạn 0-5) - số tháng liên tục không giảm quá 20%
    # result_df["score_8"] = result_df["max_stable_streak"].fillna(0).clip(0, 5).astype(str)

    # Nếu doanh thu ổn định liên tục >= 4 tháng thì trả về 1, ngược lại 0
    result_df["revenue_decline_last_4_months"] = np.where(
        result_df["max_decline_streak"] >= 4, 0, 1
    )
    return result_df[["cus_id", "revenue_decline_last_4_months", "score_7"]]
