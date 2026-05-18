from src.scripts.utils.load_config import load_config

def get_postgres_connection(config_file: str = 'connect.yaml'):
    """
    Lấy thông tin kết nối Postgres từ file cấu hình và trả về connection đến Postgres
    """
    # lấy ra config
    config = load_config(config_file)
    pg_config = config.get('postgres', {})
    
    # tạo kết nối đến PostgreSQL
    try:
        import psycopg
        conn = psycopg.connect(
            host=pg_config.get('host', 'localhost'),
            port=pg_config.get('port', 5432),
            user=pg_config.get('user', ''),
            password=pg_config.get('password', ''),
            dbname=pg_config.get('database', '')
        )
    except:
        import psycopg2
        conn = psycopg2.connect(
            host=pg_config.get('host', 'localhost'),
            port=pg_config.get('port', 5432),
            user=pg_config.get('user', ''),
            password=pg_config.get('password', ''),
            dbname=pg_config.get('database', '')
        )
    
    return conn