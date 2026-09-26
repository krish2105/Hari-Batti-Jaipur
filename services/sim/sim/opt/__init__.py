"""W2 signal-timing optimisation on the calibrated digital twin (everything here is SIM).

networks.py  isolated-junction and corridor networks cut from the calibrated build, survey demand
             for any date, and the shared stage set every adaptive controller chooses from
envs.py      sumo-rl environments, observations (PressLight-style), pressure reward, MaxPressure
train.py     PPO training (stable-baselines3): single-junction and corridor agents
evaluate.py  every controller x 5 seeds on held-out 12 May demand -> controllers.json
greenwave.py corridor offsets that maximise green bandwidth both ways -> timespace.json
report.py    services/ml/reports/optimisation.md
Recommendations only: nothing here can reach a real signal.
"""
