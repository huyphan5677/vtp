import yaml
from src.config.data_path import CONFIG_PATH
def load_config(yml_file_name: str):
    """
    Đọc file cấu hình time.yaml
    -> trả về config
    """
    config_file_path = f"{CONFIG_PATH}/{yml_file_name}"
    with open(config_file_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config