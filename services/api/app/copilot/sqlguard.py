"""Check SQL written by the local LLM before it runs. Only one read-only SELECT on allowed views.

This is the first line of defence; the query also runs inside a READ ONLY transaction with a
statement timeout (db.read_only), so even a missed case cannot change data.
"""

import re

ALLOWED_TABLES = {"copilot_metrics", "copilot_counts_hourly", "junctions", "approaches"}
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|grant|revoke|truncate|copy|vacuum|analyze|call|do|execute|"
    r"prepare|set|reset|lock|listen|notify|comment|security|pg_sleep|pg_read_file|pg_ls_dir|lo_import|"
    r"lo_export|dblink|into)\b",
    re.IGNORECASE,
)
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
    for t in TABLE_REF.findall(s):
        name = t.lower().split(".")[-1]
        if name not in ALLOWED_TABLES and name not in ctes:
            raise UnsafeSQL(f"table not allowed: {t}")
    return f"SELECT * FROM ({s}) AS copilot_q LIMIT {MAX_ROWS}"
