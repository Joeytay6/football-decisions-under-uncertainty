"""Shared settings and helpers for the portfolio analyses."""
import json, os
import numpy as np
import pandas as pd
from scipy.stats import chi2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "output")
os.makedirs(OUT, exist_ok=True)

MEN = {  # folder: display name (StatsBomb open data, all four leagues are complete seasons)
    "epl_2015_16": "Premier League",
    "laliga_2015_16": "La Liga",
    "seriea_2015_16": "Serie A",
    "ligue1_2015_16": "Ligue 1",
}
WOMEN = {"wsl_2023_24": "Women's Super League"}


def load(folder, table):
    return pd.read_csv(os.path.join(DATA, folder, f"{table}.csv"))


def load_many(folders, table):
    frames = []
    for f in folders:
        path = os.path.join(DATA, f, f"{table}.csv")
        if os.path.exists(path) and os.path.getsize(path) > 5:
            d = pd.read_csv(path)
            d["league"] = f
            frames.append(d)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def available(folders):
    return [f for f in folders if os.path.exists(os.path.join(DATA, f, "player_match.csv"))
            and os.path.getsize(os.path.join(DATA, f, "player_match.csv")) > 5]


def poisson_rate_ci(k, hours, per=1000):
    """Exact (Garwood) 95% interval for a Poisson rate per `per` hours."""
    lo = chi2.ppf(0.025, 2 * k) / 2 if k > 0 else 0.0
    hi = chi2.ppf(0.975, 2 * k + 2) / 2
    return k / hours * per, lo / hours * per, hi / hours * per


def rate_ratio_ci(k1, t1, k0, t0):
    """Rate ratio with a log-scale Wald 95% interval."""
    rr = (k1 / t1) / (k0 / t0)
    se = np.sqrt(1 / k1 + 1 / k0)
    return rr, rr * np.exp(-1.96 * se), rr * np.exp(1.96 * se)


def kaplan_meier(time, event):
    """Kaplan-Meier survivor function. Returns DataFrame(time, at_risk, events, surv)."""
    d = pd.DataFrame({"t": time, "e": event}).sort_values("t")
    rows, s = [], 1.0
    n = len(d)
    for t, g in d.groupby("t"):
        e = int(g["e"].sum())
        if e:
            s *= 1 - e / n
        rows.append((t, n, e, s))
        n -= len(g)
    return pd.DataFrame(rows, columns=["time", "at_risk", "events", "surv"])


def km_at(km, t):
    """Survivor probability just after time t (step function)."""
    s = km.loc[km["time"] <= t, "surv"]
    return float(s.iloc[-1]) if len(s) else 1.0


# ------------------------------------------------------------------ chart style
for f in font_manager.findSystemFonts():
    if "Inter" in os.path.basename(f):
        font_manager.fontManager.addfont(f)
plt.rcParams.update({
    "font.family": "Inter", "font.size": 8.5, "axes.titlesize": 9.5, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.labelsize": 8.3, "xtick.labelsize": 7.8, "ytick.labelsize": 7.8,
    "legend.fontsize": 7.5, "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#8a938e", "axes.linewidth": 0.6, "xtick.color": "#3a4440", "ytick.color": "#3a4440",
    "axes.labelcolor": "#1c2420", "text.color": "#1c2420", "savefig.dpi": 300, "figure.dpi": 100,
    "axes.grid": False, "legend.frameon": False,
})
# Categorical order (validated for colour-vision deficiency): green, purple, amber. Grey = context.
GREEN, PURPLE, AMBER = "#1e7a4c", "#5b4b9a", "#d3962e"
GREY, LIGHT, INK, MUTED, REF = "#9aa59f", "#d9dfdb", "#1c2420", "#5b6660", "#8b3a3a"
WIDTH = 7.0


def save(fig, name):
    fig.savefig(os.path.join(OUT, f"{name}.png"), bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


def write_numbers(name, obj):
    with open(os.path.join(OUT, f"{name}.json"), "w") as f:
        json.dump(obj, f, indent=1, default=lambda x: x.item() if hasattr(x, "item") else str(x))


def poisson_glm(y, X, offset=None, names=None):
    """Poisson regression with log link fitted by iteratively reweighted least squares.
    Returns dict name -> (coef, se, z, p). X should include a constant column."""
    from scipy.stats import norm
    y = np.asarray(y, float); X = np.asarray(X, float)
    off = np.zeros(len(y)) if offset is None else np.asarray(offset, float)
    beta = np.zeros(X.shape[1]); beta[0] = np.log(max(y.mean(), 1e-9)) - off.mean()
    for _ in range(100):
        eta = X @ beta + off
        mu = np.exp(eta)
        z = eta - off + (y - mu) / mu
        W = mu
        XtW = X.T * W
        new = np.linalg.solve(XtW @ X, XtW @ z)
        if np.max(np.abs(new - beta)) < 1e-10:
            beta = new
            break
        beta = new
    mu = np.exp(X @ beta + off)
    cov = np.linalg.inv((X.T * mu) @ X)
    se = np.sqrt(np.diag(cov))
    zval = beta / se
    p = 2 * norm.sf(np.abs(zval))
    names = names or [f"x{i}" for i in range(X.shape[1])]
    return {n: dict(coef=float(b), se=float(s), rr=float(np.exp(b)), lo=float(np.exp(b - 1.96 * s)),
                    hi=float(np.exp(b + 1.96 * s)), p=float(pv)) for n, b, s, pv in zip(names, beta, se, p)}
