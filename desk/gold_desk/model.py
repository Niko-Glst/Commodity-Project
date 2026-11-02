"""GARCH(1,1) with Student-t shocks: fit on daily gold closes, simulate price paths.

Same specification as the paper's model (src/goldmodel/simulate.py on the paper
branches), with one fix: the simulation starts from the one-step-ahead variance,
so the latest day's shock counts. The paper starts from the variance *of* the
last day, which is set before that day's move. The simulation has no drift: the
model sizes moves, it does not call direction.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from arch import arch_model

H_MAX = 21                      # trading days ahead, about one month
HORIZONS = (1, 5, 10, 21)       # horizons the track record scores
FAN_Q = (1, 5, 25, 50, 75, 95, 99)
GRID_Q = np.arange(1, 100)      # percentile grid kept per scored horizon, for PIT values
N_PATHS = 20_000
SEED = 42
DAYS_PER_YEAR = 252


@dataclass
class Fit:
    mu: float
    omega: float
    alpha: float
    beta: float
    nu: float
    var_next: float             # daily variance for the next trading day (fraction squared)
    n_obs: int

    @property
    def persistence(self) -> float:
        return self.alpha + self.beta

    @property
    def half_life(self) -> float:
        if self.persistence >= 1:
            return float("inf")
        return float(np.log(0.5) / np.log(self.persistence))

    @property
    def vol_next(self) -> float:
        """Annualised volatility for the next day."""
        return float(np.sqrt(self.var_next * DAYS_PER_YEAR))

    @property
    def vol_long_run(self) -> float:
        if self.persistence >= 1:
            return float("nan")
        return float(np.sqrt(self.omega / (1 - self.persistence) * DAYS_PER_YEAR))


def fit(gold: pd.Series) -> Fit:
    """Fit on daily log returns (in percent, for numerical stability) and scale back."""
    returns = np.log(gold).diff().dropna() * 100.0
    result = arch_model(returns, vol="GARCH", p=1, q=1, dist="t", mean="Constant").fit(
        disp="off", show_warning=False
    )
    p = result.params
    var_next = float(result.forecast(horizon=1, reindex=False).variance.iloc[-1, 0]) / 1e4
    return Fit(
        mu=float(p["mu"]) / 100.0,
        omega=float(p["omega"]) / 1e4,
        alpha=float(p["alpha[1]"]),
        beta=float(p["beta[1]"]),
        nu=float(p["nu"]),
        var_next=var_next,
        n_obs=len(returns),
    )


def simulate(f: Fit, horizon: int = H_MAX, n_paths: int = N_PATHS, seed: int = SEED) -> np.ndarray:
    """Cumulative log returns, shape (n_paths, horizon + 1); column 0 is zero."""
    if f.nu <= 2:
        raise ValueError("Student-t shocks need more than 2 degrees of freedom.")
    rng = np.random.default_rng(seed)
    scale = np.sqrt(f.nu / (f.nu - 2))
    variance = np.full(n_paths, f.var_next)
    paths = np.zeros((n_paths, horizon + 1))
    for day in range(horizon):
        shock = np.sqrt(variance) * rng.standard_t(f.nu, n_paths) / scale
        paths[:, day + 1] = paths[:, day] + shock
        variance = f.omega + f.alpha * shock**2 + f.beta * variance
    return paths


@dataclass
class Forecast:
    origin: pd.Timestamp
    spot: float
    source: str                     # "live" (made on the day) or "backfill" (reconstructed)
    fit: Fit
    fan: dict[int, np.ndarray]      # FAN_Q percentile -> price for h = 1..H_MAX
    grid: dict[int, np.ndarray]     # HORIZONS h -> price at each GRID_Q percentile

    def to_record(self) -> dict:
        return {
            "origin": f"{self.origin:%Y-%m-%d}",
            "spot": round(self.spot, 2),
            "source": self.source,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "fit": asdict(self.fit),
            "fan": {str(q): np.round(v, 2).tolist() for q, v in self.fan.items()},
            "grid": {str(h): np.round(v, 2).tolist() for h, v in self.grid.items()},
        }

    @classmethod
    def from_record(cls, rec: dict) -> Forecast:
        return cls(
            origin=pd.Timestamp(rec["origin"]),
            spot=rec["spot"],
            source=rec["source"],
            fit=Fit(**rec["fit"]),
            fan={int(q): np.asarray(v) for q, v in rec["fan"].items()},
            grid={int(h): np.asarray(v) for h, v in rec["grid"].items()},
        )


def make_forecast(
    gold: pd.Series, source: str = "live", n_paths: int = N_PATHS, seed: int = SEED
) -> tuple[Forecast, np.ndarray]:
    """Forecast from the last close in `gold`; returns the forecast and the simulated paths."""
    f = fit(gold)
    paths = simulate(f, n_paths=n_paths, seed=seed)
    spot = float(gold.iloc[-1])
    prices = spot * np.exp(paths[:, 1:])
    fan = {q: np.percentile(prices, q, axis=0) for q in FAN_Q}
    grid = {h: np.percentile(prices[:, h - 1], GRID_Q) for h in HORIZONS}
    return Forecast(gold.index[-1], spot, source, f, fan, grid), paths


def touch_probabilities(f: Fit, spot: float, levels: list[float], horizon: int = H_MAX) -> dict:
    """Share of paths that trade through each level at some close within the horizon."""
    prices = spot * np.exp(simulate(f, horizon=horizon)[:, 1:])
    low, high = prices.min(axis=1), prices.max(axis=1)
    return {
        lvl: float((low <= lvl).mean() if lvl < spot else (high >= lvl).mean()) for lvl in levels
    }
