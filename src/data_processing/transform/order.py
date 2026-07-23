from __future__ import annotations

import pandas as pd
import numpy as np

from src.utils.common import month_date_range
from src.utils.minio_client import (
    save_to_minio,
    extract_data_by_date,
    extract_data_by_range,
    object_exists,
    save_artifact,
    load_artifact,
)

def transform_order_by_day(
    date: str,
    day_prefix: str,
    raw_day_prefix: str,
    day_partition_key: str,
) -> pd.DataFrame:
    """Giai đoạn ngày: đọc raw ngày `date` từ MinIO, làm sạch, lưu xuống
    `day_prefix`/`day_partition_key`={date}/.

    -> trả về dữ liệu ngày đã làm sạch, 3 cột: cus_id, count, value
    """
    # 1, Đọc dữ liệu raw theo ngày
    raw_df = extract_data_by_date(
        date, prefix=raw_day_prefix, day_partition_key=day_partition_key
    )

    # 2, Làm sạch dữ liệu: chỉ giữ cus_id, don_ptc, tong_tien; bỏ dòng cus_id null;
    #    đổi tên don_ptc -> count, tong_tien -> value
    clean_df = raw_df[["cus_id", "don_ptc", "tong_tien"]].copy()
    clean_df = clean_df.dropna(subset=["cus_id"])
    clean_df["cus_id"] = clean_df["cus_id"].astype(str)
    clean_df = clean_df.rename(
        columns={"don_ptc": "count", "tong_tien": "value"}
    )

    # 3, Lưu dữ liệu đã làm sạch xuống MinIO
    save_to_minio(
        clean_df,
        object_name=f"{day_prefix}/{day_partition_key}={date}/data.parquet",
    )
    return clean_df


def transform_order_avg_lxm(
    month: str,
    months_window: int,
    # min_count: float,
    # min_value: float,
    day_prefix: str,
    month_prefix: str,
    day_partition_key: str,
    month_partition_key: str,
) -> pd.DataFrame:
    """Giai đoạn tháng (có window): tự load `months_window` tháng dữ liệu
    ngày đã clean (`day_prefix`), tính avg count/value theo cus_id, so với
    ngưỡng min_count/min_value, và tự lưu xuống `month_prefix`.

    Tất cả tham số đều lấy từ features.yaml.

    -> trả về bảng gồm cus_id, f_order_avg_count_l{N}m, f_order_avg_value_l{N}m
    """
    # 1, Xác định khoảng ngày cần load: từ đầu tháng (month - months_window + 1)
    #    đến cuối tháng (month)
    start_month = (pd.Period(month, freq="M") - months_window + 1).strftime(
        "%Y%m"
    )
    start_date = month_date_range(start_month)[0]
    end_date = month_date_range(month)[1]

    # 2, Load dữ liệu ngày đã clean
    day_df = extract_data_by_range(
        start_date,
        end_date,
        prefix=day_prefix,
        day_partition_key=day_partition_key,
    )
    day_df["month"] = day_df[day_partition_key].astype(str).str[:6].astype(int)

    # 3, Tính avg count/value theo cus_id
    count_col = f"f_order_avg_count_l{months_window}m"
    value_col = f"f_order_avg_value_l{months_window}m"
    #active_months_col = f"f_order_active_months_l{months_window}m"
    # count_ok_col = f"f_order_count_ok_l{months_window}m"
    # value_ok_col = f"f_order_value_ok_l{months_window}m"

    result_df = (
    day_df
    .groupby(["cus_id", "month"])
    .agg(
        monthly_count=("count", "sum"),
        monthly_value=("value", "sum"),
    )
    .groupby("cus_id")
    .agg(
        **{count_col: ("monthly_count", "mean")},
        **{value_col: ("monthly_value", "mean")},
        #**{active_months_col: ("month", "nunique")},
    )
    .reset_index()
)

    # # Đạt ngưỡng chỉ khi >= min VÀ có đủ dữ liệu cả months_window tháng
    # has_full_window = result_df["active_months"] == months_window
    # result_df[count_ok_col] = (
    #     (result_df[count_col] >= min_count) & has_full_window
    # ).astype(int)
    # result_df[value_ok_col] = (
    #     (result_df[value_col] >= min_value) & has_full_window
    # ).astype(int)

    # 4, Chỉ giữ các cột cần thiết
    result_df = result_df[["cus_id", count_col, value_col]] #active_months_col]]

    # 5, Lưu dữ liệu đã làm sạch xuống.
    save_to_minio(
        result_df,
        object_name=f"{month_prefix}/{month_partition_key}={month}/data.parquet",
    )
    return result_df


def transform_order_avg_bin_lxm(
    month: str,
    months_window: int,
    n_bins: int,
    metric_col: str,
    #output_prefix: str,
    avg_month_prefix: str,
    month_prefix: str,
    month_partition_key: str,
) -> pd.DataFrame:
    """
    Chia feature avg order count/value LxM thành n_bins.

    metric_col:
        - count -> f_order_avg_count_l{N}m
        - value -> f_order_avg_value_l{N}m

    Output:
        cus_id, f_order_avg_{metric_col}_bin_l{N}m
    """

    # 1. Load feature avg đã được tính trước
    avg_df = extract_data_by_date(
        month,
        prefix=avg_month_prefix,
        day_partition_key=month_partition_key,
    )

    # 2. Xác định feature cần bin
    if metric_col not in ("count", "value"):
        raise ValueError(
            f"metric_col không hợp lệ: {metric_col}"
        )

    metric_feature = (
        f"f_order_avg_{metric_col}_l{months_window}m"
    )

    avg_df = avg_df.rename(
        columns={
            metric_feature: "avg_metric"
        }
    )

    avg_df = avg_df.dropna(
        subset=["avg_metric"]
    )

    # 3. Artifact chứa quantile của bins
    artifact_name = (
        f"artifacts/order/"
        f"avg_{metric_col}_l{months_window}_{n_bins}bins.pkl"
)

    # 4. Nếu chưa có artifact -> fit bins
    if not object_exists(artifact_name):
        quantiles = np.quantile(
            avg_df["avg_metric"],
            np.linspace(0, 1, n_bins + 1)[1:-1],
        )
        quantiles = np.unique(quantiles)

        save_artifact(quantiles, artifact_name)

    # 5. Nếu có rồi -> load lại bins
    else:
        quantiles = load_artifact(artifact_name)

    # 6. 6. Gán bin
    score = np.digitize(
        avg_df["avg_metric"],
        quantiles,
        right=True,
    ) + 1

    score = np.clip(score, 1, n_bins)

    bin_col = (
        f"f_order_avg_{metric_col}"
        f"_bin_l{months_window}m"
    )

    avg_df[bin_col] = (
    pd.Series(score, index=avg_df.index)
    .astype(str)
    .str.zfill(len(str(n_bins)))
)

    result_df = avg_df[["cus_id", bin_col]]

    save_to_minio(
        result_df,
        object_name=f"{month_prefix}/{month_partition_key}={month}/data.parquet",
    )

    return result_df


def transform_order_value_summary_lxm(
        month: str,
    months_window: int,
    day_prefix: str,
    month_prefix: str,
    day_partition_key: str,
    month_partition_key: str,
) -> pd.DataFrame:
    """Tổng doanh thu (VND) theo từng tháng->lấy min + trong toàn bộ window(4digits)

    -> trả về: cus_id, f_order_sum_value_l{N}m, f_order_sum_value_handy_l{N}m
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

    min_value_col = f"f_order_min_value_l{months_window}m"
    sum_handy_col = f"f_order_sum_value_handy_l{months_window}m"

    result_df = (
    day_df
    .groupby(["cus_id", "month"])
    .agg(monthly_value=("value", "sum"))
    .groupby("cus_id", as_index=False)
    .agg(
        **{min_value_col: ("monthly_value", "min")},
        **{"sum_value": ("monthly_value", "sum")},
    )
)

    # Tạo handy 4 digit
    result_df[sum_handy_col] = (
        (result_df["sum_value"] / 1_000_000)
        .round()
        .clip(1, 9999)
        .astype(int)
        .astype(str)
        .str.zfill(4)
    )

    result_df = result_df[["cus_id", min_value_col, sum_handy_col]]

    save_to_minio(
        result_df,
        object_name=f"{month_prefix}/{month_partition_key}={month}/data.parquet",
    )
    return result_df


def transform_success_order_all_months_lxm(
    month: str,
    months_window: int,
    day_prefix: str,
    month_prefix: str,
    day_partition_key: str,
    month_partition_key: str,
) -> pd.DataFrame:
    """
    Kiểm tra trong X tháng gần nhất:
    - tháng nào cũng có đơn thành công (count >= 1)
    - đủ X tháng dữ liệu

    Trả về: cus_id, success_order_all_months
    """
    start_month = (pd.Period(month, freq="M") - months_window + 1).strftime("%Y%m")

    start_date = month_date_range(start_month)[0]
    end_date = month_date_range(month)[1]


    day_df = extract_data_by_range(
        start_date,
        end_date,
        prefix=day_prefix,
        day_partition_key=day_partition_key,
    )

    day_df["month"] = (day_df[day_partition_key].astype(str).str[:6].astype(int))


    result_df = (
        day_df
        .groupby(["cus_id", "month"])
        .agg(
            monthly_count=("count", "sum")
        )
        .reset_index()
        .groupby("cus_id")
        .agg(
            success_order_all_months=(
                "monthly_count",
                lambda x: (x >= 1).all()
            ),
            #active_months=("month", "nunique"),
        )
        .reset_index()
)

    #result_df = result_df[["cus_id", "success_order_all_months", "active_months"]]

    save_to_minio(
        result_df,
        object_name=f"{month_prefix}/{month_partition_key}={month}/data.parquet",
    )

    return result_df


# def transform_order_value_decline_streak_lq(
#     month: str,
#     quarters_window: int,
#     day_prefix: str,
#     month_prefix: str,
#     day_partition_key: str,
#     month_partition_key: str,
# ) -> pd.DataFrame:

#     """
#     Đếm số quý giảm doanh thu liên tục.

#     Logic:
#     - Tổng value theo quý
#     - Xét N quý gần nhất (không tính quý hiện tại)
#     - Giảm >=30% so với quý trước
#     - Tính streak dài nhất

#     Trả về: cus_id, f_order_value_decline_streak_l{N}q
#     """
#     scoring_period = pd.Period(month, freq="M")

#     # bỏ quý hiện tại
#     end_quarter = (scoring_period.asfreq("Q", how="start")- 1)

#     start_quarter = (end_quarter - quarters_window + 1)

#     start_date = (start_quarter.start_time)
#     end_date = (end_quarter.end_time)


#     day_df = extract_data_by_range(
#         start_date.strftime("%Y%m%d"),
#         end_date.strftime("%Y%m%d"),
#         prefix=day_prefix,
#         day_partition_key=day_partition_key,
#     )

#     day_df["month"] = (day_df[day_partition_key].astype(str).str[:6].astype(int))

#     day_df["quarter"] = (pd.to_datetime(day_df["month"], format="%Y%m").dt.to_period("Q"))


#     # Tổng doanh thu theo quý
#     quarter_df = (
#         day_df
#         .groupby(["cus_id","quarter"], as_index=False)
#         .agg(quarterly_value=("value","sum"))
#     )

#     # sắp xếp theo thời gian
#     quarter_df = quarter_df.sort_values(["cus_id", "quarter"])

#     # quý trước
#     quarter_df["prev_value"] = (
#         quarter_df
#         .groupby("cus_id")["quarterly_value"]
#         .shift(1)
#     )

#     # giảm >=30%
#     quarter_df["is_decline"] = (
#         quarter_df["quarterly_value"]
#         /
#         quarter_df["prev_value"]
#         -
#         1
#     ) <= -0.3


#     def max_streak(x):
#         groups = (
#             x != x.shift()
#         ).cumsum()

#         return (
#             x
#             .groupby(groups)
#             .cumsum()
#             .max()
#         )

#     feature_col = f"f_order_value_decline_streak_l{quarters_window}q"


#     result_df = (
#         quarter_df
#         .groupby("cus_id")["is_decline"]
#         .apply(max_streak)
#         .fillna(0)
#         .astype(int)
#         .reset_index(name=feature_col)
#     )

#     save_to_minio(
#         result_df,
#         object_name=f"{month_prefix}/{month_partition_key}={month}/data.parquet",
#     )

#     return result_df


def transform_order_value_decline_streak_lxm(
    month: str,
    months_window: int,
    day_prefix: str,
    month_prefix: str,
    day_partition_key: str,
    month_partition_key: str,
) -> pd.DataFrame:
    """
    Đếm chuỗi tháng giảm doanh thu liên tục dài nhất.

    Logic:
    - Xét N tháng gần nhất.
    - Tổng value theo tháng.
    - Tháng thiếu fill = 0.0001.
    - Giảm >= 20% so với tháng trước được đánh dấu.
    - Tính streak giảm dài nhất.

    Trả về: cus_id, f_order_value_decline_streak_l{N}m
    """
    start_month = (pd.Period(month, freq="M") - months_window + 1).strftime("%Y%m")

    start_date = month_date_range(start_month)[0]
    end_date = month_date_range(month)[1]


    day_df = extract_data_by_range(
        start_date,
        end_date,
        prefix=day_prefix,
        day_partition_key=day_partition_key,
    )

    day_df["month"] = (day_df[day_partition_key].astype(str).str[:6].astype(int))


    monthly_df = (
        day_df
        .groupby(
            ["cus_id", "month"],
            as_index=False
        )
        .agg(
            monthly_value=("value", "sum")
        )
    )

    # ============================
    # Fill đủ tháng bị thiếu
    # tạo all cus_id x all month để xử lí tháng ko phát sinh doanh thu-> fill 0.0001
    # ============================
    full_df = (
    monthly_df
    .set_index(["cus_id", "month"])
    .reindex(
        pd.MultiIndex.from_product(
            [
                monthly_df["cus_id"].unique(),
                pd.period_range(
                    start=pd.Period(start_month, freq="M"),
                    end=pd.Period(month, freq="M"),
                    freq="M",
                )
                .strftime("%Y%m")
                .astype(int),
            ],
            names=["cus_id", "month"],
        ),
        fill_value=0.0001,
    )
    .reset_index()
)

    # ============================
    # Tính % giảm so với tháng trước
    # ============================

    full_df = full_df.sort_values(["cus_id","month"])

    full_df["prev_value"] = (
        full_df
        .groupby("cus_id")["monthly_value"]
        .shift(1)
    )

    full_df["is_decline"] = (
        (
            full_df["monthly_value"]
            /
            full_df["prev_value"]
            -
            1
        )
        <= -0.2
    )

    # ============================
    # Hàm tính streak
    # ============================
    def max_streak(series):

        groups = (
            series != series.shift()
        ).cumsum()

        return (
            series
            .groupby(groups)
            .cumsum()
            .max()
        )

    feature_col =  f"f_order_value_decline_streak_l{months_window}m"


    result_df = (
        full_df
        .groupby("cus_id")["is_decline"]
        .apply(max_streak)
        .fillna(0)
        .astype(int)
        .reset_index(name=feature_col)
    )

    # Giới hạn streak tối đa 5 tháng
    result_df[feature_col] = (
        result_df[feature_col]
        .clip(0, 5)
)
    save_to_minio(
        result_df,
        object_name=f"{month_prefix}/{month_partition_key}={month}/data.parquet",
    )

    return result_df