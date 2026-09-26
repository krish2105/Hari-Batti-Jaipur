"""PPO training (stable-baselines3) for the W2 study. Training data: 11 May only (SIM).

single    one policy for any isolated junction: 8 SUMO processes in parallel, each an isolated
          J03-J08 junction with its own 11 May surveyed demand, episodes starting at random times
          of the survey day (08:00-20:45).
corridor  one shared policy for all six corridor junctions (J03-J08) in the same simulation,
          with neighbour observations (PressLight-style); the six agents act as six environments.
Models are saved to services/sim/build/opt/models/<kind>-seed<k>.zip (not committed).
Run: uv run --group rl python -m sim.opt.train single --seed 0 --steps 200000
"""

import argparse
import json
import os
import time
from pathlib import Path

os.environ.setdefault("LIBSUMO_AS_TRACI", "1")  # SUMO in-process: much faster; one SUMO per process

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv, VecEnv, VecMonitor, VecNormalize

from .envs import make_env
from .networks import CORRIDOR, OPT_DIR, corridor_routes, cut_net, junction_flows

TRAIN_DATE = "2026-05-11"
# every 15 minutes from 07:45 to 21:00 (sim time 0 = 08:00; 07:45 is the next morning's last slot)
TRAIN_STARTS = [f"{h:02d}:{m:02d}" for h in range(8, 21) for m in (0, 15, 30, 45)]
EPISODE_S = 3600
MODELS = OPT_DIR / "models"
PPO_KW = {
    "n_steps": 256,
    "batch_size": 256,
    "n_epochs": 10,
    "learning_rate": 3e-4,
    "gamma": 0.98,
    "gae_lambda": 0.95,
    "clip_range": 0.2,
    "ent_coef": 0.01,
    "policy_kwargs": {"net_arch": [128, 128]},
}


def isolated_inputs(jid: str, date: str) -> tuple[Path, Path]:
    net = cut_net([jid], jid)
    routes = net.parent / f"flows-{date}.rou.xml"
    if not routes.exists():
        junction_flows(jid, date, routes)
    return net, routes


def _single_env(jid: str, seed: int, rank: int):
    def thunk():
        net, routes = isolated_inputs(jid, TRAIN_DATE)
        return make_env(net, routes, TRAIN_STARTS, EPISODE_S, single_agent=True,
                        sumo_seed=1000 * seed + rank, rng_seed=1000 * seed + rank)  # fmt: skip

    return thunk


class AgentsVecEnv(VecEnv):
    """The signals of ONE multi-agent simulation seen by SB3 as parallel environments that share a
    policy (parameter sharing). They act in lockstep: every signal decides every DELTA_S seconds."""

    def __init__(self, env):
        self.env = env
        self.ids = [j for j in CORRIDOR if j in env.ts_ids]
        super().__init__(len(self.ids), env.observation_spaces(self.ids[0]), env.action_spaces(self.ids[0]))
        self._actions = None

    def _stack(self, obs: dict) -> np.ndarray:
        return np.stack([obs[i] for i in self.ids]).astype(np.float32)

    def reset(self):
        return self._stack(self.env.reset())

    def step_async(self, actions):
        self._actions = actions

    def step_wait(self):
        obs, rew, dones, _ = self.env.step({i: int(a) for i, a in zip(self.ids, self._actions, strict=True)})
        o = self._stack(obs)
        r = np.array([rew[i] for i in self.ids], dtype=np.float32)
        done = bool(dones["__all__"])
        infos = [{} for _ in self.ids]
        if done:
            for k, info in enumerate(infos):
                info["terminal_observation"] = o[k]
                info["TimeLimit.truncated"] = True
            o = self.reset()
        return o, r, np.full(self.num_envs, done), infos

    def close(self):
        self.env.close()

    def get_attr(self, attr_name, indices=None):
        return [getattr(self.env, attr_name)] * self.num_envs

    def set_attr(self, attr_name, value, indices=None):
        setattr(self.env, attr_name, value)

    def env_method(self, method_name, *args, indices=None, **kwargs):
        return [getattr(self.env, method_name)(*args, **kwargs)] * self.num_envs

    def env_is_wrapped(self, wrapper_class, indices=None):
        return [False] * self.num_envs

    def seed(self, seed=None):
        return [seed] * self.num_envs


def corridor_env(date: str, seed: int, starts: list[str], seconds: int, extra_cmd: str = ""):
    net = cut_net(CORRIDOR, "corridor")
    routes = corridor_routes(date, net.parent / f"routes-{date}.rou.xml")
    return make_env(net, routes, starts, seconds, corridor=True, single_agent=False, sumo_seed=seed,
                    rng_seed=seed, extra_cmd=extra_cmd)  # fmt: skip


def train(kind: str, seed: int, steps: int, n_envs: int = 8) -> Path:
    MODELS.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    if kind == "single":
        order = ["J03", "J04", "J05", "J06", "J07", "J08", "J05", "J07"]  # two extra busy junctions
        for jid in set(order):
            isolated_inputs(jid, TRAIN_DATE)  # build once, before the workers start
        venv = SubprocVecEnv([_single_env(order[k % len(order)], seed, k) for k in range(n_envs)])
    else:
        venv = AgentsVecEnv(corridor_env(TRAIN_DATE, 1000 * seed, TRAIN_STARTS, EPISODE_S))
    # queues run to hundreds of vehicles at the peak: scale rewards (not observations, which are
    # already 0-1) so the value function trains; the saved policy needs no normaliser to act
    venv = VecNormalize(VecMonitor(venv), norm_obs=False, norm_reward=True, gamma=PPO_KW["gamma"])
    model = PPO("MlpPolicy", venv, seed=seed, verbose=1, device="cpu", **PPO_KW)
    model.learn(total_timesteps=steps, progress_bar=False)
    out = MODELS / f"{kind}-seed{seed}.zip"
    model.save(out)
    venv.close()
    meta = {"kind": kind, "seed": seed, "steps": steps, "train_date": TRAIN_DATE, "episode_s": EPISODE_S,
            "wall_s": round(time.monotonic() - t0), "ppo": {k: v for k, v in PPO_KW.items() if k != "policy_kwargs"},
            "net_arch": PPO_KW["policy_kwargs"]["net_arch"]}  # fmt: skip
    (MODELS / f"{kind}-seed{seed}.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"[train] {kind} seed {seed}: {steps:,} steps in {meta['wall_s']} s -> {out}", flush=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["single", "corridor"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--steps", type=int, default=200_000)
    ap.add_argument("--envs", type=int, default=8)
    a = ap.parse_args()
    train(a.kind, a.seed, a.steps, a.envs)


if __name__ == "__main__":
    main()
