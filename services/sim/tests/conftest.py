"""Shared test fixtures: a fast schematic build (network + signal plans, no 24-h demand)."""

import pytest

from sim.build import build
from sim.config import TMC_CSV

# tmc_clean.csv is confidential and not in the public repo: skip tests that need it on a fresh clone.
NEEDS_SURVEY = ("test_registry_demand.py", "test_build_stream.py")


def pytest_collection_modifyitems(config, items):
    if TMC_CSV.exists():
        return
    skip = pytest.mark.skip(reason="data/processed/tmc_clean.csv not present (confidential, local only)")
    for item in items:
        if item.fspath.basename in NEEDS_SURVEY:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def static_build(tmp_path_factory):
    """Build the schematic network into a temp folder once per test session (no routeSampler)."""
    return build("schematic", out_root=tmp_path_factory.mktemp("simbuild"), demand=False)
