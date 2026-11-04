"""Project 4. Scouting numbers judged the way medicine judges a screening test.

Question   If a recruitment team shortlists attackers on their numbers from the first half of a season,
           how often does the shortlist contain the players who are genuinely the most productive in the
           second half? Which number makes the best screening test?
Design     Diagnostic accuracy study with a chronological split (no player's future is used to build the
           test). Index tests: per-90 numbers from each team's first 19 league matches. Reference standard:
           top fifth of the league for non-penalty goals + assists per 90 in the team's last 19 matches.
Population Attacking players (at least half their minutes as forward, winger, attacking or wide midfielder)
           with >= 900 minutes in both halves of the season.
Measures   AUC (chance a true top-fifth player outranks one who is not), sensitivity, specificity, PPV,
           positive likelihood ratio, and shortlist size needed per true top-fifth player found (1/PPV).
           95% intervals by bootstrap (2,000 resamples of players). Reported in line with STARD where it applies.
"""
import numpy as np
import pandas as pd
from common import (MEN, available, load_many, plt, save, write_numbers, GREEN, PURPLE, AMBER, GREY, LIGHT,
                    INK, MUTED, WIDTH)

LEAGUES = available(MEN)
pm = load_many(LEAGUES, "player_match")
matches = load_many(LEAGUES, "matches")
MIN_MINUTES, TOP_SHARE, B, SEED = 900, 0.20, 2000, 2026
N = {"leagues": [MEN[l] for l in LEAGUES], "min_minutes": MIN_MINUTES, "top_share": TOP_SHARE}

# chronological split within each team's fixture list
pm = pm.merge(matches[["match_id", "date"]], on="match_id")
order = pm[["league", "team", "match_id", "date"]].drop_duplicates().sort_values(["team", "date", "match_id"])
order["k"] = order.groupby(["league", "team"]).cumcount()
order["n"] = order.groupby(["league", "team"])["match_id"].transform("count")
order["half"] = np.where(order["k"] < order["n"] / 2, 1, 2)
pm = pm.merge(order[["team", "match_id", "half"]], on=["team", "match_id"])
pm["ga"] = pm["goals"] + pm["assists"]
pm["npxg_xa"] = pm["npxg"] + pm["xa"]

ATTACK = {"Center Forward", "Left Center Forward", "Right Center Forward", "Secondary Striker", "Left Wing",
          "Right Wing", "Center Attacking Midfield", "Left Attacking Midfield", "Right Attacking Midfield",
          "Left Midfield", "Right Midfield"}
pm["attack_min"] = np.where(pm["position"].isin(ATTACK), pm["minutes"], 0.0)
share = pm.groupby(["league", "player_id"])[["attack_min", "minutes"]].sum()
main_pos = pd.Series(np.where(share["attack_min"] / share["minutes"] >= 0.5, "ATT", "other"), index=share.index)
agg = pm.groupby(["league", "player_id", "player", "half"])[["minutes", "ga", "goals", "shots", "npxg", "npxg_xa"]].sum()
wide = agg.unstack("half")
wide.columns = [f"{a}_{b}" for a, b in wide.columns]
wide = wide.reset_index()
wide["pos"] = [main_pos.get((l, p)) for l, p in zip(wide["league"], wide["player_id"])]
coh = wide[(wide["pos"] == "ATT") & (wide["minutes_1"] >= MIN_MINUTES) & (wide["minutes_2"] >= MIN_MINUTES)].copy()
for c in ("ga", "goals", "shots", "npxg", "npxg_xa"):
    for h in (1, 2):
        coh[f"{c}90_{h}"] = 90 * coh[f"{c}_{h}"] / coh[f"minutes_{h}"]

# reference standard: top fifth of each league's cohort in the second half
coh["rank2"] = coh.groupby("league")["ga90_2"].rank(pct=True, method="average")
coh["target"] = (coh["rank2"] > 1 - TOP_SHARE).astype(int)
coh["rank2_x"] = coh.groupby("league")["npxg_xa90_2"].rank(pct=True, method="average")
coh["target_x"] = (coh["rank2_x"] > 1 - TOP_SHARE).astype(int)
N["cohort"] = dict(players=int(len(coh)), positives=int(coh["target"].sum()),
                   by_league=coh.groupby("league").size().rename(index=MEN).to_dict())

TESTS = {"ga90_1": "Goals + assists per 90", "goals90_1": "Goals per 90", "shots90_1": "Shots per 90",
         "npxg90_1": "Expected goals (npxG) per 90", "npxg_xa90_1": "npxG + expected assists per 90"}


def auc(score, y):
    r = pd.Series(score).rank().to_numpy()
    n1, n0 = y.sum(), len(y) - y.sum()
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def operating_point(d, col, target):
    pos_test = (d.groupby("league")[col].rank(pct=True, method="first") > 1 - TOP_SHARE).to_numpy()
    y = d[target].to_numpy().astype(bool)
    tp, fp = (pos_test & y).sum(), (pos_test & ~y).sum()
    fn, tn = (~pos_test & y).sum(), (~pos_test & ~y).sum()
    sens, spec = tp / (tp + fn), tn / (tn + fp)
    ppv = tp / (tp + fp)
    return dict(sens=sens, spec=spec, ppv=ppv, lr_pos=sens / (1 - spec) if spec < 1 else np.inf,
                nns=1 / ppv if ppv > 0 else np.inf, tp=int(tp), fp=int(fp), fn=int(fn), tn=int(tn))


rng = np.random.default_rng(SEED)
boot_idx = [rng.integers(0, len(coh), len(coh)) for _ in range(B)]
res = {}
for target in ("target", "target_x"):
    y = coh[target].to_numpy()
    out = {}
    for col, label in TESTS.items():
        a = auc(coh[col].to_numpy(), y)
        bs = [auc(coh[col].to_numpy()[i], y[i]) for i in boot_idx if 0 < y[i].sum() < len(i)]
        op = operating_point(coh, col, target)
        bop = [operating_point(coh.iloc[i], col, target) for i in boot_idx[:500]]
        out[col] = dict(label=label, auc=a, auc_lo=float(np.percentile(bs, 2.5)), auc_hi=float(np.percentile(bs, 97.5)),
                        **op, ppv_lo=float(np.percentile([b["ppv"] for b in bop], 2.5)),
                        ppv_hi=float(np.percentile([b["ppv"] for b in bop], 97.5)))
    res[target] = out
N["tests"] = res["target"]
N["tests_xref"] = res["target_x"]
# paired bootstrap: npxG + xA versus goals + assists
y = coh["target"].to_numpy()
diff = [auc(coh["npxg_xa90_1"].to_numpy()[i], y[i]) - auc(coh["ga90_1"].to_numpy()[i], y[i]) for i in boot_idx]
N["auc_diff_npxgxa_vs_ga"] = dict(diff=float(auc(coh["npxg_xa90_1"], y) - auc(coh["ga90_1"], y)),
                                  lo=float(np.percentile(diff, 2.5)), hi=float(np.percentile(diff, 97.5)),
                                  p_le_0=float(np.mean(np.array(diff) <= 0)))
# how often does a 'hot' first half on goals + assists, without the underlying numbers, carry on?
hot = coh[(coh.groupby("league")["ga90_1"].rank(pct=True) > 0.8)]
lucky = hot[hot.groupby("league")["npxg_xa90_1"].rank(pct=True) <= 0.5] if len(hot) else hot
N["write_up"] = dict(prevalence=float(y.mean()))

write_numbers("screening", N)
print(N["cohort"])
for t in ("tests", "tests_xref"):
    print(t)
    for col, v in N[t].items():
        print(f"  {v['label']:34s} AUC {v['auc']:.3f} ({v['auc_lo']:.3f}-{v['auc_hi']:.3f}) sens {v['sens']:.2f} spec {v['spec']:.2f} "
              f"PPV {v['ppv']:.2f} ({v['ppv_lo']:.2f}-{v['ppv_hi']:.2f}) LR+ {v['lr_pos']:.2f} NNS {v['nns']:.2f}")
print(N["auc_diff_npxgxa_vs_ga"])

# ------------------------------------------------------------------ chart: ROC curves for three tests
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(WIDTH, 2.45), gridspec_kw=dict(width_ratios=[1, 1.25], wspace=0.5))
for col, colr in (("ga90_1", PURPLE), ("npxg_xa90_1", GREEN)):
    s = coh[col].to_numpy()
    thr = np.sort(np.unique(s))[::-1]
    tpr = [((s >= t_) & (y == 1)).sum() / y.sum() for t_ in thr]
    fpr = [((s >= t_) & (y == 0)).sum() / (1 - y).sum() for t_ in thr]
    ax1.plot([0] + fpr, [0] + tpr, color=colr, lw=2)
ax1.plot([0, 1], [0, 1], ls="--", color=GREY, lw=0.8)
v1, v2 = N["tests"]["npxg_xa90_1"], N["tests"]["ga90_1"]
ax1.text(0.50, 0.36, f"npxG + xA:\nAUC {v1['auc']:.2f}", color=GREEN, fontsize=7.3, fontweight="bold")
ax1.text(0.50, 0.12, f"Goals + assists:\nAUC {v2['auc']:.2f}", color=PURPLE, fontsize=7.3, fontweight="bold")
ax1.set_xlabel("False-positive rate (1 - specificity)"); ax1.set_ylabel("True-positive rate (sensitivity)")
ax1.set_xlim(0, 1); ax1.set_ylim(0, 1.01); ax1.set_aspect("equal")
ax1.set_title("ROC curves", fontsize=9)
order_t = sorted(TESTS, key=lambda c: N["tests"][c]["ppv"])
for i, c in enumerate(order_t):
    v = N["tests"][c]
    colr = GREEN if c == "npxg_xa90_1" else (PURPLE if c == "ga90_1" else GREY)
    ax2.barh(i, 100 * v["ppv"], color=colr, height=0.6)
    ax2.text(100 * v["ppv"] + 1.5, i, f"{100 * v['ppv']:.0f}%  ·  1 in {v['nns']:.1f}", va="center", fontsize=7.2)
ax2.axvline(100 * TOP_SHARE, color=MUTED, ls="--", lw=0.8)
ax2.text(100 * TOP_SHARE + 1, len(order_t) - 0.35, "Picking at random: 20%", fontsize=7, color=MUTED)
SHORT = {"ga90_1": "Goals + assists", "goals90_1": "Goals", "shots90_1": "Shots", "npxg90_1": "npxG", "npxg_xa90_1": "npxG + xA"}
ax2.set_yticks(range(len(order_t))); ax2.set_yticklabels([SHORT[c] + " per 90" for c in order_t], fontsize=7.4)
ax2.set_xlim(0, 100); ax2.set_ylim(-0.6, len(order_t) - 0.1)
ax2.set_xlabel("Shortlisted players who were truly top-fifth (PPV, %)")
ax2.set_title("Shortlist the top fifth on each number", fontsize=9)
save(fig, "screening")
