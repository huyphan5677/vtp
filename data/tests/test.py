from __future__ import annotations

import pandas as pd
from vtp.src.utils.postgres_connect import (
    get_postgres_connection,
)


if __name__ == "__main__":
    connection = get_postgres_connection("connect.yaml")

    query = """
        select * from public.tbl_output_scoring
    """

    df_schema = pd.read_sql(query, connection)
    print(df_schema)

    connection.close()
