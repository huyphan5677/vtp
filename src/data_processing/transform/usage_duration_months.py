from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils.common import with_config


def feature_engineering_usage_duration(
    df: pd.DataFrame, column_name: str
) -> pd.DataFrame:
    """Xử lý thời gian hợp tác.

    -> df có thêm cột: usage_duration_months
    """
    today = pd.Timestamp.today()
    df["usage_duration_months"] = (today - df[column_name]).dt.days / 30
    return df


@with_config("rules.yaml")
def transform_usage_duration_months(
    df: pd.DataFrame, column_name: str, config=None
) -> pd.DataFrame:
    """Xử lý cột usage_duration_months.

    -> trả về bảng usage_duration_months với 3 cột: cus_id, tgian_hdong_chinh,
    và usage_duration_months

    Args:
        df (pd.DataFrame): Bảng chứa dữ liệu giao dịch.
        column_name (str): Tên cột chứa thời gian hoạt động chính.
        config (dict): Config từ rules.yaml.

    Returns:
        pd.DataFrame: Bảng chứa dữ liệu.
    """
    # Đọc config
    usage_duration_months_rule = config.get("usage_duration_months", {})
    min_usage_duration_months = usage_duration_months_rule.get("min")

    # Tính toán thời gian hoạt động chính
    df_usage_duration_months = (
        df.groupby("cus_id").agg({column_name: "max"}).reset_index()
    )
    # Tạo cột usage_duration_months
    df_usage_duration_months["usage_duration_months"] = np.where(
        df_usage_duration_months[column_name] >= min_usage_duration_months, 1, 0
    )

    # Tạo cột usage_duration_group
    conditions = [
        df_usage_duration_months[column_name] < 3,
        (
            (df_usage_duration_months[column_name] >= 4)
            & (df_usage_duration_months[column_name] <= 6)
        ),
        (
            (df_usage_duration_months[column_name] >= 7)
            & (df_usage_duration_months[column_name] <= 12)
        ),
        (
            (df_usage_duration_months[column_name] >= 13)
            & (df_usage_duration_months[column_name] <= 18)
        ),
        df_usage_duration_months[column_name] > 18,
    ]

    choices = ["00", "01", "02", "03", "04"]
    df_usage_duration_months["usage_duration_group"] = np.select(
        conditions, choices, default="99"
    )

    # Tạo score cho rule 1
    df_usage_duration_months["score_1"] = df_usage_duration_months[
        "usage_duration_group"
    ] + df_usage_duration_months["usage_duration_months"].astype(str)

    return df_usage_duration_months[
        [
            "cus_id",
            column_name,
            "usage_duration_months",
            "usage_duration_group",
            "score_1",
        ]
    ]
