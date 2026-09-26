# Scaling HariBatti

*Measured, not guessed: see [services/api/reports/loadtest.md](../services/api/reports/loadtest.md).*

## Where we are (September 2026)

| Load | Result | Setup |
| --- | --- | --- |
| 10,000 app clients on WebSockets, 400 junctions updating every second, read API at 200 requests/s | p95 message lag **657 ms**, 0 connection errors, HTTP p95 **47 ms** | 1 laptop, API with 4 workers (clients and generators on the same laptop) |
| Same, 1 worker | p95 lag 882 ms, 32 of 10,000 connections failed during the ramp | 1 laptop |

The Mansarovar pilot (8 junctions, 32 approaches) needs a small fraction of this: one 2-vCPU server with
2 workers is plenty.

## How the live feed scales

```
signal source (SIM / ITMS connector) -> Redis pub/sub -> each API worker: LiveHub -> Broadcaster -> WebSocket clients
```

- **Batching:** each worker sends one frame every 0.5 s with only the newest state per approach.
- **Serialise once:** a frame is built once per subscription (all junctions, or a set such as `?junctions=J03,J04`)
  and the same text goes to every client with that subscription.
- **Slow clients skip, not block:** a client still receiving the last frame skips one and gets the newest next time.
- **Subscriptions:** apps ask only for their corridor; the dashboard only for the pilot junctions; at most 50 junctions per connection.
- **Workers:** every worker subscribes to Redis itself, so adding workers (and servers behind a load balancer) adds capacity linearly.
- **No compression per message** (`--ws-per-message-deflate false`): compressing for every client costs more CPU than it saves.

## Next steps, in order

1. **Production start command:** `uvicorn app.main:app --workers <cores> --ws-per-message-deflate false --backlog 4096 --timeout-graceful-shutdown 3` behind Caddy (TLS).
2. **Beyond one server:** several API servers behind a load balancer with WebSocket support; Redis stays the fan-in.
   Rate-limit counters move from process memory to Redis (app/ratelimit.py) so limits hold across servers.
3. **Many cities / tenants:** one Redis channel per tenant or city, so a worker only receives states it may send.
4. **Beyond ~50,000 clients per city:** a dedicated push tier (e.g. a small Go or Rust WebSocket fan-out, or a managed
   pub/sub gateway) fed by Redis; the API stays for REST.

## Reproduce

```
make infra                   # Postgres + Redis
make loadtest CLIENTS=10000  # starts an isolated API on port 8013 (4 workers), runs 60 s, writes the result
```
