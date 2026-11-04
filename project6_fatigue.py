"""Project 6. A physiological signal in event data: do players press less as a match goes on?

Why        Clubs have GPS and heart-rate data for their own players only. For opponents and recruitment
           targets, event data is often all there is. Pressing (StatsBomb 'Pressure': a player closing
           down the ball carrier) is a repeated high-intensity action, so its rate should fall with fatigue.
Problem    Pressing also changes with tactics and the score (teams that lead sit deeper), so a simple
           'pressing falls late in matches' curve mixes fatigue with game state.
Design     Natural comparison inside the same minutes of the same match: fresh substitutes against players
           who started, in the same 15-minute period. Mantel-Haenszel rate ratio stratified by
           player x period x score state, so each player is compared only with himself in the same context.
Outcome    Pressures per minute on the pitch (Poisson rates with exposure in minutes).
"""
import numpy as np
import pandas as pd
from common import (MEN, available, load_many, plt, save, write_numbers, GREEN, PURPLE, AMBER, GREY, LIGHT, INK,
                    MUTED, WIDTH)

LEAGUES = available(MEN)
bins = load_many(LEAGUES, "player_bins")
pm = load_many(LEAGUES, "player_match")
matches = load_many(LEAGUES, "matches")
matches = matches[matches["has_events"] == 1]
goals = load_many(LEAGUES, "goals")
BINS = ["0-15", "15-30", "30-45+", "45-60", "60-75", "75-90+"]
N = {"leagues": [MEN[l] for l in LEAGUES]}

bins = bins.merge(pm[["match_id", "player_id", "position_group", "off", "exit", "match_length"]],
                  on=["match_id", "player_id"])
bins = bins[bins["position_group"] != "GK"].copy()
bins = bins.merge(matches[["match_id", "first_half"]], on="match_id")
bin_idx = bins["bin"].map({b: i for i, b in enumerate(BINS)}).to_numpy()
L1 = bins["first_half"].to_numpy()
starts = np.select([bin_idx == i for i in range(6)], [0, 15, 30, L1, L1 + 15, L1 + 30])
ends = np.select([bin_idx == i for i in range(6)], [15, 30, L1, L1 + 15, L1 + 30, bins["match_length"]])
bins["bin_start"], bins["bin_end"], bins["bin_i"] = starts, ends, bin_idx

# score state for the player's team at the start of each period
g = goals.sort_values("el")
gd = []
for (mid, team, t0) in zip(bins["match_id"], bins["team"], bins["bin_start"]):
    gd.append(None)
goal_lists = {mid: d[["team", "el"]].to_numpy() for mid, d in g.groupby("match_id")}
state = []
for mid, team, t0 in zip(bins["match_id"], bins["team"], bins["bin_start"]):
    arr = goal_lists.get(mid)
    if arr is None:
        state.append(0); continue
    before = arr[arr[:, 1].astype(float) < t0]
    diff = int((before[:, 0] == team).sum() - (before[:, 0] != team).sum())
    state.append(int(np.sign(diff)))
bins["state"] = state

# who is 'fresh'? substitutes who were already on at the start of the period; starters still on.
bins["full_period"] = bins["exposure"] >= (bins["bin_end"] - bins["bin_start"]) - 0.5
bins["role"] = np.where(bins["started"] == 1, "starter", np.where(bins["on"] <= bins["bin_start"] + 0.01, "sub", "sub_entered"))

# ------------------------------------------------------------------ descriptive curve (crude)
crude = (bins[bins["role"] != "sub_entered"].groupby(["bin", "role"])[["pressures", "exposure"]].sum().reset_index())
crude["per90"] = 90 * crude["pressures"] / crude["exposure"]
N["crude"] = crude.to_dict(orient="records")


# ------------------------------------------------------------------ Mantel-Haenszel rate ratio
RNG = np.random.default_rng(2015)
N_BOOT = 1000


def mh_rate_ratio(d, strata):
    """Rate ratio substitutes vs starters, stratified (Mantel-Haenszel).
    95% interval from a cluster bootstrap over players (1,000 resamples), because pressures are over-dispersed
    and a player's matches are not independent; the Greenland-Robins (Poisson) interval is kept for reference."""
    keys = list(dict.fromkeys(["player_id"] + strata))
    s = d[d["role"] == "sub"].groupby(keys)[["pressures", "exposure"]].sum()
    t = d[d["role"] == "starter"].groupby(keys)[["pressures", "exposure"]].sum()
    if "player_id" in strata:
        j = s.join(t, lsuffix="_1", rsuffix="_0", how="inner")
        j = j[(j["exposure_1"] > 0) & (j["exposure_0"] > 0)]
    else:   # strata pooled over players: keep each player's contribution to every stratum
        j = s.join(t, lsuffix="_1", rsuffix="_0", how="outer").fillna(0)
    a, T1, b, T0 = (j[c].to_numpy(float) for c in ("pressures_1", "exposure_1", "pressures_0", "exposure_0"))
    player = j.index.get_level_values("player_id").to_numpy()
    other = [k for k in strata if k != "player_id"]
    stratum = (j.reset_index()[other].astype(str).agg("|".join, axis=1).to_numpy() if other
               else np.zeros(len(j), dtype=int).astype(str))
    players, p_idx = np.unique(player, return_inverse=True)

    def mh(w_rows):
        if "player_id" in strata:
            A1, B1, A0, B0 = a * w_rows, T1 * w_rows, b * w_rows, T0 * w_rows
            T = T1 + T0
            num, den = (A1 * T0 / T).sum(), (A0 * T1 / T).sum()
            return num, den, None
        df = pd.DataFrame(dict(st=stratum, a=a * w_rows, T1=T1 * w_rows, b=b * w_rows, T0=T0 * w_rows)).groupby("st").sum()
        df = df[(df["T1"] > 0) & (df["T0"] > 0)]
        T = df["T1"] + df["T0"]
        return (df["a"] * df["T0"] / T).sum(), (df["b"] * df["T1"] / T).sum(), df

    num, den, agg = mh(np.ones(len(a)))
    rr = num / den
    if "player_id" in strata:
        Tt = T1 + T0
        var = ((a + b) * T1 * T0 / Tt ** 2).sum() / (num * den)
        n_strata, sm, tm, sp, tp = len(j), T1.sum(), T0.sum(), a.sum(), b.sum()
    else:
        Tt = agg["T1"] + agg["T0"]
        var = ((agg["a"] + agg["b"]) * agg["T1"] * agg["T0"] / Tt ** 2).sum() / (num * den)
        n_strata, sm, tm, sp, tp = len(agg), agg["T1"].sum(), agg["T0"].sum(), agg["a"].sum(), agg["b"].sum()
    se = np.sqrt(var)
    boots = []
    for _ in range(N_BOOT):
        w_player = np.bincount(RNG.integers(0, len(players), len(players)), minlength=len(players))
        n_, d_, _ = mh(w_player[p_idx].astype(float))
        boots.append(n_ / d_)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return dict(rr=float(rr), lo=float(lo), hi=float(hi),
                lo_poisson=float(rr * np.exp(-1.96 * se)), hi_poisson=float(rr * np.exp(1.96 * se)),
                strata=int(n_strata), players=int(len(players)),
                sub_minutes=float(sm), starter_minutes=float(tm), sub_pressures=int(sp), starter_pressures=int(tp))


late = bins[bins["bin"].isin(["60-75", "75-90+"]) & bins["role"].isin(["sub", "starter"])]
N["mh_late"] = mh_rate_ratio(late, ["player_id", "bin", "state"])
N["mh_by_bin"] = {b: mh_rate_ratio(bins[(bins["bin"] == b) & bins["role"].isin(["sub", "starter"])],
                                   ["player_id", "state"]) for b in ["45-60", "60-75", "75-90+"]}
N["mh_by_position"] = {p: mh_rate_ratio(late[late["position_group"] == p], ["player_id", "bin", "state"])
                       for p in ["DEF", "MID", "FWD"]}
# same comparison ignoring player identity and score: shows why the design matters
N["crude_late"] = mh_rate_ratio(late.assign(one=1), ["one"])
N["mh_late_player_only"] = mh_rate_ratio(late, ["player_id"])

# ------------------------------------------------------------------ within-player decline for players who played 90
full = bins[(bins["started"] == 1) & (bins["exit"] == "Final Whistle")]
dec = {}
for b in BINS:
    d = full[full["bin"].isin(["0-15", b])].copy()
    d["role"] = np.where(d["bin"] == b, "sub", "starter")        # reuse: 'sub' = later period, 'starter' = 0-15
    dec[b] = mh_rate_ratio(d, ["player_id", "match_id"]) if b != "0-15" else dict(rr=1.0, lo=1.0, hi=1.0)
N["within_match_decline"] = dec

write_numbers("fatigue", N)
print(crude.round(2).to_string())
for k in ("mh_late", "crude_late", "mh_late_player_only"):
    print(k, {x: round(v, 3) if isinstance(v, float) else v for x, v in N[k].items()})
for b, v in N["mh_by_bin"].items():
    print(b, round(v["rr"], 3), round(v["lo"], 3), round(v["hi"], 3), v["players"])
for b, v in N["mh_by_position"].items():
    print(b, round(v["rr"], 3), round(v["lo"], 3), round(v["hi"], 3), v["players"])
for b, v in dec.items():
    print("decline", b, round(v["rr"], 3), round(v["lo"], 3), round(v["hi"], 3))

# ------------------------------------------------------------------ chart
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(WIDTH, 2.6), gridspec_kw=dict(width_ratios=[1.15, 1], wspace=0.55))
x = np.arange(6)
st = crude[crude["role"] == "starter"].set_index("bin").reindex(BINS)
sb = crude[crude["role"] == "sub"].set_index("bin").reindex(BINS)
ax1.plot(x, st["per90"], color=PURPLE, lw=2, marker="o", ms=4)
ax1.plot(x[3:], sb["per90"].iloc[3:], color=GREEN, lw=2, marker="o", ms=4)
ax1.text(5.1, st["per90"].iloc[-1], "Started", color=INK, fontsize=7.4, va="center")
ax1.text(5.1, sb["per90"].iloc[-1], "Came on\nas a sub", color=INK, fontsize=7.4, va="center")
ax1.set_xticks(x); ax1.set_xticklabels([f"{b}'" for b in BINS], fontsize=6.8, rotation=35, ha="right", rotation_mode="anchor")
ax1.set_xlim(-0.3, 6.1)
ax1.set_ylabel("Pressures per 90 minutes")
ax1.set_ylim(10, 19)
ax1.set_title("Raw pressing rate by period", fontsize=9)
rows = [("45-60' (all outfield)", N["mh_by_bin"]["45-60"], True), ("60-75'", N["mh_by_bin"]["60-75"], True),
        ("75-90+'", N["mh_by_bin"]["75-90+"], True), ("Defenders, 60-90+'", N["mh_by_position"]["DEF"], False),
        ("Midfielders, 60-90+'", N["mh_by_position"]["MID"], False), ("Forwards, 60-90+'", N["mh_by_position"]["FWD"], False)]
for i, (lab, v, main) in enumerate(rows[::-1]):
    ax2.plot([v["lo"], v["hi"]], [i, i], color=GREEN if main else GREY, lw=2.2)
    ax2.plot(v["rr"], i, "o", color=GREEN if main else INK, ms=4.5)
    ax2.text(v["hi"] + 0.012, i, f"{v['rr']:.2f}", va="center", fontsize=7.2)
ax2.axhline(2.5, color=LIGHT, lw=0.8)
ax2.axvline(1, color=MUTED, lw=0.8, ls="--")
ax2.set_yticks(range(len(rows))); ax2.set_yticklabels([r[0] for r in rows[::-1]], fontsize=7.2)
ax2.set_xlim(0.95, 1.3)
ax2.set_xlabel("Rate ratio: fresh substitute vs starter\n(same player, same period, same score state)")
ax2.set_title("Fair comparison (Mantel–Haenszel)", fontsize=9)
save(fig, "fatigue")
