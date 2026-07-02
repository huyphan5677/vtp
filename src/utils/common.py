from __future__ import annotations

import shlex
import pathlib
import calendar

import yaml
from loguru import logger

from src.config.data_path import CONFIG_PATH


def month_date_range(month: str) -> tuple[str, str]:
    """Đổi tháng dạng 'YYYYMM' thành (ngày đầu tháng, ngày cuối tháng) dạng 'YYYYMMDD'."""
    year, mon = int(month[:4]), int(month[4:6])
    last_day = calendar.monthrange(year, mon)[1]
    return f"{month}01", f"{month}{last_day:02d}"


def load_config(yml_file_name: str):
    """Đọc file cấu hình yaml.

    -> trả về config
    """
    config_file_path = f"{CONFIG_PATH}/{yml_file_name}"
    with pathlib.Path(config_file_path).open(encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def process_args_to_dict(args_string: str) -> dict[str, str | None]:
    """Parse a command-line argument string into a dictionary.

    Args:
        args_string (str): The argument string (e.g.,
            "--mode prod --skip_dags a,b,c").

    Returns:
        dict[str, str | None]: Dictionary mapping argument keys to their values.
                                Keys without values will have None.
    """
    tokens = shlex.split(args_string)
    args_dict: dict[str, str | None] = {}

    lst_tokens: list[str] = []
    lst_idx: list[int] = []

    i = 0
    while i < len(tokens):
        if tokens[i].startswith("--"):
            key = tokens[i][2:]  # Remove '--' prefix

            lst_tokens.append(key)
            lst_idx.append(i)

            # Check if next token is a value
            if i + 1 < len(tokens) and not tokens[i + 1].startswith("--"):
                args_dict[key] = tokens[i + 1]
                i += 2
            else:
                args_dict[key] = None
                i += 1
        else:
            i += 1  # Skip unexpected tokens

    # Handle special case for skip_dags (list of dags)
    if "skip_dags" in lst_tokens:
        try:
            idx = lst_tokens.index("skip_dags")
            idx_token = lst_idx[idx]
            idx_next_token = (
                lst_idx[idx + 1] if idx + 1 < len(lst_idx) else len(tokens)
            )
            args_dict["skip_dags"] = "".join(
                tokens[i] for i in range(idx_token + 1, idx_next_token)
            ).split(",")
        except ValueError as exc:
            logger.warning("Failed to parse 'skip_dags': %s", exc)

    return args_dict
