"""Project 10. Set pieces as an investment: a repeatable edge, and what it is worth.

Question   Is a team's set-piece quality, in attack and defence, a repeatable characteristic of the team
           (and so something coaching can change) or mostly noise? If it is real, how big is the gap between
           good and poor set-piece teams, in goals and points a season?
Design     Reliability study (split-half across matches, Spearman-Brown; first half of the season against
           the second) of set-piece and open-play expected goals, for and against; between-team spread of the
           true set-piece edge (observed variance x reliability); conversion to points with the league's own
           points-per-goal relationship. Money is left out: what a point is worth differs by club.
Definition A set-piece shot is a direct free kick or corner, or a shot within 20 seconds of a corner, free kick
           or throw-in taken in the final third, in the same possession. Penalties are excluded throughout.
Data       Premier League, La Liga, Serie A, Ligue 1 2015/16; FA WSL 2018/19 to 2023/24.
"""
import numpy as np
import pandas as pd
from common import plt, save, write_numbers, GREEN, PURPLE, AMBER, GREY, LIGHT, INK, MUTED, WIDTH, MEN
from common_team import team_tables, WSL_SEASONS, place_labels

rng = np.random.default_rng(2026)


def frame(folders):
    mm, ma, sh, tm = team_tables(folders)
    s = sh[(sh.shot_type != "Penalty") & (sh.shot_type != "Own Goal")].copy()
    s["sp"] = s.set_piece.astype(int)
    g = s.groupby(["league", "match_id", "team", "sp"]).agg(xg=("xg", "sum"), goals=("goal", "sum"), shots=("xg", "size"))
    g = g.unstack("sp", fill_value=0)
    g.columns = [f"{a}_{'sp' if b else 'op'}" for a, b in g.columns]
    base = tm[tm.scope == "all"][["league", "match_id", "team", "opp", "corners", "fk_f3", "throw_f3"]].copy()
    base["n_sp"] = base.corners + base.fk_f3 + base.throw_f3
    base = base.drop(columns=["corners", "fk_f3", "throw_f3"])
    f = base.merge(g.reset_index(), on=["league", "match_id", "team"], how="left").fillna(0)
    o = f.drop(columns=["opp"]).rename(columns={c: c + "_a" for c in list(g.columns) + ["n_sp"]}).rename(columns={"team": "opp"})
    f = f.merge(o, on=["league", "match_id", "opp"])
    f = f.merge(mm[["match_id", "date"]], on="match_id").sort_values(["league", "team", "date", "match_id"])
    f["k"] = f.groupby(["league", "team"]).cumcount()
    f["n"] = f.groupby(["league", "team"])["match_id"].transform("count")
    f["xgd_sp"] = f.xg_sp - f.xg_sp_a
    f["xgd_op"] = f.xg_op - f.xg_op_a
    return f, sh, ma


def split_half(f, col, splits=300):
    rs = []
    for _ in range(splits):
        h = []
        for (lg, t), g in f.groupby(["league", "team"]):
            v = g[col].to_numpy(); idx = rng.permutation(len(v)); m = len(v) // 2
            h.append((lg, v[idx[:m]].mean(), v[idx[m:2 * m]].mean()))
        h = pd.DataFrame(h, columns=["lg", "a", "b"])
        h[["a", "b"]] = h[["a", "b"]] - h.groupby("lg")[["a", "b"]].transform("mean")
        rs.append(np.corrcoef(h.a, h.b)[0, 1])
    return float(np.mean(rs)), float(np.percentile(rs, 2.5)), float(np.percentile(rs, 97.5))


COLS = {"xg_sp": "Set-piece xG for", "xg_sp_a": "Set-piece xG against", "xgd_sp": "Set-piece xG difference",
        "xg_op": "Open-play xG for", "xg_op_a": "Open-play xG against", "xgd_op": "Open-play xG difference"}


def analyse(folders, label, splits=300):
    f, sh, ma = frame(folders)
    s = sh[(sh.shot_type != "Own Goal")]
    np_ = s[s.shot_type != "Penalty"]
    out = dict(label=label, matches=int(f.match_id.nunique()), teams=int(f.groupby(["league", "team"]).ngroups),
               share_np_goals=float(np_[np_.set_piece == 1].goal.sum() / np_.goal.sum()),
               share_npxg=float(np_[np_.set_piece == 1].xg.sum() / np_.xg.sum()),
               share_shots=float(np_.set_piece.mean()),
               xg_per_shot_sp=float(np_[np_.set_piece == 1].xg.mean()), xg_per_shot_op=float(np_[np_.set_piece == 0].xg.mean()))
    half_n = int(f.groupby(["league", "team"]).size().min() // 2)
    nseason = float(f.groupby(["league", "team"]).size().median())
    rel = {}
    first = f[f.k < f.n / 2].groupby(["league", "team"])[list(COLS)].mean()
    second = f[f.k >= f.n / 2].groupby(["league", "team"])[list(COLS)].mean()
    for c, lab in COLS.items():
        r, lo, hi = split_half(f, c, splits)
        kk = nseason / half_n
        rs = kk * r / (1 + (kk - 1) * r)
        fs = first[c] - first.groupby(level=0)[c].transform("mean")
        ss = second[c] - second.groupby(level=0)[c].transform("mean")
        season_means = f.groupby(["league", "team"])[c].mean()
        season_means = season_means - season_means.groupby(level=0).transform("mean")
        true_sd = float(np.sqrt(max(rs, 0)) * season_means.std())
        rel[c] = dict(label=lab, r_half=r, r_lo=lo, r_hi=hi, season=rs, half_matches=half_n,
                      m80=half_n * 0.8 * (1 - r) / (r * 0.2) if r > 0 else float("inf"),
                      test_retest=float(np.corrcoef(fs, ss)[0, 1]), obs_sd=float(season_means.std()), true_sd=true_sd)
    out["rel"] = rel

    # volume against quality: set pieces won follow dominance; xG per set piece is closer to coaching
    def split_ratio(num, den, splits):
        rs = []
        for _ in range(splits):
            h = []
            for (lg, t), g in f.groupby(["league", "team"]):
                idx = rng.permutation(len(g)); m = len(g) // 2
                a_, b_ = g.iloc[idx[:m]], g.iloc[idx[m:2 * m]]
                h.append((lg, a_[num].sum() / a_[den].sum(), b_[num].sum() / b_[den].sum()))
            h = pd.DataFrame(h, columns=["lg", "a", "b"])
            h[["a", "b"]] = h[["a", "b"]] - h.groupby("lg")[["a", "b"]].transform("mean")
            rs.append(np.corrcoef(h.a, h.b)[0, 1])
        r = float(np.mean(rs)); kk = nseason / half_n
        return dict(r_half=r, season=kk * r / (1 + (kk - 1) * r), m80=half_n * 0.8 * (1 - r) / (r * 0.2) if r > 0 else None)
    tt = f.groupby(["league", "team"]).agg(nsp=("n_sp", "sum"), nspa=("n_sp_a", "sum"), spx=("xg_sp", "sum"), spxa=("xg_sp_a", "sum"),
                                           xo=("xgd_op", "mean"), m=("match_id", "size"))
    tt["vol_d"] = (tt.nsp - tt.nspa) / tt.m
    tt["q_for"] = 100 * tt.spx / tt.nsp
    tt["q_against"] = 100 * tt.spxa / tt.nspa
    tt["sp_d"] = (tt.spx - tt.spxa) / tt.m
    cen = tt - tt.groupby(level=0).transform("mean")
    out["volume_quality"] = dict(
        sp_per_match=float(f.n_sp.mean()), xg_per_100_sp=float(100 * f.xg_sp.sum() / f.n_sp.sum()),
        r_volume_openplay=float(np.corrcoef(cen.vol_d, cen.xo)[0, 1]),
        r_qfor_openplay=float(np.corrcoef(cen.q_for, cen.xo)[0, 1]),
        r_qagainst_openplay=float(np.corrcoef(cen.q_against, cen.xo)[0, 1]),
        r_spd_openplay=float(np.corrcoef(cen.sp_d, cen.xo)[0, 1]),
        rel_q_for=split_ratio("xg_sp", "n_sp", splits), rel_q_against=split_ratio("xg_sp_a", "n_sp_a", splits),
        rel_volume=split_ratio("n_sp", "n_sp_a", 1) if False else None,
        q_for_p10=float(tt.q_for.quantile(0.1)), q_for_p90=float(tt.q_for.quantile(0.9)),
        q_against_p10=float(tt.q_against.quantile(0.1)), q_against_p90=float(tt.q_against.quantile(0.9)))
    # what better delivery is worth at average volume: the true spread in xG per set piece
    vq = out["volume_quality"]
    sd_q = float(np.sqrt(max(vq["rel_q_for"]["season"], 0)) * cen.q_for.std()) / 100
    out["volume_quality"]["true_sd_q_for"] = sd_q
    out["volume_quality"]["goals_season_1sd_q_for"] = sd_q * float(f.n_sp.mean()) * nseason
    # what is the edge worth: points per goal from the league tables
    res = []
    for r in ma.itertuples():
        for t, gf, ga in ((r.home, r.home_score, r.away_score), (r.away, r.away_score, r.home_score)):
            res.append((r.league, t, 3 if gf > ga else (1 if gf == ga else 0), gf - ga))
    tb = pd.DataFrame(res, columns=["league", "team", "pts", "gd"]).groupby(["league", "team"]).sum()
    tb = tb - tb.groupby(level=0).transform("mean")
    slope = float(np.polyfit(tb.gd, tb.pts, 1)[0])
    out["points_per_goal"] = slope
    out["matches_per_season"] = nseason
    sd = rel["xgd_sp"]["true_sd"]
    out["edge"] = dict(true_sd_xgd_sp_per_match=sd, goals_per_season_1sd=sd * nseason,
                       points_per_season_1sd=sd * nseason * slope,
                       p90_vs_p10_goals=2 * 1.2816 * sd * nseason, p90_vs_p10_points=2 * 1.2816 * sd * nseason * slope,
                       true_sd_xgd_op_per_match=rel["xgd_op"]["true_sd"])
    # best and worst set-piece teams
    tt = f.groupby(["league", "team"]).agg(spf=("xg_sp", "sum"), spa=("xg_sp_a", "sum"), gsp=("goals_sp", "sum"),
                                           gspa=("goals_sp_a", "sum"), m=("match_id", "size"))
    tt["d"] = (tt.spf - tt.spa) / tt.m
    out["best"] = [dict(team=t, league=MEN.get(l, l), per_match=float(r.d), xg_for=float(r.spf), xg_against=float(r.spa),
                        goals_for=int(r.gsp), goals_against=int(r.gspa)) for (l, t), r in tt.sort_values("d").tail(5)[::-1].iterrows()]
    out["worst"] = [dict(team=t, league=MEN.get(l, l), per_match=float(r.d), xg_for=float(r.spf), xg_against=float(r.spa),
                         goals_for=int(r.gsp), goals_against=int(r.gspa)) for (l, t), r in tt.sort_values("d").head(5).iterrows()]
    by = np_.groupby("league").apply(lambda d: d[d.set_piece == 1].goal.sum() / d.goal.sum(), include_groups=False)
    out["share_by_league"] = {MEN.get(k, WSL_SEASONS.get(k, k)): float(v) for k, v in by.items()}
    out["restart_mix"] = np_[np_.set_piece == 1].groupby("restart_type").goal.sum().to_dict()
    return out, f


N = {}
N["men"], fm = analyse(list(MEN), "Men's top flights 2015/16")
try:
    N["women"], fw = analyse(list(WSL_SEASONS), "WSL 2018/19 to 2023/24", splits=200)
except (FileNotFoundError, ValueError) as e:
    print("women's check skipped:", e)
write_numbers("set_pieces", N)
for g in N:
    v = N[g]
    print(g, {k: v[k] for k in ("matches", "teams", "share_np_goals", "share_npxg", "share_shots", "points_per_goal")})
    for c, r in v["rel"].items():
        print(f"   {r['label']:26s} r_half {r['r_half']:.2f} ({r['r_lo']:.2f}-{r['r_hi']:.2f}) season {r['season']:.2f} "
              f"m80 {r['m80']:.0f} test-retest {r['test_retest']:.2f} true sd {r['true_sd']:.3f}")
    print("  edge", v["edge"]); print("  best", v["best"][:3]); print("  worst", v["worst"][:3])
    print("  volume/quality", v["volume_quality"])

# ------------------------------------------------------------------ charts
fig, ax = plt.subplots(figsize=(WIDTH, 2.5))
rows = ["xg_sp", "xg_sp_a", "xgd_sp", "xg_op", "xg_op_a", "xgd_op"]
for i, c in enumerate(rows[::-1]):
    r = N["men"]["rel"][c]
    colr = AMBER if "sp" in c else GREEN
    ax.barh(i, r["season"], color=colr, height=0.6)
    ax.text(r["season"] + 0.01, i, f"{r['season']:.2f}", va="center", fontsize=7.2)
ax.set_yticks(range(len(rows))); ax.set_yticklabels([COLS[c] for c in rows[::-1]], fontsize=7.4)
ax.axvline(0.7, color=MUTED, ls="--", lw=0.8)
ax.set_xlim(0, 1); ax.set_xlabel("Reliability over a 38-match season (men's top flights 2015/16)")
save(fig, "c10_reliability")

fig, ax = plt.subplots(figsize=(WIDTH, 2.6))
t = fm.groupby(["league", "team"]).agg(f=("xg_sp", "mean"), a=("xg_sp_a", "mean"))
ax.scatter(t.f, t.a, s=16, color=AMBER, lw=0, alpha=0.85)
d_ = t.f - t.a
lab = t[(d_ > d_.quantile(0.95)) | (d_ < d_.quantile(0.05))]
place_labels(ax, lab.f.values, lab.a.values, [tn for _, tn in lab.index], fontsize=6.4)
ax.invert_yaxis()
ax.set_xlabel("Set-piece xG created per match"); ax.set_ylabel("Set-piece xG conceded per match\n(better at the top)")
save(fig, "c10_map")
