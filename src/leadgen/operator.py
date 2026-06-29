import re
import pandas as pd
from src.leadgen.config import *
from src.leadgen.overlap_resolver import resolve_overlap

import warnings
warnings.filterwarnings("ignore")


def sql_to_pandas(query: str) -> str:
    # IS NOT NULL -> .notna()
    query = re.sub(
        r'(\w+)\s+is\s+not\s+null',
        r'\1.notna()',
        query,
        flags=re.IGNORECASE
    )

    # IS NULL -> .isna()
    query = re.sub(
        r'(\w+)\s+is\s+null',
        r'\1.isna()',
        query,
        flags=re.IGNORECASE
    )

    # <> -> !=
    query = re.sub(r'<>', '!=', query)

    # = -> == (không đụng >= <= != ==)
    query = re.sub(r'(?<![<>=!])=(?!=)', '==', query)

    # IN (...) -> IN [...]
    query = re.sub(
        r'\bin\s*\((.*?)\)',
        r'in [\1]',
        query,
        flags=re.IGNORECASE
    )

    # AND / OR / NOT
    query = re.sub(r'\band\b', 'and', query, flags=re.IGNORECASE)
    query = re.sub(r'\bor\b', 'or', query, flags=re.IGNORECASE)
    query = re.sub(r'\bnot\b', 'not', query, flags=re.IGNORECASE)

    return query

def evaluate_query(df: pd.DataFrame, query: str) -> pd.Series:
    query = query.strip()

    if query.lower() in ("all", "1=1", "1==1"):
        return pd.Series(True, index=df.index)

    query = sql_to_pandas(query)

    return df.eval(query, engine="python")


def apply_general_rules(df: pd.DataFrame, rules_df: pd.DataFrame) -> pd.DataFrame:
    reject_rules = rules_df[rules_df['status'] == 'reject']
    pass_rules   = rules_df[rules_df['status'] == 'pass']

    funnel_log = [{"step": "initial", "rule": None, "leads": len(df)}]

    for _, row in reject_rules.iterrows():
        mask = evaluate_query(df, row['rule'])
        df = df[~mask].reset_index(drop=True)
        funnel_log.append({"step": "reject", "rule": row['rule'], "leads": len(df)})

    if not pass_rules.empty:
        pass_mask = pd.Series(True, index=df.index)

        for _, row in pass_rules.iterrows():
            mask = evaluate_query(df, row["rule"])
            pass_mask &= mask

        df = df[pass_mask].reset_index(drop=True)
        funnel_log.append({"step": "pass", "rule": " | ".join(pass_rules['rule'].tolist()), "leads": len(df)})

    # print funnel
    print("\n Funnel Summary")
    print("=" * 60)
    for i, step in enumerate(funnel_log):
        indent = "  " * i
        drop = funnel_log[i-1]["leads"] - step["leads"] if i > 0 else 0
        drop_str = f"(-{drop})" if drop > 0 else ""
        label = f"[{step['step'].upper()}] {step['rule']}" if step['rule'] else "[INITIAL]"
        print(f"{indent}→ {label}")
        print(f"{indent}  leads: {step['leads']} {drop_str}")
    print("=" * 60)

    return df


def apply_product_eligibility(df: pd.DataFrame, products_df: pd.DataFrame) -> pd.DataFrame:
    """Sheet 2.x — gán product eligible, 1 lead pass được nhiều sản phẩm."""
    enabled_products = products_df[
        products_df['enabled'].astype(str).str.upper() == 'TRUE'
    ]

    product_results = {}
    for _, row in enabled_products.iterrows():
        product_id = row['product_id']
        mask = evaluate_query(df, row['query'])
        product_results['rule_' + product_id] = mask
        print(f"  [PRODUCT] {product_id}: {mask.sum()} leads eligible")

    if product_results:
        df = pd.concat([df, pd.DataFrame(product_results, index=df.index)], axis=1)

    return df


def run_strategy(df: pd.DataFrame) -> pd.DataFrame:
    all_sheets = pd.read_excel(STRATEGY_CONFIG, sheet_name=None)

    for sheet_name in sorted(all_sheets.keys()):
        sheet_df = all_sheets[sheet_name]
        print(f"\n── Sheet: '{sheet_name}' ──")

        if sheet_name.startswith("1."):
            df = apply_general_rules(df, sheet_df)
            print(f"  → Remaining {len(df)} leads after general rules")

        elif sheet_name.startswith("2."):
            df = apply_product_eligibility(df, sheet_df)
            df = resolve_overlap(df, sheet_df)

    return df