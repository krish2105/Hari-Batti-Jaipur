<!-- Launch: claude --model opus --effort high --permission-mode plan -->
Do docs/02-dashboard.md Phase 1 (simulator) in services/sim.
Install SUMO with `uv add eclipse-sumo traci sumolib` and read SUMO_HOME from the `sumo` Python package.
Write a script that downloads the OSM extract covering the Mansarovar corridor junctions J01–J08 (data/junction_registry.csv), build the network with netconvert,
build SUMO demand from data/processed/tmc_clean.csv (15-min flows and turn ratios per junction; 11 May = calibration, 12 May = validation), use data/signal_timings.csv if filled else a flagged default plan, and stream PhaseState JSON to Redis channel "signals" at 1 Hz.
`make sim` must start it. Stop after this phase and tell me how to verify.
