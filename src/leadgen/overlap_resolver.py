import pandas as pd

import warnings
warnings.filterwarnings("ignore")

from itertools import combinations

def resolve_overlap(df: pd.DataFrame, products_df: pd.DataFrame) -> pd.DataFrame:
    enabled_products = products_df[
        products_df['enabled'].astype(str).str.upper() == 'TRUE'
    ].set_index('product_id')

    product_ids = enabled_products.index.tolist()

    # Precompute overlap sets 1 lần
    def get_overlap_set(pid):
        raw = str(enabled_products.loc[pid, 'overlap_with']).strip()
        if raw.lower() == 'all':
            return set(product_ids)
        if raw.lower() in ('nan', ''):
            return set()
        return {x.strip() for x in raw.split(',')}

    overlap_sets = {pid: get_overlap_set(pid) for pid in product_ids}

    def can_coexist(a, b):
        return b in overlap_sets[a] and a in overlap_sets[b]

    def resolve_row(row):
        assign = {p: bool(row[f'rule_{p}']) for p in product_ids}
        print(f"\nINIT: {assign}")

        changed = True
        while changed:
            changed = False
            for a, b in combinations(product_ids, 2):
                if not assign[a] or not assign[b]:
                    continue
                if not can_coexist(a, b):
                    pa = enabled_products.loc[a, 'priority']
                    pb = enabled_products.loc[b, 'priority']
                    loser = b if pa <= pb else a
                    print(f"  CONFLICT ({a} p={pa}) vs ({b} p={pb}) → drop {loser}")
                    print(f"  overlap[{a}] = {overlap_sets[a]}")
                    print(f"  overlap[{b}] = {overlap_sets[b]}")
                    if pa <= pb:
                        assign[b] = False
                    else:
                        assign[a] = False
                    changed = True
                    break

        print(f"FINAL: {assign}")
        return pd.Series({f'assign_{p}': v for p, v in assign.items()})

    df = df.copy()
    assign_df = df.apply(resolve_row, axis=1)
    return pd.concat([df, assign_df], axis=1)