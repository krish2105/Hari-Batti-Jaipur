"""The copilot's SQL guard only lets one read-only SELECT on allowed views through."""

import pytest

from app.copilot.sqlguard import UnsafeSQL, check_sql

OK = [
    "SELECT junction_id, avg(health) FROM copilot_metrics GROUP BY junction_id",
    "select * from copilot_counts_hourly where junction_id = 'J04' and hour_start = '18:00'",
    "WITH t AS (SELECT * FROM copilot_metrics) SELECT * FROM t JOIN junctions j ON j.id = t.junction_id",
    "SELECT name FROM junctions;",
    "SELECT junction_id, round(avg(health)::numeric, 1) AS h, count(*) FILTER (WHERE health < 50) FROM copilot_metrics WHERE hour IN (17, 18) GROUP BY junction_id ORDER BY h",
    "SELECT junction_id, rank() OVER (PARTITION BY survey_date ORDER BY health) FROM copilot_metrics WHERE junction_id = 'set_config(x)'",
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
    # injection attempts (P8 W16)
    ("SELECT name FROM junctions UNION SELECT email FROM users", "table not allowed"),
    ("SELECT * FROM junctions WHERE id = 'J01' OR 1=1; DELETE FROM users", "one statement"),
    ("SELECT * FROM junctions /* hidden */", "comments"),
    ("SELECT pg_read_file('/etc/passwd')", "not allowed"),
    ("SELECT * FROM dblink('host=x', 'select 1') AS t(a int)", "not allowed"),
    ("COPY junctions TO '/tmp/x'", "only SELECT"),
    ("SELECT set_config('role', 'haribatti', false)", "not allowed"),
    ("SELECT lo_import('/etc/passwd')", "not allowed"),
    ("SELECT * FROM pg_catalog.pg_authid", "table not allowed"),
    ("SELECT * FROM information_schema.tables", "table not allowed"),
    ("UPDATE junctions SET name = 'x'", "only SELECT"),
    ("WITH x AS (DELETE FROM junctions RETURNING *) SELECT * FROM x", "not allowed"),
    ("SELECT query_to_xml('select email from users', true, true, '')", "function not allowed"),
    ("SELECT current_setting('jwt_secret')", "function not allowed"),
    ("SELECT pg_catalog.pg_read_binary_file('x')", "function not allowed"),
]


@pytest.mark.parametrize("sql", OK)
def test_allowed(sql):
    assert check_sql(sql).endswith("LIMIT 500")


@pytest.mark.parametrize(("sql", "why"), BAD)
def test_refused(sql, why):
    with pytest.raises(UnsafeSQL, match=why):
        check_sql(sql)
