from __future__ import annotations

import pandas as pd

from src.utils.common import load_config

RULES_CONFIG_FILE = "rules.yaml"


def _get_rules_config() -> dict:
    return load_config(RULES_CONFIG_FILE)


VALID_REGION_CODES = {
    "01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
    "11", "12", "14", "15", "16", "17", "18", "19", "20", "21",
    "22", "23", "24", "25", "26", "27", "28", "29", "30", "31",
    "32", "33", "34", "35", "36", "37", "38", "39", "40", "41",
    "42", "43", "44", "45", "46", "47", "48", "49", "50", "51",
    "52", "53", "54", "55", "56", "57", "58", "59", "60", "61",
    "62", "63", "64", "65", "66", "67", "68", "69", "70", "71",
    "72", "73", "74", "75", "76", "77", "78", "79", "80", "81",
}


def transform_usage_duration_by_day(
    date: str,
    day_prefix: str,
    raw_day_prefix: str,
    day_partition_key: str,
) -> pd.DataFrame:
    """Giữ lại các cột cần thiết cho rule usage duration ở giai đoạn ngày."""
    from src.utils.minio_client import extract_data_by_date, save_to_minio

    raw_df = extract_data_by_date(
        date, prefix=raw_day_prefix, day_partition_key=day_partition_key
    )
    clean_df = raw_df[["cus_id", "so_thang_hdong"]].copy()
    clean_df = clean_df.dropna(subset=["cus_id"])
    clean_df["cus_id"] = clean_df["cus_id"].astype(str)
    clean_df["month"] = date[:6]
    save_to_minio(
        clean_df,
        object_name=f"{day_prefix}/{day_partition_key}={date}/data.parquet",
    )
    return clean_df


def _ensure_month_column(df: pd.DataFrame, month_col: str, day_partition_key: str | None = None) -> pd.DataFrame:
    if month_col in df.columns:
        return df
    if day_partition_key and day_partition_key in df.columns:
        out = df.copy()
        out[month_col] = pd.to_numeric(out[day_partition_key].astype(str).str[:6], errors="coerce")
        return out
    return df


def transform_usage_duration_months(df: pd.DataFrame, months_window: int = 12) -> pd.DataFrame:
    """Tạo cột usage_duration_months và behavior_score từ so_thang_hdong."""
    rules = _get_rules_config()
    min_months = rules.get("usage_duration_months", {}).get("min", 4)

    out = df[["cus_id", "so_thang_hdong"]].copy()
    out = out.dropna(subset=["cus_id"])
    out["so_thang_hdong"] = pd.to_numeric(out["so_thang_hdong"], errors="coerce")

    grouped = (
        out.groupby("cus_id", as_index=False)["so_thang_hdong"]
        .max()
        .rename(columns={"so_thang_hdong": "max_so_thang_hdong"})
    )

    grouped["usage_duration_months"] = (
        grouped["max_so_thang_hdong"] >= min_months
    ).astype(int)

    def _behavior_code(months: float) -> str:
        if pd.isna(months):
            return "00"
        if months < 4:
            return "00"
        if months <= 6:
            return "01"
        if months <= 12:
            return "02"
        if months <= 18:
            return "03"
        return "04"

    grouped["behavior_score"] = grouped["max_so_thang_hdong"].apply(
        _behavior_code
    )
    return grouped[["cus_id", "usage_duration_months", "behavior_score"]]


def transform_sales_region_by_day(
    date: str,
    day_prefix: str,
    raw_day_prefix: str,
    day_partition_key: str,
) -> pd.DataFrame:
    """Giữ lại các cột cần thiết cho rule sales_region ở giai đoạn ngày."""
    from src.utils.minio_client import extract_data_by_date, save_to_minio

    raw_df = extract_data_by_date(
        date, prefix=raw_day_prefix, day_partition_key=day_partition_key
    )
    clean_df = raw_df[["cus_id", "ma_tinh_hoatdong_chinh"]].copy()
    clean_df = clean_df.dropna(subset=["cus_id"])
    clean_df["cus_id"] = clean_df["cus_id"].astype(str)
    clean_df["month"] = date[:6]
    save_to_minio(
        clean_df,
        object_name=f"{day_prefix}/{day_partition_key}={date}/data.parquet",
    )
    return clean_df


def transform_sales_region(df: pd.DataFrame, month_col: str = "month", months_window: int = 1, day_partition_key: str | None = None) -> pd.DataFrame:
    """Lấy bản ghi cuối cùng theo tháng của mỗi cus_id và kiểm tra tỉnh hợp lệ."""
    rules = _get_rules_config()
    valid_regions = set(rules.get("sales_region", {}).get("valid", []))

    work = df[["cus_id", month_col, "ma_tinh_hoatdong_chinh"]].copy() if month_col in df.columns else df[["cus_id", "ma_tinh_hoatdong_chinh"]].copy()
    work = _ensure_month_column(work, month_col, day_partition_key=day_partition_key)
    work = work[["cus_id", month_col, "ma_tinh_hoatdong_chinh"]].copy()
    work = work.dropna(subset=["cus_id"])
    work[month_col] = pd.to_numeric(work[month_col], errors="coerce")
    work["ma_tinh_hoatdong_chinh"] = work["ma_tinh_hoatdong_chinh"].astype(str)

    latest = (
        work.sort_values(["cus_id", month_col], ascending=[True, True])
        .groupby("cus_id", as_index=False)
        .tail(1)
    )
    latest["sales_region"] = (
        latest["ma_tinh_hoatdong_chinh"].isin(valid_regions)
    ).astype(int)
    return latest[["cus_id", "sales_region"]]


def transform_success_order_by_day(
    date: str,
    day_prefix: str,
    raw_day_prefix: str,
    day_partition_key: str,
) -> pd.DataFrame:
    """Giữ lại các cột cần thiết cho rule success_order_all_months ở giai đoạn ngày."""
    from src.utils.minio_client import extract_data_by_date, save_to_minio

    raw_df = extract_data_by_date(
        date, prefix=raw_day_prefix, day_partition_key=day_partition_key
    )
    clean_df = raw_df[["cus_id", "don_ptc"]].copy()
    clean_df = clean_df.dropna(subset=["cus_id"])
    clean_df["cus_id"] = clean_df["cus_id"].astype(str)
    clean_df["month"] = date[:6]
    save_to_minio(
        clean_df,
        object_name=f"{day_prefix}/{day_partition_key}={date}/data.parquet",
    )
    return clean_df


def transform_success_order_all_months(df: pd.DataFrame, month_col: str = "month", months_window: int = 4, day_partition_key: str | None = None) -> pd.DataFrame:
    """Đánh dấu khách hàng có đơn thành công trong 4 tháng gần nhất."""
    work = df[["cus_id", month_col, "don_ptc"]].copy() if month_col in df.columns else df[["cus_id", "don_ptc"]].copy()
    work = _ensure_month_column(work, month_col, day_partition_key=day_partition_key)
    work = work[["cus_id", month_col, "don_ptc"]].copy()
    work = work.dropna(subset=["cus_id"])
    work[month_col] = pd.to_numeric(work[month_col], errors="coerce")
    work["don_ptc"] = pd.to_numeric(work["don_ptc"], errors="coerce")

    recent = work.sort_values(["cus_id", month_col], ascending=[True, True])
    recent = recent.groupby("cus_id").tail(months_window)

    result = (
        recent.groupby("cus_id", as_index=False)
        .agg(
            month_count=(month_col, "count"),
            has_success=("don_ptc", lambda s: (s >= 1).all()),
        )
    )
    result["success_order_all_months"] = (
        (result["month_count"] == months_window) & (result["has_success"])
    ).astype(int)
    return result[["cus_id", "success_order_all_months"]]


def transform_gmv_by_day(
    date: str,
    day_prefix: str,
    raw_day_prefix: str,
    day_partition_key: str,
) -> pd.DataFrame:
    """Giữ lại các cột cần thiết cho rule gmv ở giai đoạn ngày."""
    from src.utils.minio_client import extract_data_by_date, save_to_minio

    raw_df = extract_data_by_date(
        date, prefix=raw_day_prefix, day_partition_key=day_partition_key
    )
    clean_df = raw_df[[
        "cus_id",
        "don_ptc",
        "tong_tien",
        "thu_ho",
        "thuho_tongdon",
        "don_ptc_cod",
        "tongdon_cod",
        "tong_don",
    ]].copy()
    clean_df = clean_df.dropna(subset=["cus_id"])
    clean_df["cus_id"] = clean_df["cus_id"].astype(str)
    clean_df["month"] = date[:6]
    save_to_minio(
        clean_df,
        object_name=f"{day_prefix}/{day_partition_key}={date}/data.parquet",
    )
    return clean_df


def transform_gmv(df: pd.DataFrame, median_ratio_cod: float = 1.0, months_window: int = 12) -> pd.DataFrame:
    """Ước tính GMV 12 tháng theo nhóm COD/non-COD."""
    work = df[[
        "cus_id",
        "don_ptc",
        "tong_tien",
        "thu_ho",
        "thuho_tongdon",
        "don_ptc_cod",
        "tongdon_cod",
        "tong_don",
    ]].copy()

    work["don_ptc"] = pd.to_numeric(work["don_ptc"], errors="coerce")
    work["tong_tien"] = pd.to_numeric(work["tong_tien"], errors="coerce")
    work["thu_ho"] = pd.to_numeric(work["thu_ho"], errors="coerce")
    work["thuho_tongdon"] = pd.to_numeric(work["thuho_tongdon"], errors="coerce")
    work["don_ptc_cod"] = pd.to_numeric(work["don_ptc_cod"], errors="coerce")
    work["tongdon_cod"] = pd.to_numeric(work["tongdon_cod"], errors="coerce")
    work["tong_don"] = pd.to_numeric(work["tong_don"], errors="coerce")

    def _is_cod(row: pd.Series) -> bool:
        return (row["thu_ho"] > 0) or (row["thuho_tongdon"] > 0)

    def _gmv_value(row: pd.Series) -> float:
        if _is_cod(row):
            if pd.notna(row["don_ptc_cod"]) and row["don_ptc_cod"] > 0:
                avg_don = row["thu_ho"] / row["don_ptc_cod"]
            else:
                avg_don = row["thu_ho"] / max(row["don_ptc"], 1)
            return row["don_ptc"] * avg_don
        if row["tong_don"] and row["tong_don"] > 0:
            return (row["don_ptc"] * row["tong_tien"] / row["tong_don"]) / median_ratio_cod
        return 0.0

    work["gmv"] = work.apply(_gmv_value, axis=1)
    work["gvm_score"] = (work["gmv"] / 1_000_000).clip(lower=1, upper=9999)
    return work[["cus_id", "gvm_score"]]


def transform_recommendation_by_day(
    date: str,
    day_prefix: str,
    raw_day_prefix: str,
    day_partition_key: str,
) -> pd.DataFrame:
    """Giữ lại các cột cần thiết cho rule recommendation ở giai đoạn ngày."""
    from src.utils.minio_client import extract_data_by_date, save_to_minio

    raw_df = extract_data_by_date(
        date, prefix=raw_day_prefix, day_partition_key=day_partition_key
    )
    clean_df = raw_df[["cus_id"]].copy()
    clean_df = clean_df.dropna(subset=["cus_id"])
    clean_df["cus_id"] = clean_df["cus_id"].astype(str)
    clean_df["month"] = date[:6]
    save_to_minio(
        clean_df,
        object_name=f"{day_prefix}/{day_partition_key}={date}/data.parquet",
    )
    return clean_df


def transform_recommendation(df: pd.DataFrame, months_window: int = 1) -> pd.DataFrame:
    """Tạo cột recommendation từ các điều kiện business rule."""
    work = df[[
        "cus_id",
        "gvm_score",
        "sales_region",
        "usage_duration_months",
        "total_success_order_value_per_month",
    ]].copy()
    work["gvm_score"] = pd.to_numeric(work["gvm_score"], errors="coerce")
    work["sales_region"] = pd.to_numeric(work["sales_region"], errors="coerce")
    work["usage_duration_months"] = pd.to_numeric(work["usage_duration_months"], errors="coerce")
    work["total_success_order_value_per_month"] = pd.to_numeric(
        work["total_success_order_value_per_month"], errors="coerce"
    )

    work["recommendation"] = (
        (work["gvm_score"] >= 100)
        & (work["sales_region"] == 1)
        & (work["usage_duration_months"] == 1)
        & (work["total_success_order_value_per_month"] == 1)
    ).astype(int)
    return work[["cus_id", "recommendation"]]
