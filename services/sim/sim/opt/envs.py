"""sumo-rl environments for the W2 study: observations, reward and the MaxPressure controller.

Every adaptive controller (MaxPressure and PPO) runs through the same sumo-rl mechanics: it picks
one of the junction's stages every DELTA_S seconds, a stage change inserts YELLOW_S seconds of
amber (amber + all-red of the fixed plans, lumped), and a stage is held at least MIN_GREEN_S.
Observation (PressLight-style, same size at every junction because all have 4 arms with 4 / 3
lanes): current stage (one-hot), a min-green flag, and per lane the queue and density on the
incoming lanes and the density on the outgoing lanes. The corridor agent also sees each
neighbour's pressure and whether the neighbour is serving the main road.
Reward: the intersection pressure (vehicles leaving − vehicles approaching) / 100.
Environment variable LIBSUMO_AS_TRACI=1 (set by train.py / evaluate.py) makes SUMO run in-process.
"""

import random
from pathlib import Path

import numpy as np
import sumo_rl
from gymnasium import spaces
from sumo_rl.environment.observations import ObservationFunction

from ..config import load_assumptions
from ..sumo_env import SUMO_HOME  # noqa: F401 - sets SUMO_HOME before sumo_rl is imported
from .networks import neighbours, survey_seconds

DELTA_S = 6  # decision every 6 s (sumo-rl needs it longer than the amber)
YELLOW_S = 5  # amber 3 s + all-red 2 s of the fixed plans
MIN_GREEN_S = 10  # same minimum green as the assumed plans
TELEPORT_S = 300  # SUMO default, same as the fixed-plan runs
N_STAGES = 6
N_LANES = 14  # 4 + 4 + 3 + 3 incoming (and outgoing) lanes at every junction


def lane_order(ts) -> tuple[list[str], list[str]]:
    """Incoming and outgoing lanes in signal-link order (stable across processes and junctions)."""
    ins: list[str] = []
    outs: list[str] = []
    for link in ts.sumo.trafficlight.getControlledLinks(ts.id):
        if link:
            i, o, _via = link[0]
            if i not in ins:
                ins.append(i)
            if o not in outs:
                outs.append(o)
    return ins, outs


def _cap(ts, lane: str) -> float:
    """Vehicles that fit on a lane (sumo-rl's measure, with a floor for an empty lane)."""
    return max(1.0, ts.lanes_length.get(lane, ts.sumo.lane.getLength(lane)) / 7.5)


def own_features(ts) -> list[float]:
    if not hasattr(ts, "_hb_lanes"):
        ts._hb_lanes = lane_order(ts)
    ins, outs = ts._hb_lanes
    lane = ts.sumo.lane
    phase = [1.0 if ts.green_phase == i else 0.0 for i in range(N_STAGES)]
    min_green = [1.0 if ts.time_since_last_phase_change >= ts.min_green + ts.yellow_time else 0.0]
    queue = [min(1.0, lane.getLastStepHaltingNumber(x) / _cap(ts, x)) for x in ins]
    dens_in = [min(1.0, lane.getLastStepVehicleNumber(x) / _cap(ts, x)) for x in ins]
    dens_out = [min(1.0, lane.getLastStepVehicleNumber(x) / _cap(ts, x)) for x in outs]
    return phase + min_green + queue + dens_in + dens_out


OWN = N_STAGES + 1 + 3 * N_LANES


class JunctionObservation(ObservationFunction):
    """Single-junction agent: only what this junction's own detectors would see."""

    def __call__(self) -> np.ndarray:
        return np.array(own_features(self.ts), dtype=np.float32)

    def observation_space(self) -> spaces.Box:
        return spaces.Box(low=0.0, high=1.0, shape=(OWN,), dtype=np.float32)


class CorridorObservation(ObservationFunction):
    """Corridor agent: own features + each neighbour's pressure and whether it serves the main road."""

    def __call__(self) -> np.ndarray:
        extra: list[float] = []
        for nb in neighbours(self.ts.id):
            other = self.ts.env.traffic_signals.get(nb) if nb else None
            if other is None:
                extra += [0.0, 0.0]
            else:
                # stages 0, 2, 4 serve the main road (2-phase main, approach-wise W and E)
                main = 1.0 if other.green_phase in (0, 2, 4) else 0.0
                extra += [float(np.clip(other.get_pressure() / 100.0, -1, 1)), main]
        return np.array(own_features(self.ts) + extra, dtype=np.float32)

    def observation_space(self) -> spaces.Box:
        return spaces.Box(low=-1.0, high=1.0, shape=(OWN + 4,), dtype=np.float32)


def pressure_reward(ts) -> float:
    """Vehicles on outgoing lanes minus vehicles on incoming lanes, scaled (higher = more moved through)."""
    return ts.get_pressure() / 100.0


def sumo_extra(work: Path | None = None) -> str:
    """Extra SUMO options shared with the fixed-plan runs: vehicle types and the sublane model."""
    a = load_assumptions()
    parts = ["--lateral-resolution", str(a["sublane"]["lateral_resolution_m"]), "--no-step-log", "true"]
    if work is not None:
        parts += ["-a", str(work / "vtypes.add.xml")]
    return " ".join(parts)


class HBEnv(sumo_rl.SumoEnvironment):
    """sumo-rl environment that starts each training episode at a random time of the survey day.

    starts: candidate start clock times ("HH:MM"); one is drawn at every reset (training) or the
    first one is always used (evaluation). The episode lasts `seconds` simulated seconds."""

    def __init__(self, starts: list[str], seconds: int, rng_seed: int = 0, **kw):
        self._starts = [survey_seconds(s) for s in starts]
        self._rng = random.Random(rng_seed)
        self._seconds = seconds
        kw.setdefault("delta_time", DELTA_S)
        kw.setdefault("yellow_time", YELLOW_S)
        kw.setdefault("min_green", MIN_GREEN_S)
        kw.setdefault("max_green", 120)
        kw.setdefault("time_to_teleport", TELEPORT_S)
        kw.setdefault("sumo_warnings", False)
        kw.setdefault("add_system_info", False)
        kw.setdefault("add_per_agent_info", False)
        super().__init__(begin_time=self._starts[0], num_seconds=seconds, **kw)

    def reset(self, seed=None, **kwargs):
        self.begin_time = self._rng.choice(self._starts)
        self.sim_max_time = self.begin_time + self._seconds
        return super().reset(seed=seed, **kwargs)

    def _start_simulation(self):
        # sumo-rl passes "-b <t>" as ONE argument; give SUMO a proper "--begin" instead
        keep_begin = self.begin_time
        self.begin_time = 0
        extra = self.additional_sumo_cmd
        self.additional_sumo_cmd = f"{extra or ''} --begin {keep_begin}".strip()
        try:
            super()._start_simulation()
        finally:
            self.begin_time = keep_begin
            self.additional_sumo_cmd = extra


def make_env(net_file: Path, route_file: Path, starts: list[str], seconds: int, corridor: bool = False,
             single_agent: bool = True, sumo_seed: int | str = "random", rng_seed: int = 0,
             extra_cmd: str = "") -> HBEnv:  # fmt: skip
    """One environment on a cut network (isolated junction or the J03-J08 corridor)."""
    work = net_file.parent
    return HBEnv(
        starts=starts,
        seconds=seconds,
        rng_seed=rng_seed,
        net_file=str(net_file),
        route_file=str(route_file),
        single_agent=single_agent,
        reward_fn=pressure_reward,
        observation_class=CorridorObservation if corridor else JunctionObservation,
        sumo_seed=sumo_seed,
        additional_sumo_cmd=f"{sumo_extra(work)} {extra_cmd}".strip(),
    )


# ---------------------------------------------------------------- MaxPressure


def stage_pressures(ts) -> list[float]:
    """For every stage: sum over its green links of (vehicles on the in lane − vehicles on the out lane)."""
    lane = ts.sumo.lane
    links = ts.sumo.trafficlight.getControlledLinks(ts.id)
    counts: dict[str, int] = {}

    def n(x: str) -> int:
        if x not in counts:
            counts[x] = lane.getLastStepVehicleNumber(x)
        return counts[x]

    out = []
    for stage in ts.green_phases:
        p = 0.0
        for idx, ch in enumerate(stage.state):
            if ch in "Gg" and idx < len(links) and links[idx]:
                i, o, _ = links[idx][0]
                p += n(i) - n(o)
        out.append(p)
    return out


def max_pressure_actions(env: HBEnv) -> dict[str, int]:
    """MaxPressure (Varaiya 2013): every signal picks the stage with the highest pressure."""
    return {ts_id: int(np.argmax(stage_pressures(ts))) for ts_id, ts in env.traffic_signals.items()}
