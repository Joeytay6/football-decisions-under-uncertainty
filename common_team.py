"""Shared helpers for projects 7 to 10 (team-level work)."""
import os
import numpy as np
import pandas as pd
from common import DATA, OUT, MEN, WOMEN, write_numbers  # noqa: F401  (chart style comes from common)

WSL_SEASONS = {"wsl_2018_19": "WSL 2018/19", "wsl_2019_20": "WSL 2019/20", "wsl_2020_21": "WSL 2020/21",
               "wsl_2023_24": "WSL 2023/24"}


def team_tables(folders):
    """Load matches, shots and team-match rows for several competitions, with a league column."""
    mm, ma, sh, tm = [], [], [], []
    for f in folders:
        p = os.path.join(DATA, f)
        a = pd.read_csv(os.path.join(p, "matches_mgr.csv")); a["league"] = f; mm.append(a)
        b = pd.read_csv(os.path.join(p, "matches_all.csv")); b["league"] = f; ma.append(b)
        c = pd.read_csv(os.path.join(p, "shots_all.csv")); c["league"] = f; sh.append(c)
        d = pd.read_csv(os.path.join(p, "team_match.csv")); d["league"] = f; tm.append(d)
    return (pd.concat(mm, ignore_index=True), pd.concat(ma, ignore_index=True),
            pd.concat(sh, ignore_index=True), pd.concat(tm, ignore_index=True))


def goal_dist(probs):
    """Poisson-binomial distribution of goals from independent possession-level scoring chances."""
    d = np.array([1.0])
    for p in probs:
        d = np.convolve(d, [1 - p, p])
    return d


def match_probs(shots):
    """For each match and team: probability of a win, draw and loss, and expected points, from the
    chances created. Shots in the same possession are combined (1 - prod(1 - xG)) so a rebound isn't
    counted as a second, independent chance. Own goals carry no xG."""
    s = shots[shots.shot_type != "Own Goal"].copy()
    s["miss"] = 1 - s["xg"].clip(0, 0.999)
    pos = s.groupby(["match_id", "team", "possession"])["miss"].prod().reset_index()
    pos["p"] = 1 - pos["miss"]
    rows = []
    for mid, g in pos.groupby("match_id"):
        teams = list(g.team.unique())
        rows.append((mid, teams, {t: g.loc[g.team == t, "p"].values for t in teams}))
    return pos, rows


def xpts_table(matches_mgr, shots):
    """One row per team per match: points, expected points, P(win/draw/loss), variance of points."""
    pos, _ = match_probs(shots)
    pmap = {(m, t): g["p"].values for (m, t), g in pos.groupby(["match_id", "team"])}
    out = []
    for r in matches_mgr.itertuples():
        dh = goal_dist(pmap.get((r.match_id, r.home), []))
        da = goal_dist(pmap.get((r.match_id, r.away), []))
        joint = np.outer(dh, da)
        hw = np.tril(joint, -1).sum(); dr = np.trace(joint); aw = np.triu(joint, 1).sum()
        for team, opp, w, l, gf, ga, home in ((r.home, r.away, hw, aw, r.home_score, r.away_score, 1),
                                              (r.away, r.home, aw, hw, r.away_score, r.home_score, 0)):
            xp = 3 * w + dr
            var = 9 * w + dr - xp ** 2
            pts = 3 if gf > ga else (1 if gf == ga else 0)
            out.append(dict(match_id=r.match_id, date=r.date, league=r.league, team=team, opp=opp, home=home,
                            gf=gf, ga=ga, pts=pts, p_win=w, p_draw=dr, p_loss=l, xpts=xp, var_pts=var))
    return pd.DataFrame(out)


def place_labels(ax, xs, ys, texts, fontsize=6.6, color="#1c2420", pad_pts=3, avoid_points=True):
    """Put a text label beside each point, choosing for each the candidate position (right, left, above,
    below, diagonals) that overlaps least with labels already placed, the points and the axes edge."""
    import numpy as np
    fig = ax.figure
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    allpts = ax.transData.transform(np.column_stack([np.concatenate([c.get_offsets()[:, 0] for c in ax.collections if hasattr(c, "get_offsets") and len(c.get_offsets())] or [np.array(xs)]),
                                                     np.concatenate([c.get_offsets()[:, 1] for c in ax.collections if hasattr(c, "get_offsets") and len(c.get_offsets())] or [np.array(ys)])]))
    axbb = ax.get_window_extent(r)
    placed = []
    cands = [(1, 0, "left", "center"), (-1, 0, "right", "center"), (0, 1.2, "center", "bottom"), (0, -1.2, "center", "top"),
             (1, 1, "left", "bottom"), (-1, 1, "right", "bottom"), (1, -1, "left", "top"), (-1, -1, "right", "top"),
             (2.5, 2.5, "left", "bottom"), (-2.5, -2.5, "right", "top"), (2.5, -2.5, "left", "top"), (-2.5, 2.5, "right", "bottom")]
    for x, y, t in zip(xs, ys, texts):
        best, best_score = None, None
        for dx, dy, ha, va in cands:
            a = ax.annotate(t, (x, y), xytext=(dx * pad_pts, dy * pad_pts), textcoords="offset points",
                            fontsize=fontsize, ha=ha, va=va, color=color)
            bb = a.get_window_extent(r).expanded(1.03, 1.08)
            a.remove()
            score = 0.0
            for q in placed:
                ix = max(0, min(bb.x1, q.x1) - max(bb.x0, q.x0)); iy = max(0, min(bb.y1, q.y1) - max(bb.y0, q.y0))
                score += ix * iy
            if avoid_points:
                inside = (allpts[:, 0] > bb.x0) & (allpts[:, 0] < bb.x1) & (allpts[:, 1] > bb.y0) & (allpts[:, 1] < bb.y1)
                score += 60 * inside.sum()
            out = max(0, axbb.x0 - bb.x0) + max(0, bb.x1 - axbb.x1) + max(0, axbb.y0 - bb.y0) + max(0, bb.y1 - axbb.y1)
            score += 500 * out + 2 * (abs(dx) + abs(dy))
            if best_score is None or score < best_score:
                best, best_score = (dx, dy, ha, va), score
        dx, dy, ha, va = best
        a = ax.annotate(t, (x, y), xytext=(dx * pad_pts, dy * pad_pts), textcoords="offset points", fontsize=fontsize,
                        ha=ha, va=va, color=color,
                        arrowprops=dict(arrowstyle="-", lw=0.4, color="#9aa59f") if max(abs(dx), abs(dy)) > 2 else None)
        placed.append(a.get_window_extent(r).expanded(1.03, 1.08))
