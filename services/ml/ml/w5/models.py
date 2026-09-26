"""Forecasting models for 15-min movement counts (one step = 15 minutes ahead).

All models see only information available BEFORE the slot they predict.
Baselines   seasonal naive (same slot the day before), weekly naive (same slot a week before, SIM),
            weekday profile (mean of the same weekday and slot in the training weeks, SIM),
            level-adjusted profile (yesterday's slot x the ratio of the last hour today vs yesterday).
LightGBM    gradient boosting on lags, same-slot-yesterday/last-week, time of day, weekday, movement.
GWN-lite    a simplified Graph WaveNet-style network: dilated causal convolutions over time plus a
            graph convolution over the corridor's movements (fixed junction adjacency + a learned one).
Conformal   split conformal: the 90% quantile of absolute errors on a calibration week gives a band
            that should cover ~90% of the test week.
"""

import math

import numpy as np

SLOTS = 96


def metrics(y: np.ndarray, p: np.ndarray) -> dict:
    """MAE, RMSE (vehicles per 15 min) and WAPE (sum |error| / sum actual)."""
    e = p - y
    return {
        "mae": float(np.mean(np.abs(e))),
        "rmse": float(math.sqrt(np.mean(e**2))),
        "wape": float(np.abs(e).sum() / max(1.0, y.sum())),
    }


def conformal_q(abs_residuals: np.ndarray, coverage: float = 0.9) -> float:
    """Finite-sample split-conformal quantile of absolute residuals."""
    n = abs_residuals.size
    k = min(n, math.ceil((n + 1) * coverage))
    return float(np.sort(abs_residuals)[k - 1])


def level_adjusted(prev_day: np.ndarray, series: np.ndarray, i: int, window: int = 4) -> float:
    """Yesterday's value for slot i, scaled by how busy the last `window` slots were vs yesterday."""
    if i < SLOTS + window:
        return float(prev_day[i - SLOTS]) if i >= SLOTS else float(series[i])
    now, then = series[i - window : i].sum(), series[i - SLOTS - window : i - SLOTS].sum()
    ratio = np.clip(now / then, 0.5, 2.0) if then > 0 else 1.0
    return float(series[i - SLOTS] * ratio)


# ---------------------------------------------------------------- LightGBM features

FEATURES = [
    "slot_sin",
    "slot_cos",
    "dow",
    "lag1",
    "lag2",
    "lag3",
    "lag4",
    "mean4",
    "day_ago",
    "day_ago_next",
    "week_ago",
    "movement",
    "junction",
]


def feature_rows(series: np.ndarray, rows_idx: range, movement: int, junction: int, day0_dow: int = 0,
                 week: bool = True) -> np.ndarray:  # fmt: skip
    """Feature matrix for predicting series[i] for every i in rows_idx (uses only series[:i])."""
    out = []
    for i in rows_idx:
        s, d = i % SLOTS, i // SLOTS
        a = 2 * math.pi * s / SLOTS
        lags = [series[i - k] for k in range(1, 5)]
        day = series[i - SLOTS] if i >= SLOTS else np.nan
        day_next = series[i - SLOTS + 1] if i >= SLOTS else np.nan
        wk = series[i - 7 * SLOTS] if week and i >= 7 * SLOTS else np.nan
        out.append(
            [
                math.sin(a),
                math.cos(a),
                (day0_dow + d) % 7,
                *lags,
                float(np.mean(lags)),
                day,
                day_next,
                wk,
                movement,
                junction,
            ]
        )
    return np.array(out, dtype=float)


def lightgbm(
    x: np.ndarray,
    y: np.ndarray,
    x_val: np.ndarray | None = None,
    y_val: np.ndarray | None = None,
    seed: int = 0,
):
    import lightgbm as lgb

    model = lgb.LGBMRegressor(objective="poisson", n_estimators=600, learning_rate=0.04, num_leaves=31, min_child_samples=30,
                              subsample=0.8, subsample_freq=1, colsample_bytree=0.9, random_state=seed, verbose=-1)  # fmt: skip
    cats = [FEATURES.index("movement"), FEATURES.index("junction")]
    fit_kw = {"categorical_feature": cats}
    if x_val is not None:
        fit_kw |= {"eval_set": [(x_val, y_val)], "callbacks": [lgb.early_stopping(50, verbose=False)]}
    return model.fit(x, y, **fit_kw)


def shap_importance(model, x: np.ndarray) -> list[dict]:
    """Mean |SHAP value| per feature (LightGBM's exact TreeSHAP via pred_contrib)."""
    contrib = model.predict(x, pred_contrib=True)[:, :-1]
    imp = np.abs(contrib).mean(axis=0)
    order = np.argsort(-imp)
    return [{"feature": FEATURES[i], "meanAbsShap": round(float(imp[i]), 4)} for i in order]


# ---------------------------------------------------------------- GWN-lite (torch)


def gwn_lite(counts: np.ndarray, adjacency: np.ndarray, train_end: int, val_end: int, window: int = 16,
             epochs: int = 12, seed: int = 0) -> tuple[np.ndarray, dict]:  # fmt: skip
    """Train on steps [window, train_end), early-stop on [train_end, val_end), predict every step
    from val_end to the end. Returns (predictions for steps val_end.., training info)."""
    import torch
    from torch import nn

    torch.manual_seed(seed)
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    n, t = counts.shape
    scale = counts[:, :train_end].mean(axis=1, keepdims=True) + 1.0
    z = torch.tensor(counts / scale, dtype=torch.float32)
    a = torch.tensor(adjacency / adjacency.sum(axis=1, keepdims=True), dtype=torch.float32, device=dev)
    slot = torch.arange(t) % SLOTS
    dow = (torch.arange(t) // SLOTS) % 7
    time_feat = torch.stack([torch.sin(2 * math.pi * slot / SLOTS), torch.cos(2 * math.pi * slot / SLOTS),
                             torch.sin(2 * math.pi * dow / 7), torch.cos(2 * math.pi * dow / 7)])  # fmt: skip

    class Net(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            c = 32
            self.inp = nn.Conv1d(1 + 4, c, 1)
            self.filt = nn.ModuleList([nn.Conv1d(c, c, 2, dilation=d) for d in (1, 2, 4, 8)])
            self.gate = nn.ModuleList([nn.Conv1d(c, c, 2, dilation=d) for d in (1, 2, 4, 8)])
            self.e1 = nn.Parameter(torch.randn(n, 8) * 0.1)
            self.e2 = nn.Parameter(torch.randn(8, n) * 0.1)
            self.mix = nn.Linear(2 * c, c)
            self.out = nn.Sequential(nn.ReLU(), nn.Linear(c + 4, 32), nn.ReLU(), nn.Linear(32, 1))

        def forward(self, x: torch.Tensor, tf: torch.Tensor, tf_next: torch.Tensor) -> torch.Tensor:
            # x: (batch, n, window); tf: (batch, 4, window); tf_next: (batch, 4) for the target step
            b = x.shape[0]
            h = torch.cat([x.unsqueeze(2), tf.unsqueeze(1).expand(b, n, 4, x.shape[-1])], dim=2).reshape(
                b * n, 5, -1
            )
            h = self.inp(h)
            for f, g in zip(self.filt, self.gate, strict=True):
                h = torch.tanh(f(h)) * torch.sigmoid(g(h))
            h = h[..., -1].reshape(b, n, -1)  # last time step's features per movement
            adaptive = torch.softmax(torch.relu(self.e1 @ self.e2), dim=1)
            g = torch.cat(
                [torch.einsum("ij,bjc->bic", a, h), torch.einsum("ij,bjc->bic", adaptive, h)], dim=-1
            )
            h = h + self.mix(g)
            return self.out(torch.cat([h, tf_next.unsqueeze(1).expand(b, n, 4)], dim=-1)).squeeze(-1)

    def batch(idx: list[int]):
        x = torch.stack([z[:, i - window : i] for i in idx])
        tf = torch.stack([time_feat[:, i - window : i] for i in idx])
        return x.to(dev), tf.to(dev), time_feat[:, idx].T.to(dev), torch.stack([z[:, i] for i in idx]).to(dev)

    net = Net().to(dev)
    opt = torch.optim.Adam(net.parameters(), lr=2e-3)
    train_idx = list(range(window, train_end))
    val_idx = list(range(train_end, val_end))
    rng = np.random.default_rng(seed)
    best, best_state, losses = math.inf, None, []
    for _ in range(epochs):
        net.train()
        rng.shuffle(train_idx)
        for k in range(0, len(train_idx), 64):
            x, tf, tn, y = batch(train_idx[k : k + 64])
            loss = nn.functional.mse_loss(net(x, tf, tn), y)
            opt.zero_grad()
            loss.backward()
            opt.step()
        net.eval()
        with torch.no_grad():
            vl = float(np.mean([nn.functional.mse_loss(net(*batch(val_idx[k : k + 256])[:3]), batch(val_idx[k : k + 256])[3]).item()
                                for k in range(0, len(val_idx), 256)]))  # fmt: skip
        losses.append(vl)
        if vl < best:
            best, best_state = vl, {k: v.detach().clone() for k, v in net.state_dict().items()}
    net.load_state_dict(best_state)
    net.eval()
    preds = []
    with torch.no_grad():
        idx = list(range(val_end, t))
        for k in range(0, len(idx), 256):
            x, tf, tn, _ = batch(idx[k : k + 256])
            preds.append(net(x, tf, tn).cpu().numpy())
    pred = np.concatenate(preds, axis=0).T * scale  # (n, steps)
    params = sum(p.numel() for p in net.parameters())
    return np.clip(pred, 0, None), {
        "device": dev,
        "epochs": epochs,
        "valLoss": [round(v, 4) for v in losses],
        "parameters": params,
    }
