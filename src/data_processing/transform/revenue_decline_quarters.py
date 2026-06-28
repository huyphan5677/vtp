from __future__ import annotations

import pandas as pd

from src.utils.common import with_config


@with_config("rules.yaml")
def transform_revenue_decline_last_n_quarters(
    df: pd.DataFrame, column_name: str, config=None, scoring_month=None
) -> pd.DataFrame:
    """Xử lý cột tong_tien - Rule: Giảm doanh thu 03 quý gần nhất.

    Logic: Doanh thu KHÔNG giảm liên tục 30% so với quý liền kề trước đó.
    (Giảm so với quý trước đó 30%: Q1 < 70%Q2 < 70%Q3 -- Q1 là quý gần nhất)
    -> Trả về 0 nếu VI PHẠM (tức là có giảm liên tục), 1 nếu OK (không giảm liên tục)

    Args:
        df (pd.DataFrame): Bảng chứa dữ liệu giao dịch.
        column_name (str): Tên cột chứa doanh thu.
        config (dict): Config từ rules.yaml.
        scoring_month (str): Tháng tính toán, định dạng 'YYYYMM'.

    Returns:
        pd.DataFrame: Bảng chứa dữ liệu.
    """
    rule_config = config.get("revenue_decline_last_3_quarters", {})
    decline_threshold = rule_config.get("decline_pct", 0.3)  # 30%

    temp_df = df.copy()
    temp_df["month"] = pd.to_datetime(temp_df["month"], format="%Y%m")

    # Chuyển đổi sang dữ liệu Quý (Quarter) và tính tổng doanh thu theo Quý
    temp_df["quarter"] = temp_df["month"].dt.to_period("Q")

    # Xác định 3 quý gần nhất dựa trên scoring_month trong time.yaml
    scoring_date = pd.to_datetime(scoring_month, format="%Y%m")

    # Quý chứa scoring_month (Ví dụ 09/2022 -> Q3/2022)
    current_quarter = scoring_date.to_period("Q")

    # logic: Lấy 3 quý HOÀN CHỈNH gần nhất (không tính quý chứa scoring_month)
    # Ví dụ: Max date = 07/2022 (Q3) -> Lấy Q2/2022, Q1/2022, Q4/2021
    target_quarters = [current_quarter - i for i in range(1, 4)]
    # target_quarters sẽ là [Q_prev, Q_prev2, Q_prev3] -> Tương ứng Q1, Q2, Q3 trong công thức

    print(
        "Các quý được xét trong transform_revenue_decline_last_3_quarters:",
        [str(q) for q in target_quarters],
    )

    # Lọc dữ liệu chỉ nằm trong 3 quý này
    quarter_df = (
        temp_df[temp_df["quarter"].isin(target_quarters)]
        .groupby(["cus_id", "quarter"])[column_name]
        .sum()
        .reset_index()
    )

    # Pivot để có các cột Q1, Q2, Q3 cho mỗi user (để dễ so sánh cột)
    # Tạo bảng khung đủ 3 quý cho mỗi user
    unique_users = temp_df["cus_id"].unique()
    index_df = pd.MultiIndex.from_product(
        [unique_users, target_quarters], names=["cus_id", "quarter"]
    ).to_frame(index=False)

    merged_q_df = index_df.merge(
        quarter_df, on=["cus_id", "quarter"], how="left"
    )
    merged_q_df[column_name] = merged_q_df[column_name].fillna(0)

    # Pivot: Index là cus_id, Columns là Quarter, Values là tong_tien
    pivoted = merged_q_df.pivot(
        index="cus_id", columns="quarter", values=column_name
    )

    # Sắp xếp cột theo thời gian tăng dần: Q3(cũ nhất) -> Q2 -> Q1(mới nhất)
    pivoted = pivoted.sort_index(axis=1)

    cols = pivoted.columns  # [Q_oldest, Q_middle, Q_newest] ~ [Q3, Q2, Q1]

    # tính phần trăm thay đổi so với tháng trước
    def calculate_percentage_with_prev(row, prev_col, curr_col):
        # Lấy giá trị của cột từ row
        prev_val = row[prev_col]
        curr_val = row[curr_col]

        if prev_val == 0 and curr_val == 0:
            return 0.0
        if prev_val == 0:
            return 1.0

        return (curr_val - prev_val) / prev_val

    # tạo ra các cột chênh lệch doanh thu ở đoạn này
    # Lưu ý: cols[2] là Q1 (mới nhất), cols[1] là Q2, cols[0] là Q3 (cũ nhất)
    # diff_pct_q1_q2 = (Q1 - Q2) / Q2
    pivoted["diff_pct_q1_q2"] = pivoted.apply(
        lambda row: calculate_percentage_with_prev(row, cols[1], cols[2]),
        axis=1,
    )
    # diff_pct_q2_q3 = (Q2 - Q3) / Q3
    pivoted["diff_pct_q2_q3"] = pivoted.apply(
        lambda row: calculate_percentage_with_prev(row, cols[0], cols[1]),
        axis=1,
    )

    def check_violation(row):
        """Kiểm tra vi phạm: Nếu cả 2 lần so sánh đều giảm >= 30% thì vi phạm (return 0)"""
        if (
            row["diff_pct_q1_q2"] < -decline_threshold
            and row["diff_pct_q2_q3"] < -decline_threshold
        ):
            return 0
        return 1

    def count_consecutive_decline_quarters(row):
        """Đếm số quý giảm LIÊN TỤC >=30% so với quý trước, tính từ quý gần nhất (Q1).

        Logic:
        - Bắt đầu từ Q1 (mới nhất), kiểm tra Q1 có giảm >=30% so với Q2 không
        - Nếu có, tiếp tục kiểm tra Q2 có giảm >=30% so với Q3 không
        - Nếu chuỗi bị đứt (quý nào đó không giảm >=30%), dừng đếm

        Ví dụ:
        - Q3=100, Q2=60, Q1=40 → Q1 giảm 33%, Q2 giảm 40% → chuỗi = 2
        - Q3=100, Q2=90, Q1=60 → Q1 giảm 33%, Q2 không giảm (10%) → chuỗi = 1
        - Q3=100, Q2=60, Q1=55 → Q1 không giảm (8%), chuỗi đứt → chuỗi = 0
        """
        consecutive_count = 0

        # Bước 1: Kiểm tra Q1 có giảm >=30% so với Q2 không
        if row["diff_pct_q1_q2"] < -decline_threshold:
            consecutive_count += 1

            # Bước 2: Nếu Q1 giảm, tiếp tục kiểm tra Q2 có giảm >=30% so với Q3 không
            if row["diff_pct_q2_q3"] < -decline_threshold:
                consecutive_count += 1

        return str(consecutive_count)

    pivoted["revenue_decline_last_3_quarters"] = pivoted.apply(
        check_violation, axis=1
    )
    pivoted["score_6"] = pivoted.apply(
        count_consecutive_decline_quarters, axis=1
    )
    pivoted["score_6"] = pivoted["score_6"].fillna("0")

    return pivoted[["revenue_decline_last_3_quarters", "score_6"]].reset_index()
