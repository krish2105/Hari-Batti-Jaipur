"""Prepare the database before `make api`: migrate, seed from the data files, compute metrics.

If Postgres is not running the API still starts (file-based endpoints work); this prints why.
"""

import logging
import subprocess
import sys

from .db import db_available
from .jobs import metrics, seed

log = logging.getLogger("haribatti.bootstrap")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if not db_available():
        log.warning("Postgres not reachable — run `make infra`. Starting the API without the database.")
        return 0
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    log.info("seed: %s", seed.run())
    log.info("metrics: %d junction-hours", metrics.run())
    return 0


if __name__ == "__main__":
    sys.exit(main())
