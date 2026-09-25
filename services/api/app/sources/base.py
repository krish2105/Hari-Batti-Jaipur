"""PhaseSource: the one interface every signal data provider implements.

Swapping the simulator for the police ITMS feed means writing one new PhaseSource; nothing
downstream changes. Sources only READ signal states — there is no method to control a signal.
"""

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Literal, Protocol

PhaseState = dict  # camelCase JSON, see packages/core/src/types.ts


class PhaseSource(Protocol):
    """Any provider of live signal phases (simulator, crowd, police ITMS)."""

    name: Literal["SIM", "CROWD", "ITMS"]

    def stream(self) -> AsyncIterator[PhaseState]:
        """Yield PhaseState dicts as they arrive (about 1 Hz per approach)."""
        ...

    async def history(self, junction_id: str, start: datetime, end: datetime) -> list[PhaseState]:
        """Past phase changes for one junction."""
        ...
