# import pandas as pd
# import numpy as np
# from src.scripts.utils.useful_wrapper import with_config
# from src.scripts.utils.load_config import load_config
# from datetime import datetime
# from src.scripts.utils.bining import binning_data

# @with_config("rules.yaml")
# def transform_nam_tuoi(df: pd.DataFrame, column_name: str, config=None) -> pd.DataFrame:
#     """
#     Xử lý cột nam_tuoi
#     -> trả về bảng age với 2 cột: cus_id và age
#     """
#     # đọc config
#     age_rule = config.get("age", {})
#     min_age = age_rule.get("min")
#     max_age = age_rule.get("max")
    
#     df_age = df.groupby("cus_id").agg({column_name: "max"}).reset_index()
#     df_age["age"] = np.where((df_age[column_name] >= min_age) & (df_age[column_name] <= max_age), 1, 0)
#     return df_age[["cus_id", "age"]]

# @with_config("rules.yaml")
# def transform_sales_region(df: pd.DataFrame, column_name: str, config=None) -> pd.DataFrame:
#     """
#     Xử lý cột sales_region
#     -> trả về bảng sales_region với 2 cột: cus_id và sales_region
#     """
#     sales_region_rule = config.get("sales_region", {})
#     valid_sales_region = sales_region_rule.get("valid", [])
    
#     temp_df = df.copy()
#     temp_df["month"] = pd.to_datetime(temp_df["month"], format="%Y%m")
#     temp_df["month"] = temp_df["month"].dt.to_period("M")
    
#     # Lấy tháng cuối cùng được ghi nhận của mỗi khách hàng
#     newest_month_per_cus = temp_df.groupby("cus_id")["month"].max().reset_index()
#     newest_month_per_cus.columns = ["cus_id", "max_month"]
    
#     # Merge để lấy sales_region ghi nhận tại tháng cuối cùng của mỗi khách hàng
#     temp_df = temp_df.merge(newest_month_per_cus, on="cus_id")
#     current_region_df = temp_df[temp_df["month"] == temp_df["max_month"]][["cus_id", column_name]].drop_duplicates()
    
#     # Kiểm tra khu vực hiện tại có nằm trong danh sách hợp lệ không
#     current_region_df["sales_region"] = current_region_df[column_name].isin(valid_sales_region).astype(int)
#     # return current_region_df[["cus_id", "sales_region"]]

#     # Group by cus_id để kiểm tra thuộc 1 trong 48 tỉnh là được
#     result_df = current_region_df.groupby("cus_id")["sales_region"].max().reset_index()

#     return result_df

# @with_config("rules.yaml")
# def transform_usage_duration_months(df: pd.DataFrame, column_name: str, config=None) -> pd.DataFrame:
#     """
#     Xử lý cột usage_duration_months
#     -> trả về bảng usage_duration_months với 3 cột: cus_id, tgian_hdong_chinh, và usage_duration_months
#     """
#     usage_duration_months_rule = config.get("usage_duration_months", {})
#     min_usage_duration_months = usage_duration_months_rule.get("min")
    
#     df_usage_duration_months = df.groupby("cus_id").agg({column_name: "max"}).reset_index()
#     df_usage_duration_months["usage_duration_months"] = np.where(df_usage_duration_months[column_name] >= min_usage_duration_months, 1, 0)

#     # tạo score cho rule 1 
#     df_usage_duration_months["score_1"] = binning_data(df_usage_duration_months,column_name,20) + df_usage_duration_months["usage_duration_months"].astype("str")
    
#     return df_usage_duration_months[["cus_id", "usage_duration_months", "score_1"]]

# @with_config("rules.yaml")
# def transform_avg_success_order_value_per_month(df: pd.DataFrame, column_name: str, config=None) -> pd.DataFrame:
#     """
#     Xử lý cột tong_tien
#     -> trả về bảng avg_success_order_value_per_month với 3 cột: cus_id, month (đếm số tháng hđ),tong_tien (Trung bình) và avg_success_order_value_per_month
#     """
#     months_window = config.get("avg_success_order_value_per_month", {}).get("months_window")
#     min_avg_success_order = config.get("avg_success_order_value_per_month", {}).get("min")
#     # đầu tiên cần lấy ra tháng cao nhất
#     temp_df = df.copy()
    
#     temp_df["month"] = pd.to_datetime(temp_df["month"], format="%Y%m")
#     temp_df["month"] = temp_df["month"].dt.to_period("M")
#     max_month = temp_df["month"].max()
    
#     # Chỉ trích xuất X tháng gần nhất
#     min_month = max_month - months_window + 1 # phải cộng 1 vì như này: ví dụ tháng 
#                                               # 12 thì phải trích xuất 6 tháng gần nhất từ tháng 7 đến tháng 12
    
#     print("Tính toán avg_success_order_value_per_month xét từ tháng", min_month, "đến tháng", max_month)

#     # tinh tong tien o tat ca chi nhanh va thang hoat dong
#     df_avg_success_order_value_per_month = temp_df[temp_df["month"].between(min_month, max_month)].groupby("cus_id").agg({column_name: "sum", "month": "nunique"}).reset_index()
    
#     # tinh trung binh tien theo thang
#     df_avg_success_order_value_per_month["avg_success_order_value_per_month"] = df_avg_success_order_value_per_month[column_name] / df_avg_success_order_value_per_month["month"]
    
#     # Hơn nữa nếu số tháng ghi nhận được từ khách hàng < 6 tháng thì trả về 0
#     df_avg_success_order_value_per_month["avg_success_order_value_per_month"] = np.where((df_avg_success_order_value_per_month["avg_success_order_value_per_month"] >= min_avg_success_order) & (df_avg_success_order_value_per_month["month"] == months_window), 1, 0)

#     df_avg_success_order_value_per_month["score_2"] = \
#                     binning_data(df_avg_success_order_value_per_month,column_name,20) + df_avg_success_order_value_per_month["avg_success_order_value_per_month"].astype("str")
    
#     return df_avg_success_order_value_per_month[["cus_id", "avg_success_order_value_per_month", "score_2"]]

# @with_config("rules.yaml")
# def transform_total_success_order_value_per_month(df: pd.DataFrame, column_name: str, config=None) -> pd.DataFrame:
#     """
#     Xử lý cột tong_tien
#     -> trả về bảng total_success_order_value_per_month với 3 cột: cus_id, month (đếm số tháng hđ),tong_tien (Tối thiểu) và total_success_order_value_per_month
#     """
#     months_window = config.get("total_success_order_value_per_month", {}).get("months_window")
#     min_total_success_order = config.get("total_success_order_value_per_month", {}).get("min")
#     # đầu tiên cần lấy ra tháng cao nhất
#     temp_df = df.copy()
#     temp_df["month"] = pd.to_datetime(temp_df["month"], format="%Y%m")
#     temp_df["month"] = temp_df["month"].dt.to_period("M")
#     max_month = temp_df["month"].max()
    
#     # Chỉ trích xuất X tháng gần nhất
#     min_month = max_month - months_window + 1 # phải cộng 1 vì như này: ví dụ tháng 
#                                               # 12 thì phải trích xuất 6 tháng gần nhất từ tháng 7 đến tháng 12
#     print("Tính toán total_success_order_value_per_month xét từ tháng", min_month, "đến tháng", max_month)
#     valid_data_range = temp_df[temp_df["month"].between(min_month, max_month)]

#     # tinh tong tien theo thang o tat ca chi nhanh
#     total_success_order_value_per_month = valid_data_range.groupby(["cus_id", "month"]).agg({
#                                                                 column_name: "sum"}).reset_index()
#     # tinh doanh thu thap nhat theo thang va so thang hoat dong
#     result = total_success_order_value_per_month.groupby("cus_id").agg(min_value_per_month=(column_name,"min"), active_months=("month","nunique")).reset_index()
    
#     # Tạo cột is_success: Nêu có tháng nào có tổng giá trị đơn hàng thành công < 3tr trả về 0 nếu không trả về 1
#     # Hơn nữa nếu số tháng ghi nhận được từ khách hàng < 6 tháng thì trả về 0
#     result["total_success_order_value_per_month"] = np.where((result["min_value_per_month"] >= min_total_success_order) & (result["active_months"] == months_window), 1, 0)    
#     result["score_3"] = result["total_success_order_value_per_month"].astype("str")
#     return result[["cus_id", "total_success_order_value_per_month", "score_3"]]

# @with_config("rules.yaml")
# def transform_avg_success_order_count_per_month(df: pd.DataFrame, column_name: str, config=None) -> pd.DataFrame:
#     """
#     Nhận vào cột don_ptc
#     -> trả về bảng avg_success_order_count_per_month với 3 cột: cus_id, month (đếm số tháng hđ),don_ptc (Trung bình) và avg_success_order_count_per_month
#     """
    
#     months_window = config.get("avg_success_order_count_per_month", {}).get("months_window")
#     min_avg_success_order_count = config.get("avg_success_order_count_per_month", {}).get("min")
#     # đầu tiên cần lấy ra tháng cao nhất
#     temp_df = df.copy()
#     temp_df["month"] = pd.to_datetime(temp_df["month"], format="%Y%m")
#     temp_df["month"] = temp_df["month"].dt.to_period("M")
#     max_month = temp_df["month"].max()
    
#     # Chỉ trích xuất X tháng gần nhất
#     min_month = max_month - months_window + 1 # phải cộng 1 vì như này: ví dụ tháng 
#                                               # 12 thì phải trích xuất 6 tháng gần nhất từ tháng 7 đến tháng 12
    
#     print("Tính toán avg_success_order_count_per_month xét từ tháng", min_month, "đến tháng", max_month)
    
#     # Xét trong X tháng, số đơn hàng thành công trung bình/tháng >= Y
#     # Lưu ý rằng: dữ liệu khách hàng phải đủ 6 tháng thì mới pass rule base
#     df_avg_success_order_count = temp_df[temp_df["month"].between(min_month, max_month)].groupby("cus_id").agg({column_name: "mean", "month": "count"}).reset_index()
#     df_avg_success_order_count["avg_success_order_count_per_month"] = np.where((df_avg_success_order_count[column_name] >= min_avg_success_order_count) & (df_avg_success_order_count["month"] == months_window), 1, 0)
#     df_avg_success_order_count["score_5"] = binning_data(df_avg_success_order_count,column_name,20) + df_avg_success_order_count["avg_success_order_count_per_month"].astype("str")
#     return df_avg_success_order_count[["cus_id", "avg_success_order_count_per_month", "score_5"]]

# @with_config("rules.yaml")
# def transform_total_success_order(df: pd.DataFrame, column_name: str, config=None) -> pd.DataFrame:
#     """
#     Xử lý cột tong_tien
#     -> trả về bảng total_success_order với 3 cột: cus_id và total_success_order, score
#     """
#     temp_df = df.copy()
#     temp_df["month"] = pd.to_datetime(temp_df["month"], format="%Y%m").dt.to_period("M")
    
#     # Xác định khoảng thời gian đang xét trong data
#     max_month = temp_df["month"].max()
#     min_month = temp_df["month"].min()
    
#     time_we_consider = int(config.get("total_success_order").get("min", 12 )) # số tháng tối thiểu để xét tổng doanh thu
    
#     min_month = max_month - time_we_consider + 1
    
#     # Lọc dữ liệu trong khung thời gian ta xét
#     valid_df = temp_df[temp_df["month"].between(min_month, max_month)].copy()
#     df_total_success_order = valid_df.groupby("cus_id").agg({column_name: "sum"}).reset_index()
    
#     df_total_success_order["score_4"] = np.round((df_total_success_order[column_name]/1000000).clip(1, 9999)).astype(int)
#     df_total_success_order["score_4"] = df_total_success_order["score_4"].apply(lambda x: f"{x:04d}")
#     return df_total_success_order[["cus_id", "score_4"]]


# @with_config("rules.yaml")
# def transform_revenue_decline_last_n_quarters(df: pd.DataFrame, column_name: str, config=None, scoring_month=None) -> pd.DataFrame:
#     """
#     Xử lý cột tong_tien - Rule: Giảm doanh thu 03 quý gần nhất
#     Logic: Doanh thu KHÔNG giảm liên tục 30% so với quý liền kề trước đó.
#     (Giảm so với quý trước đó 30%: Q1 < 70%Q2 < 70%Q3 -- Q1 là quý gần nhất)
#     -> Trả về 0 nếu VI PHẠM (tức là có giảm liên tục), 1 nếu OK (không giảm liên tục)
#     """
#     rule_config = config.get("revenue_decline_last_3_quarters", {})
#     decline_threshold = rule_config.get("decline_pct", 0.3) # 30%
    
#     temp_df = df.copy()
#     temp_df["month"] = pd.to_datetime(temp_df["month"], format="%Y%m")
    
#     # 1. Chuyển đổi sang dữ liệu Quý (Quarter) và tính tổng doanh thu theo Quý
#     temp_df["quarter"] = temp_df["month"].dt.to_period("Q")
    
#     # Xác định 3 quý gần nhất dựa trên scoring_month trong time.yaml
#     scoring_date = pd.to_datetime(scoring_month, format="%Y%m")
    
#     # Quý chứa scoring_month (Ví dụ 09/2022 -> Q3/2022)
#     current_quarter = scoring_date.to_period("Q")
    
#     # logic: Lấy 3 quý HOÀN CHỈNH gần nhất (không tính quý chứa scoring_month)
#     # Ví dụ: Max date = 07/2022 (Q3) -> Lấy Q2/2022, Q1/2022, Q4/2021
#     target_quarters = [current_quarter - i for i in range(1, 4)] 
#     # target_quarters sẽ là [Q_prev, Q_prev2, Q_prev3] -> Tương ứng Q1, Q2, Q3 trong công thức
    
#     print("Các quý được xét trong transform_revenue_decline_last_3_quarters:", [str(q) for q in target_quarters])
    
#     # Lọc dữ liệu chỉ nằm trong 3 quý này
#     quarter_df = temp_df[temp_df["quarter"].isin(target_quarters)].groupby(["cus_id", "quarter"])[column_name].sum().reset_index()
    
#     # Pivot để có các cột Q1, Q2, Q3 cho mỗi user (để dễ so sánh cột)
#     # Tạo bảng khung đủ 3 quý cho mỗi user
#     unique_users = temp_df["cus_id"].unique()
#     index_df = pd.MultiIndex.from_product([unique_users, target_quarters], names=['cus_id', 'quarter']).to_frame(index=False)
    
#     merged_q_df = index_df.merge(quarter_df, on=['cus_id', 'quarter'], how='left')
#     merged_q_df[column_name] = merged_q_df[column_name].fillna(0)
    
#     # Pivot: Index là cus_id, Columns là Quarter, Values là tong_tien
#     pivoted = merged_q_df.pivot(index='cus_id', columns='quarter', values=column_name)
    
#     # Sắp xếp cột theo thời gian tăng dần: Q3(cũ nhất) -> Q2 -> Q1(mới nhất)
#     pivoted = pivoted.sort_index(axis=1)

#     cols = pivoted.columns # [Q_oldest, Q_middle, Q_newest] ~ [Q3, Q2, Q1]
    
#     # tính phần trăm thay đổi so với tháng trước
#     def calculate_percentage_with_prev(row, prev_col, curr_col):
#         # Lấy giá trị của cột từ row
#         prev_val = row[prev_col]
#         curr_val = row[curr_col]
        
#         if prev_val == 0 and curr_val == 0:
#             return 0.0       
#         if prev_val == 0:
#             return 1.0
        
#         return (curr_val - prev_val) / prev_val
    
#     # tạo ra các cột chênh lệch doanh thu ở đoạn này
#     # Lưu ý: cols[2] là Q1 (mới nhất), cols[1] là Q2, cols[0] là Q3 (cũ nhất)
#     # diff_pct_q1_q2 = (Q1 - Q2) / Q2
#     pivoted["diff_pct_q1_q2"] = pivoted.apply(lambda row: calculate_percentage_with_prev(row, cols[1], cols[2]), axis=1)
#     # diff_pct_q2_q3 = (Q2 - Q3) / Q3
#     pivoted["diff_pct_q2_q3"] = pivoted.apply(lambda row: calculate_percentage_with_prev(row, cols[0], cols[1]), axis=1)
    
#     def check_violation(row):
#         """Kiểm tra vi phạm: Nếu cả 2 lần so sánh đều giảm >= 30% thì vi phạm (return 0)"""
#         if row["diff_pct_q1_q2"] < -decline_threshold and row["diff_pct_q2_q3"] < -decline_threshold:
#             return 0
#         return 1
  
#     def count_consecutive_decline_quarters(row):
#         """
#         Đếm số quý giảm LIÊN TỤC >=30% so với quý trước, tính từ quý gần nhất (Q1).
        
#         Logic:
#         - Bắt đầu từ Q1 (mới nhất), kiểm tra Q1 có giảm >=30% so với Q2 không
#         - Nếu có, tiếp tục kiểm tra Q2 có giảm >=30% so với Q3 không
#         - Nếu chuỗi bị đứt (quý nào đó không giảm >=30%), dừng đếm
        
#         Ví dụ:
#         - Q3=100, Q2=60, Q1=40 → Q1 giảm 33%, Q2 giảm 40% → chuỗi = 2
#         - Q3=100, Q2=90, Q1=60 → Q1 giảm 33%, Q2 không giảm (10%) → chuỗi = 1
#         - Q3=100, Q2=60, Q1=55 → Q1 không giảm (8%), chuỗi đứt → chuỗi = 0
#         """
#         consecutive_count = 0
        
#         # Bước 1: Kiểm tra Q1 có giảm >=30% so với Q2 không
#         if row["diff_pct_q1_q2"] < -decline_threshold:
#             consecutive_count += 1
            
#             # Bước 2: Nếu Q1 giảm, tiếp tục kiểm tra Q2 có giảm >=30% so với Q3 không
#             if row["diff_pct_q2_q3"] < -decline_threshold:
#                 consecutive_count += 1
        
#         return str(consecutive_count)
            
#     pivoted["revenue_decline_last_3_quarters"] = pivoted.apply(check_violation, axis=1)
#     pivoted["score_6"] = pivoted.apply(count_consecutive_decline_quarters, axis=1)
#     pivoted["score_6"] = pivoted["score_6"].fillna("0")
    
#     return pivoted[["revenue_decline_last_3_quarters", "score_6"]].reset_index()
    

# @with_config("rules.yaml")
# def transform_revenue_decline_last_n_months(
#     df: pd.DataFrame,
#     column_name: str,
#     config=None
# ) -> pd.DataFrame:
#     """
#     Tiêu chí: giảm doanh thu 6 tháng
#     Logic:
#     - Xét 6 tháng gần nhất
#     - Đếm số tháng giảm liên tục >=20% so với tháng liền kề
#     - Output:
#         cus_id
#         score_7
#     """

#     rule_config = config.get("revenue_decline_6_months", {})
#     months_window = rule_config.get("months_window", 6)
#     decline_threshold = rule_config.get("decline_pct", 0.2)

#     temp_df = df.copy()
#     temp_df["month"] = pd.to_datetime(temp_df["month"], format="%Y%m").dt.to_period("M")

#     # 1. Xác định 6 tháng gần nhất
#     max_month = temp_df["month"].max()
#     min_month = max_month - months_window + 1

#     valid_df = temp_df[temp_df["month"].between(min_month, max_month)]

#     # 2. Lấp đầy tháng thiếu
#     users = valid_df["cus_id"].unique()
#     full_months = pd.period_range(min_month, max_month, freq="M")

#     index_df = pd.MultiIndex.from_product(
#         [users, full_months],
#         names=["cus_id", "month"]
#     ).to_frame(index=False)

#     merged_df = index_df.merge(
#         valid_df, on=["cus_id", "month"], how="left"
#     )
#     merged_df[column_name] = merged_df[column_name].fillna(0.0001)

#     # 3. Tính % thay đổi so với tháng trước
#     merged_df = merged_df.sort_values(["cus_id", "month"])
#     merged_df["prev_value"] = merged_df.groupby("cus_id")[column_name].shift(1)
#     merged_df = merged_df.dropna(subset=["prev_value"])

#     merged_df["ratio"] = merged_df[column_name] / merged_df["prev_value"] - 1

#     # 4. Đánh dấu các loại tháng:
#     # - is_decline: Tháng GIẢM >= 20% (ratio <= -0.2) → Vi phạm
#     # - is_stable_or_up: Tháng KHÔNG giảm quá 20% (ratio > -0.2) → Ổn định/Tăng trưởng
#     merged_df["is_decline"] = (merged_df["ratio"] <= -decline_threshold).astype(int)
#     # merged_df["is_stable_or_up"] = (merged_df["ratio"] > -decline_threshold).astype(int)

#     # 5. Tính chuỗi GIẢM liên tục
#     # Logic: Mỗi khi gặp tháng KHÔNG GIẢM -> tạo nhóm mới (streak_id tăng lên)
#     # Các tháng giảm liên tục sẽ có cùng streak_id
#     merged_df["decline_streak_id"] = (
#         (~merged_df["is_decline"].astype(bool))
#         .groupby(merged_df["cus_id"])
#         .cumsum()
#     )

#     merged_df["decline_streak"] = (
#         merged_df
#         .groupby(["cus_id", "decline_streak_id"])["is_decline"]
#         .cumsum()
#     )

#     # # 6. Tính chuỗi ỔN ĐỊNH/TĂNG liên tục (không giảm quá 20%)
#     # # Logic: Mỗi khi gặp tháng GIẢM >= 20% -> tạo nhóm mới
#     # # Các tháng ổn định/tăng liên tục sẽ có cùng streak_id
#     # merged_df["stable_streak_id"] = (
#     #     (~merged_df["is_stable_or_up"].astype(bool))
#     #     .groupby(merged_df["cus_id"])
#     #     .cumsum()
#     # )

#     # merged_df["stable_streak"] = (
#     #     merged_df
#     #     .groupby(["cus_id", "stable_streak_id"])["is_stable_or_up"]
#     #     .cumsum()
#     # )

#     # 7. Tổng hợp kết quả
#     result_df = (
#         merged_df
#         .groupby("cus_id", as_index=False)
#         .agg(
#             max_decline_streak=("decline_streak", "max"),      # Chuỗi giảm dài nhất
#             # max_stable_streak=("stable_streak", "max")         # Chuỗi ổn định/tăng dài nhất (không giảm >=20%)
#         )
#     )

    
#     # Score 7: dựa trên chuỗi giảm (giới hạn 0-5)
#     result_df["score_7"] = result_df["max_decline_streak"].fillna(0).clip(0, 5).astype(str)
    
#     # # Score 8: dựa trên chuỗi ổn định/tăng (giới hạn 0-5) - số tháng liên tục không giảm quá 20%
#     # result_df["score_8"] = result_df["max_stable_streak"].fillna(0).clip(0, 5).astype(str)
    
#     # Nếu doanh thu ổn định liên tục >= 4 tháng thì trả về 1, ngược lại 0
#     result_df["revenue_decline_last_4_months"] = np.where(result_df["max_decline_streak"] >= 4, 0, 1)
#     return result_df[["cus_id", "revenue_decline_last_4_months", "score_7"]]
    
# ## new rule
# @with_config("rules.yaml")
# def transform_success_order_all_months(df: pd.DataFrame, column_name: str, config=None) -> pd.DataFrame:
#     """
#     Rule: Trong X tháng gần nhất, tháng nào cũng có đơn phát thành công (>=1)
#     """

#     rule_config = config.get("success_order_all_months", {})
#     months_window = rule_config.get("months_window")

#     temp_df = df.copy()
#     temp_df["month"] = pd.to_datetime(temp_df["month"], format="%Y%m")
#     temp_df["month"] = temp_df["month"].dt.to_period("M")

#     max_month = temp_df["month"].max()
#     min_month = max_month - months_window + 1

#     print(f"Tính toán rule từ {min_month} đến {max_month}")

#     # filter X tháng gần nhất
#     temp_df = temp_df[temp_df["month"].between(min_month, max_month)]

#     # mask: tháng có đơn thành công
#     temp_df["has_success"] = temp_df[column_name] >= 1

#     # aggregate
#     df_result = temp_df.groupby("cus_id").agg(
#         all_months_have_success=("has_success", "all"),  # tất cả tháng đều True
#         month_count=("month", "count")                  # số tháng có data
#     ).reset_index()

#     # rule: phải đủ tháng + tất cả đều có đơn
#     df_result["success_order_all_months"] = np.where(
#         (df_result["all_months_have_success"]) &
#         (df_result["month_count"] == months_window),
#         1,
#         0
#     )

#     return df_result[["cus_id", "success_order_all_months"]]

# @with_config("rules.yaml")
# def main_transform_data(df, config=None, scoring_month=None) -> pd.DataFrame:    
#     df_age = transform_nam_tuoi(df, "nam_tuoi", config=config)
#     df_usage_duration_months = transform_usage_duration_months(df, "so_thang_hdong", config=config)
#     df_sales_region = transform_sales_region(df, "ma_tinh_hoatdong_chinh", config=config)
#     df_avg_success_order_value_per_month = transform_avg_success_order_value_per_month(df, "tong_tien", config=config)
#     df_total_success_order_value_per_month = transform_total_success_order_value_per_month(df, "tong_tien", config=config)
#     df_avg_success_order_count_per_month = transform_avg_success_order_count_per_month(df, "don_ptc", config=config)
#     df_revenue_decline_last_n_quarters = transform_revenue_decline_last_n_quarters(df, "tong_tien", config=config, scoring_month=scoring_month)
#     df_transform_revenue_decline_last_n_months = transform_revenue_decline_last_n_months(df, "tong_tien", config=config)
#     df_total_success_order = transform_total_success_order(df, "tong_tien", config=config) 
#     df_success_ord_all_months = transform_success_order_all_months(df, "don_ptc", config=config)

#     # Join tất cả các dataframe lại theo cus_id
#     result_df = df_age.merge(df_usage_duration_months, on="cus_id", how="outer") \
#                       .merge(df_sales_region, on="cus_id", how="outer") \
#                       .merge(df_avg_success_order_value_per_month, on="cus_id", how="outer") \
#                       .merge(df_total_success_order_value_per_month, on="cus_id", how="outer") \
#                       .merge(df_avg_success_order_count_per_month, on="cus_id", how="outer") \
#                       .merge(df_revenue_decline_last_n_quarters, on="cus_id", how="outer") \
#                       .merge(df_total_success_order, on="cus_id", how="outer") \
#                       .merge(df_transform_revenue_decline_last_n_months, on="cus_id", how="outer")\
#                       .merge(df_success_ord_all_months, on="cus_id", how="outer")                 

#     # Điền null cho các cột score
#     ## Với các cột score_1, score_2, score_5 số thì ta sẽ thay null là 010 với 01: dành cho số 0, flat là 0
#     result_df["score_1"] = result_df["score_1"].fillna("010") 
#     result_df["score_2"] = result_df["score_2"].fillna("010") 
#     result_df["score_5"] = result_df["score_5"].fillna("010")
#     ## Với cột score_3 thì ta thay null là 0, score 4 ta thay null là 0001
#     result_df["score_3"] = result_df["score_3"].fillna("0") 
#     result_df["score_4"] = result_df["score_4"].fillna("0001")
    
#     # Với null (các cột boolean thôi) thì ta sẽ fill = 0
#     result_df = result_df.fillna(0)
    
#     # Đổi lại thành user_id cho đồng bộ
#     result_df = result_df.rename(columns={"cus_id": "user_id"})

#     # Sửa lỗi user_id bị .0 nếu còn xảy ra, UNCOMMENT dòng này nếu như không bị nữa nhé
#     # result_df["user_id"] = result_df["user_id"].replace(r'\.0$', '', regex=True)

#     # Tính score
#     result_df["behavior_score"] = "0." + result_df["score_1"] + result_df["score_5"]
#     result_df["gvm_score"] = "0." + result_df["score_2"] + result_df["score_3"] + result_df["score_4"]
    
#     result_df["trend_score"] = (
#         result_df["score_6"]
#         .astype(str)
#         .str.cat(result_df["score_7"].astype(str))
#         .radd("0.")
#     )
        
#     # Xóa đi các cột score thừa
#     result_df = result_df.drop(columns=['score_1', 'score_2', 'score_3', 'score_4', 'score_5', "score_6", "score_7"]) # "behavior_score", "gvm_score", "trend_score"

#     # khong dung score col + age de danh gia
#     recommend_columns = [col for col in result_df.columns if col != "user_id" and "score" not in col and "age" not in col]
#     result_df["recommendation"] = (result_df[recommend_columns] == 1).all(axis=1).astype(int)

#     # CÁC CÁI NÀY TẠM THỜI FAKE
#     result_df["score"] = "0"
#     result_df["rule_score"] = np.random.randint(0, 2, size=result_df.shape[0])
    
#     result_df["phone"] = "09" + result_df["user_id"].astype(str) # tạm thời là lấy 0 + user_id

#     result_df["date"] = datetime.now().strftime("%Y-%m-%d")
#     result_df["model_version"] = config.get("model_version", "v1.0.0")
    
#     return result_df