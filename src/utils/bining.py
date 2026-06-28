from __future__ import annotations

import numpy as np
import pandas as pd


def binning_data(df: pd.DataFrame, bin_col: str, bin_number: int) -> pd.Series:
    """Chia 20 bin theo tỷ trọng (xấp xỉ mỗi bin ~ 5% user) -> trả về score 01-20."""
    # rank để đảm bảo rằng mỗi bin sẽ tồn tại ít nhất 5% dữ liệu
    # nếu về sau mà team mình coi giá trị kiểu 25000 xuất hiện nhiều lần
    # cùng 1 rank thì đổi cái method sang dense là được
    r = df[bin_col].rank(method="first").astype(float)

    # scale về 1..20
    denom = float(r.max()) if float(r.max()) > 0 else 1.0
    score = np.ceil(r / denom * bin_number).astype(int)

    # đảm bảo trong [1, 20]
    score = score.clip(1, bin_number)

    # cái này để đảm bảo rằng là ví dụ như là: bin_number 2 chữ số thì score
    # cũng sẽ có dạng 2 chữ số
    width = len(str(bin_number))

    # convert sang string và zfill động
    score_str = score.astype(str).str.zfill(width)

    return score_str
