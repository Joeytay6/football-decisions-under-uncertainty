"""Project 5. What public event data can tell you about match injuries in men's elite football.

Design      Retrospective cohort, every player appearance in four complete men's league seasons (2015/16).
Case        A substitution that StatsBomb records as caused by injury ("injury withdrawal").
Exposure    Minutes on the pitch from lineup on/off times (period-aware, stoppage time included).
Key bias    In 2015/16 a team could make three substitutions. Once all three were used, an injured player
            could not be withdrawn, so the injury cannot appear in the data. Rates are therefore also
            computed using only exposure while the player's team still had a substitution left.
Outcome 2   Return to the matchday squad after an injury withdrawal, compared with players taken off
            for tactical reasons (same leagues, same season) to remove ordinary rotation.
Comparison  UEFA Elite Club Injury Study (Ekstrand et al 2011): time-loss match injury incidence 27.5/1000 h.
            Argibay-Gonzalez et al 2022: 135 (Premier League) and 142 (La Liga) injury withdrawals in 2018/19.
"""
import numpy as np
import pandas as pd
from scipy import stats
from common import (MEN, available, load_many, poisson_rate_ci, rate_ratio_ci, kaplan_meier, km_at, poisson_glm,
                    plt, save, write_numbers, GREEN, PURPLE, AMBER, GREY, LIGHT, INK, MUTED, REF, WIDTH)

LEAGUES = available(MEN)
pm = load_many(LEAGUES, "player_match")
matches = load_many(LEAGUES, "matches")
matches = matches[matches["has_events"] == 1]
inj = load_many(LEAGUES, "injury_subs")
subs = load_many(LEAGUES, "subs")
squads = load_many(LEAGUES, "squads")
stoppages = load_many(LEAGUES, "stoppages")
N = {"leagues": [MEN[l] for l in LEAGUES], "matches": int(len(matches)),
     "appearances": int(len(pm)), "players": int(pm["player_id"].nunique()),
     "player_hours": float(pm["minutes"].sum() / 60), "injury_withdrawals": int(len(inj))}
UEFA_MATCH_INCIDENCE = 27.5        # Ekstrand, Hagglund & Walden 2011, BJSM 45:553-558

# ------------------------------------------------------------------ 1. incidence by league
rows = []
for lg in LEAGUES:
    k = int((inj["league"] == lg).sum())
    h = pm.loc[pm["league"] == lg, "minutes"].sum() / 60
    r, lo, hi = poisson_rate_ci(k, h)
    rows.append(dict(league=MEN[lg], withdrawals=k, matches=int((matches["league"] == lg).sum()),
                     player_hours=h, rate=r, lo=lo, hi=hi, per_team_season=k / 20))
k, h = len(inj), pm["minutes"].sum() / 60
r, lo, hi = poisson_rate_ci(k, h)
rows.append(dict(league="All four leagues", withdrawals=k, matches=len(matches), player_hours=h, rate=r, lo=lo,
                 hi=hi, per_team_season=k / (20 * len(LEAGUES))))
by_league = pd.DataFrame(rows)
N["by_league"] = by_league.to_dict(orient="records")
N["overall_rate"] = dict(rate=r, lo=lo, hi=hi)
N["share_of_uefa_time_loss"] = r / UEFA_MATCH_INCIDENCE
N["withdrawals_per_match"] = k / len(matches)

# ------------------------------------------------------------------ 2. when do teams run out of substitutions?
subs = subs.sort_values(["league", "match_id", "team", "el"])
subs["n"] = subs.groupby(["match_id", "team"]).cumcount() + 1
third = subs[subs["n"] == 3].set_index(["match_id", "team"])["el"]
team_matches = pm[["league", "match_id", "team"]].drop_duplicates()
team_matches["t3"] = [third.get((m, t), np.inf) for m, t in zip(team_matches["match_id"], team_matches["team"])]
team_matches = team_matches.merge(matches[["match_id", "first_half", "second_half"]], on="match_id")
team_matches["len"] = team_matches["first_half"] + team_matches["second_half"]
used3 = np.isfinite(team_matches["t3"])
# convert elapsed time of the third substitution back to the match clock (second half restarts at 45)
t3_clock = np.where(team_matches["t3"] > team_matches["first_half"],
                    45 + team_matches["t3"] - team_matches["first_half"], team_matches["t3"])
N["subs"] = dict(share_all_three_used=float(used3.mean()),
                 median_third_sub_clock=float(np.median(t3_clock[used3])),
                 share_with_none_left_by_80=float(((t3_clock <= 80) & used3).mean()),
                 share_with_none_left_by_85=float(((t3_clock <= 85) & used3).mean()))
# order of the injury substitution among the team's substitutions
inj = inj.merge(subs[["match_id", "team", "player_id", "el", "n"]], on=["match_id", "team", "player_id", "el"],
                how="left")
N["injury_sub_order"] = inj["n"].value_counts().sort_index().to_dict()

# ------------------------------------------------------------------ 3. timing: crude vs 'observable' exposure
pmx = pm.merge(team_matches[["match_id", "team", "t3", "first_half", "len"]], on=["match_id", "team"])
L1 = pmx["first_half"].to_numpy()
edges = np.column_stack([np.zeros(len(pmx)), np.full(len(pmx), 15.0), np.full(len(pmx), 30.0), L1, L1 + 15, L1 + 30,
                         pmx["len"].to_numpy()])
on, off = pmx["on"].to_numpy(), pmx["off"].to_numpy()
off_obs = np.minimum(off, pmx["t3"].to_numpy())
BINS = ["0-15", "15-30", "30-45+", "45-60", "60-75", "75-90+"]
expo_all = np.zeros(6); expo_obs = np.zeros(6)
for i in range(6):
    a, b = edges[:, i], edges[:, i + 1]
    expo_all[i] = np.clip(np.minimum(off, b) - np.maximum(on, a), 0, None).sum() / 60
    expo_obs[i] = np.clip(np.minimum(off_obs, b) - np.maximum(on, a), 0, None).sum() / 60
inj = inj.merge(matches[["match_id", "first_half"]], on="match_id")
c1 = inj["clock"].to_numpy()
# A withdrawal made at half-time (second-half clock 45:00) is an injury from the first half: it goes in 30-45+.
half_time = (inj["period"].to_numpy() == 2) & (c1 <= 45.05)
inj["bin"] = np.where((inj["period"] == 1) | half_time, np.where(c1 < 15, 0, np.where(c1 < 30, 1, 2)),
                      np.where(c1 < 60, 3, np.where(c1 < 75, 4, 5)))
inj.loc[half_time, "bin"] = 2
N["half_time_withdrawals"] = int(half_time.sum())
counts = inj["bin"].value_counts().reindex(range(6), fill_value=0).to_numpy()
timing = pd.DataFrame({"bin": BINS, "withdrawals": counts, "hours_all": expo_all, "hours_observable": expo_obs})
timing["rate_crude"] = 1000 * timing["withdrawals"] / timing["hours_all"]
timing["rate_observable"] = 1000 * timing["withdrawals"] / timing["hours_observable"]
ci = [poisson_rate_ci(k_, h_) for k_, h_ in zip(timing["withdrawals"], timing["hours_observable"])]
timing["obs_lo"] = [c[1] for c in ci]; timing["obs_hi"] = [c[2] for c in ci]
ci = [poisson_rate_ci(k_, h_) for k_, h_ in zip(timing["withdrawals"], timing["hours_all"])]
timing["crude_lo"] = [c[1] for c in ci]; timing["crude_hi"] = [c[2] for c in ci]
N["timing"] = timing.to_dict(orient="records")
N["share_of_exposure_unobservable_75_90"] = float(1 - expo_obs[5] / expo_all[5])

# Poisson regression: trend across the three bins within each half (observable exposure)
X = np.column_stack([np.ones(6), [0, 0, 0, 1, 1, 1], [0, 1, 2, 0, 1, 2]])
fit_obs = poisson_glm(timing["withdrawals"], X, np.log(timing["hours_observable"]), ["const", "second_half", "within"])
fit_all = poisson_glm(timing["withdrawals"], X, np.log(timing["hours_all"]), ["const", "second_half", "within"])
N["trend"] = dict(rr_per_15min_within_half=fit_obs["within"]["rr"], lo=fit_obs["within"]["lo"], hi=fit_obs["within"]["hi"],
                  p=fit_obs["within"]["p"], rr_second_half=fit_obs["second_half"]["rr"], p_half=fit_obs["second_half"]["p"])
N["trend_crude"] = dict(rr_per_15min_within_half=fit_all["within"]["rr"], lo=fit_all["within"]["lo"],
                        hi=fit_all["within"]["hi"], p=fit_all["within"]["p"])

# ------------------------------------------------------------------ 4. position and starters vs substitutes
pmx["obs_minutes"] = np.clip(off_obs - on, 0, None)
pos_rows = []
inj_pos = inj.merge(pm[["match_id", "player_id", "position_group"]], on=["match_id", "player_id"], how="left")
for g in ["GK", "DEF", "MID", "FWD"]:
    k_ = int((inj_pos["position_group"] == g).sum())
    h_ = pmx.loc[pmx["position_group"] == g, "obs_minutes"].sum() / 60
    r_, lo_, hi_ = poisson_rate_ci(k_, h_)
    pos_rows.append(dict(group=g, withdrawals=k_, hours=h_, rate=r_, lo=lo_, hi=hi_))
pos = pd.DataFrame(pos_rows)
ref = pos.set_index("group").loc["MID"]
for g in ["GK", "DEF", "FWD"]:
    row = pos.set_index("group").loc[g]
    rr_, lo_, hi_ = rate_ratio_ci(row["withdrawals"], row["hours"], ref["withdrawals"], ref["hours"])
    pos.loc[pos["group"] == g, ["rr_vs_mid", "rr_lo", "rr_hi"]] = rr_, lo_, hi_
N["position"] = pos.to_dict(orient="records")
for s_, lab in ((1, "starters"), (0, "substitutes")):
    k_ = int((inj["started"] == s_).sum())
    h_ = pmx.loc[pmx["started"] == s_, "obs_minutes"].sum() / 60
    N[f"rate_{lab}"] = dict(zip(["rate", "lo", "hi"], poisson_rate_ci(k_, h_))) | {"withdrawals": k_, "hours": h_}

# ------------------------------------------------------------------ 5. stoppages that end in a withdrawal
st = stoppages.drop_duplicates(["match_id", "player_id", "el"])
m_ = st.merge(inj[["match_id", "player_id", "el"]].rename(columns={"el": "el_sub"}), on=["match_id", "player_id"], how="left")
m_["followed"] = (m_["el_sub"] >= m_["el"]) & (m_["el_sub"] - m_["el"] <= 15)
followed = m_.groupby(["match_id", "player_id", "el"])["followed"].any()
N["stoppages"] = dict(n=int(len(followed)), per_match=float(len(followed) / len(matches)),
                      share_followed_by_withdrawal=float(followed.mean()))

# ------------------------------------------------------------------ 6. return to the matchday squad
dates = matches.set_index("match_id")["date"]
sq = squads.merge(matches[["match_id", "date"]], on="match_id")
team_fixtures = sq[["league", "team", "match_id", "date"]].drop_duplicates().sort_values(["team", "date", "match_id"])
fixtures = {t: g["match_id"].tolist() for t, g in team_fixtures.groupby("team")}
named = set(zip(sq["match_id"], sq["player_id"]))


# a player who later appears in another club's squad has left: follow-up stops at that point (censored)
sq_dates = sq[["team", "player_id", "date"]].drop_duplicates()
other_club = {}
for pid, g in sq_dates.groupby("player_id"):
    other_club[pid] = list(zip(g["date"], g["team"]))
fixture_date = dict(zip(team_fixtures["match_id"], team_fixtures["date"]))


def matches_until_back(team, match_id, player_id):
    """Team league matches missed from the squad before he is named again.
    Returns (missed, back): back=0 means censored (season ended or he moved club first)."""
    fx = fixtures[team]
    i = fx.index(match_id)
    d0 = fixture_date[match_id]
    moved = min([d for d, t in other_club.get(player_id, []) if t != team and d > d0], default=None)
    missed = 0
    for nxt in fx[i + 1:]:
        if moved is not None and fixture_date[nxt] >= moved:
            return missed, 0
        if (nxt, player_id) in named:
            return missed, 1
        missed += 1
    return missed, 0


cases = inj[["match_id", "team", "player_id"]].copy()
cases["group"] = "injury"
ctrl = pm[(pm["exit"] == "Substitution - Off (Tactical)") & (pm["started"] == 1)][["match_id", "team", "player_id"]].copy()
ctrl["group"] = "tactical"
coh = pd.concat([cases, ctrl], ignore_index=True)
res = [matches_until_back(t, m, p) for t, m, p in zip(coh["team"], coh["match_id"], coh["player_id"])]
coh["missed"] = [r_[0] for r_ in res]; coh["back"] = [r_[1] for r_ in res]
# no follow-up at all (team's last match, or he moved club straight away): excluded
coh = coh[~((coh["missed"] == 0) & (coh["back"] == 0))]
HORIZON = 10
ret = {}
for g, d in coh.groupby("group"):
    km = kaplan_meier(d["missed"].to_numpy(), d["back"].to_numpy())
    # km 'survival' S(t) = P(missed > t) = still out of the squad after t further matches
    S = lambda t: float(km_at(km, t))
    km_curve = [(int(t), S(t)) for t in range(0, 11)]
    ret[g] = dict(n=int(len(d)), absent_next=S(0), absent_next2=S(1), absent_next4=S(3),
                  censored=int((d["back"] == 0).sum()), km=km_curve,
                  restricted_mean_missed=float(sum(S(t) for t in range(HORIZON))),
                  median_missed=float(d["missed"].median()))
N["return"] = ret
N["return"]["horizon"] = HORIZON
a1, n1 = (coh.query("group=='injury'")["missed"] >= 1).sum(), (coh["group"] == "injury").sum()
a0, n0 = (coh.query("group=='tactical'")["missed"] >= 1).sum(), (coh["group"] == "tactical").sum()
rr = (a1 / n1) / (a0 / n0)
se = np.sqrt(1 / a1 - 1 / n1 + 1 / a0 - 1 / n0)
N["return"]["rr_absent_next"] = dict(rr=float(rr), lo=float(rr * np.exp(-1.96 * se)), hi=float(rr * np.exp(1.96 * se)))
excess = ret["injury"]["restricted_mean_missed"] - ret["tactical"]["restricted_mean_missed"]
N["return"]["excess_matches_missed_per_withdrawal"] = float(excess)
N["return"]["excess_matches_per_team_season"] = float(excess * by_league.iloc[-1]["per_team_season"])

write_numbers("injury", N)
print(by_league.round(2).to_string())
print(timing.round(2).to_string())
print(pos.round(2).to_string())
for k_ in ("subs", "injury_sub_order", "trend", "trend_crude", "rate_starters", "rate_substitutes", "stoppages",
           "share_of_uefa_time_loss", "share_of_exposure_unobservable_75_90"):
    print(k_, N[k_])
for g in ("injury", "tactical"):
    print(g, {k_: v for k_, v in N["return"][g].items() if k_ != "km"})
print(N["return"]["rr_absent_next"], excess, N["return"]["excess_matches_per_team_season"])

# ------------------------------------------------------------------ charts
fig, ax = plt.subplots(figsize=(WIDTH, 2.55))
x = np.arange(6)
ax.bar(x - 0.19, timing["rate_crude"], width=0.36, color=GREY, label="All minutes played (crude)")
ax.bar(x + 0.19, timing["rate_observable"], width=0.36, color=GREEN,
       label="Only minutes when the team could still substitute (corrected)")
ax.errorbar(x + 0.19, timing["rate_observable"], yerr=[timing["rate_observable"] - timing["obs_lo"],
            timing["obs_hi"] - timing["rate_observable"]], fmt="none", ecolor=INK, elinewidth=0.7, capsize=2)
for i in range(6):
    ax.text(i + 0.19, timing["obs_hi"].iat[i] + 0.4, f"{timing['rate_observable'].iat[i]:.1f}", ha="center", fontsize=7.2)
    ax.text(i - 0.19, timing["rate_crude"].iat[i] + 0.4, f"{timing['rate_crude'].iat[i]:.1f}", ha="center", fontsize=7.2,
            color=MUTED)
ax.axvline(2.5, color=LIGHT, lw=1)
ax.set_xticks(x); ax.set_xticklabels([f"{b}'" for b in BINS])
ax.set_ylabel("Injury withdrawals\nper 1,000 player-hours")
ax.set_xlabel("Match clock (stoppage time included in the last period of each half)")
ax.set_title("When injury withdrawals happen, before and after correcting for teams with no substitutes left")
ax.legend(loc="upper left", fontsize=7.2)
ax.set_ylim(0, max(timing["obs_hi"]) * 1.3)
save(fig, "inj_timing")

fig, ax = plt.subplots(figsize=(WIDTH, 2.3))
lab_pos = {"injury": (1.15, 64), "tactical": (0.15, 13.5)}
for g, col, lab in (("injury", GREEN, "Withdrawn injured"), ("tactical", PURPLE, "Tactical substitution (comparison)")):
    km = N["return"][g]["km"]
    t_ = [k_ for k_, _ in km]; s_ = [100 * v for _, v in km]
    ax.step(t_, s_, where="post", color=col, lw=2)
    ax.text(*lab_pos[g], f"{lab} (n = {N['return'][g]['n']:,})", color=INK, fontsize=7.4, va="bottom")
ax.set_xlim(0, 10); ax.set_ylim(0, 100)
ax.set_xticks(range(0, 11))
ax.set_xlabel("Team's next league matches")
ax.set_ylabel("Not yet back in the\nmatchday squad (%)")
ax.set_title("Return to the matchday squad after leaving the pitch (Kaplan–Meier)")
save(fig, "inj_return")
