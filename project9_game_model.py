"""Project 9. Measuring a game model: style KPIs validated the way a clinical questionnaire is.

Question   A club's football methodology says how its teams should play. Can free event data measure that,
           well enough to check a team is playing the intended way, compare teams across a multi-club group,
           and find players and partner clubs from similar systems?
Design     Measurement validation, following the checks used for clinical outcome measures (COSMIN):
           reliability (how many matches before a KPI measures the team), stability (first half of the season
           against the second), construct validity (do the KPIs move with game state the way every coach
           knows teams do: leading teams sit deeper and give up the ball?), structure (how many separate
           dimensions of style the KPIs capture), and responsiveness (do the KPIs pick up a change of head
           coach?). Then the validated KPIs are used to map every team's style.
Data       Premier League, La Liga, Serie A, Ligue 1 2015/16 (78 teams); FA WSL 2018/19 to 2023/24 as a check.
"""
import numpy as np
import pandas as pd
from common import plt, save, write_numbers, GREEN, PURPLE, AMBER, GREY, LIGHT, INK, MUTED, WIDTH, MEN
from common_team import team_tables, WSL_SEASONS, place_labels

rng = np.random.default_rng(2026)
MENF = list(MEN)

KPIS = {  # name: (label, dimension it is meant to capture, higher means)
    "poss": ("Possession share (in-play time)", "Control", "more of the ball"),
    "tilt": ("Field tilt (share of final-third passes)", "Control", "more play in the opponent's third"),
    "ppp": ("Passes per possession", "Build-up", "more patient build-up"),
    "tempo": ("Passes per minute in possession", "Build-up", "faster circulation"),
    "long": ("Long-ball share of open-play passes", "Build-up", "more direct"),
    "ppda": ("PPDA (opponent passes per defensive action)", "Pressing", "less intense press"),
    "press_h": ("Average pressure height (yards from own goal)", "Pressing", "higher press"),
    "cp": ("Counterpresses per 90", "Pressing", "more counterpressing"),
    "line": ("Defenders' action height (yards from own goal)", "Pressing", "higher line"),
    "regain": ("High regains per 90 (final third)", "Pressing", "more high turnovers"),
    "width": ("Final-third passes from wide areas", "Chance creation", "wider"),
    "cross": ("Crosses as a share of passes into the box", "Chance creation", "more crossing"),
    "counter": ("Shots from counter-attacks (share)", "Chance creation", "more counter-attacking"),
    "xg_shot": ("npxG per shot", "Chance creation", "better shot selection"),
    "sp": ("Set-piece share of npxG", "Chance creation", "more set-piece reliant"),
}


FLIP = {"all": "all", "level": "level", "lead": "trail", "trail": "lead"}


def kpis(tm, scope="all"):
    """Per team-match KPIs from the team_match table, for one game state (the opponent's figures come
    from the opposite state: when a team leads, its opponent trails)."""
    t = tm[tm.scope == scope].copy()
    o = tm[tm.scope == FLIP[scope]][["match_id", "team", "poss_secs", "f3_passes"]].rename(
        columns={"team": "opp", "poss_secs": "o_poss", "f3_passes": "o_f3"})
    t = t.merge(o, on=["match_id", "opp"])
    k = pd.DataFrame({"match_id": t.match_id, "team": t.team, "league": t.league, "minutes": t.minutes})
    k["poss"] = t.poss_secs / (t.poss_secs + t.o_poss)
    k["tilt"] = t.f3_passes / (t.f3_passes + t.o_f3)
    k["ppp"] = t.op_passes / t.possessions
    k["tempo"] = t.op_passes / (t.poss_secs / 60)
    k["long"] = t.long_op / t.op_passes
    k["ppda"] = t.opp_passes_ppda / t.def_act_ppda.replace(0, np.nan)
    k["press_h"] = t.press_x_sum / t.pressures
    k["cp"] = 90 * t.counterpress / t.minutes
    k["line"] = t.def_x_sum / t.def_x_n
    k["regain"] = 90 * t.high_regains / t.minutes
    k["width"] = t.wide_f3 / t.f3_passes
    k["cross"] = t.crosses_box / t.box_pass_att
    k["counter"] = t.counter_shots / t.np_shots.replace(0, np.nan)
    k["xg_shot"] = t.npxg / t.np_shots.replace(0, np.nan)
    k["sp"] = t.sp_npxg / t.npxg.replace(0, np.nan)
    return k


def order_matches(k, mm):
    k = k.merge(mm[["match_id", "date"]], on="match_id").sort_values(["league", "team", "date", "match_id"])
    k["k"] = k.groupby(["league", "team"]).cumcount()
    k["n"] = k.groupby(["league", "team"])["match_id"].transform("count")
    return k


mm, ma, sh, tm = team_tables(MENF)
k_all = order_matches(kpis(tm), mm)
N = {"teams": int(k_all.groupby(["league", "team"]).ngroups), "matches": int(k_all.match_id.nunique()),
     "kpis": {c: dict(label=v[0], dim=v[1], higher=v[2]) for c, v in KPIS.items()}}


def split_half(frame, col, splits=200):
    rs = []
    for _ in range(splits):
        h = []
        for (lg, tm_), g in frame.groupby(["league", "team"]):
            v = g[col].dropna().to_numpy()
            if len(v) < 10:
                continue
            idx = rng.permutation(len(v))
            m = len(v) // 2
            h.append((lg, v[idx[:m]].mean(), v[idx[m:2 * m]].mean()))
        h = pd.DataFrame(h, columns=["lg", "a", "b"])
        rs.append(np.corrcoef(h.a, h.b)[0, 1])
    return float(np.mean(rs))


def icc1(frame, col):
    """Share of match-to-match variation that is between teams (one-way random effects ICC)."""
    g = frame.dropna(subset=[col]).groupby(["league", "team"])[col]
    n0 = g.size().mean()
    msb = (g.size() * (g.mean() - frame[col].mean()) ** 2).sum() / (g.ngroups - 1)
    msw = ((frame[col] - g.transform("mean")) ** 2).sum() / (len(frame.dropna(subset=[col])) - g.ngroups)
    return float((msb - msw) / (msb + (n0 - 1) * msw))


def m_needed(r, half_n, target=0.8):
    return half_n * target * (1 - r) / (r * (1 - target))


half_n = 19
rel = {}
first = k_all[k_all.k < k_all.n / 2].groupby(["league", "team"])[list(KPIS)].mean()
second = k_all[k_all.k >= k_all.n / 2].groupby(["league", "team"])[list(KPIS)].mean()
for c in KPIS:
    r = split_half(k_all, c)
    rel[c] = dict(r_half=r, icc=icc1(k_all, c), m80=m_needed(r, half_n), season=38 / half_n * r / (1 + (38 / half_n - 1) * r),
                  test_retest=float(np.corrcoef(first[c], second[c])[0, 1]))
N["reliability"] = rel

# construct validity: within-team shift from leading to trailing (known-groups)
kl = kpis(tm, "lead").assign(state="lead")
kt = kpis(tm, "trail").assign(state="trail")
kv = kpis(tm, "level").assign(state="level")
st = pd.concat([kl, kt, kv])
st = st[st.minutes >= 10]
w = st.groupby(["league", "team", "state"])[list(KPIS)].mean().unstack("state")
shift = {}
for c in ("poss", "tilt", "ppda", "press_h", "line"):
    d = (w[(c, "trail")] - w[(c, "lead")]).dropna()
    sd_between = k_all.groupby(["league", "team"])[c].mean().std()
    shift[c] = dict(lead=float(w[(c, "lead")].mean()), level=float(w[(c, "level")].mean()), trail=float(w[(c, "trail")].mean()),
                    diff=float(d.mean()), share_teams_same_direction=float((np.sign(d) == np.sign(d.mean())).mean()),
                    effect_in_team_sd=float(d.mean() / sd_between))
N["game_state"] = shift

# structure: principal components of season-level KPIs (standardised within league)
season = k_all.groupby(["league", "team"])[list(KPIS)].mean()
Z = (season - season.groupby("league").transform("mean")) / season.std()
Z = Z.dropna(axis=1)
U, S, Vt = np.linalg.svd(Z.to_numpy() - Z.to_numpy().mean(0), full_matrices=False)
ev = S ** 2 / (S ** 2).sum()
load = pd.DataFrame(Vt[:4].T, index=Z.columns, columns=["PC1", "PC2", "PC3", "PC4"])
# orient: PC1 positive = more possession, PC2 positive = higher press
if load.loc["poss", "PC1"] < 0:
    load["PC1"] *= -1
if load.loc["press_h", "PC2"] < 0:
    load["PC2"] *= -1
scores = pd.DataFrame(Z.to_numpy() @ load.to_numpy(), index=Z.index, columns=load.columns)
N["pca"] = dict(var_explained=[float(v) for v in ev[:5]], loadings=load.round(3).to_dict(),
                n_eigen_over_1=int((S ** 2 / (len(Z) - 1) > 1).sum()))

# style twins: nearest teams in the full standardised KPI space (across leagues, raw standardisation)
Zr = (season - season.mean()) / season.std()


def twins(team, n=4):
    v = Zr.loc[[i for i in Zr.index if i[1] == team][0]]
    d = np.sqrt(((Zr - v) ** 2).sum(axis=1)).drop(v.name).sort_values()
    return [dict(team=t, league=MEN[l], distance=float(dd)) for (l, t), dd in d.head(n).items()]


N["twins"] = {t: twins(t) for t in ("Tottenham Hotspur", "Leicester City", "Barcelona", "Juventus", "Aston Villa")}
N["season_kpis"] = season.reset_index().assign(league=lambda d: d.league.map(MEN)).round(4).to_dict("records")

# responsiveness: does the style profile shift more after a change of head coach than in matched windows?
try:
    import json
    ch = json.load(open("output/coaches.json"))["changes"]
    K = 6
    rel_w = np.array([rel[c]["r_half"] for c in Zr.columns])
    sdv = k_all.groupby(["league", "team"])[list(KPIS)].mean().std()

    FAST = [c for c in KPIS if rel[c]["m80"] <= 12]   # KPIs reliable within about 6 matches a side

    def style_shift(lg, team, k0, cols=None):
        cols = cols or list(KPIS)
        g = k_all[(k_all.league == lg) & (k_all.team == team)]
        pre, post = g[(g.k >= k0 - K) & (g.k < k0)], g[(g.k >= k0) & (g.k < k0 + K)]
        if len(pre) < K or len(post) < K:
            return np.nan
        d = ((post[cols].mean() - pre[cols].mean()) / sdv[cols])
        return float(np.sqrt((d ** 2).mean()))

    inv = {v: k for k, v in MEN.items()}
    treated = []
    for c in ch:
        lg = inv[c["league"]]
        g = k_all[(k_all.league == lg) & (k_all.team == c["team"])]
        k0 = int(g[g.date >= c["date"]].k.min())
        treated.append((lg, c["team"], k0, style_shift(lg, c["team"], k0), style_shift(lg, c["team"], k0, FAST)))
    tset = {(a, b) for a, b, _, _, _ in treated}
    ctrl, ctrl_f = [], []
    for (lg, team), g in k_all.groupby(["league", "team"]):
        if (lg, team) in tset:
            continue
        for k0 in range(K, int(g.n.iloc[0]) - K + 1, 3):
            ctrl.append(style_shift(lg, team, k0)); ctrl_f.append(style_shift(lg, team, k0, FAST))
    N["responsiveness"] = {}
    for key, ti, cl in (("all_kpis", 3, ctrl), ("fast_kpis", 4, ctrl_f)):
        tv = np.array([t[ti] for t in treated if not np.isnan(t[ti])]); cv = np.array([c for c in cl if not np.isnan(c)])
        bt = [rng.choice(tv, len(tv)).mean() / rng.choice(cv, len(cv)).mean() for _ in range(4000)]
        N["responsiveness"][key] = dict(changes=int(len(tv)), control_windows=int(len(cv)), shift_changed=float(tv.mean()),
                                        shift_control=float(cv.mean()), ratio=float(tv.mean() / cv.mean()),
                                        ratio_lo=float(np.percentile(bt, 2.5)), ratio_hi=float(np.percentile(bt, 97.5)),
                                        share_above_control_median=float((tv > np.median(cv)).mean()))
    N["responsiveness"]["fast_kpis_list"] = [KPIS[c][0] for c in FAST]
except FileNotFoundError:
    print("run project8_coaches.py first for the responsiveness check")

# the women's game: same KPIs, reliability and season-to-season stability
try:
    wf = list(WSL_SEASONS)
    mmw, maw, shw, tmw = team_tables(wf)
    kw = order_matches(kpis(tmw), mmw)
    hw = int(kw.groupby(["league", "team"]).size().min() // 2)
    relw = {c: split_half(kw, c, 100) for c in KPIS}
    sw = kw.groupby(["league", "team"])[list(KPIS)].mean().reset_index()
    pairs = [("wsl_2018_19", "wsl_2019_20"), ("wsl_2019_20", "wsl_2020_21")]
    tr_ = {}
    for c in KPIS:
        a_, b_ = [], []
        for s1, s2 in pairs:
            m_ = sw[sw.league == s1].merge(sw[sw.league == s2], on="team")
            a_ += list(m_[f"{c}_x"]); b_ += list(m_[f"{c}_y"])
        tr_[c] = float(np.corrcoef(a_, b_)[0, 1])
    N["women"] = dict(team_seasons=int(len(sw)), seasons=[WSL_SEASONS[f] for f in wf], half_matches=hw,
                      rel={c: dict(r_half=relw[c], m80=m_needed(relw[c], hw)) for c in KPIS},
                      season_to_season=tr_, pairs=int(len(a_)))
except (FileNotFoundError, ValueError) as e:
    print("women's check skipped:", e)

for c, v in rel.items():
    print(f"  {KPIS[c][0]:48s} ICC {v['icc']:.2f}  r_half {v['r_half']:.2f}  m80 {v['m80']:.1f}  test-retest {v['test_retest']:.2f}")
print(N["game_state"]); print(N["pca"]["var_explained"]); print(load.round(2)); print(N["twins"]); print(N.get("responsiveness"))
if "women" in N:
    print({c: round(v["m80"], 1) for c, v in N["women"]["rel"].items()}, N["women"]["season_to_season"])

# ------------------------------------------------------------------ charts
fig, ax = plt.subplots(figsize=(WIDTH, 3.4))
order = sorted(KPIS, key=lambda c: rel[c]["m80"])
for i, c in enumerate(order):
    m80 = rel[c]["m80"]
    colr = GREEN if m80 <= 12 else (AMBER if m80 <= 38 else PURPLE)
    ax.barh(i, min(m80, 60), color=colr, height=0.62)
    ax.text(min(m80, 60) + 0.8, i, f"{m80:.0f}" if m80 < 60 else f"{m80:.0f} (off scale)", va="center", fontsize=7)
ax.axvline(38, color=MUTED, ls=":", lw=0.8)
ax.text(38.6, len(order) - 0.6, "one season", fontsize=7, color=MUTED)
ax.set_yticks(range(len(order))); ax.set_yticklabels([KPIS[c][0] for c in order], fontsize=7.2)
ax.set_xlim(0, 66); ax.set_xlabel("Matches before the KPI measures the team (reliability 0.8)")
save(fig, "c9_reliability")

# composite scores for the map: control (with the ball) and pressing (without it), z-scored within league
CONTROL = {"poss": 1, "tilt": 1, "ppp": 1, "long": -1}
PRESS = {"ppda": -1, "press_h": 1, "line": 1, "cp": 1}
zs = (season - season.groupby("league").transform("mean")) / season.groupby("league").transform("std")
comp = pd.DataFrame({"control": sum(s_ * zs[c] for c, s_ in CONTROL.items()) / len(CONTROL),
                     "press": sum(s_ * zs[c] for c, s_ in PRESS.items()) / len(PRESS)})
b1, b0 = np.polyfit(comp.control, comp.press, 1)
comp["press_resid"] = comp.press - (b0 + b1 * comp.control)
N["composite"] = dict(r_control_press=float(np.corrcoef(comp.control, comp.press)[0, 1]), slope=float(b1),
                      most_press_for_control=[dict(team=t, league=MEN[l], resid=float(v)) for (l, t), v in comp.press_resid.sort_values().tail(6)[::-1].items()],
                      least_press_for_control=[dict(team=t, league=MEN[l], resid=float(v)) for (l, t), v in comp.press_resid.sort_values().head(6).items()],
                      scores=[dict(team=t, league=MEN[l], control=float(r.control), press=float(r.press)) for (l, t), r in comp.iterrows()])
write_numbers("game_model", N)
print(N["composite"]["r_control_press"], N["composite"]["most_press_for_control"], N["composite"]["least_press_for_control"])
print(N["responsiveness"])

fig, ax = plt.subplots(figsize=(WIDTH, 3.6))
LGC = {"epl_2015_16": GREEN, "laliga_2015_16": PURPLE, "seriea_2015_16": AMBER, "ligue1_2015_16": "#2f6f9f"}
xx = np.linspace(comp.control.min() - 0.2, comp.control.max() + 0.2, 10)
ax.plot(xx, b0 + b1 * xx, color=GREY, lw=0.8, ls="--")
for lg, g in comp.groupby(level=0):
    ax.scatter(g.control, g.press, s=20, color=LGC[lg], lw=0, alpha=0.9, label=MEN[lg])
show = set(t for t, *_ in [(d["team"],) for d in N["composite"]["most_press_for_control"][:4] + N["composite"]["least_press_for_control"][:4]])
show = set(d["team"] for d in N["composite"]["most_press_for_control"][:5] + N["composite"]["least_press_for_control"][:4])
show |= {"Barcelona", "Leicester City", "Juventus", "Paris Saint-Germain"}
lab = comp[[t in show for _, t in comp.index]]
place_labels(ax, lab.control.values, lab.press.values, [t for _, t in lab.index], fontsize=6.4)
ax.set_xlabel("Control with the ball: possession, territory, patient build-up (z)")
ax.set_ylabel("Pressing without it: intensity and height (z)")
ax.legend(loc="lower right", fontsize=6.8, ncol=2)
save(fig, "c9_style_map")

fig, ax = plt.subplots(figsize=(WIDTH, 2.4))
labs = {"poss": "Possession share", "tilt": "Field tilt", "press_h": "Pressure height (yards)", "line": "Defenders' action height (yards)"}
for i, c in enumerate(["poss", "tilt", "press_h", "line"]):
    v = N["game_state"][c]
    sc = 100 if c in ("poss", "tilt") else 1
    ax.plot([v["lead"] * sc, v["trail"] * sc], [i, i], color=LIGHT, lw=6, solid_capstyle="round", zorder=1)
    ax.scatter([v["lead"] * sc], [i], color=PURPLE, s=40, zorder=3, label="Leading" if i == 0 else None)
    ax.scatter([v["level"] * sc], [i], color=GREY, s=30, zorder=3, label="Level" if i == 0 else None)
    ax.scatter([v["trail"] * sc], [i], color=GREEN, s=40, zorder=3, label="Trailing" if i == 0 else None)
ax.set_yticks(range(4)); ax.set_yticklabels([labs[c] for c in ["poss", "tilt", "press_h", "line"]], fontsize=7.4)
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), fontsize=7, ncol=3)
ax.set_ylim(-0.5, 3.5)
ax.set_xlabel("Average across 80 teams (share in %, height in yards from own goal)")
save(fig, "c9_game_state")
