"""W10 load test: many app WebSocket clients + synthetic junctions + read-API traffic, measured.

Everything here is SIM and stays on its own Redis channel ("loadtest") and API instance (started
with RECORD_PHASE_EVENTS=false), so nothing reaches the pilot data.

  uv run --group loadtest python -m loadtest.run --api http://localhost:8013 --clients 10000 \
      --junctions 400 --rps 200 --seconds 60 --label after

Measures: message lag (publish -> client receive) p50/p95/p99, WebSocket connect errors and drops,
HTTP latency p50/p95/p99 and errors at the target request rate, API process CPU and memory, Redis
CPU and memory (from INFO). Writes loadtest/results/<label>.json.
"""

import argparse
import asyncio
import json
import multiprocessing as mp
import os
import random
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path

RESULTS = Path(__file__).parent / "results"


def pct(xs: list[float], p: float) -> float | None:
    if not xs:
        return None
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(p / 100 * len(xs)))], 1)


# ---- synthetic junctions (SIM) -------------------------------------------------------------------


async def publisher(redis_url: str, channel: str, junctions: int, seconds: float, stop: float) -> int:
    """Every approach of every synthetic junction once a second (like the simulator), source SIM."""
    import redis.asyncio as aioredis

    # realistic fixed plans: 60 s cycle, 25 s green, 3 s amber, a random offset per junction
    approaches = [
        (f"LT{j:03d}", f"LT{j:03d}-{a}", random.uniform(0, 60) + (30 if a in "bd" else 0))
        for j in range(1, junctions + 1)
        for a in "abcd"
    ]
    r, sent, errors = aioredis.from_url(redis_url), 0, 0
    while time.time() < stop:
        tick = time.time()
        try:
            pipe = r.pipeline(transaction=False)
            for jid, aid, off in approaches:
                now = time.time()
                x = (now + off) % 60
                colour, rem = (
                    ("GREEN", 25 - x) if x < 25 else ("AMBER", 28 - x) if x < 28 else ("RED", 60 - x)
                )
                pipe.publish(channel, json.dumps({"junctionId": jid, "approachId": aid, "colour": colour, "secondsRemaining": round(rem, 1),
                                                  "confidence": 0.9, "source": "SIM", "updatedAt": datetime.fromtimestamp(now, UTC).isoformat(),
                                                  "sentAt": now, "loadtest": True}))  # fmt: skip
            await pipe.execute()
            sent += len(approaches)
        except (OSError, aioredis.RedisError):
            errors += 1
            await r.aclose()
            r = aioredis.from_url(redis_url)
        await asyncio.sleep(max(0.0, 1.0 - (time.time() - tick)))
    await r.aclose()
    return sent


# ---- WebSocket clients (one OS process per slice) ------------------------------------------------


def client_proc(
    ws_url: str, n: int, ramp_per_s: float, stop: float, out: str, seed: int, junctions: int = 400
) -> None:
    import websockets

    async def one(i: int, stats: dict) -> None:
        await asyncio.sleep(i / ramp_per_s)
        # like real use: an app follows one junction; 1 in 1,000 clients is a control-room screen watching all
        url = ws_url if i % 1000 == 0 else f"{ws_url}?junction=LT{random.randint(1, junctions):03d}"
        try:
            async with websockets.connect(
                url, open_timeout=30, max_size=2**24, compression=None, ping_interval=None
            ) as ws:
                stats["connected"] += 1
                while time.time() < stop:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=max(0.1, stop - time.time()))
                    except TimeoutError:
                        break
                    now = time.time()
                    msg = json.loads(raw)
                    states = msg.get("states") or []
                    stats["messages"] += 1
                    stats["states"] += len(states)
                    if msg.get("type") != "snapshot" and states and (i % 20 == 0):  # sample 5% of clients
                        s = states[-1]
                        if "sentAt" in s:
                            stats["lag"].append((now - s["sentAt"]) * 1000)
        except Exception as e:  # noqa: BLE001 - counted, not raised
            stats["errors"] += 1
            stats["errorKinds"][type(e).__name__] = stats["errorKinds"].get(type(e).__name__, 0) + 1

    async def main() -> None:
        stats = {"connected": 0, "messages": 0, "states": 0, "errors": 0, "errorKinds": {}, "lag": []}
        await asyncio.gather(*(one(i, stats) for i in range(n)))
        Path(out).write_text(json.dumps(stats))

    random.seed(seed)
    asyncio.run(main())


# ---- read API traffic (open loop) ----------------------------------------------------------------


async def http_load(api: str, rps: int, stop: float) -> dict:
    import httpx

    paths = [
        "/junctions",
        "/signals/latest?junction=LT001",
        "/corridor/mansarovar/kpis",
        "/health",
        "/junctions/J05",
    ]
    lat, errors, codes = [], 0, {}

    async def one(c: httpx.AsyncClient, path: str) -> None:
        nonlocal errors
        t = time.perf_counter()
        try:
            r = await c.get(api + path, timeout=10)
            codes[r.status_code] = codes.get(r.status_code, 0) + 1
            if r.status_code >= 400:
                errors += 1
            lat.append((time.perf_counter() - t) * 1000)
        except httpx.HTTPError:
            errors += 1

    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=200)) as c:
        tasks, k = [], 0
        start = time.time()
        while time.time() < stop:
            due = start + k / rps
            await asyncio.sleep(max(0.0, due - time.time()))
            tasks.append(asyncio.create_task(one(c, paths[k % len(paths)])))
            k += 1
        await asyncio.gather(*tasks)
    return {"requests": k, "achievedRps": round(k / max(1e-9, stop - start), 1), "errors": errors, "codes": codes,
            "p50": pct(lat, 50), "p95": pct(lat, 95), "p99": pct(lat, 99)}  # fmt: skip


def http_proc(api: str, rps: int, stop: float, out: str) -> None:
    """The read-API load in its own process, so the publisher cannot slow the request schedule."""
    Path(out).write_text(json.dumps(asyncio.run(http_load(api, rps, stop))))


# ---- resource sampling ---------------------------------------------------------------------------


async def sample(api_pid: int, redis_url: str, stop: float) -> dict:
    import psutil
    import redis.asyncio as aioredis

    p = psutil.Process(api_pid)
    procs = [p, *p.children(recursive=True)]
    for q in procs:
        q.cpu_percent(None)
    r = aioredis.from_url(redis_url)
    info0 = await r.info("cpu")
    cpu, rss = [], []
    t0 = time.time()
    while time.time() < stop:
        await asyncio.sleep(2)
        cpu.append(sum(q.cpu_percent(None) for q in procs))
        rss.append(sum(q.memory_info().rss for q in procs) / 2**20)
    info1, mem = await r.info("cpu"), await r.info("memory")
    await r.aclose()
    dt = time.time() - t0
    redis_cpu = (
        100
        * (
            (info1["used_cpu_sys"] + info1["used_cpu_user"])
            - (info0["used_cpu_sys"] + info0["used_cpu_user"])
        )
        / dt
    )
    return {"apiCpuPctMean": round(statistics.mean(cpu), 1) if cpu else None, "apiCpuPctMax": round(max(cpu), 1) if cpu else None,
            "apiRssMbMax": round(max(rss), 1) if rss else None, "redisCpuPct": round(redis_cpu, 1), "redisUsedMb": round(mem["used_memory"] / 2**20, 1)}  # fmt: skip


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8013")
    ap.add_argument("--api-pid", type=int, required=True)
    ap.add_argument("--redis", default="redis://localhost:6380/0")
    ap.add_argument("--channel", default="loadtest")
    ap.add_argument("--clients", type=int, default=10_000)
    ap.add_argument("--procs", type=int, default=5)
    ap.add_argument("--ramp", type=float, default=500, help="new connections per second (all processes)")
    ap.add_argument("--junctions", type=int, default=400)
    ap.add_argument("--rps", type=int, default=200)
    ap.add_argument("--seconds", type=float, default=60)
    ap.add_argument("--label", default="run")
    a = ap.parse_args()
    RESULTS.mkdir(exist_ok=True)
    ramp_s = a.clients / a.ramp
    t_measure = time.time() + ramp_s + 5  # measure only after every client had time to connect
    stop = t_measure + a.seconds
    ws_url = a.api.replace("http", "ws", 1) + "/ws/signals"
    per = a.clients // a.procs
    outs = [str(RESULTS / f".{a.label}-c{i}.json") for i in range(a.procs)]
    procs = [
        mp.Process(target=client_proc, args=(ws_url, per, a.ramp / a.procs, stop, outs[i], i, a.junctions))
        for i in range(a.procs)
    ]
    for p in procs:
        p.start()
    http_out = str(RESULTS / f".{a.label}-http.json")

    async def orchestrate() -> tuple:
        pub = asyncio.create_task(publisher(a.redis, a.channel, a.junctions, a.seconds, stop))
        await asyncio.sleep(max(0.0, t_measure - time.time()))
        hp = mp.Process(target=http_proc, args=(a.api, a.rps, stop, http_out))
        hp.start()
        out = await asyncio.gather(pub, sample(a.api_pid, a.redis, stop))
        await asyncio.to_thread(hp.join, 120)
        return out

    sent, res = asyncio.run(orchestrate())
    http = json.loads(Path(http_out).read_text())
    Path(http_out).unlink(missing_ok=True)
    for p in procs:
        p.join(timeout=120)
    parts = [json.loads(Path(o).read_text()) for o in outs if Path(o).exists()]
    for o in outs:
        Path(o).unlink(missing_ok=True)
    lag = [x for s in parts for x in s["lag"]]
    kinds: dict[str, int] = {}
    for s in parts:
        for k, v in s["errorKinds"].items():
            kinds[k] = kinds.get(k, 0) + v
    result = {
        "label": a.label, "at": datetime.now(UTC).isoformat(), "source": "SIM (load test)", "machine": f"{os.cpu_count()} CPU laptop (API, Redis, publisher and all clients on one machine)",
        "target": {"clients": a.clients, "junctions": a.junctions, "approaches": a.junctions * 4, "rps": a.rps, "seconds": a.seconds},
        "ws": {"connected": sum(s["connected"] for s in parts), "errors": sum(s["errors"] for s in parts), "errorKinds": kinds,
               "frames": sum(s["messages"] for s in parts), "states": sum(s["states"] for s in parts),
               "lagMs": {"p50": pct(lag, 50), "p95": pct(lag, 95), "p99": pct(lag, 99), "samples": len(lag)}},
        "published": sent, "http": http, "resources": res,
    }  # fmt: skip
    (RESULTS / f"{a.label}.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
