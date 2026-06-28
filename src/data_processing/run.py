from __future__ import annotations

import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from loguru import logger

from src.utils import common as utils
from src.utils.common import with_config
from src.utils.extract import (
    extract_day_data,
    extract_data_by_date,
    extract_scoring_data,
)
from src.utils.minio_client import (
    load_data_to_minio,
    load_clean_data_to_minio,
)
from src.utils.grouping_data import group_data_by_month
from src.utils.postgres_client import load_data_to_postgres
from src.data_processing.preprocesssor import (
    main_pipeline_day,
)
from src.data_processing.transform.age import (
    transform_nam_tuoi,
    feature_engineering_date_of_birth,
)
from src.data_processing.transform.gmv import (
    transform_gmv_3th,
    transform_gmv_12th,
)
from src.data_processing.transform.avg_order_count import (
    transform_avg_success_order_count_per_month,
)
from src.data_processing.transform.avg_order_value import (
    transform_avg_success_order_value_per_month,
    transform_total_success_order_value_per_month,
)
from src.data_processing.transform.sales_region_latest import (
    transform_sales_region,
)
from src.data_processing.transform.usage_duration_months import (
    transform_usage_duration_months,
    feature_engineering_usage_duration,
)
from src.data_processing.transform.revenue_decline_months import (
    transform_revenue_decline_last_n_months,
)
from src.data_processing.transform.revenue_decline_quarters import (
    transform_revenue_decline_last_n_quarters,
)
from src.data_processing.transform.success_order_all_months import (
    transform_success_order_all_months,
)
from src.data_processing.transform.active_months_with_orders import (
    transform_total_success_order,
)


def main_pipeline_by_day(date: str) -> pd.DataFrame:
    """Xử lý dữ liệu theo ngày.

    xuất ra file parquet dữ liệu được xử lý

    Returns:
        pd.DataFrame: Dữ liệu được xử lý
    """
    logger.info(f"Start pipeline day data for {date}")
    day_data = extract_day_data(date)
    day_data = main_pipeline_day(day_data)
    day_data = feature_engineering_date_of_birth(day_data, "ngay_sinh")
    day_data = feature_engineering_usage_duration(day_data, "ngay_hoptac")

    # Save data to minio
    load_clean_data_to_minio(folder_name="hitech_day", date=date, data=day_data)
    logger.info(f"Pipeline day data completed for {date}")

    return day_data


def main_pipeline_by_month(start_date, end_date):
    """Xử lý dữ liệu theo tháng.

    xuất ra file parquet dữ liệu được xử lý
    """
    logger.info(f"Start grouping data from {start_date} to {end_date}")
    df = extract_data_by_date(start_date, end_date)

    # Group data by month and save to minio
    group_data_by_month(df)


@with_config("rules.yaml")
def main_transform_data(df, config=None, scoring_month=None) -> pd.DataFrame:
    """Transform raw data to feature data by applying rule-based transformations.

    Args:
        df (pd.DataFrame): Raw data to be transformed.
        config (dict): Configuration for the transformation.
        scoring_month (str): Scoring month.

    Returns:
        pd.DataFrame: Transformed data.
    """
    logger.info("Start transform data")
    df_age = transform_nam_tuoi(df, "nam_tuoi", config=config)
    df_usage_duration_months = transform_usage_duration_months(
        df, "so_thang_hdong", config=config
    )
    df_sales_region = transform_sales_region(
        df, "ma_tinh_hoatdong_chinh", config=config
    )
    df_avg_success_order_value_per_month = (
        transform_avg_success_order_value_per_month(
            df, "tong_tien", config=config
        )
    )
    df_total_success_order_value_per_month = (
        transform_total_success_order_value_per_month(
            df, "tong_tien", config=config
        )
    )
    df_avg_success_order_count_per_month = (
        transform_avg_success_order_count_per_month(
            df, "don_ptc", config=config
        )
    )
    df_revenue_decline_last_n_quarters = (
        transform_revenue_decline_last_n_quarters(
            df, "tong_tien", config=config, scoring_month=scoring_month
        )
    )
    df_transform_revenue_decline_last_n_months = (
        transform_revenue_decline_last_n_months(df, "tong_tien", config=config)
    )
    df_total_success_order = transform_total_success_order(
        df, "tong_tien", config=config
    )
    df_success_ord_all_months = transform_success_order_all_months(
        df, "don_ptc", config=config
    )
    df_gmv_12th = transform_gmv_12th(df, config=config)
    df_gmv_3th = transform_gmv_3th(df, config=config)

    # Join tất cả các dataframe lại theo cus_id
    result_df = (
        df_age
        .merge(df_usage_duration_months, on="cus_id", how="outer")
        .merge(df_sales_region, on="cus_id", how="outer")
        .merge(df_avg_success_order_value_per_month, on="cus_id", how="outer")
        .merge(df_total_success_order_value_per_month, on="cus_id", how="outer")
        .merge(df_avg_success_order_count_per_month, on="cus_id", how="outer")
        .merge(df_revenue_decline_last_n_quarters, on="cus_id", how="outer")
        .merge(df_total_success_order, on="cus_id", how="outer")
        .merge(
            df_transform_revenue_decline_last_n_months, on="cus_id", how="outer"
        )
        .merge(df_success_ord_all_months, on="cus_id", how="outer")
        .merge(df_gmv_12th, on="cus_id", how="outer")
        .merge(df_gmv_3th, on="cus_id", how="outer")
    )

    # Điền null cho các cột score
    # Với các cột score_1, score_2, score_5 số thì ta sẽ thay null là 010 với
    # 01: dành cho số 0, flat là 0
    result_df["score_1"] = result_df["score_1"].fillna("010")
    result_df["score_2"] = result_df["score_2"].fillna("010")
    result_df["score_5"] = result_df["score_5"].fillna("010")
    result_df["score_3"] = result_df["score_3"].fillna("0")
    result_df["score_4"] = result_df["score_4"].fillna("0001")

    # Với null (các cột boolean thôi) thì ta sẽ fill = 0
    result_df = result_df.fillna(0)

    # Đổi lại thành user_id cho đồng bộ
    result_df = result_df.rename(columns={"cus_id": "user_id"})

    # Sửa lỗi user_id bị .0 nếu còn xảy ra, UNCOMMENT dòng này nếu như không bị nữa nhé
    # result_df["user_id"] = result_df["user_id"].replace(r'\.0$', '', regex=True)

    # Tính score
    # result_df["behavior_score"] = "0." + result_df["score_1"] + result_df["score_5"]
    # result_df["gvm_score"] = "0." + result_df["score_2"] + result_df["score_3"] + result_df["score_4"]

    # result_df["trend_score"] = (
    #     result_df["score_6"]
    #     .astype(str)
    #     .str.cat(result_df["score_7"].astype(str))
    #     .radd("0.")
    # )
    result_df = result_df.drop(["total_success_order_value_per_month"], axis=1)
    result_df = result_df.rename(
        columns={
            "gmv_12th": "gvm_score",
            "gmv_3th": "trend_score",
            "usage_duration_group": "behavior_score",
            "success_order_all_months": "total_success_order_value_per_month",
        }
    )

    # Assign cac column ma rule v2 khong dung nua ve 0 de de phan biet
    for col in [
        "avg_success_order_count_per_month",
        "avg_success_order_value_per_month",
        "revenue_decline_last_3_quarters",
        "revenue_decline_last_4_months",
    ]:
        result_df[col] = 0

    # Xóa đi các cột score thừa
    result_df = result_df[result_df.gvm_score >= 100]
    result_df = result_df.drop(
        columns=[
            "score_1",
            "score_2",
            "score_3",
            "score_4",
            "score_5",
            "score_6",
            "score_7",
        ]
    )  # "behavior_score", "gvm_score", "trend_score"

    # Khong dung score col + age de danh gia
    recommend_columns = [
        "sales_region",
        "usage_duration_months",
        "total_success_order_value_per_month",
    ]
    result_df["recommendation"] = (
        (result_df[recommend_columns] == 1).all(axis=1).astype(int)
    )

    # Tạm thời fake các cột sau
    result_df["score"] = "0"
    result_df["rule_score"] = np.random.randint(0, 2, size=result_df.shape[0])
    result_df["phone"] = "09" + result_df["user_id"].astype(
        str
    )  # tạm thời là lấy 0 + user_id
    result_df["date"] = datetime.now().strftime("%Y-%m-%d")
    result_df["model_version"] = "v2.0.0"

    return result_df


def main_pipeline_scoring(scoring_month):
    # Extract data
    df = extract_scoring_data(scoring_month)

    # Transform data
    df = main_transform_data(df, scoring_month=scoring_month)

    # Load data
    load_data_to_minio(df, scoring_month=scoring_month)
    load_data_to_postgres(df)


if __name__ == "__main__":
    # Lấy tham số từ command line
    args_string = " ".join(sys.argv[1:])
    logger.info("Processing arguments...")

    # Xử lý tham số
    args = utils.process_args_to_dict(args_string)
    start_date_str = args["dt_from"]
    end_date_str = args["dt_to"]
    logger.info("Parsed ARGS in run_create_feature: %s", args)

    # Chuyển tham số sang dạng datetime
    start_date = datetime.strptime(start_date_str, "%Y%m%d")
    end_date = datetime.strptime(end_date_str, "%Y%m%d")

    # Xử lý theo ngày
    logger.info(f"Start pipeline day from {start_date} to {end_date}")
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        main_pipeline_by_day(date_str)
        current_date += timedelta(days=1)

    # Xử lý theo tháng - chỉ chạy các tháng có đủ dữ liệu
    current_month = start_date.replace(day=1)  # => datetime format %Y%m01
    while current_month <= end_date:
        # Tính ngày cuối tháng
        if current_month.month == 12:
            next_month = current_month.replace(
                year=current_month.year + 1, month=1
            )
        else:
            next_month = current_month.replace(month=current_month.month + 1)
        month_end = next_month - timedelta(days=1)

        # Chỉ chạy nếu end_date >= ngày cuối tháng (đủ dữ liệu cả tháng)
        if end_date >= month_end:
            logger.info(
                f"Processing month: {current_month.strftime('%Y%m')} "
                f"({current_month.strftime('%Y%m%d')} -> "
                f"{month_end.strftime('%Y%m%d')})"
            )
            main_pipeline_by_month(
                current_month.strftime("%Y%m%d"),
                month_end.strftime("%Y%m%d"),
            )
        else:
            logger.info(
                f"Skipping month: {current_month.strftime('%Y%m')} "
                f"(chưa đủ dữ liệu, end_date="
                f"{end_date.strftime('%Y%m%d')} < "
                f"{month_end.strftime('%Y%m%d')})"
            )

        current_month = next_month

    # Tính toán scoring
    scoring_month = args.get("scoring_month")
    if scoring_month:
        main_pipeline_scoring(scoring_month)
