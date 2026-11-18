"""Project 7. How good is a team really? Judging a club on its chances, the way hospitals are judged on
risk-adjusted outcomes.

Question   When a club is assessed (an acquisition, a partner club, a season review), how much of its league
           position is the quality of its football and how much is chance? Which numbers tell you, and after
           how many matches?
Design     Observed against expected, as in risk-adjusted hospital and surgeon outcomes (observed and expected
           deaths). Expected points come from every chance each team created and conceded: shots in the same
           possession are combined so rebounds aren't double counted, goals follow a Poisson-binomial
           distribution, and the chance of a win, draw or loss gives expected points and their variance.
Checks     (1) Is the gap between points and expected points bigger than chance alone would produce?
           (2) Reliability: how many matches before points, goal difference and expected-goal difference
               measure a team rather than its luck (split-half, Spearman-Brown, 300 random splits)?
           (3) Prognostic validation: chronological split, first half of the season against points per game
               in the second half. Which first-half number predicts best?
Data       Premier League, La Liga, Serie A and Ligue 1 2015/16; FA WSL 2018/19 to 2023/24 as a check.
"""
import numpy as np
import pandas as pd
from common import plt, save, write_numbers, GREEN, PURPLE, AMBER, GREY, LIGHT, INK, MUTED, WIDTH, MEN
from common_team import team_tables, xpts_table, WSL_SEASONS, place_labels

rng = np.random.default_rng(2026)
MENF = list(MEN)
N = {"leagues": [MEN[l] for l in MENF]}


def team_match_frame(folders):
    mm, ma, sh, tm = team_tables(folders)
    x = xpts_table(mm, sh)
    a = tm[tm.scope == "all"][["match_id", "team", "npxg", "np_shots"]]
    x = x.merge(a, on=["match_id", "team"])
    opp = a.rename(columns={"team": "opp", "npxg": "npxga", "np_shots": "np_shots_a"})
    x = x.merge(opp, on=["match_id", "opp"])
    x["gd"] = x.gf - x.ga
    x["xgd"] = x.npxg - x.npxga
    x["sd"] = x.np_shots - x.np_shots_a
    x = x.sort_values(["league", "team", "date", "match_id"])
    x["k"] = x.groupby(["league", "team"]).cumcount()
    x["n"] = x.groupby(["league", "team"])["match_id"].transform("count")
    return x, ma


x, ma = team_match_frame(MENF)
# full-season points from every result (Ligue 1 has 3 matches without event data)
res = []
for r in ma.itertuples():
    for t, gf, ga in ((r.home, r.home_score, r.away_score), (r.away, r.away_score, r.home_score)):
        res.append((r.league, t, 3 if gf > ga else (1 if gf == ga else 0)))
table = pd.DataFrame(res, columns=["league", "team", "pts"]).groupby(["league", "team"]).pts.agg(["sum", "count"])

season = x.groupby(["league", "team"]).agg(pts=("pts", "sum"), xpts=("xpts", "sum"), var=("var_pts", "sum"),
                                           m=("pts", "size"), gf=("gf", "sum"), ga=("ga", "sum"),
                                           npxg=("npxg", "sum"), npxga=("npxga", "sum")).reset_index()
season["diff"] = season.pts - season.xpts
season["z"] = season["diff"] / np.sqrt(season["var"])
season["ratio"] = season.pts / season.xpts
season["rank_pts"] = season.groupby("league").pts.rank(ascending=False, method="min")
season["rank_xpts"] = season.groupby("league").xpts.rank(ascending=False, method="min")

# 1. luck in the table: observed spread of (points - expected) against the spread chance alone produces
chance_var = season["var"].mean()
obs_var = season["diff"].var(ddof=1)
# sampling interval for the observed variance (chi-square), to say whether it exceeds chance
from scipy.stats import chi2
df_ = len(season) - 1
N["luck"] = dict(teams=int(len(season)), matches_per_team=float(season.m.mean()),
                 sd_obs=float(np.sqrt(obs_var)), sd_chance=float(np.sqrt(chance_var)),
                 share_chance=float(min(1.0, chance_var / obs_var)),
                 sd_obs_lo=float(np.sqrt(obs_var * df_ / chi2.ppf(0.975, df_))),
                 sd_obs_hi=float(np.sqrt(obs_var * df_ / chi2.ppf(0.025, df_))),
                 outside95=int((season.z.abs() > 1.96).sum()), expected_outside95=float(0.05 * len(season)),
                 mean_abs_diff=float(season["diff"].abs().mean()),
                 max_over=season.sort_values("diff").iloc[-1][["team", "league", "pts", "xpts"]].to_dict(),
                 max_under=season.sort_values("diff").iloc[0][["team", "league", "pts", "xpts"]].to_dict(),
                 rank_changes=int((season.rank_pts != season.rank_xpts).sum()),
                 top4_by_xpts_not_top4=int(((season.rank_xpts <= 4) & (season.rank_pts > 4)).sum()))
cases = season.sort_values("diff")
N["season_table"] = [dict(team=r.team, league=MEN[r.league], pts=int(r.pts), xpts=float(r.xpts), m=int(r.m),
                          diff=float(r.diff), z=float(r.z), rank_pts=int(r.rank_pts), rank_xpts=int(r.rank_xpts),
                          gf=int(r.gf), ga=int(r.ga), npxg=float(r.npxg), npxga=float(r.npxga))
                     for r in season.itertuples()]


# 2. reliability: how many matches before each per-match number measures the team
def split_half(frame, col, splits=300):
    rs = []
    for _ in range(splits):
        h = []
        for (lg, tm_), g in frame.groupby(["league", "team"]):
            v = g[col].to_numpy()
            idx = rng.permutation(len(v))
            a, b = v[idx[: len(v) // 2]].mean(), v[idx[len(v) // 2: 2 * (len(v) // 2)]].mean()
            h.append((lg, a, b))
        h = pd.DataFrame(h, columns=["lg", "a", "b"])
        h[["a", "b"]] = h[["a", "b"]] - h.groupby("lg")[["a", "b"]].transform("mean")  # within league
        rs.append(np.corrcoef(h.a, h.b)[0, 1])
    return float(np.mean(rs)), float(np.percentile(rs, 2.5)), float(np.percentile(rs, 97.5))


def sb(r, k):
    return k * r / (1 + (k - 1) * r)


def matches_for(r, half_n, target):
    return half_n * target * (1 - r) / (r * (1 - target))


METRICS = {"pts": "Points", "gd": "Goal difference", "xpts": "Expected points", "xgd": "Expected-goal difference (npxG)",
           "sd": "Shot difference"}
half_n = int(x.groupby(["league", "team"]).size().min() // 2)
N["reliability"] = {}
for c, lab in METRICS.items():
    r, lo, hi = split_half(x, c)
    N["reliability"][c] = dict(label=lab, r_half=r, r_lo=lo, r_hi=hi, half_matches=half_n,
                               season=sb(r, 38 / half_n), m70=matches_for(r, half_n, 0.7),
                               m80=matches_for(r, half_n, 0.8))

# 3. prognostic validation: first half of the season against second-half points per game
first = x[x.k < x.n / 2].groupby(["league", "team"])[list(METRICS)].mean()
second = x[x.k >= x.n / 2].groupby(["league", "team"])["pts"].mean().rename("pts2")
pv = first.join(second).reset_index()
N["prognostic"] = {}
B = 2000
boot = [rng.integers(0, len(pv), len(pv)) for _ in range(B)]
for c, lab in METRICS.items():
    r = float(np.corrcoef(pv[c], pv.pts2)[0, 1])
    rb = [np.corrcoef(pv[c].to_numpy()[i], pv.pts2.to_numpy()[i])[0, 1] for i in boot]
    # leave-one-league-out calibrated prediction error (points over 19 matches)
    err = []
    groups = pv.league if pv.league.nunique() > 1 else pv.team
    for lg in groups.unique():
        tr, te = pv[groups != lg], pv[groups == lg]
        b1, b0 = np.polyfit(tr[c], tr.pts2, 1)
        err += list(np.abs(b0 + b1 * te[c] - te.pts2) * 19)
    N["prognostic"][c] = dict(label=lab, r=r, r_lo=float(np.percentile(rb, 2.5)), r_hi=float(np.percentile(rb, 97.5)),
                              r2=r * r, mae_pts19=float(np.mean(err)))
d = [np.corrcoef(pv.xgd.to_numpy()[i], pv.pts2.to_numpy()[i])[0, 1] - np.corrcoef(pv.pts.to_numpy()[i], pv.pts2.to_numpy()[i])[0, 1]
     for i in boot]
N["prognostic_diff_xgd_vs_pts"] = dict(diff=N["prognostic"]["xgd"]["r"] - N["prognostic"]["pts"]["r"],
                                       lo=float(np.percentile(d, 2.5)), hi=float(np.percentile(d, 97.5)))
N["prognostic_teams"] = int(len(pv))

# 4. the women's game as a check
wf = [f for f in WSL_SEASONS]
try:
    xw, _ = team_match_frame(wf)
    sw = xw.groupby(["league", "team"]).agg(pts=("pts", "sum"), xpts=("xpts", "sum"), var=("var_pts", "sum"),
                                            m=("pts", "size")).reset_index()
    sw["diff"] = sw.pts - sw.xpts
    rw = {c: split_half(xw, c, 200) for c in ("pts", "xgd")}
    hn = int(xw.groupby(["league", "team"]).size().min() // 2)
    N["women"] = dict(team_seasons=int(len(sw)), sd_obs=float(sw["diff"].std()), sd_chance=float(np.sqrt(sw["var"].mean())),
                      rel={c: dict(r_half=v[0], half_matches=hn, m70=matches_for(v[0], hn, 0.7)) for c, v in rw.items()},
                      seasons=[WSL_SEASONS[f] for f in wf])
except (FileNotFoundError, ValueError) as e:
    print("women's check skipped:", e)

write_numbers("team_strength", N)
season.to_csv("output/team_strength_season.csv", index=False)
print({k: v for k, v in N["luck"].items()})
for c, v in N["reliability"].items():
    print(f"  {v['label']:34s} r_half {v['r_half']:.2f}  season {v['season']:.2f}  m70 {v['m70']:.1f}  m80 {v['m80']:.1f}")
for c, v in N["prognostic"].items():
    print(f"  {v['label']:34s} r {v['r']:.2f} ({v['r_lo']:.2f}-{v['r_hi']:.2f})  MAE {v['mae_pts19']:.1f} pts")
print(N["prognostic_diff_xgd_vs_pts"], N.get("women"))

# ------------------------------------------------------------------ charts
LG_SHORT = {"epl_2015_16": "PL", "laliga_2015_16": "LL", "seriea_2015_16": "SA", "ligue1_2015_16": "L1"}
fig, ax = plt.subplots(figsize=(WIDTH, 3.3))
lim = (10, 95)
xx = np.linspace(*lim, 50)
band = 1.96 * np.sqrt(chance_var)
ax.fill_between(xx, xx - band, xx + band, color=LIGHT, lw=0, label="Range chance alone would produce (95%)")
ax.plot(xx, xx, color=GREY, lw=0.8)
inside = season.z.abs() <= 1.96
ax.scatter(season.xpts[inside], season.pts[inside], s=16, color=GREEN, alpha=0.75, lw=0, zorder=3)
ax.scatter(season.xpts[~inside], season.pts[~inside], s=22, color=PURPLE, lw=0, zorder=4)
lab = season[~inside]
place_labels(ax, lab.xpts.values, lab.pts.values, [f"{t} ({LG_SHORT[l]})" for t, l in zip(lab.team, lab.league)], fontsize=6.8)
ax.set_xlim(*lim); ax.set_ylim(*lim)
ax.set_xlabel("Expected points, from the chances each team created and conceded")
ax.set_ylabel("Actual points")
ax.legend(loc="upper left", fontsize=7)
save(fig, "c7_table")

fig, ax = plt.subplots(figsize=(WIDTH, 2.7))
ns = np.arange(1, 61)
cols = {"pts": PURPLE, "gd": AMBER, "xgd": GREEN}
for c, colr in cols.items():
    v = N["reliability"][c]
    ax.plot(ns, [sb(v["r_half"], n / half_n) for n in ns], color=colr, lw=2,
            label=f"{v['label'].split(' (')[0]}: {v['m70']:.0f} matches to reach 0.7")
    ax.plot([v["m70"], v["m70"]], [0, 0.7], color=colr, lw=0.8, ls=":")
ax.legend(loc="lower right", bbox_to_anchor=(1.0, 0.04), fontsize=7.2, framealpha=1, frameon=True, edgecolor="none")
ax.axhline(0.7, color=MUTED, ls="--", lw=0.8)
ax.axvline(38, color=GREY, ls=":", lw=0.8)
ax.text(38.5, 0.97, "one season", fontsize=7, color=MUTED, va="top")
ax.set_xlim(0, 60); ax.set_ylim(0, 1)
ax.set_xlabel("Matches of evidence"); ax.set_ylabel("Reliability")
save(fig, "c7_reliability")

fig, ax = plt.subplots(figsize=(WIDTH, 2.2))
order = sorted(METRICS, key=lambda c: N["prognostic"][c]["r"])
for i, c in enumerate(order):
    v = N["prognostic"][c]
    colr = GREEN if c in ("xgd", "xpts") else (PURPLE if c == "pts" else GREY)
    ax.barh(i, v["r"], color=colr, height=0.6)
    ax.plot([v["r_lo"], v["r_hi"]], [i, i], color=INK, lw=0.8)
    ax.text(v["r_hi"] + 0.01, i, f"r = {v['r']:.2f}", va="center", fontsize=7.2)
ax.set_yticks(range(len(order))); ax.set_yticklabels([METRICS[c].split(" (")[0] + " per match" for c in order], fontsize=7.4)
ax.set_xlim(0, 1)
ax.set_xlabel("Correlation of first-half number with second-half points per game (95% CI)")
save(fig, "c7_prognostic")
