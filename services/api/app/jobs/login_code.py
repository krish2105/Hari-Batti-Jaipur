"""Issue a sign-in code from the server console (P8 W18), for when no email service is configured.

    docker compose -f infra/docker-compose.prod.yml --env-file infra/.env.production \\
        exec api uv run --no-sync python -m app.jobs.login_code you@example.in

Only someone with shell access to the server can run this. The code works once, for 10 minutes.
"""

import sys

from ..audit_log import record
from ..auth import issue_code


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python -m app.jobs.login_code <email>")
        return 2
    try:
        code = issue_code(sys.argv[1])
    except ValueError as e:
        print(e)
        return 1
    record("login_code_console", sys.argv[1].strip().lower(), None)
    print(f"Sign-in code for {sys.argv[1]}: {code} (valid 10 minutes, one use)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
