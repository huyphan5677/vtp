from __future__ import annotations

import sys
import inspect
import importlib
from datetime import datetime, timedelta
from functools import reduce

import pandas as pd
from loguru import logger

from src.utils import common as utils
from src.utils.common import load_config
from src.utils.minio_client import save_to_minio, read_minio_parquet


FEATURES_CONFIG_FILE = "features.yaml"


def _get_global_config() -> dict:
    """Lấy config chung (áp dụng cho mọi feature) từ features.yaml."""
    return load_config(FEATURES_CONFIG_FILE).get("config", {})


def _get_feature_config(feature_name: str) -> dict:
    """Lấy config của 1 feature theo tên (name) từ features.yaml."""
    for feature_cfg in load_config(FEATURES_CONFIG_FILE)["features"]:
        if feature_cfg["name"] == feature_name:
            return feature_cfg
    raise ValueError(
        f"Không tìm thấy feature '{feature_name}' trong features.yaml"
    )


def _get_day_feature_config(day_feature: str) -> dict:
    """Trả về feature config đại diện cho 1 day_feature.

    Nhiều rule instance (name) có thể dùng chung 1 day_feature (ví dụ
    order_l3m/order_l6m dùng chung "order") — chỉ cần tìm 1 entry khớp.
    """
    for feature_cfg in load_config(FEATURES_CONFIG_FILE)["features"]:
        if feature_cfg["day_feature"] == day_feature:
            return feature_cfg
    raise ValueError(
        f"Không tìm thấy day_feature '{day_feature}' trong features.yaml"
    )


def _call_with_declared_kwargs(func, *args, **candidate_kwargs) -> None:
    """Gọi func(*args, **kwargs) chỉ với các kwargs mà func khai báo.

    Cho phép gộp chung config (day_prefix, input, config chung...) rồi mỗi
    hàm tự lấy đúng phần mình cần, không phải sửa chỗ gọi khi thêm/bớt tham số.
    """
    sig_params = inspect.signature(func).parameters
    kwargs = {k: v for k, v in candidate_kwargs.items() if k in sig_params}
    return func(*args, **kwargs)


def run_feature_day(day_feature: str, dt_from: str, dt_to: str) -> None:
    """Giai đoạn ngày: chạy day_function cho từng ngày trong [dt_from, dt_to].

    day_function tự đọc raw, tự làm sạch, tự lưu — ở đây chỉ tra config rồi
    lặp qua từng ngày gọi, không phụ thuộc feature/ngày khác.
    """
    feature_cfg = _get_day_feature_config(day_feature)
    module = importlib.import_module(feature_cfg["module"])
    func = getattr(module, feature_cfg["day_function"])

    candidate_kwargs = {
        "day_prefix": feature_cfg.get("day_prefix"),
        **_get_global_config(),
    }

    current_date = datetime.strptime(dt_from, "%Y%m%d")
    end_date = datetime.strptime(dt_to, "%Y%m%d")
    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        logger.info(f"Start day-feature '{day_feature}' for date={date_str}")
        _call_with_declared_kwargs(func, date_str, **candidate_kwargs)
        current_date += timedelta(days=1)


def run_feature(feature_name: str, month: str) -> None:
    """Giai đoạn tháng (có window): chạy 1 rule instance theo config.

    function tự load N tháng dữ liệu ngày đã clean, tự tính, tự lưu — ở đây
    chỉ tra config rồi gọi.
    """
    feature_cfg = _get_feature_config(feature_name)
    module = importlib.import_module(feature_cfg["module"])
    func = getattr(module, feature_cfg["function"])

    candidate_kwargs = {
        "day_prefix": feature_cfg.get("day_prefix"),
        "month_prefix": feature_cfg.get("month_prefix"),
        **feature_cfg.get("input", {}),
        **_get_global_config(),
    }

    logger.info(f"Start feature '{feature_name}' for month={month}")
    _call_with_declared_kwargs(func, month, **candidate_kwargs)
    logger.info(f"Feature '{feature_name}' completed")


def _months_to_score(dt_from: str, dt_to: str) -> list[str]:
    """Các tháng (YYYYMM) cần tính trong khoảng [dt_from, dt_to].

    Pipeline chạy hàng ngày, xử lý theo ngày; mỗi khi gặp ngày đầu tháng thì
    tháng LIỀN TRƯỚC ngày đó coi như đã đủ dữ liệu cả tháng nên cần tính.
    Ví dụ dt_from=20251201, dt_to=20260308 gặp 4 ngày đầu tháng
    (20251201, 20260101, 20260201, 20260301) -> cần tính 4 tháng
    (202511, 202512, 202601, 202602).
    """
    current_date = datetime.strptime(dt_from, "%Y%m%d")
    end_date = datetime.strptime(dt_to, "%Y%m%d")

    months = []
    while current_date <= end_date:
        if current_date.day == 1:
            prev_month_date = current_date - timedelta(days=1)
            months.append(prev_month_date.strftime("%Y%m"))
        current_date += timedelta(days=1)
    return months


def run_feature_range(feature_name: str, dt_from: str, dt_to: str) -> None:
    """Chạy giai đoạn tháng cho MỌI tháng cần tính trong [dt_from, dt_to].

    Dùng cho DAG chạy hàng ngày: đa số ngày sẽ không có tháng nào cần tính
    (danh sách rỗng, không làm gì); chỉ ngày đầu tháng mới có 1 tháng cần
    tính (tháng liền trước) — hoặc nhiều tháng hơn nếu chạy backfill 1
    khoảng ngày dài.
    """
    months = _months_to_score(dt_from, dt_to)
    if not months:
        logger.info(
            f"Không có tháng nào cần tính cho feature '{feature_name}' "
            f"trong [{dt_from}, {dt_to}]"
        )
        return

    for month in months:
        run_feature(feature_name, month)


def merge_features_for_month(month: str) -> pd.DataFrame:
    """Ghép kết quả giai đoạn tháng của MỌI feature trong 1 tháng lại theo
    cus_id, lưu xuống `merged_prefix`/`month_partition_key`={month}/.
    """
    global_cfg = _get_global_config()
    month_partition_key = global_cfg["month_partition_key"]

    feature_dfs = []
    for feature_cfg in load_config(FEATURES_CONFIG_FILE)["features"]:
        prefix = f"{feature_cfg['month_prefix']}/{month_partition_key}={month}"
        feature_dfs.append(read_minio_parquet(prefix))

    merged_df = reduce(
        lambda left, right: left.merge(right, on="cus_id", how="outer"),
        feature_dfs,
    )

    save_to_minio(
        merged_df,
        object_name=(
            f"{global_cfg['merged_prefix']}/{month_partition_key}={month}/data.parquet"
        ),
    )
    return merged_df


def run_merge_range(dt_from: str, dt_to: str) -> None:
    """Ghép feature cho MỌI tháng cần tính trong [dt_from, dt_to] (giống
    danh sách tháng mà run_feature_range đã tính ở giai đoạn tháng).
    """
    months = _months_to_score(dt_from, dt_to)
    if not months:
        logger.info(f"Không có tháng nào cần ghép trong [{dt_from}, {dt_to}]")
        return

    for month in months:
        logger.info(f"Start merge features for month={month}")
        merge_features_for_month(month)
        logger.info(f"Merge features completed for month={month}")


if __name__ == "__main__":
    # Lấy tham số từ command line
    args_string = " ".join(sys.argv[1:])
    logger.info("Processing arguments...")

    args = utils.process_args_to_dict(args_string)
    logger.info("Parsed ARGS in run_create_feature: %s", args)

    mode = args.get("mode")

    if mode == "feature_day":
        day_feature = args.get("day_feature")
        dt_from = args.get("dt_from")
        dt_to = args.get("dt_to")
        if not day_feature or not dt_from or not dt_to:
            raise ValueError(
                "--day_feature, --dt_from và --dt_to là bắt buộc khi "
                "--mode feature_day"
            )
        run_feature_day(day_feature, dt_from, dt_to)

    elif mode == "feature":
        feature_name = args.get("feature_name")
        dt_from = args.get("dt_from")
        dt_to = args.get("dt_to")
        if not feature_name or not dt_from or not dt_to:
            raise ValueError(
                "--feature_name, --dt_from và --dt_to là bắt buộc khi "
                "--mode feature"
            )
        run_feature_range(feature_name, dt_from, dt_to)

    elif mode == "merge":
        dt_from = args.get("dt_from")
        dt_to = args.get("dt_to")
        if not dt_from or not dt_to:
            raise ValueError(
                "--dt_from và --dt_to là bắt buộc khi --mode merge"
            )
        run_merge_range(dt_from, dt_to)

    else:
        raise ValueError(
            f"--mode không hợp lệ: '{mode}' (chỉ nhận feature_day, feature "
            "hoặc merge)"
        )
