import ast

# chuyển cus_id từ string sang dict nếu cần
def parse_cus_id(x):
    if isinstance(x, dict):
        return x
    if isinstance(x, str):
        try:
            return ast.literal_eval(x)
        except (ValueError, SyntaxError):
            return None
    return None
