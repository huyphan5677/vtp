# VTP — Pipeline tính feature theo ngày/tháng

Pipeline tính feature dạng "config-driven": mọi thứ hay thay đổi (đường dẫn
lưu trên MinIO, tên cột partition, ngưỡng, window,...) khai báo trong
`src/config/features.yaml`, không hardcode trong code Python. Thêm 1 feature
mới chỉ cần 1 file `.py` + vài dòng yaml — không phải sửa `run.py` hay DAG.

## Kiến trúc

Mỗi feature có đúng 2 hàm, cùng nằm trong 1 file `.py` (`src/data_processing/transform/<feature>.py`):

```
raw (MinIO)                     day_function                         function (có window)
raw/hitech_day/          -->    clean/fts/<feature>/day/       -->    clean/fts/<feature>/month_lNm/
partition_date=YYYYMMDD/        partition_date=YYYYMMDD/              partition=YYYYMM/
(1 dòng/khách/ngày)              (đã làm sạch, 1 dòng/khách/ngày)      (đã tính theo N tháng)
```

Sau đó `merge_features_for_month` đọc lại output tháng của **mọi** feature,
ghép theo `cus_id`, lưu vào `clean/merged/partition=YYYYMM/`.

- **day_function**: đọc raw 1 ngày, làm sạch, tự lưu. Chạy 1 lần/ngày,
  không phụ thuộc feature khác hay ngày khác.
- **function** (giai đoạn tháng, có window): tự load N tháng dữ liệu ngày đã
  clean ở trên (N = `months_window`), tính toán + so ngưỡng, tự lưu.

Pipeline chạy **hàng ngày** (`dag_monthly_phase1.py`, schedule `30 7 * * *`):
mỗi ngày chạy `day_function` cho đúng ngày đó; khi ngày đó là **ngày đầu
tháng**, giai đoạn tháng tự tính luôn cho tháng liền trước (đã đủ dữ liệu cả
tháng) — xem `_months_to_score` trong `run.py`. Đa số ngày trong tháng thì
giai đoạn tháng/merge sẽ không làm gì (no-op).

## Chạy thử local

```bash
# 1. Lên MinIO + Postgres + pgweb (xem docker/database/docker-compose.yaml)
docker compose -f docker/database/docker-compose.yaml up -d

# 2. Nạp raw data mẫu (data/output/hitech_day) lên MinIO
python scripts/upload_raw_to_minio.py

# 3a. Chạy qua notebook (khuyến nghị để test nhanh, có sẵn từng bước)
#     mở src/notebooks/test.ipynb

# 3b. Hoặc chạy trực tiếp qua CLI (giống cách DAG gọi)
python src/data_processing/run.py --mode feature_day --day_feature order --dt_from 20251201 --dt_to 20251231
python src/data_processing/run.py --mode feature --feature_name order_l3m --dt_from 20251231 --dt_to 20260101
python src/data_processing/run.py --mode merge --dt_from 20251231 --dt_to 20260101
```

pgweb xem Postgres tại `http://localhost:8081`, MinIO console tại `http://localhost:9991`.

## Cách thêm 1 feature mới

Ví dụ đã có sẵn trong repo: `order` (`src/data_processing/transform/order.py`)
và `age` (`src/data_processing/transform/age.py`) — đọc 2 file này làm mẫu.

### Bước 1 — Viết file `src/data_processing/transform/<feature>.py`

Cần đúng 2 hàm:

**1a. Hàm ngày** — đọc raw 1 ngày, làm sạch, tự lưu:

```python
def transform_<feature>_by_day(
    date: str,              # 'YYYYMMDD', do run.py truyền vào
    day_prefix: str,        # nơi lưu output ngày, lấy từ features.yaml
    raw_day_prefix: str,    # nơi lấy raw, lấy từ features.yaml (config chung)
    day_partition_key: str, # tên cột partition ngày, lấy từ features.yaml (config chung)
) -> pd.DataFrame:
    raw_df = extract_data_by_date(
        date, prefix=raw_day_prefix, day_partition_key=day_partition_key
    )
    clean_df = ...  # chọn cột cần, làm sạch, tính toán ở mức 1 dòng/khách/ngày

    save_to_minio(
        clean_df,
        object_name=f"{day_prefix}/{day_partition_key}={date}/data.parquet",
    )
    return clean_df
```

**1b. Hàm tháng (có window)** — tự load N tháng dữ liệu ngày đã clean, tính + so ngưỡng, tự lưu:

```python
def transform_<feature>_lxm(
    month: str,              # 'YYYYMM', do run.py truyền vào
    months_window: int,      # N tháng cần load, lấy từ features.yaml (input)
    <threshold_params>,      # bao nhiêu tham số ngưỡng cũng được, lấy từ features.yaml (input)
    day_prefix: str,
    month_prefix: str,
    day_partition_key: str,
    month_partition_key: str,
) -> pd.DataFrame:
    start_date, end_date = ...  # tính khoảng ngày ứng với N tháng trước `month`
    day_df = extract_data_by_range(
        start_date, end_date, prefix=day_prefix, day_partition_key=day_partition_key
    )

    result_df = ...  # groupby cus_id, tính f_<feature>_..._l{N}m, so ngưỡng

    save_to_minio(
        result_df,
        object_name=f"{month_prefix}/{month_partition_key}={month}/data.parquet",
    )
    return result_df
```

Lưu ý quan trọng:
- **Không hardcode path/ngưỡng** trong file `.py` — tất cả nhận qua tham số
  (xem bảng tham số bên dưới). `run.py` tự đọc `features.yaml`, gộp `config`
  chung + `input` của feature, rồi chỉ truyền đúng những tham số mà hàm bạn
  viết có khai báo (`_call_with_declared_kwargs`) — nên hàm chỉ cần khai báo
  tham số nào nó thực sự dùng.
- Tên cột output nên nhúng `months_window` vào (ví dụ `f_<feature>_l{N}m`)
  để nhiều window (3m/6m/12m,...) của cùng 1 feature không đè path/tên cột
  lên nhau.

### Bước 2 — Khai báo trong `src/config/features.yaml`

Thêm 1 (hoặc nhiều, nếu có nhiều window) entry vào mảng `features`:

```yaml
- name: <feature>_l<N>m         # tên rule instance, duy nhất trong toàn file
  module: src.data_processing.transform.<feature>
  day_feature: <feature>        # nhiều entry cùng feature (khác window) dùng CHUNG giá trị này
  day_function: transform_<feature>_by_day
  function: transform_<feature>_lxm
  day_prefix: clean/fts/<feature>/day
  month_prefix: clean/fts/<feature>/month_l<N>m   # PHẢI khác nhau giữa các window
  input:
    months_window: <N>
    <threshold_param_1>: ...
    <threshold_param_2>: ...
```

- `day_feature`/`day_function`/`day_prefix` phải **giống nhau** giữa các
  entry cùng feature (chỉ khác window) — để giai đoạn ngày chỉ chạy/lưu 1
  lần, không lặp lại cho mỗi window.
- `month_prefix` phải **khác nhau** giữa các window (đã nhúng `l<N>m`) — nếu
  giống nhau, window sau sẽ ghi đè lên window trước.

### Xong — không cần sửa `run.py` hay `dag_monthly_phase1.py`

Cả 2 file đều tự đọc `features.yaml`:
- `run.py`: `run_feature_day`/`run_feature`/`merge_features_for_month` tra
  config theo tên, dùng `importlib` để gọi đúng hàm trong module bạn khai báo.
- `dag_monthly_phase1.py`: `_load_day_features()`/`_load_feature_names()`
  đọc thẳng từ yaml lúc parse DAG, tự tạo task cho feature mới.

Test ngay bằng cách thêm feature mới vào loop trong `src/notebooks/test.ipynb`
(notebook đã tự loop qua mọi `day_feature`/`name` trong `features.yaml`, nên
tự nhận feature mới không cần sửa notebook) hoặc gọi CLI trực tiếp:

```bash
python src/data_processing/run.py --mode feature_day --day_feature <feature> --dt_from 20251201 --dt_to 20251231
python src/data_processing/run.py --mode feature --feature_name <feature>_l<N>m --dt_from 20251231 --dt_to 20260101
```

## Tham khảo

### `features.yaml` — `config` (áp dụng chung mọi feature)

| Key | Ý nghĩa |
|---|---|
| `raw_day_prefix` | Thư mục (trên MinIO) chứa raw theo ngày |
| `day_partition_key` | Tên cột partition theo ngày (Hive-style `key=value` trong path) |
| `month_partition_key` | Tên cột partition theo tháng |
| `merged_prefix` | Thư mục lưu kết quả đã ghép tất cả feature theo tháng |

### `features.yaml` — mỗi entry trong `features`

| Key | Ý nghĩa |
|---|---|
| `name` | Tên rule instance, dùng làm `--feature_name` khi gọi CLI |
| `module` | Đường dẫn Python module chứa 2 hàm |
| `day_feature` | Tên gốc giai đoạn ngày — dùng chung giữa các window của cùng feature |
| `day_function` | Tên hàm giai đoạn ngày trong `module` |
| `function` | Tên hàm giai đoạn tháng trong `module` |
| `day_prefix` | Thư mục lưu output giai đoạn ngày |
| `month_prefix` | Thư mục lưu output giai đoạn tháng (riêng theo window) |
| `input` | Dict các kwargs khác truyền vào `function` (ví dụ `months_window`, ngưỡng) |

### CLI `run.py`

| `--mode` | Tham số | Việc làm |
|---|---|---|
| `feature_day` | `--day_feature --dt_from --dt_to` | Chạy `day_function` cho từng ngày trong khoảng |
| `feature` | `--feature_name --dt_from --dt_to` | Tự tìm tháng cần tính trong khoảng (ngày đầu tháng → tháng liền trước), chạy `function` cho mỗi tháng |
| `merge` | `--dt_from --dt_to` | Ghép mọi feature theo `cus_id` cho mỗi tháng cần tính trong khoảng |

### File liên quan

| File | Vai trò |
|---|---|
| `src/config/features.yaml` | Config duy nhất — path, ngưỡng, window |
| `src/config/connect.yaml` | Credentials MinIO/Postgres |
| `src/data_processing/transform/*.py` | Code từng feature (2 hàm/file) |
| `src/data_processing/run.py` | Dispatcher — đọc yaml, gọi đúng hàm |
| `src/utils/minio_client.py` | Đọc/ghi MinIO dùng chung (`save_to_minio`, `extract_data_by_date`, `extract_data_by_range`, `read_minio_parquet`) |
| `src/utils/common.py` | `load_config`, `month_date_range`, `process_args_to_dict` |
| `dag_monthly_phase1.py` | DAG Airflow, tự đọc `features.yaml` để tạo task |
| `src/notebooks/test.ipynb` | Test từng bước trên local (không qua Airflow) |
| `scripts/upload_raw_to_minio.py` | Nạp data mẫu (`data/output/hitech_day`) lên MinIO để test |
| `docker/database/docker-compose.yaml` | MinIO + Postgres + pgweb để mô phỏng local |
