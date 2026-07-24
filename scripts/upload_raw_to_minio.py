"""Upload local sample raw day data (data/output/hitech_day) lên MinIO.

Dùng cho local/dev: nạp dữ liệu mẫu vào raw/hitech_day/partition_date=YYYYMMDD/
để chạy thử pipeline (transform_order_by_day đọc raw từ đây).

Usage: python scripts/upload_raw_to_minio.py
"""

from __future__ import annotations

import sys
import pathlib


sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import pandas as pd

#from src.utils.minio_client import load_data_to_minio
from src.utils.minio_client import save_to_minio


LOCAL_RAW_DIR = (
    pathlib.Path(__file__).parent.parent / "data" / "output" / "hitech_day"
)


def main() -> None:
    day_dirs = sorted(p for p in LOCAL_RAW_DIR.iterdir() if p.is_dir())
    print(f"Tìm thấy {len(day_dirs)} ngày trong {LOCAL_RAW_DIR}")

    for day_dir in day_dirs:
        date = day_dir.name
        parquet_files = list(day_dir.glob("*.parquet"))
        if not parquet_files:
            print(f"  Bỏ qua {date}: không có file parquet")
            continue

        df = pd.read_parquet(parquet_files[0])
        #load_data_to_minio(
        save_to_minio(
            df,
            object_name=f"raw/hitech_day/partition_date={date}/data_hitech_day.parquet",
        )
        print(f"  Đã upload {date} ({len(df)} dòng)")


if __name__ == "__main__":
    main()
