"""Find SUMO from the eclipse-sumo Python package (no system install needed).

SUMO_HOME is read from the `sumo` package and set before traci/sumolib tools are used.
"""

import os
import subprocess
import sys
from pathlib import Path

import sumo

SUMO_HOME = Path(sumo.SUMO_HOME)
os.environ["SUMO_HOME"] = str(SUMO_HOME)
TOOLS = SUMO_HOME / "tools"
if str(TOOLS) not in sys.path:
    sys.path.append(str(TOOLS))

import sumolib  # needs SUMO_HOME set first (above)


def binary(name: str) -> str:
    """Full path of a SUMO program such as 'sumo' or 'netconvert'."""
    return sumolib.checkBinary(name)


def run_tool(script: str, args: list[str], log: Path | None = None) -> None:
    """Run a SUMO Python tool (e.g. routeSampler.py) with this venv's Python. Raises on failure."""
    cmd = [sys.executable, str(TOOLS / script), *args]
    res = subprocess.run(cmd, capture_output=True, text=True, env=os.environ.copy(), check=False)
    if log:
        log.write_text(res.stdout + "\n" + res.stderr, encoding="utf-8")
    if res.returncode != 0:
        raise RuntimeError(f"{script} failed ({res.returncode}):\n{res.stderr[-2000:]}")


def run_binary(name: str, args: list[str], log: Path | None = None) -> None:
    """Run a SUMO program (netconvert, duarouter, ...). Raises on failure."""
    res = subprocess.run([binary(name), *args], capture_output=True, text=True, check=False)
    if log:
        log.write_text(res.stdout + "\n" + res.stderr, encoding="utf-8")
    if res.returncode != 0:
        raise RuntimeError(f"{name} failed ({res.returncode}):\n{res.stderr[-2000:]}")
