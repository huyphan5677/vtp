import pandas as pd
from src.scripts.utils.postgres_connect import get_postgres_connection
from src.scripts.utils.load_config import load_config
import uuid


def load_data_to_postgres(df):
    """
    Load data into a PostgreSQL table.

    Parameters:
    - df: Pandas DataFrame representing the rows to be inserted.
    - schema: Schema name.
    - table_name: Name of the target table in PostgreSQL.
    """
    connection = None
    cursor = None
    try:
        database_configuration = load_config("connect.yaml").get("postgres")
        schema = database_configuration.get("schema")
        table_name = database_configuration.get("table_name")
        connection = get_postgres_connection('connect.yaml')
        
        cursor = connection.cursor()

        expected_columns = [
            'id',
            'user_id',
            'age',
            'avg_success_order_count_per_month',
            'avg_success_order_value_per_month',
            'date',
            'model_version',
            'phone',
            'recommendation',
            'revenue_decline_last_3_quarters',
            'revenue_decline_last_4_months',
            'sales_region',
            'score',
            'rule_score',
            'behavior_score',
            'gvm_score',
            'trend_score',
            'total_success_order_value_per_month',
            'usage_duration_months'
        ]

        # Convert boolean columns (Postgres BOOLEAN doesn't like 1/0 integers)
        bool_cols = [
            'age', 'avg_success_order_count_per_month', 'avg_success_order_value_per_month',
            'recommendation', 'revenue_decline_last_3_quarters', 'revenue_decline_last_4_months',
            'sales_region', 'rule_score', 'total_success_order_value_per_month', 'usage_duration_months'
        ]
        for col in bool_cols:
            if col in df.columns:
                df[col] = df[col].astype(bool)
                
        df["id"] = [uuid.uuid4() for i in range(len(df))]
        
        # Ensure only expected columns are present (and in order?)
        # Filter for expected columns that exist in the dataframe to be safe, 
        # but better to ensure all expected columns are there or handle missing ones.
        # Since this is a pipeline, we expect them to be there.
        
        # Check if any expected columns are missing
        missing_cols = set(expected_columns) - set(df.columns)
        if missing_cols:
            print(f"Warning: Missing columns in dataframe: {missing_cols}")
        
        # Select columns that are both in expected_columns and df.columns
        final_cols = [col for col in expected_columns if col in df.columns]
        df_to_insert = df[final_cols].copy()
        
        # Sửa cái lỗi nếu .0 vẫn xuất hiện (thực tế ở trong code pipeline tôi đã sửa rồi)
        # if 'user_id' in df_to_insert.columns:
        #     df_to_insert['user_id'] = df_to_insert['user_id'].astype(str).replace(r'\.0$', '', regex=True)

        # Chuyển datafrema thành list of tuples để phục vụ insert
        data = [tuple(x) for x in df_to_insert.to_numpy()]

        # Tạo lệnh để insert
        if not data:
             print("No data to insert.")
             return

        placeholders = ', '.join(['%s'] * len(df_to_insert.columns))
        columns_str = ', '.join(df_to_insert.columns)
        insert_query = f"INSERT INTO {schema}.{table_name} ({columns_str}) VALUES ({placeholders})"

        cursor.executemany(insert_query, data)
        connection.commit()
        print(f"Hoàn thành load {len(data)} vào {schema}.{table_name}.")

    except Exception as e:
        if connection:
            connection.rollback()
        raise RuntimeError(f"Lỗi khi load dữ liệu vào PostgreSQL: {e}")
    
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
