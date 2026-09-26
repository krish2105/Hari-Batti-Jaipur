"""Networks and demand for the W2 optimisation study, cut from the calibrated corridor build.

- Isolated junction: one junction with its four arms (for fast single-junction training and a
  clean per-junction comparison). Demand = that junction's own surveyed 15-min turning counts for
  the chosen date, as flows. 11 May trains, 12 May evaluates (a day the agents never saw).
- Corridor J03-J08: the six main-road junctions and their shared links. Demand = routeSampler
  fitted to that date's counts for J03-J08 (J01-J02 are a separate pair with no 12 May counts).
- Stage set: the green stages of the two assumed plans (2-phase with free left, and approach-wise),
  so fixed plans, MaxPressure and PPO all serve the same movements.
Everything produced here is SIM.
"""

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

from .. import config
from ..build import TURN_TARGET, load_manifest, state_string, write_turn_counts
from ..demand import load_day
from ..sumo_env import run_binary, run_tool, sumolib

CAL = config.BUILD_DIR / "schematic"  # the calibrated default build (services/sim/calibrated.json)
OPT_DIR = config.BUILD_DIR / "opt"
CORRIDOR = ["J08", "J07", "J06", "J05", "J04", "J03"]  # west (Mansarovar Metro) -> east (Sanganer Stadium)
ML_REPORTS = config.ROOT / "services" / "ml" / "reports"


def survey_seconds(clock_hhmm: str) -> int:
    """Clock time -> simulation seconds (sim time 0 = 08:00, the start of the survey day)."""
    h, m = (int(x) for x in clock_hhmm.split(":"))
    return ((h - config.SURVEY_DAY_START_HOUR) % 24) * 3600 + m * 60


def _moves(d: dict[str, str]) -> dict[tuple[str, str], str]:
    """Manifest phase moves {"WS": "G"} -> {("W", "S"): "G"}."""
    return {(k[0], k[1]): v for k, v in d.items()}


def stages(manifest: dict, jid: str) -> list[dict[tuple[str, str], str]]:
    """Green stages of the 2-phase and approach-wise plans (duplicates removed, order kept)."""
    out: list[dict[tuple[str, str], str]] = []
    for pid in ("demand2", "webster4"):
        for ph in manifest["plans"][pid][jid]["phases"]:
            mv = _moves(ph["moves"])
            if ph["kind"] == "green" and mv not in out:
                out.append(mv)
    return out


def links_on(net, manifest: dict, jid: str) -> tuple[dict[int, tuple[str, str]], int]:
    """SUMO link index -> (approach side, turn) on a (cut) network, and the number of links."""
    apps = manifest["approaches"][jid]
    side_in = {v["in_edge"]: v["side"] for v in apps.values()}
    side_out = {v["out_edge"]: v["side"] for v in apps.values()}
    links: dict[int, tuple[str, str]] = {}
    conns = net.getTLS(manifest["tls_ids"][jid]).getConnections()
    for in_lane, out_lane, idx in conns:
        s_in, s_out = side_in.get(in_lane.getEdge().getID()), side_out.get(out_lane.getEdge().getID())
        if s_in and s_out:
            turn = next((t for t, target in TURN_TARGET[s_in].items() if target == s_out), None)
            if turn:
                links[idx] = (s_in, turn)
    return links, 1 + max(c[2] for c in conns)


def cut_net(jids: list[str], name: str, force: bool = False) -> Path:
    """Cut the junctions (with all their arms) out of the calibrated network and give each signal
    the shared stage set as its default program (sumo-rl reads the green stages from it)."""
    out = OPT_DIR / name
    net_file = out / "net.net.xml"
    if net_file.exists() and not force:
        return net_file
    out.mkdir(parents=True, exist_ok=True)
    m = load_manifest(CAL)
    keep = sorted(
        {e for j in jids for v in m["approaches"][j].values() for e in (v["in_edge"], v["out_edge"])}
    )
    raw = out / "cut.net.xml"
    run_binary(
        "netconvert",
        ["-s", str(CAL / "network.net.xml"), "--keep-edges.explicit", ",".join(keep), "-o", str(raw)],
    )
    net = sumolib.net.readNet(str(raw), withPrograms=True)
    parts = ["<tlLogics>"]
    for j in jids:
        links, n = links_on(net, m, j)
        parts.append(f'  <tlLogic id="{m["tls_ids"][j]}" type="static" programID="0" offset="0">')
        parts += [f'    <phase duration="30" state="{state_string(s, links, n)}"/>' for s in stages(m, j)]
        parts.append("  </tlLogic>")
    parts.append("</tlLogics>")
    tll = out / "stages.tll.xml"
    tll.write_text("\n".join(parts) + "\n", encoding="utf-8")
    run_binary("netconvert", ["-s", str(raw), "--tllogic-files", str(tll), "-o", str(net_file)])
    raw.unlink()
    shutil.copy(CAL / "vtypes.add.xml", out / "vtypes.add.xml")
    return net_file


def fixed_programs(
    net_file: Path, jids: list[str], plan: str, out: Path, offsets: dict[str, int] | None = None
) -> Path:
    """A fixed-time plan (even / demand2 / webster4) as programID "haribatti" on a cut network,
    with optional corridor offsets (seconds) for a green wave."""
    m = load_manifest(CAL)
    net = sumolib.net.readNet(str(net_file), withPrograms=True)
    parts = ["<additional>"]
    for j in jids:
        links, n = links_on(net, m, j)
        off = (offsets or {}).get(j, 0)
        parts.append(f'  <tlLogic id="{m["tls_ids"][j]}" type="static" programID="haribatti" offset="{off}">')
        for ph in m["plans"][plan][j]["phases"]:
            parts.append(
                f'    <phase duration="{ph["duration_s"]}" state="{state_string(_moves(ph["moves"]), links, n)}"/>'
            )
        parts.append("  </tlLogic>")
    parts.append("</additional>")
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return out


def junction_flows(jid: str, date: str, out: Path) -> Path:
    """Isolated junction demand: one flow per surveyed movement per 15-min slot (Survey, May 2026)."""
    m = load_manifest(CAL)
    apps = m["approaches"][jid]
    day = load_day(date)
    lines = ["<routes>"]
    flows = []
    for mv, series in day.veh.items():
        if mv.junction_id != jid or mv.from_approach not in apps or mv.to_approach not in apps:
            continue
        frm, to = apps[mv.from_approach]["in_edge"], apps[mv.to_approach]["out_edge"]
        for slot, n in enumerate(series):
            if n > 0:
                b = slot * config.SLOT_S
                flow = (
                    f'  <flow id="{frm}-{to}-{slot:02d}" type="mix" begin="{b}" end="{b + config.SLOT_S}" '
                    f'number="{round(n)}" from="{frm}" to="{to}" departLane="best" departSpeed="max" '
                    'departPosLat="random"/>'
                )
                flows.append((b, flow))
    lines += [f for _, f in sorted(flows, key=lambda x: x[0])]
    lines.append("</routes>")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def corridor_routes(date: str, out: Path) -> Path:
    """Corridor J03-J08 demand for a date: routeSampler fitted to that day's turning counts."""
    if out.exists():
        return out
    m = load_manifest(CAL)
    net_file = cut_net(CORRIDOR, "corridor")
    net = sumolib.net.readNet(str(net_file))
    edges = {e.getID() for e in net.getEdges()}
    work = out.parent
    # candidate routes of the calibrated build that stay inside the corridor
    cand = work / f"candidates-{date}.rou.xml"
    kept = ["<routes>"]
    for line in (CAL / "candidates.rou.xml").read_text(encoding="utf-8").splitlines():
        if "<route " in line:
            route_edges = line.split('edges="', 1)[1].split('"', 1)[0].split()
            if all(e in edges for e in route_edges):
                kept.append(line)
    kept.append("</routes>")
    cand.write_text("\n".join(kept) + "\n", encoding="utf-8")
    turns = work / f"turns-{date}.xml"
    info = SimpleNamespace(approaches={j: m["approaches"][j] for j in CORRIDOR})
    write_turn_counts(turns, load_day(date), info)
    run_tool(
        "routeSampler.py",
        ["-r", str(cand), "-t", str(turns), "-o", str(out), "--optimize", "full", "--minimize-vehicles", "0.5",
         "--geh-ok", "5", "--attributes", 'type="mix" departLane="best" departSpeed="max" departPosLat="random"',
         "--prefix", f"d{date[-2:]}_", "--seed", "42", "--threads", "4"],
        log=work / f"routeSampler-{date}.log",
    )  # fmt: skip
    return out


def controlled_lanes(net_file: Path, tls_id: str) -> tuple[list[str], list[str], list[tuple[str, str, int]]]:
    """Incoming lanes, outgoing lanes and (in lane, out lane, link index) for one signal."""
    net = sumolib.net.readNet(str(net_file), withPrograms=True)
    conns = [(i.getID(), o.getID(), k) for i, o, k in net.getTLS(tls_id).getConnections()]
    ins = sorted({c[0] for c in conns})
    outs = sorted({c[1] for c in conns})
    return ins, outs, conns


def neighbours(jid: str) -> tuple[str | None, str | None]:
    """West and east neighbour on the corridor (None at the ends or off the corridor)."""
    if jid not in CORRIDOR:
        return None, None
    i = CORRIDOR.index(jid)
    return (CORRIDOR[i - 1] if i > 0 else None, CORRIDOR[i + 1] if i < len(CORRIDOR) - 1 else None)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
