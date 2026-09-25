"""The copilot's SQL guard only lets one read-only SELECT on allowed views through."""

import pytest

from app.copilot.sqlguard import UnsafeSQL, check_sql

OK = [
    "SELECT junction_id, avg(health) FROM copilot_metrics GROUP BY junction_id",
    "select * from copilot_counts_hourly where junction_id = 'J04' and hour_start = '18:00'",
    "WITH t AS (SELECT * FROM copilot_metrics) SELECT * FROM t JOIN junctions j ON j.id = t.junction_id",
    "SELECT name FROM junctions;",
]
BAD = [
    ("DELETE FROM junctions", "only SELECT"),
    ("SELECT 1; DROP TABLE users", "one statement"),
    ("SELECT * FROM users", "table not allowed"),
    ("SELECT * FROM otp_codes", "table not allowed"),
    ("SELECT pg_sleep(10)", "not allowed"),
    ("SELECT * INTO x FROM junctions", "not allowed"),
    ("SELECT * FROM junctions -- hi", "comments"),
    ("", "empty"),
]


@pytest.mark.parametrize("sql", OK)
def test_allowed(sql):
    assert check_sql(sql).endswith("LIMIT 500")


@pytest.mark.parametrize(("sql", "why"), BAD)
def test_refused(sql, why):
    with pytest.raises(UnsafeSQL, match=why):
        check_sql(sql)
