"""Shared test fixtures: a fast schematic build (network + signal plans, no 24-h demand)."""

import pytest

from sim.build import build


@pytest.fixture(scope="session")
def static_build(tmp_path_factory):
    """Build the schematic network into a temp folder once per test session (no routeSampler)."""
    return build("schematic", out_root=tmp_path_factory.mktemp("simbuild"), demand=False)
