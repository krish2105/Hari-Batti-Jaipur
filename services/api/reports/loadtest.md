# HariBatti API — load test (P8 W10)

> **SIM** · 400 synthetic junctions (1,600 approaches, one message each per second, realistic 60 s plans) on
> their own Redis channel and API instance (`RECORD_PHASE_EVENTS=false`), so nothing reached the pilot data.
> Machine: one laptop running the API, Redis, the publisher, **all client processes** and the HTTP load
> generator at the same time — a pessimistic setup; a server with its own clients elsewhere does better.
> 60 s measured after all clients had connected. Lag = time from publishing a state to a client receiving it.

| Run | Clients | Each client follows | Connected / errors | Lag p50 / p95 / p99 (ms) | HTTP req/s reached (target 200) | HTTP errors | HTTP p50 / p95 / p99 (ms) | API CPU % (sum of cores) / RAM MB | Redis CPU % / MB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Before (per-client queues), 1 worker | 1,000 | all 1,600 approaches | 513 / 487 | 2,278 / 4,662 / 5,158 | 200.1 | 5,980 | 5,599 / 9,241 / 9,241 | 99.9 / 149 | 1.3 / 1.1 |
| After (broadcast), 1 worker | 1,000 | all 1,600 approaches | 1,000 / 0 | 627 / 768 / 788 | 136.9 | 0 | 198 / 782 / 1,299 | 60.6 / 158 | 0.6 / 1.1 |
| After, 1 worker | 10,000 | all 1,600 approaches | 8,004 / 6,574 | 1,042 / 1,513 / 1,751 | 58.2 | 415 | 1,083 / 7,821 / 10,065 | 58.6 / 360 | 0.7 / 1.2 |
| After, 1 worker | 10,000 | 1 junction each (1 in 1,000: all) | 9,964 / 32 | 609 / 882 / 965 | 92.8 | 4 | 290 / 1,288 / 2,204 | 51.9 / 467 | 0.9 / 1.2 |
| After, 4 workers | 10,000 | 1 junction each (1 in 1,000: all) | 9,996 / 0 | 569 / 657 / 748 | 200.0 | 1 | 3 / 47 / 106 | 87.5 / 824 | 0.8 / 1.2 |

The 10,000-client runs used 6 client processes × 1,666 = 9,996 clients.

## Result against the goal

**Goal: p95 message lag < 1.5 s at 10,000 clients.** Met: **657 ms with 4 workers** (882 ms with 1 worker), with
0 connection errors and the read API holding 200 requests/s at p95 47 ms. Before the fixes, one worker could not
serve even 1,000 clients (half failed to connect, p95 lag 4.7 s, 99.8% of HTTP requests failed).

## The bottlenecks found and fixed

1. **Per-client fan-out** — every state went into every client's queue and was serialised once per client
   (1,600 × N operations per second; 100% CPU at 1,000 clients). Now one broadcaster collects states for 0.5 s,
   keeps the newest per approach, serialises each frame **once per subscription** and sends the same text to all
   clients; a client still busy with the last frame skips one instead of slowing the others (`app/broadcast.py`).
2. **Everyone received everything** — clients can now subscribe to their junctions (`?junctions=J03,J04`), the
   snapshot on connect is cached per tick, and the dashboard and app request only their own junctions. The
   worst case (every client receiving all 1,600 approaches) is shown above for honesty: 1 worker then cannot
   hold 10,000 clients.
3. **One process** — the API is stateless per connection (each worker subscribes to Redis itself), so
   `--workers N` spreads clients over cores; per-message compression is off (`--ws-per-message-deflate false`)
   because it costs CPU for every client, and the accept backlog is raised (`--backlog 4096`).

Also found: the freshness monitor would have sent one "impossible value" alert per occurrence — an alert flood;
repeats for the same approach are now suppressed for 10 minutes.

Reproduce: `make loadtest` (see docs/scaling.md). Raw results: `services/api/loadtest/results/`.
