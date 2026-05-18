from functools import wraps
from src.scripts.utils.load_config import load_config

def with_config(yml_file: str):
    """Decorator đảm bảo load config trước khi chạy hàm, truyền thêm kwarg 'config' """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            config = kwargs.pop("config", None)
            if config is None:
                config = load_config(yml_file)
            return func(*args, config=config, **kwargs)
        return wrapper
    return decorator