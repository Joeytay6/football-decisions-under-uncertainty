"""Project 8. Judging a head coach: funnel plots, and does a mid-season change work?

Question   (a) Which head coaches got more, or less, from their teams' chances than chance alone explains?
           (b) When a club changes its head coach mid-season, do results improve because of the change, or
               would they have bounced back anyway (regression to the mean)?
Design     (a) Funnel plot, as used to publish surgeon- and hospital-level outcomes in the NHS: each spell's
               points minus expected points per match, against matches in charge, with 95% and 99.8% control
               limits for chance.
           (b) Controlled before-and-after study. Every mid-season change of head coach in four men's leagues
               2015/16, comparing the 6 league matches before with the 6 after. Comparison group: the same
               leagues' team-moments with no change within 6 matches either side, matched on points from the
               previous 6 matches and on expected points from those matches (nearest 10).
Data       Premier League, La Liga, Serie A, Ligue 1 2015/16 (head coaches as named in StatsBomb's match data).
"""
import numpy as np
import pandas as pd
from common import plt, save, write_numbers, GREEN, PURPLE, AMBER, GREY, LIGHT, INK, MUTED, WIDTH, MEN
from common_team import team_tables, xpts_table, place_labels

rng = np.random.default_rng(2026)
MENF = list(MEN)
K, MIN_SPELL, NN = 6, 4, 10
mm, ma, sh, tm = team_tables(MENF)
x = xpts_table(mm, sh)
a = tm[tm.scope == "all"][["match_id", "team", "npxg"]]
x = x.merge(a, on=["match_id", "team"]).merge(a.rename(columns={"team": "opp", "npxg": "npxga"}), on=["match_id", "opp"])
x["xgd"] = x.npxg - x.npxga
mg = pd.concat([mm[["match_id", "home", "home_mgr"]].rename(columns={"home": "team", "home_mgr": "mgr"}),
                mm[["match_id", "away", "away_mgr"]].rename(columns={"away": "team", "away_mgr": "mgr"})])
x = x.merge(mg, on=["match_id", "team"], how="left")
x["mgr"] = x["mgr"].fillna("")
x = x.sort_values(["league", "team", "date", "match_id"]).reset_index(drop=True)
x["k"] = x.groupby(["league", "team"]).cumcount()
x["n"] = x.groupby(["league", "team"])["match_id"].transform("count")


def names(s):
    return set(p for p in s.split("/") if p)


# regimes: a label that shares a name with the current coach continues the regime (co-listed assistants,
# data-entry variants); a run of a new coach of fewer than MIN_SPELL matches that then hands back to the
# previous coach is treated as a stand-in, not a change.
spells, changes = [], []
for (lg, team), g in x.groupby(["league", "team"]):
    labs = list(g["mgr"])
    # carry forward missing labels
    for i in range(len(labs)):
        if not labs[i] and i:
            labs[i] = labs[i - 1]
    runs = []  # [names, start, end]
    for i, l in enumerate(labs):
        nm = names(l)
        if runs and (nm & runs[-1][0] or not nm):
            runs[-1][2] = i
            runs[-1][0] = runs[-1][0] | nm if len(runs[-1][0]) == 0 else runs[-1][0]
        else:
            runs.append([nm, i, i])
    # merge short stand-in runs that hand back to the same coach
    merged = []
    for r in runs:
        if len(merged) >= 2 and merged[-1][2] - merged[-1][1] + 1 < MIN_SPELL and (r[0] & merged[-2][0]):
            stand_in = merged.pop()
            merged[-1][2] = r[2]
            continue
        merged.append(list(r))
    def main_name(a, b):
        """The coach named most often in matches a..b (co-listed names are data-entry variants)."""
        from collections import Counter
        c = Counter(n for l in labs[a:b + 1] for n in names(l))
        return c.most_common(1)[0][0] if c else ""
    for r in merged:
        r.append(main_name(r[1], r[2]))
        spells.append(dict(league=lg, team=team, coach=r[3], start=r[1], end=r[2]))
    for prev, new in zip(merged, merged[1:]):
        if prev[2] - prev[1] + 1 >= MIN_SPELL and new[1] >= K and new[1] + K <= len(labs):
            changes.append(dict(league=lg, team=team, k0=new[1], out=prev[3], inn=new[3], date=g.iloc[new[1]]["date"]))
spells = pd.DataFrame(spells)
changes = pd.DataFrame(changes)

# (a) funnel plot of spells
sp = []
for s in spells.itertuples():
    g = x[(x.league == s.league) & (x.team == s.team) & (x.k >= s.start) & (x.k <= s.end)]
    sp.append(dict(league=s.league, team=s.team, coach=s.coach, m=len(g), pts=g.pts.sum(), xpts=g.xpts.sum(),
                   var=g.var_pts.sum(), xgd=g.xgd.mean()))
sp = pd.DataFrame(sp)
sp = sp[sp.m >= 5].copy()
sp["d"] = (sp.pts - sp.xpts) / sp.m
sp["z"] = (sp.pts - sp.xpts) / np.sqrt(sp["var"])
sigma = float(np.sqrt(x.var_pts.mean()))
N = {"spells": int(len(sp)), "sigma_per_match": sigma,
     "outside95": int((sp.z.abs() > 1.96).sum()), "outside998": int((sp.z.abs() > 3.09).sum()),
     "expected_outside95": float(0.05 * len(sp)), "expected_outside998": float(0.002 * len(sp)),
     "above95": sp[sp.z > 1.96][["coach", "team", "m", "pts", "xpts"]].to_dict("records"),
     "below95": sp[sp.z < -1.96][["coach", "team", "m", "pts", "xpts"]].to_dict("records")}

# (b) controlled before-and-after study
x["pts_pre"] = x.groupby(["league", "team"])["pts"].transform(lambda s: s.shift(1).rolling(K).sum())
x["xpts_pre"] = x.groupby(["league", "team"])["xpts"].transform(lambda s: s.shift(1).rolling(K).sum())
x["xgd_pre"] = x.groupby(["league", "team"])["xgd"].transform(lambda s: s.shift(1).rolling(K).mean())
x["pts_post"] = x.groupby(["league", "team"])["pts"].transform(lambda s: s[::-1].rolling(K).sum()[::-1])
x["xpts_post"] = x.groupby(["league", "team"])["xpts"].transform(lambda s: s[::-1].rolling(K).sum()[::-1])
x["xgd_post"] = x.groupby(["league", "team"])["xgd"].transform(lambda s: s[::-1].rolling(K).mean()[::-1])
chg_keys = set()
for c in changes.itertuples():
    for j in range(c.k0 - K, c.k0 + K + 1):
        chg_keys.add((c.league, c.team, j))
ctrl = x[[(l, t, k) not in chg_keys for l, t, k in zip(x.league, x.team, x.k)]].dropna(subset=["pts_pre", "pts_post"])
tr = []
for c in changes.itertuples():
    row = x[(x.league == c.league) & (x.team == c.team) & (x.k == c.k0)].iloc[0]
    pool = ctrl[(ctrl.pts_pre == row.pts_pre)]
    if len(pool) < NN:
        pool = ctrl[(ctrl.pts_pre - row.pts_pre).abs() <= 1]
    pool = pool.assign(dist=(pool.xpts_pre - row.xpts_pre).abs()).nsmallest(NN, "dist")
    tr.append(dict(team=c.team, league=MEN[c.league], out=c.out, inn=c.inn, date=c.date,
                   pts_pre=row.pts_pre, pts_post=row.pts_post, xpts_pre=row.xpts_pre, xpts_post=row.xpts_post,
                   xgd_pre=row.xgd_pre, xgd_post=row.xgd_post,
                   c_pts_pre=pool.pts_pre.mean(), c_pts_post=pool.pts_post.mean(),
                   c_xpts_pre=pool.xpts_pre.mean(), c_xpts_post=pool.xpts_post.mean(),
                   c_xgd_pre=pool.xgd_pre.mean(), c_xgd_post=pool.xgd_post.mean()))
tr = pd.DataFrame(tr)
for v in ("pts", "xpts"):
    tr[f"d_{v}"] = (tr[f"{v}_post"] - tr[f"{v}_pre"]) / K
    tr[f"cd_{v}"] = (tr[f"c_{v}_post"] - tr[f"c_{v}_pre"]) / K
tr["d_xgd"] = tr.xgd_post - tr.xgd_pre
tr["cd_xgd"] = tr.c_xgd_post - tr.c_xgd_pre


def boot_ci(v, B=4000):
    v = np.asarray(v, float)
    b = [v[rng.integers(0, len(v), len(v))].mean() for _ in range(B)]
    return float(np.mean(v)), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


res = {}
for v in ("pts", "xpts", "xgd"):
    res[v] = dict(changed=boot_ci(tr[f"d_{v}"]), control=boot_ci(tr[f"cd_{v}"]),
                  effect=boot_ci(tr[f"d_{v}"] - tr[f"cd_{v}"]))
N["before_after"] = dict(changes=int(len(tr)), window=K, controls_per_change=NN,
                         ppg_pre=float(tr.pts_pre.mean() / K), ppg_post=float(tr.pts_post.mean() / K),
                         c_ppg_pre=float(tr.c_pts_pre.mean() / K), c_ppg_post=float(tr.c_pts_post.mean() / K),
                         xppg_pre=float(tr.xpts_pre.mean() / K), xppg_post=float(tr.xpts_post.mean() / K),
                         c_xppg_pre=float(tr.c_xpts_pre.mean() / K), c_xppg_post=float(tr.c_xpts_post.mean() / K),
                         league_ppg=float(x.pts.mean()),
                         pre_luck=float((tr.pts_pre - tr.xpts_pre).mean() / K), results=res,
                         by_league=tr.groupby("league").size().to_dict())
N["changes"] = tr.round(3).to_dict("records")
write_numbers("coaches", N)
print({k: v for k, v in N.items() if k not in ("changes", "above95", "below95")})
print(tr[["team", "out", "inn", "date", "pts_pre", "pts_post", "xpts_pre", "xpts_post"]].to_string())

# ------------------------------------------------------------------ charts
fig, ax = plt.subplots(figsize=(WIDTH, 3.0))
mx = np.linspace(4, 40, 100)
for zz, ls_, lab_ in ((1.96, "--", "95% limits"), (3.09, ":", "99.8% limits")):
    ax.plot(mx, zz * sigma / np.sqrt(mx), color=MUTED, ls=ls_, lw=0.9, label=lab_)
    ax.plot(mx, -zz * sigma / np.sqrt(mx), color=MUTED, ls=ls_, lw=0.9)
ax.axhline(0, color=GREY, lw=0.8)
inside = sp.z.abs() <= 1.96
ax.scatter(sp.m[inside], sp.d[inside], s=16, color=GREEN, alpha=0.7, lw=0, zorder=3)
ax.scatter(sp.m[~inside], sp.d[~inside], s=22, color=PURPLE, lw=0, zorder=4)
SHORT = {"Claudio Ranieri": "Ranieri", "Diego Pablo Simeone": "Simeone", "Zinédine Zidane": "Zidane",
         "Marcelino García Toral": "Marcelino", "Frédéric Hantz": "Hantz", "Luciano Spalletti": "Spalletti",
         "Tim Sherwood": "Sherwood", "David Moyes": "Moyes", "Dominique Arribagé": "Arribagé", "Fabrizio Castori": "Castori"}
o = sp[~inside]
place_labels(ax, o.m.values, o.d.values, [f"{SHORT.get(c, c.split(' ')[-1])}, {t}" for c, t in zip(o.coach, o.team)], fontsize=6.6)
ax.set_xlim(4, 40); ax.set_ylim(-1.6, 1.6)
ax.set_xlabel("League matches in charge (2015/16)")
ax.set_ylabel("Points per match above expected")
ax.legend(loc="upper right", fontsize=7)
save(fig, "c8_funnel")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(WIDTH, 2.5), gridspec_kw=dict(wspace=0.35))
for ax, v, lab_ in ((ax1, "pts", "Points per match"), (ax2, "xpts", "Expected points per match")):
    pre, post = tr[f"{v}_pre"].mean() / K, tr[f"{v}_post"].mean() / K
    cpre, cpost = tr[f"c_{v}_pre"].mean() / K, tr[f"c_{v}_post"].mean() / K
    ax.plot([0, 1], [pre, post], color=PURPLE, lw=2.2, marker="o", ms=5, label="Changed coach")
    ax.plot([0, 1], [cpre, cpost], color=GREEN, lw=2.2, marker="o", ms=5, label="Same slump, kept coach")
    ax.axhline(x[v].mean(), color=GREY, ls=":", lw=0.8)
    ax.text(1.24, x[v].mean() + 0.02, "league average", fontsize=6.6, color=MUTED, ha="right", va="bottom")
    ax.set_xticks([0, 1]); ax.set_xticklabels([f"{K} matches before", f"{K} matches after"])
    ax.set_xlim(-0.25, 1.25); ax.set_ylim(0.4, 1.6)
    ax.set_title(lab_, fontsize=8.5)
ax1.legend(loc="upper left", fontsize=6.8)
save(fig, "c8_before_after")
