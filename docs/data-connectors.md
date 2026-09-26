# HariBatti data connectors — setup guide

*For the Jaipur Traffic Police ITMS team and signal vendors. Print-friendly: plain text and tables only.*

HariBatti shows signal countdowns to riders and helps officers audit signal timing. Today the countdowns
come from a simulator (labelled **SIM**). A data connector lets HariBatti **read** the real signal
states from your system instead, so every timer can say **ITMS**.

## What HariBatti will and will not do

| HariBatti will | HariBatti will never |
| --- | --- |
| Read signal states (colour + seconds left) from a feed you choose | Send any command, plan or setting to a signal or controller |
| Use only HTTP GET, WebSocket receive, MQTT subscribe, or read files you copy to it | Publish to your MQTT broker, POST/PUT/DELETE to your API, or change your files |
| Keep your endpoints and passwords in a private settings file on its own server | Put your endpoints or passwords in its public code |
| Label every timer with where it came from (ITMS, SIM, CROWD) | Show a timer without its source |

This is enforced in code: an automated test fails if any connector ever gains a method that could
write, send, publish or control. The API route list is also checked on every build.

## Ways to connect (pick one)

| Option | What you provide | How often |
| --- | --- | --- |
| **HTTP JSON (polling)** | A URL that returns current signal states as JSON, plus an access token | HariBatti asks once a second (adjustable) |
| **WebSocket** | A `wss://` URL that pushes JSON messages | As you send them |
| **MQTT** | Broker address, topic (e.g. `jaipur/signals/+/state`), a read-only user | As you publish them |
| **CSV / Excel files** | A folder (or an SFTP location we sync from) where your system drops exports | Every few seconds to every few minutes |
| **SAE J2735 SPaT** | SPaT messages in JSON form over any of the above | As sent (usually 10 per second) |

## What one record needs

Any field names work; we map them. Each record needs:

| Meaning | Example field name in your feed | Example value |
| --- | --- | --- |
| Junction | `junctionCode` | `MSR-05` |
| Arm / approach / signal group | `armNo` | `1` |
| Current colour | `aspect` | `G`, `GREEN`, `2` (any consistent words) |
| Seconds until the colour changes | `remainingSec` | `24` |
| Time the state was measured (optional, recommended) | `updatedAt` | `2026-09-01T12:00:00+05:30` or epoch seconds |

For SPaT we read `intersections[].id`, `states[].signalGroup`, `eventState` and `timing.minEndTime`
(tenths of a second within the hour). "Dark" and "unavailable" states and unknown times are skipped.

## Mapping your IDs to ours

HariBatti's pilot junctions are **J01–J08** (Mansarovar corridor). Each arm has an ID like
`J05-mansarover-metro`. An Admin opens **Signal Command → Data connectors**, picks the connector and fills in:

1. your field names (the table above),
2. your colour words (for example `R=RED`, `Y=AMBER`, `G=GREEN`),
3. one row per arm: your `junction/arm` (for example `MSR-05/1`) → our arm, chosen from a list.

Before saving, paste a few real records into **Live preview**: it shows each mapped timer and lists
any record it could not map. Nothing is fetched, stored or sent by the preview. Mappings that name
a junction outside J01–J08 are refused.

## Switching the live feed

1. Copy `config/connectors.example.yaml` to `config/connectors.yaml` on the HariBatti server and fill in your
   connector (URLs and topics go here; this file is never committed).
2. Put tokens and passwords in the server's `.env` file (for example `ITMS_API_TOKEN=…`); the YAML only names them.
3. Set `SIGNAL_SOURCE=<connector id>` in `.env` and restart the API. `SIGNAL_SOURCE=sim` switches back.

The dashboard's Data connectors screen then shows, for the live connector: records received and
rejected, age of the latest record, and **clock drift** (the difference between your timestamps and
ours). Drift above 2 seconds raises a warning, because countdowns depend on both clocks agreeing: please
keep your controllers and servers on NTP.

## Timing plans (no live feed needed)

If you can share the timing plan sheet (CSV, Excel, or a PDF with a table), HariBatti turns it into a
**proposed** timing file for a person to check:

```
cd services/api && uv run python -m app.connectors.timing_import plan.pdf
```

It writes `data/signal_timings.proposed.csv` and lists anything that needs checking (unknown junctions,
greens outside 3–240 s, amber outside 2–6 s, phases that do not add up to the cycle). Nothing is applied
automatically; reviewed rows are copied into `data/signal_timings.csv` by hand. Scanned PDFs need OCR first.

## Testing without your system

A made-up demo feed ships with the code (labelled **SIM**, because it is not real data):
`SIGNAL_SOURCE=demo-replay`. You can also record a short sample of your feed on the HariBatti server
(`uv run python -m app.connectors.replay record <id> sample.jsonl --seconds 600`) and replay it for tests.
Recordings stay on that server and out of the public code.

## Data handling

- Feed data is used to show countdowns and to store colour changes for audits (the `phase_events` table).
- Recordings, drop folders and imported timing proposals are excluded from the public repository.
- HariBatti uses no paid cloud services; the feed stays on the server you choose.

## Contact

Questions about a connector: open an issue on the project repository or contact the HariBatti team
through the Jaipur Traffic Police project channel.
