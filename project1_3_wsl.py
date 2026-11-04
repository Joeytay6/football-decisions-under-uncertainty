"""Projects 1-3 (women's game): signing appraisal and outcomes-based deal, finishing skill or luck,
measurement science (reliability, critical differences and a league-wide watch-list).

Data: StatsBomb (Hudl) open data, FA Women's Super League 2023/24 (competition 37, season 281),
tables from build_tables_clock.py, which counts minutes on the match clock as when these projects were first built.
Run: python project1_3_wsl.py            ->  output/wsl.json and charts c1-c7 in output/
     python project1_3_wsl.py elapsed    ->  output/wsl_elapsed.json: the same analyses on the elapsed-time
                                             tables from build_tables.py (sensitivity check; no charts)

Inputs that are not data (fee, wages, value of a league point, injury and recovery rates, minutes share, resale)
are illustrative and labelled as such in the portfolio.
"""
import json, os
from itertools import combinations_with_replacement
import numpy as np
import pandas as pd
from scipy.special import gammaln
from scipy.stats import norm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

import sys
HERE = os.path.dirname(os.path.abspath(__file__))
SENSITIVITY = len(sys.argv) > 1 and sys.argv[1] == "elapsed"
DATA = os.path.join(HERE, "data", "wsl_2023_24" if SENSITIVITY else "wsl_2023_24_clock")
OUT = os.path.join(HERE, "output")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- style
for f in font_manager.findSystemFonts():
    if "Inter" in os.path.basename(f):
        font_manager.fontManager.addfont(f)
plt.rcParams.update({
    "font.family": "Inter", "font.size": 8.5, "axes.titlesize": 9.5, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.labelsize": 8.5, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "legend.fontsize": 7.5, "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#5b6660", "axes.linewidth": 0.7, "xtick.color": "#3a4440", "ytick.color": "#3a4440",
    "axes.labelcolor": "#1c2420", "text.color": "#1c2420", "savefig.dpi": 300, "figure.dpi": 100,
})
GREEN, SAGE, RED, INK, GOLD = "#1e7a4c", "#9db0a3", "#8b3a3a", "#1c2420", "#c9a227"
CREDIT = "Data: StatsBomb (Hudl), FA WSL 2023/24"


def credit(ax, y=-0.02):
    pass


def save(fig, name):
    if not SENSITIVITY:
        fig.savefig(f"{OUT}/{name}.png", bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


# ---------------------------------------------------------------- data
player_match = pd.read_csv(f"{DATA}/player_match.csv")
shots = pd.read_csv(f"{DATA}/shots.csv")
matches = pd.read_csv(f"{DATA}/matches.csv")


def short_team(name):
    for suffix in (" WFC", " FCW", " LFC", " Women", " W"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


most_common = lambda s: s.mode().iat[0]
players = (player_match.groupby(["player_id", "player"])
           .agg(team=("team", most_common), position_group=("position_group", most_common),
                matches=("match_id", "nunique"), minutes=("minutes", "sum"))
           .reset_index())
N = {}

# ================================================================ 1. Signing appraisal (as notebook 2)
POSITION = "FWD"
ASKING_FEE = 100_000
EXTRA_WAGES_PER_SEASON = 30_000
SEASONS, MATCHES_PER_SEASON = 2, 22
VALUE_PER_POINT = 60_000
COMPARATOR_PERCENTILE = 25
DISCOUNT_RATE = 0.035
SHORT_INJURY, LONG_INJURY = (4, 96), (1, 199)
SHORT_RECOVERY, LONG_RECOVERY = (10, 10), (5, 70)
RESALE_SHARE, MINUTES_SHARE = (3, 7), (17, 3)
N_SIMS, SEED = 10_000, 2026


# What a goal is worth: OLS of league points on goal difference across the 2023/24 table (all 132 results).
def league_table(m):
    rows = []
    for _, r in m.iterrows():
        for team, gf, ga in ((r["home"], r["home_score"], r["away_score"]), (r["away"], r["away_score"], r["home_score"])):
            rows.append(dict(team=team, gd=gf - ga, pts=3 * (gf > ga) + (gf == ga)))
    return pd.DataFrame(rows).groupby("team")[["gd", "pts"]].sum()


table = league_table(matches)
X_ = np.column_stack([np.ones(len(table)), table["gd"]])
coef_, *_ = np.linalg.lstsq(X_, table["pts"].to_numpy(), rcond=None)
resid_ = table["pts"].to_numpy() - X_ @ coef_
se_ = np.sqrt(resid_ @ resid_ / (len(table) - 2) * np.linalg.inv(X_.T @ X_)[1, 1])
r2_ = 1 - resid_ @ resid_ / ((table["pts"] - table["pts"].mean()) ** 2).sum()
# The model uses the slope and its standard error to two and three decimals (0.52, 0.028)
POINTS_PER_GOAL, POINTS_PER_GOAL_SE = round(float(coef_[1]), 2), round(float(se_), 3)
TOP_FOUR = ["Chelsea FCW", "Manchester City WFC", "Arsenal WFC", "Liverpool WFC"]
beta_mean = lambda ab: ab[0] / (ab[0] + ab[1])

pm = player_match.copy()
pm["output"] = pm["npxg"] + pm["xa"]


def per90_and_se(g):
    m, c = g["minutes"].to_numpy(), g["output"].to_numpy()
    rate, n = c.sum() / m.sum(), len(g)
    var = n / (n - 1) * ((c - rate * m) ** 2).sum() / m.sum() ** 2 if n > 1 else np.nan
    return pd.Series({"per90": 90 * rate, "se": 90 * np.sqrt(var)})


season = players.merge(pm.groupby("player_id")[["minutes", "output"]].apply(per90_and_se).reset_index(), on="player_id")
regulars = season[(season["minutes"] >= 900) & (season["position_group"] == POSITION)].copy()
y, v = regulars["per90"].to_numpy(), regulars["se"].to_numpy() ** 2
w = 1 / v
k = len(y)
Q = (w * (y - (w * y).sum() / w.sum()) ** 2).sum()
tau2 = max(0.0, (Q - (k - 1)) / (w.sum() - (w ** 2).sum() / w.sum()))
w_re = 1 / (v + tau2)
mu, var_mu = (w_re * y).sum() / w_re.sum(), 1 / w_re.sum()


def true_level(per90, se):
    b = tau2 / (tau2 + se ** 2)
    return mu + b * (per90 - mu), np.sqrt(b * se ** 2 + (1 - b) ** 2 * var_mu)


regulars["true_level"], regulars["true_level_sd"] = true_level(regulars["per90"], regulars["se"])
COMPARATOR_LEVEL = np.percentile(regulars["true_level"], COMPARATOR_PERCENTILE)
outside = regulars[~regulars["team"].isin(TOP_FOUR)]
target = outside.loc[outside["true_level"].idxmax()].copy()
N_MATCHES = SEASONS * MATCHES_PER_SEASON


def fitness_trace(p):
    s_inj, l_inj = np.asarray(p["short_injury"], float), np.asarray(p["long_injury"], float)
    s_rec, l_rec = np.asarray(p["short_recovery"], float), np.asarray(p["long_recovery"], float)
    fit, short, long_ = np.ones(len(s_inj)), np.zeros(len(s_inj)), np.zeros(len(s_inj))
    trace = np.empty((len(s_inj), N_MATCHES, 3))
    for t in range(N_MATCHES):
        trace[:, t] = np.column_stack([fit, short, long_])
        fit, short, long_ = (fit * (1 - s_inj - l_inj) + short * s_rec + long_ * l_rec,
                             fit * s_inj + short * (1 - s_rec), fit * l_inj + long_ * (1 - l_rec))
    return trace


season_of_match = np.arange(N_MATCHES) // MATCHES_PER_SEASON
DISCOUNT = 1 / (1 + DISCOUNT_RATE) ** season_of_match
WAGE_COST = sum(EXTRA_WAGES_PER_SEASON / (1 + DISCOUNT_RATE) ** s for s in range(SEASONS))
RESALE_DISCOUNT = 1 / (1 + DISCOUNT_RATE) ** SEASONS

rng = np.random.default_rng(SEED)
draws = pd.DataFrame({
    "level": np.maximum(rng.normal(target["true_level"], target["true_level_sd"], N_SIMS), 0),
    "short_injury": rng.beta(*SHORT_INJURY, N_SIMS), "long_injury": rng.beta(*LONG_INJURY, N_SIMS),
    "short_recovery": rng.beta(*SHORT_RECOVERY, N_SIMS), "long_recovery": rng.beta(*LONG_RECOVERY, N_SIMS),
    "minutes_share": rng.beta(*MINUTES_SHARE, N_SIMS),
    "points_per_goal": rng.normal(POINTS_PER_GOAL, POINTS_PER_GOAL_SE, N_SIMS),
    "resale_share": rng.beta(*RESALE_SHARE, N_SIMS),
})
fit = fitness_trace(draws)[:, :, 0]
level = draws["level"].to_numpy()
share = draws["minutes_share"].to_numpy()
points = ((level - COMPARATOR_LEVEL)[:, None] * share[:, None] * fit
          * draws["points_per_goal"].to_numpy()[:, None] * DISCOUNT).sum(axis=1)
fee_factor = 1 - draws["resale_share"].to_numpy() * RESALE_DISCOUNT
cost = ASKING_FEE * fee_factor + WAGE_COST
nmb = VALUE_PER_POINT * points - cost
fees = np.arange(0, 400_001, 2_500)
nmb_by_fee = (VALUE_PER_POINT * points - WAGE_COST)[:, None] - fees[None, :] * fee_factor[:, None]
p_by_fee = (nmb_by_fee > 0).mean(axis=0)
walk_away = (VALUE_PER_POINT * points.mean() - WAGE_COST) / fee_factor.mean()
fee_80 = fees[p_by_fee >= 0.8].max() if (p_by_fee >= 0.8).any() else None


def evppi(net_benefit, inputs, degree=3):
    x = (inputs - inputs.mean(axis=0)) / inputs.std(axis=0)
    cols = [np.ones(len(net_benefit))]
    for d in range(1, degree + 1):
        for combo in combinations_with_replacement(range(x.shape[1]), d):
            cols.append(x[:, list(combo)].prod(axis=1))
    X = np.column_stack(cols)
    fitted = X @ np.linalg.lstsq(X, net_benefit, rcond=None)[0]
    return np.maximum(fitted, 0).mean() - max(fitted.mean(), 0)


evpi = np.maximum(nmb, 0).mean() - max(nmb.mean(), 0)
GROUPS = {
    "Her true level\n(scouting, more data)": ["level"],
    "Resale value\n(market)": ["resale_share"],
    "Share of matches she plays\n(manager's plans)": ["minutes_share"],
    "Points per goal\n(league model)": ["points_per_goal"],
    "Injury risk and recovery\n(medical)": ["short_injury", "long_injury", "short_recovery", "long_recovery"],
}
voi = pd.Series({n_: evppi(nmb, draws[c].to_numpy()) for n_, c in GROUPS.items()})

N["league_model"] = dict(slope=float(coef_[1]), se=float(se_), r2=float(r2_), teams=int(len(table)),
                         results=int(len(matches)), used_slope=POINTS_PER_GOAL, used_se=POINTS_PER_GOAL_SE)
N["signing_extra"] = dict(fit_share=float(fitness_trace(pd.DataFrame([{"short_injury": beta_mean(SHORT_INJURY), "long_injury": beta_mean(LONG_INJURY), "short_recovery": beta_mean(SHORT_RECOVERY), "long_recovery": beta_mean(LONG_RECOVERY)}]))[0, :, 0].mean()),
    mu_fwd=float(mu), tau=float(np.sqrt(tau2)), i2=float(max(0.0, (Q - (k - 1)) / Q)), target_team=short_team(target["team"]), target_minutes=float(target["minutes"]),
    nmb_mean=float(nmb.mean()))
N["signing"] = dict(
    target_raw_per90=float(target["per90"]), target_true=float(target["true_level"]),
    target_true_sd=float(target["true_level_sd"]), comparator=float(COMPARATOR_LEVEL), n_regular_fwd=int(k),
    points_mean=float(points.mean()), points_p5=float(np.percentile(points, 5)), points_p95=float(np.percentile(points, 95)),
    p_worth=float((nmb > 0).mean()), walk_away=float(walk_away), p_free=float(p_by_fee[0]), evpi=float(evpi),
    voi={k_.replace("\n", " "): float(v_) for k_, v_ in voi.items()},
)

# ---------------------------------------------------------------- 1b. Bridging the price gap: an outcomes-based deal
# Expected goal contributions (npxG + xA) she produces for us over the contract, and actual goals + assists (Poisson)
contrib = (level[:, None] * share[:, None] * fit).sum(axis=1)
r_deal = np.random.default_rng(11)
actual_ga = r_deal.poisson(contrib)
base_fit = fitness_trace(pd.DataFrame([{"short_injury": beta_mean(SHORT_INJURY), "long_injury": beta_mean(LONG_INJURY),
                                        "short_recovery": beta_mean(SHORT_RECOVERY), "long_recovery": beta_mean(LONG_RECOVERY)}]))[0, :, 0]
pace_seller = float(target["per90"] * beta_mean(MINUTES_SHARE) * base_fit.sum())   # if she repeats last season
HURDLE = int(np.floor(pace_seller))
hit = actual_ga >= HURDLE
p_hit = float(hit.mean())
p_hit_seller = float((r_deal.poisson(pace_seller, 200_000) >= HURDLE).mean())
# Seller gets the asking fee if she reaches the hurdle; we pay our walk-away price on average
bonus = (ASKING_FEE - walk_away) / (1 - p_hit)
upfront = ASKING_FEE - bonus
paid_deal = upfront + bonus * hit
nmb_deal = VALUE_PER_POINT * points - (paid_deal * fee_factor + WAGE_COST)
nmb_walk = VALUE_PER_POINT * points - (walk_away * fee_factor + WAGE_COST)


def profile(x):
    return dict(mean=float(x.mean()), p_worth=float((x > 0).mean()), p_big_loss=float((x < -50_000).mean()),
                p5=float(np.percentile(x, 5)), p25=float(np.percentile(x, 25)), p75=float(np.percentile(x, 75)),
                p95=float(np.percentile(x, 95)))


N["deal"] = dict(upfront=float(upfront), bonus=float(bonus), hurdle=HURDLE, pace_seller=pace_seller,
                 contrib_mean=float(contrib.mean()), p_hit_ours=p_hit, p_hit_if_repeat=p_hit_seller,
                 paid_mean=float(paid_deal.mean()), worth_if_hit=float((nmb_deal[hit] > 0).mean()),
                 worth_if_miss=float((nmb_deal[~hit] > 0).mean()), points_if_hit=float(points[hit].mean()),
                 points_if_miss=float(points[~hit].mean()),
                 fixed_ask=profile(nmb), fixed_walk=profile(nmb_walk), outcomes=profile(nmb_deal))

# ================================================================ 2. Skill or luck (as notebook 1)
per_player = (shots.groupby(["player_id", "player"])
              .agg(team=("team", most_common), shots=("xg", "size"), goals=("goal", "sum"), xg=("xg", "sum"))
              .reset_index())
per_player["raw_ratio"] = per_player["goals"] / per_player["xg"]
league_ratio = per_player["goals"].sum() / per_player["xg"].sum()
G, X = per_player["goals"].to_numpy(), np.maximum(per_player["xg"].to_numpy(), 1e-6)
means, spreads = np.linspace(0.7, 1.5, 81), np.linspace(0.005, 0.6, 120)
M, S = np.meshgrid(means, spreads, indexing="ij")
A, B = (M / S) ** 2, M / S ** 2
log_lik = np.zeros(M.shape)
for g, x in zip(G, X):
    log_lik += gammaln(A + g) - gammaln(A) - gammaln(g + 1) + A * np.log(B / (B + x)) + g * np.log(x / (B + x))
log_post = log_lik + norm.logpdf(M, 1.0, 0.25) + norm.logpdf(S, 0, 0.2)
wts = np.exp(log_post - log_post.max()); wts /= wts.sum()


def summarise(values, w_):
    o = np.argsort(values); cdf = np.cumsum(w_[o])
    return [values[o][np.searchsorted(cdf, q)] for q in (0.5, 0.05, 0.95)]


spread_mid, spread_lo, spread_hi = summarise(S.ravel(), wts.ravel())
mean_mid = summarise(M.ravel(), wts.ravel())[0]
r2 = np.random.default_rng(2026)
dr = r2.choice(wts.size, size=4000, p=wts.ravel())
a_d, b_d, m_d = A.ravel()[dr], B.ravel()[dr], M.ravel()[dr]
theta = r2.gamma(a_d[None, :] + G[:, None], 1 / (b_d[None, :] + X[:, None]))
per_player["skill"] = theta.mean(axis=1)
per_player["skill_lo"] = np.percentile(theta, 5, axis=1)
per_player["skill_hi"] = np.percentile(theta, 95, axis=1)
per_player["p_above"] = (theta > m_d[None, :]).mean(axis=1)
reg15 = per_player[per_player["shots"] >= 15]
shaw = per_player[per_player["player"].str.contains("Shaw")].iloc[0]
N["finishing"] = dict(league_ratio=float(league_ratio), spread=float(spread_mid), spread_lo=float(spread_lo),
                      spread_hi=float(spread_hi), mean=float(mean_mid), n15=int(len(reg15)),
                      n_confident=int((reg15["p_above"] >= 0.9).sum()),
                      shaw=dict(goals=int(shaw["goals"]), xg=float(shaw["xg"]), skill=float(shaw["skill"]),
                                lo=float(shaw["skill_lo"]), hi=float(shaw["skill_hi"]), p_above=float(shaw["p_above"])))

# ================================================================ 3. Measurement science: reliability and critical differences
pm60 = player_match.merge(players[["player_id", "position_group"]].rename(columns={"position_group": "pos"}), on="player_id")
pm60 = pm60[(pm60["minutes"] >= 60) & (pm60["pos"] != "GK")].copy()
pm60["npxg_xa"] = pm60["npxg"] + pm60["xa"]
pm60["g_minus_xg"] = pm60["goals"] - pm60["npxg"]
counts = pm60.groupby("player_id").size()
pm60 = pm60[pm60["player_id"].isin(counts[counts >= 10].index)]

MEASURES = {  # column: (label, positions)
    "passes": ("Passes", ["DEF", "MID", "FWD"]),
    "pressures": ("Pressures", ["DEF", "MID", "FWD"]),
    "ball_recoveries": ("Ball recoveries", ["DEF", "MID", "FWD"]),
    "shots": ("Shots (forwards)", ["FWD"]),
    "npxg_xa": ("npxG + xA (forwards)", ["FWD"]),
    "goals": ("Goals (forwards)", ["FWD"]),
    "g_minus_xg": ("Goals minus xG: finishing (forwards)", ["FWD"]),
}

# Split-half reliability: each player's matches split at random into two halves, per-90 rate in each,
# centred on the position mean; correlation across players, averaged over 300 random splits; Spearman-Brown to a full season.
r3 = np.random.default_rng(7)
rel_rows = []
for col, (label, positions) in MEASURES.items():
    d = pm60[pm60["pos"].isin(positions)]
    groups = [(pid, g_[[col, "minutes"]].to_numpy(), g_["pos"].iat[0]) for pid, g_ in d.groupby("player_id")]
    rs = []
    for _ in range(300):
        a_rates, b_rates, poss = [], [], []
        for pid, arr, pos in groups:
            idx = r3.permutation(len(arr)); h = len(arr) // 2
            A_, B_ = arr[idx[:h]], arr[idx[h:2 * h]]
            a_rates.append(90 * A_[:, 0].sum() / A_[:, 1].sum()); b_rates.append(90 * B_[:, 0].sum() / B_[:, 1].sum()); poss.append(pos)
        df_ = pd.DataFrame({"a": a_rates, "b": b_rates, "pos": poss})
        for c in ("a", "b"):
            df_[c] = df_[c] - df_.groupby("pos")[c].transform("mean")
        rs.append(np.corrcoef(df_["a"], df_["b"])[0, 1])
    r = float(np.clip(np.mean(rs), 1e-3, 0.999))
    half_matches = float(np.median([len(arr) // 2 for _, arr, _ in groups]))
    full = 2 * r / (1 + r)
    needed = half_matches * (0.7 / 0.3) / (r / (1 - r))
    rel_rows.append(dict(metric=label, col=col, players=len(groups), r_half=r, half_matches=half_matches,
                         season_reliability=full, matches_for_07=needed))
rel = pd.DataFrame(rel_rows)

# Critical differences (reference change values), as notebook 3
CD_METRICS = {"passes": "Passes", "pressures": "Pressures", "ball_recoveries": "Ball recoveries",
              "shots": "Forwards' shots", "npxg_xa": "Forwards' npxG + xA"}
cd_rows = []
for col, label in CD_METRICS.items():
    positions = MEASURES[col][1]
    d = pm60[pm60["pos"].isin(positions)].copy()
    d["p90"] = d[col] / d["minutes"] * 90
    bp = d.groupby("player_id")["p90"].agg(["mean", "std"])
    bp = bp[bp["mean"] > 0]
    cv = np.sqrt(((bp["std"] / bp["mean"]) ** 2).mean())
    cd_rows.append(dict(metric=label, cv=cv, one=1.96 * np.sqrt(2) * cv, five=1.96 * cv * np.sqrt(1 / 5 + 1 / 15)))
cd = pd.DataFrame(cd_rows)
N["reliability"] = rel.drop(columns="col").to_dict(orient="records")
N["critical"] = cd.to_dict(orient="records")

# League-wide watch-list: each regular's last 5 matches of the season against all her earlier ones, every metric;
# Benjamini-Hochberg false discovery rate control at 10%.
WINDOW, FDR = 5, 0.10
kick = matches["kick_off"].fillna("00:00:00") if "kick_off" in matches else "00:00:00"
matches["kick_off_ts"] = pd.to_datetime(matches["date"] + " " + kick)
pmw = pm60.merge(matches[["match_id", "kick_off_ts"]], on="match_id")
CVS = dict(zip(CD_METRICS, cd["cv"]))
watch_rows = []
for pid, own in pmw.groupby("player_id"):
    own = own.sort_values("kick_off_ts")
    recent, earlier = own.tail(WINDOW), own.iloc[:-WINDOW]
    for col in CD_METRICS:
        if own["pos"].iat[0] not in MEASURES[col][1]:
            continue
        before = (earlier[col] / earlier["minutes"] * 90).mean()
        after = (recent[col] / recent["minutes"] * 90).mean()
        if before <= 0:
            continue
        se_w = CVS[col] * np.sqrt(1 / WINDOW + 1 / len(earlier))
        watch_rows.append(dict(player_id=pid, metric=col, change=after / before - 1, z=(after / before - 1) / se_w))
watch = pd.DataFrame(watch_rows)
watch["p"] = 2 * norm.sf(watch["z"].abs())
m_ = len(watch)
p_sorted = np.sort(watch["p"].to_numpy())
passing = np.nonzero(p_sorted <= FDR * np.arange(1, m_ + 1) / m_)[0]
cutoff = p_sorted[passing.max()] if len(passing) else -1.0
N["critical_watch"] = dict(comparisons=int(m_), players=int(watch["player_id"].nunique()),
                           beyond_95=int((watch["p"] < 0.05).sum()), by_chance=int(round(0.05 * m_)),
                           survive_fdr=int((watch["p"] <= cutoff).sum()), fdr=FDR)

# ================================================================ charts
# C1: how much to bid
fig, ax = plt.subplots(figsize=(7.0, 2.7))
ax.plot(fees / 1000, 100 * p_by_fee, color=GREEN, lw=2)
ax.axvline(walk_away / 1000, color=RED, ls="--", lw=1)
ax.axvline(ASKING_FEE / 1000, color=INK, ls=":", lw=1)
ax.annotate(f"Walk-away price\n£{walk_away / 1000:.0f}k", (walk_away / 1000, 78), xytext=(-6, 0), textcoords="offset points",
            ha="right", va="center", fontsize=7.5, color=RED)
ax.annotate(f"Asking fee £{ASKING_FEE / 1000:.0f}k:\n{100 * (nmb > 0).mean():.0f}% chance it pays off",
            (ASKING_FEE / 1000, 100 * (nmb > 0).mean()), xytext=(14, 18), textcoords="offset points", fontsize=7.5,
            arrowprops=dict(arrowstyle="-", color="#7a8580", lw=0.6))
ax.set_xlim(0, 300); ax.set_ylim(0, 100)
ax.set_xlabel("Transfer fee (£ thousands)"); ax.set_ylabel("Chance the signing pays off (%)")
ax.set_title("How much to bid: the chance the signing pays off at every fee")
credit(ax)
save(fig, "c1_bid")

# C2: value of information
fig, ax = plt.subplots(figsize=(7.0, 2.25))
vv = voi.sort_values()
ax.barh(range(len(vv)), vv / 1000, color=[GREEN if i == len(vv) - 1 else SAGE for i in range(len(vv))], height=0.62)
ax.set_yticks(range(len(vv))); ax.set_yticklabels(vv.index, fontsize=7.5)
for i, val in enumerate(vv):
    ax.text(val / 1000 + 0.3, i, f"£{val / 1000:.1f}k", va="center", fontsize=7.5)
ax.set_xlabel("Most it's worth paying to remove this uncertainty before bidding (£ thousands)")
ax.set_title(f"Value of information: where scouting money pays (all uncertainty: £{evpi / 1000:.1f}k)")
ax.set_xlim(0, max(vv) / 1000 * 1.15)
credit(ax)
save(fig, "c2_voi")

# C3: three ways to pay — risk profile of net benefit
fig, ax = plt.subplots(figsize=(7.0, 2.35))
rows3 = [("Fixed fee at the seller's price (£100k)", N["deal"]["fixed_ask"], SAGE),
         (f"Fixed fee at our walk-away price (£{walk_away / 1000:.0f}k)", N["deal"]["fixed_walk"], SAGE),
         (f"£{upfront / 1000:.0f}k + £{bonus / 1000:.0f}k if she reaches {HURDLE} goals + assists", N["deal"]["outcomes"], GREEN)]
for i, (lab, p_, col_) in enumerate(rows3[::-1]):
    ax.plot([p_["p5"] / 1000, p_["p95"] / 1000], [i, i], color=col_, lw=1.4, solid_capstyle="butt")
    ax.plot([p_["p25"] / 1000, p_["p75"] / 1000], [i, i], color=col_, lw=7, solid_capstyle="butt")
    ax.plot(p_["mean"] / 1000, i, "o", color="white", ms=4.5, mec=INK, mew=0.9, zorder=4)
    ax.text(p_["p95"] / 1000 + 4, i, f"{100 * p_['p_big_loss']:.0f}% chance of losing £50k+", va="center", fontsize=7.3, color="#3a4440")
ax.axvline(0, color=INK, lw=0.8)
ax.set_yticks(range(3)); ax.set_yticklabels([r[0] for r in rows3[::-1]], fontsize=7.5)
ax.set_xlabel("Net benefit to the club (£ thousands): bars show the middle 50% and 90% of outcomes, dot = average")
ax.set_title("Three ways to pay for the same player")
lo = min(r[1]["p5"] for r in rows3) / 1000; hi = max(r[1]["p95"] for r in rows3) / 1000
ax.set_xlim(lo - 10, hi + 95)
credit(ax)
save(fig, "c3_deal")

# C4: finishing — raw vs estimated
pdf = per_player[per_player["xg"] >= 1.5]
fig, ax = plt.subplots(figsize=(7.0, 2.25))
ax.scatter(pdf["raw_ratio"], pdf["skill"], s=pdf["shots"] * 1.2, alpha=0.55, color=GREEN, lw=0)
lims = [0, 2.4]
ax.plot(lims, lims, ls="--", color="#7a8580", lw=0.8)
ax.text(1.62, 1.72, "If raw numbers were all skill", rotation=0, fontsize=7.2, color="#5b6660", ha="right")
ax.axhline(league_ratio, color=RED, lw=0.9)
ax.text(0.03, league_ratio + 0.06, f"League average {league_ratio:.2f}", fontsize=7.2, color=RED)
for name_, dy in (("Khadija Shaw", -0.3), ("Lauren James", 0.28), ("Viviane Asseyi", 0.28)):
    r_ = pdf[pdf["player"] == name_]
    if len(r_):
        r_ = r_.iloc[0]
        ax.annotate(name_, (r_["raw_ratio"], r_["skill"]), xytext=(r_["raw_ratio"], r_["skill"] + dy), ha="center",
                    fontsize=7.2, arrowprops=dict(arrowstyle="-", color="#7a8580", lw=0.5))
ax.set_xlim(lims); ax.set_ylim(0.5, 1.8)
ax.set_xlabel("Raw goals per xG last season (dot size = shots)"); ax.set_ylabel("Estimated true finishing")
ax.set_title("Raw finishing varies hugely; true finishing skill barely moves")
credit(ax)
save(fig, "c4_finishing")

# C5: reliability
rr = rel.sort_values("season_reliability")
fig, ax = plt.subplots(figsize=(7.0, 2.7))
cols_ = [GREEN if x >= 0.7 else (SAGE if x >= 0.4 else RED) for x in rr["season_reliability"]]
ax.barh(range(len(rr)), rr["season_reliability"], color=cols_, height=0.62)
ax.axvline(0.7, color="#7a8580", ls="--", lw=0.8, zorder=0)
ax.set_ylim(-0.6, len(rr) + 0.15)
ax.text(0.705, len(rr) - 0.32, "0.7 = trustworthy", fontsize=7, va="center", color="#3a4440")
ax.set_yticks(range(len(rr))); ax.set_yticklabels(rr["metric"], fontsize=7.6)
for i, (_, r_) in enumerate(rr.iterrows()):
    need = r_["matches_for_07"]
    txt = f"{r_['season_reliability']:.2f}  ·  " + (f"~{need:.0f} matches to reach 0.7" if need < 200 else "never reliable in practice")
    x_ = r_["season_reliability"] + 0.015
    if 0.62 < r_["season_reliability"] < 0.7:
        x_ = 0.715
    ax.text(x_, i, txt, va="center", fontsize=7.2)
ax.set_xlim(0, 1.35); ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
ax.set_xlabel("Season-long reliability: share of the differences between players that is real, not luck (0 to 1)")
ax.set_title("Which numbers can you trust after one season?")
credit(ax)
save(fig, "c5_reliability")

# C6: critical differences
fig, ax = plt.subplots(figsize=(7.0, 2.35))
yy = np.arange(len(cd))
ax.barh(yy + 0.2, 100 * cd["one"], height=0.38, color=SAGE, label="One match vs the previous one")
ax.barh(yy - 0.2, 100 * cd["five"], height=0.38, color=GREEN, label="Last 5 matches vs the previous 15")
for i, (_, r_) in enumerate(cd.iterrows()):
    ax.text(100 * r_["one"] + 3, i + 0.2, f"{100 * r_['one']:.0f}%", va="center", fontsize=7)
    ax.text(100 * r_["five"] + 3, i - 0.2, f"{100 * r_['five']:.0f}%", va="center", fontsize=7, color=GREEN)
ax.set_yticks(yy); ax.set_yticklabels(cd["metric"], fontsize=7.6); ax.invert_yaxis()
ax.set_xlabel("Smallest change that's unlikely to be noise (%)")
ax.set_title("How big must a change in form be before it's real?")
ax.legend(loc="upper right", frameon=False)
ax.set_xlim(0, 290)
credit(ax)
save(fig, "c6_critical")

N["inputs"] = dict(asking_fee=ASKING_FEE, extra_wages_per_season=EXTRA_WAGES_PER_SEASON, seasons=SEASONS,
                   matches_per_season=MATCHES_PER_SEASON, value_per_point=VALUE_PER_POINT,
                   comparator_percentile=COMPARATOR_PERCENTILE, discount_rate=DISCOUNT_RATE, n_sims=N_SIMS,
                   short_injury=beta_mean(SHORT_INJURY), long_injury=beta_mean(LONG_INJURY),
                   short_recovery=beta_mean(SHORT_RECOVERY), long_recovery=beta_mean(LONG_RECOVERY),
                   minutes_share=beta_mean(MINUTES_SHARE), resale_share=beta_mean(RESALE_SHARE),
                   min_minutes_regular=900, player_matches=int(len(player_match)), shots=int(len(shots)),
                   target_player=str(target["player"]))
json.dump(N, open(f"{OUT}/{'wsl_elapsed' if SENSITIVITY else 'wsl'}.json", "w"), indent=1, default=float)
print(json.dumps({k: N[k] for k in ("league_model", "critical_watch")}, indent=1, default=float))

# C7: credible intervals for the forwards with the most xG
top = per_player.nlargest(12, "xg").sort_values("skill")
fig, ax = plt.subplots(figsize=(7.0, 2.15))
yy = np.arange(len(top))
ax.hlines(yy, top["skill_lo"], top["skill_hi"], color=SAGE, lw=2.2)
ax.plot(top["raw_ratio"], yy, "x", color=RED, ms=5, mew=1.2, label="Raw goals per xG last season")
ax.plot(top["skill"], yy, "o", color=GREEN, ms=5, label="Estimated true finishing (90% interval)")
ax.axvline(league_ratio, color=INK, lw=0.7, ls="--")
ax.set_yticks(yy); ax.set_yticklabels([f"{p}  ({g}G, {x:.1f} xG)" for p, g, x in zip(top["player"], top["goals"], top["xg"])], fontsize=7.2)
ax.set_xlabel("Goals per xG")
ax.set_title("The 12 players with the most xG: raw finishing against what the model believes")
ax.legend(loc="lower right", frameon=False, fontsize=7)
ax.set_xlim(0.3, 2.0)
save(fig, "c7_intervals")
