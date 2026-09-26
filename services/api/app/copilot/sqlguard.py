"""Check SQL written by the local LLM before it runs. Only one read-only SELECT on allowed views.

This is the first line of defence: one statement, no comments, SELECT only, allowed tables and allowed
functions only. The query then runs inside a READ ONLY transaction with a statement timeout, as the
copilot_reader role that can read nothing but the allowed views (db.read_only, migration 0007).
"""

import re

ALLOWED_TABLES = {"copilot_metrics", "copilot_counts_hourly", "junctions", "approaches"}
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|grant|revoke|truncate|copy|vacuum|analyze|call|do|execute|"
    r"prepare|set|reset|lock|listen|notify|comment|security|pg_sleep|pg_read_file|pg_ls_dir|lo_import|"
    r"lo_export|dblink|into)\b",
    re.IGNORECASE,
)
# Functions: only this allow-list may be called. A deny-list cannot keep up (set_config could switch
# the database role back, query_to_xml can run SQL hidden in a string), so everything else is refused.
ALLOWED_FUNCTIONS = {
    "count", "sum", "avg", "min", "max", "round", "coalesce", "nullif", "greatest", "least", "abs", "ceil",
    "ceiling", "floor", "sqrt", "power", "mod", "sign", "upper", "lower", "trim", "length", "concat", "lpad",
    "rpad", "substring", "split_part", "to_char", "date_trunc", "extract", "date_part", "percentile_cont",
    "percentile_disc", "stddev", "stddev_samp", "variance", "rank", "dense_rank", "row_number", "ntile", "lag",
    "lead", "first_value", "last_value", "string_agg", "array_agg", "mode", "bool_or", "bool_and", "cast", "now",
}  # fmt: skip
# SQL words that are followed by "(" without being a function call
PAREN_KEYWORDS = {
    "in", "exists", "as", "over", "filter", "within", "and", "or", "not", "on", "when", "then", "else", "where",
    "select", "from", "join", "any", "all", "some", "using", "by", "having", "distinct", "values", "case", "is",
    "between", "like", "ilike", "with", "partition", "group", "order", "limit", "offset", "desc", "asc", "end",
}  # fmt: skip
FUNC_CALL = re.compile(r"\b([a-zA-Z_][\w.]*)\s*\(")
TABLE_REF = re.compile(r"\b(?:from|join)\s+([a-zA-Z_][\w.]*)", re.IGNORECASE)
CTE_NAME = re.compile(r"(?:\bwith\b|,)\s*([a-zA-Z_]\w*)\s+as\s*\(", re.IGNORECASE)
MAX_ROWS = 500


class UnsafeSQL(ValueError):
    """The LLM's SQL was rejected."""


def check_sql(sql: str) -> str:
    """Return a safe, row-limited version of `sql`, or raise UnsafeSQL with a plain reason."""
    s = (sql or "").strip().rstrip(";").strip()
    if not s:
        raise UnsafeSQL("empty query")
    if ";" in s:
        raise UnsafeSQL("only one statement is allowed")
    if "--" in s or "/*" in s:
        raise UnsafeSQL("comments are not allowed")
    if not re.match(r"^(select|with)\b", s, re.IGNORECASE):
        raise UnsafeSQL("only SELECT queries are allowed")
    if m := FORBIDDEN.search(s):
        raise UnsafeSQL(f"keyword not allowed: {m.group(1)}")
    ctes = {c.lower() for c in CTE_NAME.findall(s)}
    for f in FUNC_CALL.findall(re.sub(r"'[^']*'", "''", s)):  # ignore text inside string literals
        name = f.lower().split(".")[-1]
        if name not in ALLOWED_FUNCTIONS and name not in PAREN_KEYWORDS and name not in ctes:
            raise UnsafeSQL(f"function not allowed: {f}")
    for t in TABLE_REF.findall(s):
        name = t.lower().split(".")[-1]
        if name not in ALLOWED_TABLES and name not in ctes:
            raise UnsafeSQL(f"table not allowed: {t}")
    return f"SELECT * FROM ({s}) AS copilot_q LIMIT {MAX_ROWS}"
