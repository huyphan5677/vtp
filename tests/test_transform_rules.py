import pandas as pd

from src.data_processing.transform.scoring import (
    transform_gmv,
    transform_recommendation,
    transform_sales_region,
    transform_success_order_all_months,
    transform_usage_duration_months,
)


def test_usage_duration_rule_and_behavior_score():
    df = pd.DataFrame(
        {
            "cus_id": ["A", "A", "B"],
            "so_thang_hdong": [2, 8, 20],
        }
    )

    result = transform_usage_duration_months(df)

    assert result.loc[result["cus_id"] == "A", "usage_duration_months"].item() == 1
    assert result.loc[result["cus_id"] == "A", "behavior_score"].item() == "02"
    assert result.loc[result["cus_id"] == "B", "usage_duration_months"].item() == 1
    assert result.loc[result["cus_id"] == "B", "behavior_score"].item() == "04"


def test_sales_region_rule_uses_latest_record():
    df = pd.DataFrame(
        {
            "cus_id": ["A", "A"],
            "ma_tinh_hoatdong_chinh": [1, 999],
            "month": [202501, 202502],
        }
    )

    result = transform_sales_region(df, month_col="month")

    assert result.loc[result["cus_id"] == "A", "sales_region"].item() == 0


def test_success_order_all_months_requires_full_window():
    df = pd.DataFrame(
        {
            "cus_id": ["A"] * 4,
            "month": [202501, 202502, 202503, 202504],
            "don_ptc": [1, 1, 1, 1],
        }
    )

    result = transform_success_order_all_months(df, month_col="month")

    assert result.loc[0, "success_order_all_months"] == 1


def test_gmv_transform_returns_numeric_score():
    df = pd.DataFrame(
        {
            "cus_id": ["A"],
            "don_ptc": [100],
            "tong_tien": [10_000_000],
            "thu_ho": [1_000_000],
            "thuho_tongdon": [1_000_000],
            "don_ptc_cod": [50],
            "tongdon_cod": [50],
            "tong_don": [100],
        }
    )

    result = transform_gmv(df, median_ratio_cod=1.0)

    assert result.loc[0, "gvm_score"] > 0


def test_recommendation_is_true_when_all_conditions_met():
    df = pd.DataFrame(
        {
            "cus_id": ["A"],
            "gvm_score": [100],
            "sales_region": [1],
            "usage_duration_months": [1],
            "total_success_order_value_per_month": [1],
        }
    )

    result = transform_recommendation(df)

    assert result.loc[0, "recommendation"] == 1
