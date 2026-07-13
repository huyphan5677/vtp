from __future__ import annotations

import pandas as pd
import numpy as np

from src.utils.common import month_date_range
from src.utils.minio_client import (
    save_to_minio,
    extract_data_by_date,
    extract_data_by_range,
)


def transform_gmv_by_day(
    date: str,
    day_prefix: str,
    raw_day_prefix: str,
    day_partition_key: str,
) -> pd.DataFrame:
    """Giai đoạn ngày: đọc raw ngày `date` từ MinIO, chuẩn bị data cho rule
    gmv, lưu xuống `day_prefix`/`day_partition_key`={date}/.

    -> trả về dữ liệu ngày đã làm sạch: cus_id, don_ptc->count, tong_tien->value, thu_ho, thuho_tongdon, don_ptc_cod, tongdon_cod, tong_don
    """
    raw_df = extract_data_by_date(
        date, prefix=raw_day_prefix, day_partition_key=day_partition_key
    )

    clean_df = raw_df[
        [
            "cus_id",
            "don_ptc",
            "tong_tien",
            "thu_ho",
            "thuho_tongdon",
            "don_ptc_cod",
            "tongdon_cod",
            "tong_don",
            "tong_cuoc_ptc"
        ]
    ].copy()
    clean_df = clean_df.dropna(subset=["cus_id"])
    clean_df["cus_id"] = (
        clean_df["cus_id"].apply(lambda x: x.get("member0") if isinstance(x, dict) else x).astype(str)
    )
    clean_df = clean_df.rename(
        columns={"don_ptc": "count", "tong_tien": "value"}
    )
    clean_df = clean_df[
        [
            "cus_id",
            "count",
            "value",
            "thu_ho",
            "thuho_tongdon",
            "don_ptc_cod",
            "tongdon_cod",
            "tong_don",
            "tong_cuoc_ptc"
        ]
    ]
    save_to_minio(
        clean_df,
        object_name=f"{day_prefix}/{day_partition_key}={date}/data.parquet",
    )
    return clean_df


def transform_gmv_lxm(
    month: str,
    months_window: int,
    day_prefix: str,
    month_prefix: str,
    day_partition_key: str,
    month_partition_key: str,
) -> pd.DataFrame:
    """Giai đoạn tháng (có window): tự load `months_window` tháng dữ liệu
    ngày đã clean (`day_prefix`), ước tính GMV cho COD + Non-COD, rồi tự lưu xuống `month_prefix`.
    - COD (thu_ho > 0 hoặc thuho_tongdon > 0): GMV = count * avg_don
    với: avg_don = thu_ho / don_ptc_cod if thu_ho > 0, else thuho_tongdon / tongdon_cod
         ship_rev_ratio = tong_cuoc_ptc/gmv nếu cước >0 else (don_ptc*tong_tien)/tong_don / gmv)

    - Non-COD (thu_ho = 0 và thuho_tongdon = 0): GMV = tong_cuoc_ptc/med_ratio if tong_cuoc_ptc >0 else ship_rev_non/med_ratio
    với: med_ratio = median(ship_rev_ratio / thu_ho)
         ship_rev_non = (count * value)/tong_don

    -> trả về bảng gồm cus_id, f_order_gmv_l{months_window}m
    """
    start_month = (pd.Period(month, freq="M") - months_window + 1).strftime(
        "%Y%m"
    )
    start_date = month_date_range(start_month)[0]
    end_date = month_date_range(month)[1]

    day_df = extract_data_by_range(
        start_date,
        end_date,
        prefix=day_prefix,
        day_partition_key=day_partition_key,
    )
    day_df["month"] = day_df[day_partition_key].astype(str).str[:6].astype(int)
    agg_dict = {
    "count": "sum",
    "value": "sum",
    "tong_don": "sum",
    "thu_ho": "sum",
    "tong_cuoc_ptc": "sum",
    "don_ptc_cod": "sum",
    "thuho_tongdon": "sum",
    "tongdon_cod": "sum",
}

    monthly_df = (
        day_df
        .groupby(["cus_id", "month"], as_index=False)
        .agg(agg_dict)
)

    # ----------------------------
    # ship_rev chung cho cả COD và Non-COD
    # ----------------------------
    ship_rev = (
        monthly_df["count"]
        * monthly_df["value"]
        / monthly_df["tong_don"].replace(0, np.nan)
)

    # ----------------------------
    # Lọc dòng COD và Non-COD
    # ----------------------------
    cod_mask = (
        (monthly_df["thu_ho"] > 0) | (monthly_df["thuho_tongdon"] > 0)
    )

    # ----------------------------
    # avg_don
    # ----------------------------
    avg_don = np.where(
        monthly_df["thu_ho"] > 0,
        monthly_df["thu_ho"] / monthly_df["don_ptc_cod"].replace(0, np.nan),
        monthly_df["thuho_tongdon"] / monthly_df["tongdon_cod"].replace(0, np.nan),
    )

    # ----------------------------
    # COD GMV
    # ----------------------------
    gmv_cod = monthly_df["count"] * avg_don

    # ----------------------------
    # ship_rev_ratio
    # ----------------------------
    ship_rev_ratio = np.where(
        monthly_df["tong_cuoc_ptc"] > 0,
        monthly_df["tong_cuoc_ptc"] / gmv_cod,
        ship_rev / gmv_cod,
    )

    # ----------------------------
    # med_ratio
    # ----------------------------
    med_ratio = np.nanmedian(ship_rev_ratio[cod_mask])

    # tránh trường hợp med_ratio = nan (tất cả dòng đều là Non-COD) thì set med_ratio = 1.0
    if np.isnan(med_ratio):
        med_ratio = 1.0

    # ----------------------------
    # Non-COD GMV
    # ----------------------------
    gmv_non = np.where(
        monthly_df["tong_cuoc_ptc"] > 0,
        monthly_df["tong_cuoc_ptc"] / med_ratio,
        ship_rev / med_ratio,
    )

    # ----------------------------
    # GMV toàn bộ
    # ----------------------------
    monthly_df["gmv"] = np.where(
        cod_mask,
        gmv_cod,
        gmv_non,
    )

    feature = f"f_order_gmv_l{months_window}m"

    result_df = (
    monthly_df
    .groupby("cus_id", as_index=False)
    .agg(**{feature: ("gmv", "sum")})
)

    result_df[feature] = (
        result_df[feature]
        .fillna(0)
        .div(1_000_000)
        .clip(1, 9999)
    )

    save_to_minio(
        result_df,
        object_name=f"{month_prefix}/{month_partition_key}={month}/data.parquet",
    )

    return result_df