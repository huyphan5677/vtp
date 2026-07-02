-- Khớp với expected_columns/bool_cols trong src/utils/postgres_client.py
CREATE TABLE IF NOT EXISTS public.tbl_output_scoring (
    id UUID PRIMARY KEY,
    user_id TEXT,
    age BOOLEAN,
    avg_success_order_count_per_month BOOLEAN,
    avg_success_order_value_per_month BOOLEAN,
    date DATE,
    model_version TEXT,
    phone TEXT,
    recommendation BOOLEAN,
    revenue_decline_last_3_quarters BOOLEAN,
    revenue_decline_last_4_months BOOLEAN,
    sales_region BOOLEAN,
    score TEXT,
    rule_score BOOLEAN,
    behavior_score TEXT,
    gvm_score DOUBLE PRECISION,
    trend_score DOUBLE PRECISION,
    total_success_order_value_per_month BOOLEAN,
    usage_duration_months BOOLEAN
);
