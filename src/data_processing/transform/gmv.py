from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils.common import with_config


def compute_gmv(df: pd.DataFrame, months_window: int) -> pd.DataFrame:
    """Tính toán gmv 3 tháng và 12 tháng.

    Args:
        df (pd.DataFrame): Bảng chứa dữ liệu giao dịch, có các cột:
            cus_id, month, thu_ho, thuho_tongdon, don_ptc_cod,
            tongdon_cod, don_ptc, tong_tien, tong_don.
        months_window (int): Số tháng để tính toán gmv (3 hoặc 12).

    Returns:
        pd.DataFrame: Bảng chứa dữ liệu gmv.
    """
    df = df.copy()
    df["month"] = pd.to_datetime(df["month"], format="%Y%m").dt.to_period("M")

    max_month = df["month"].max()
    min_month = max_month - months_window + 1

    df = df[df["month"].between(min_month, max_month)]

    # Aggregate theo cus_id
    agg_df = (
        df
        .groupby("cus_id")
        .agg(
            thu_ho=("thu_ho", "sum"),
            thuho_tongdon=("thuho_tongdon", "sum"),
            don_ptc_cod=("don_ptc_cod", "sum"),
            tongdon_cod=("tongdon_cod", "sum"),
            don_ptc=("don_ptc", "sum"),
            tong_tien=("tong_tien", "sum"),
            tong_don=("tong_don", "sum"),
            # tong_cuoc_ptc=("tong_cuoc_ptc", "sum"),
        )
        .reset_index()
    )

    # Chia nhóm
    group_cod = agg_df[
        (agg_df["thu_ho"] > 0) | (agg_df["thuho_tongdon"] > 0)
    ].copy()

    group_non_cod = agg_df[
        (agg_df["thu_ho"] <= 0) & (agg_df["thuho_tongdon"] <= 0)
    ].copy()

    # Nhóm 1 (COD)
    # avg_don
    group_cod["avg_don"] = np.where(
        group_cod["thu_ho"] > 0,
        group_cod["thu_ho"] / group_cod["don_ptc_cod"].replace(0, np.nan),
        group_cod["thuho_tongdon"]
        / group_cod["tongdon_cod"].replace(0, np.nan),
    )

    # gmv_12th / gmv_3th
    group_cod["gmv"] = group_cod["don_ptc"] * group_cod["avg_don"]

    # ship_rev_ratio
    ship_rev = (group_cod["don_ptc"] * group_cod["tong_tien"]) / group_cod[
        "tong_don"
    ].replace(0, np.nan)

    group_cod["ship_rev_ratio"] = np.where(
        # group_cod["tong_cuoc_ptc"] > 0,
        1 > 0,
        ship_rev / group_cod["gmv"],
        group_cod["gmv"] / group_cod["gmv"],
        # group_cod["tong_cuoc_ptc"] / group_cod["gmv"] ---sau nay su dung
    )

    # Nhóm 2 (NON COD)
    med_ratio = group_cod["ship_rev_ratio"].median()

    ship_rev_non = (
        group_non_cod["don_ptc"] * group_non_cod["tong_tien"]
    ) / group_non_cod["tong_don"].replace(0, np.nan)

    group_non_cod["gmv"] = np.where(
        # group_non_cod["tong_cuoc_ptc"] > 0,
        1 > 0,
        ship_rev_non / med_ratio,
        -999999,
        # group_non_cod["tong_cuoc_ptc"] / med_ratio ---sau nay su dung
    )

    # Union
    df_final = pd.concat([
        group_cod[["cus_id", "gmv"]],
        group_non_cod[["cus_id", "gmv"]],
    ])

    # Xử lý dữ liệu sau khi tính toán
    # 1. Đổi sang triệu đồng
    df_final["gmv"] = df_final["gmv"] / 1_000_000

    # 2. Xử lý NaN / âm (nếu có)
    df_final["gmv"] = df_final["gmv"].fillna(0)
    df_final["gmv"] = df_final["gmv"].clip(lower=0)

    # 3. Clamp về range [1, 9999]
    df_final["gmv"] = df_final["gmv"].clip(lower=1, upper=9999)

    return df_final


@with_config("rules.yaml")
def transform_gmv_12th(df: pd.DataFrame, config=None) -> pd.DataFrame:
    """Tính toán gmv 12 tháng.

    Args:
        df (pd.DataFrame): Bảng chứa dữ liệu giao dịch, có các cột:
            cus_id, month, thu_ho, thuho_tongdon, don_ptc_cod,
            tongdon_cod, don_ptc, tong_tien, tong_don.
        config (dict): Configuration for the transformation.

    Returns:
        pd.DataFrame: Bảng chứa dữ liệu gmv.
    """
    months_window = 12

    df_result = compute_gmv(df, months_window)
    return df_result.rename(columns={"gmv": "gmv_12th"})


@with_config("rules.yaml")
def transform_gmv_3th(df: pd.DataFrame, config=None) -> pd.DataFrame:
    """Tính toán gmv 3 tháng.

    Args:
        df (pd.DataFrame): Bảng chứa dữ liệu giao dịch, có các cột:
            cus_id, month, thu_ho, thuho_tongdon, don_ptc_cod,
            tongdon_cod, don_ptc, tong_tien, tong_don.
        config (dict): Configuration for the transformation.

    Returns:
        pd.DataFrame: Bảng chứa dữ liệu gmv.
    """
    months_window = 3

    df_result = compute_gmv(df, months_window)
    return df_result.rename(columns={"gmv": "gmv_3th"})
