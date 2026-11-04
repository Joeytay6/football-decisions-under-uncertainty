"""Project 2, men's check. Finishing: skill or luck? Hierarchical model and out-of-sample test, four men's leagues 2015/16.

Question  When a striker scores more than his expected goals (xG), how much of that is a repeatable skill?
Model     Hierarchical (random-effects) Gamma-Poisson model, as used for small-area rates in epidemiology:
          goals_i ~ Poisson(theta_i * xG_i); theta_i ~ Gamma(mean m, sd s) across players.
          s is the real spread of finishing skill; each player's estimate is shrunk towards m in
          proportion to how little evidence he has. Posterior by grid approximation (no MCMC needed).
Check     Out-of-sample: does over-performance in the first half of the season predict the second half?
Data      Every non-penalty shot with StatsBomb xG, four complete men's league seasons 2015/16.
"""
import numpy as np
import pandas as pd
from scipy.special import gammaln
from scipy.stats import norm, spearmanr
from common import (MEN, available, load_many, plt, save, write_numbers, GREEN, PURPLE, AMBER, GREY, LIGHT, INK,
                    MUTED, REF, WIDTH)

LEAGUES = available(MEN)
shots = load_many(LEAGUES, "shots")
matches = load_many(LEAGUES, "matches")
pm = load_many(LEAGUES, "player_match")
N = {"leagues": [MEN[l] for l in LEAGUES], "shots": int(len(shots)), "goals": int(shots["goal"].sum()),
     "xg": float(shots["xg"].sum())}

most_common = lambda s: s.mode().iat[0]
pp = (shots.groupby(["player_id", "player"])
      .agg(team=("team", most_common), league=("league", most_common), shots=("xg", "size"), goals=("goal", "sum"),
           xg=("xg", "sum")).reset_index())
pp["raw_ratio"] = pp["goals"] / pp["xg"]
league_ratio = pp["goals"].sum() / pp["xg"].sum()
G, X = pp["goals"].to_numpy(), np.maximum(pp["xg"].to_numpy(), 1e-6)
means, spreads = np.linspace(0.8, 1.3, 101), np.linspace(0.005, 0.5, 199)
M, S = np.meshgrid(means, spreads, indexing="ij")
A, Bt = (M / S) ** 2, M / S ** 2
loglik = np.zeros(M.shape)
for g, x in zip(G, X):
    loglik += gammaln(A + g) - gammaln(A) - gammaln(g + 1) + A * np.log(Bt / (Bt + x)) + g * np.log(x / (Bt + x))
logpost = loglik + norm.logpdf(M, 1.0, 0.25) + norm.logpdf(S, 0, 0.2)   # weakly informative priors
w = np.exp(logpost - logpost.max()); w /= w.sum()


def summarise(values, wts):
    o = np.argsort(values); cdf = np.cumsum(wts[o])
    return [float(values[o][np.searchsorted(cdf, q)]) for q in (0.5, 0.025, 0.975)]


s_mid, s_lo, s_hi = summarise(S.ravel(), w.ravel())
m_mid = summarise(M.ravel(), w.ravel())[0]
rng = np.random.default_rng(2026)
draw = rng.choice(w.size, size=4000, p=w.ravel())
a_d, b_d, m_d = A.ravel()[draw], Bt.ravel()[draw], M.ravel()[draw]
theta = rng.gamma(a_d[None, :] + G[:, None], 1 / (b_d[None, :] + X[:, None]))
pp["skill"] = theta.mean(axis=1)
pp["skill_lo"] = np.percentile(theta, 5, axis=1)
pp["skill_hi"] = np.percentile(theta, 95, axis=1)
pp["p_above"] = (theta > m_d[None, :]).mean(axis=1)
pp["shrink"] = 1 - (pp["skill"] - m_mid) / (pp["raw_ratio"] - m_mid).replace(0, np.nan)
reg = pp[pp["shots"] >= 40]
N["model"] = dict(league_ratio=float(league_ratio), mean=m_mid, spread=s_mid, spread_lo=s_lo, spread_hi=s_hi,
                  players=int(len(pp)), regulars_40_shots=int(len(reg)),
                  regulars_confident_above=int((reg["p_above"] >= 0.9).sum()),
                  regulars_confident_below=int((reg["p_above"] <= 0.1).sum()),
                  raw_ratio_sd_regulars=float(reg["raw_ratio"].std()),
                  skill_sd_regulars=float(reg["skill"].std()))
top = pp.nlargest(12, "xg").sort_values("skill")
N["top12"] = top[["player", "team", "league", "shots", "goals", "xg", "raw_ratio", "skill", "skill_lo", "skill_hi",
                  "p_above"]].assign(league=lambda d: d["league"].map(MEN)).to_dict(orient="records")

# ------------------------------------------------------------------ out-of-sample check (chronological halves)
shots = shots.merge(matches[["match_id", "date"]], on="match_id")
order = pm[["league", "team", "match_id"]].drop_duplicates().merge(matches[["match_id", "date"]], on="match_id")
order = order.sort_values(["team", "date", "match_id"])
order["k"] = order.groupby(["league", "team"]).cumcount()
order["n"] = order.groupby(["league", "team"])["match_id"].transform("count")
order["half"] = np.where(order["k"] < order["n"] / 2, 1, 2)
shots = shots.merge(order[["team", "match_id", "half"]], on=["team", "match_id"])
h = shots.groupby(["player_id", "half"]).agg(n=("xg", "size"), g=("goal", "sum"), x=("xg", "sum")).unstack("half")
h.columns = [f"{a}{b}" for a, b in h.columns]
h = h[(h["n1"] >= 20) & (h["n2"] >= 20)].copy()
h["over1"], h["over2"] = (h["g1"] - h["x1"]) / h["n1"], (h["g2"] - h["x2"]) / h["n2"]
h["q1"], h["q2"] = h["x1"] / h["n1"], h["x2"] / h["n2"]
r_over = spearmanr(h["over1"], h["over2"])
r_qual = spearmanr(h["q1"], h["q2"])
N["halves"] = dict(players=int(len(h)), r_finishing=float(r_over.statistic), p_finishing=float(r_over.pvalue),
                   r_shot_quality=float(r_qual.statistic), p_shot_quality=float(r_qual.pvalue))

write_numbers("finishing", N)
print(N["model"]); print(N["halves"])
print(top[["player", "team", "shots", "goals", "xg", "raw_ratio", "skill", "skill_lo", "skill_hi", "p_above"]].round(2).to_string())

# ------------------------------------------------------------------ chart
fig, ax = plt.subplots(figsize=(WIDTH, 2.9))
yy = np.arange(len(top))
ax.hlines(yy, top["skill_lo"], top["skill_hi"], color=LIGHT, lw=5)
ax.plot(top["raw_ratio"], yy, "D", color=PURPLE, ms=4.5, label="Raw: goals ÷ xG this season")
ax.plot(top["skill"], yy, "o", color=GREEN, ms=5.5, label="Model estimate of true finishing (bar = 90% interval)")
for i, (r_, s_) in enumerate(zip(top["raw_ratio"], top["skill"])):
    ax.plot([r_, s_], [i, i], color=GREY, lw=0.6, zorder=0)
ax.axvline(league_ratio, color=MUTED, lw=0.8, ls="--")
ax.text(league_ratio + 0.01, -0.55, "Average", fontsize=7, color=MUTED)
ax.set_yticks(yy)
ax.set_yticklabels([f"{p}  ({g} goals from {x:.1f} xG)" for p, g, x in zip(top["player"], top["goals"], top["xg"])],
                   fontsize=7.2)
ax.set_xlabel("Goals per expected goal (1.0 = scores exactly what the chances are worth)")
ax.set_title("The 12 players with the most xG: raw finishing against the model's estimate")
ax.legend(loc="upper left", fontsize=7)
ax.set_ylim(-0.7, len(top) + 1.6)
ax.set_xlim(0.75, 1.85)
save(fig, "finishing")
