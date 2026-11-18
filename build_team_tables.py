"""Team-level tables for projects 7 to 10, built from StatsBomb (Hudl) open event data.

Usage
    python build_team_tables.py <path/to/open-data/data> <competition_id> <season_id> <output_folder>

Outputs (CSV)
    matches_mgr   one row per match: date, teams, score, the managers named for each side
    shots_all     every shot (penalties included) with xG, possession, play pattern, shot type and the
                  game state for the shooting team at the moment of the shot
    team_match    one row per team per match: chances for and against, and the style KPIs used in
                  project 9, measured over the whole match and again only while the score was level

Coordinates: StatsBomb records every event from the acting team's point of view (x = 0 own goal line,
x = 120 opponent's goal line, pitch 120 x 80 yards), so a high x for a pressure means a high press.
"""
import json, os, sys
from multiprocessing import Pool
import numpy as np
import pandas as pd

FLIP = {"all": "all", "level": "level", "lead": "trail", "trail": "lead"}   # the opponent's game state
SET_PIECE_TYPES = {"Corner", "Free Kick", "Throw-in", "Goal Kick", "Kick Off"}
SET_PIECE_PATTERNS = {"From Corner", "From Free Kick", "From Throw In"}
DEF_ACTIONS = {"Interception", "Foul Committed", "Dribbled Past"}   # plus tackles (Duel: Tackle)


def secs(ts):
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def in_box(x, y):
    return x >= 102 and 18 <= y <= 62


def is_set_piece_shot(e, restart):
    """A shot from an attacking set piece: a direct free kick or corner, or a shot within 20 seconds of a
    corner, free kick or throw-in taken in the final third, in the same possession."""
    sh = e["shot"]
    if sh["type"]["name"] in ("Free Kick", "Corner"):
        return True
    rs = restart.get(e["possession"])
    if not rs:
        return False
    kind, rx, per, t0 = rs
    return rx >= 80 and per == e["period"] and 0 <= secs(e["timestamp"]) - t0 <= 20


def match_rows(args):
    src, m = args
    mid = m["match_id"]
    path = os.path.join(src, "events", f"{mid}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        ev = json.load(f)
    home, away = m["home_team"]["home_team_name"], m["away_team"]["away_team_name"]
    teams = (home, away)
    # event files occasionally spell a team differently from the match list: use the team id
    name_of = {m["home_team"]["home_team_id"]: home, m["away_team"]["away_team_id"]: away}
    for e in ev:
        for key in ("team", "possession_team"):
            if key in e and e[key]["id"] in name_of:
                e[key]["name"] = name_of[e[key]["id"]]

    def state(team, h, a):
        d = (h - a) if team == home else (a - h)
        return "level" if d == 0 else ("lead" if d > 0 else "trail")


    # running score -> game state for every event (state before the event)
    score = {home: 0, away: 0}
    period_len = {}
    shots, kp = [], []
    ev.sort(key=lambda e: e["index"])
    state_of = []
    for e in ev:
        t = e["type"]["name"]
        team = e["team"]["name"]
        opp = away if team == home else home
        d = score[team] - score[opp]
        state_of.append((score[home], score[away]))
        if t == "Shot" and e["shot"]["outcome"]["name"] == "Goal":
            score[team] += 1
        elif t == "Own Goal Against":
            score[opp] += 1
        if t == "Half End":
            period_len[e["period"]] = max(period_len.get(e["period"], 0), secs(e["timestamp"]))

    # possession counts, and in-play possession time: the gap to the next event is credited to the team in
    # possession, ignoring gaps over 8 seconds (ball out of play or a stoppage)
    poss = {}
    for e in ev:
        q = poss.setdefault(e["possession"], [e["possession_team"]["name"], 0])
        if e["type"]["name"] == "Pass" and e["team"]["name"] == q[0]:
            q[1] += 1
    poss_secs = {(tm, sc): 0.0 for tm in teams for sc in ("all", "level", "lead", "trail")}
    st_at = {e["id"]: state_of[i] for i, e in enumerate(ev)}
    in_play = {"level": 0.0, "lead": 0.0, "trail": 0.0}
    playable = [e for e in ev if e["type"]["name"] not in ("Starting XI", "Half Start", "Half End", "Tactical Shift",
                                                            "Substitution", "Player On", "Player Off", "Injury Stoppage")]
    for e0, e1 in zip(playable, playable[1:]):
        if e0["period"] != e1["period"]:
            continue
        dt = secs(e1["timestamp"]) - secs(e0["timestamp"])
        pt_ = e0["possession_team"]["name"]
        if 0 <= dt <= 8 and pt_ in teams:
            poss_secs[(pt_, "all")] += dt
            for tm in teams:   # credit the in-play time to the state each team was in
                if tm == pt_:
                    poss_secs[(tm, state(tm, *st_at[e0["id"]]))] += dt
            in_play[state(home, *st_at[e0["id"]])] += dt
    # the set-piece restart that started each possession (if any): type, location, time
    restart = {}
    for e in ev:
        if e["type"]["name"] == "Pass" and e["pass"].get("type", {}).get("name") in ("Corner", "Free Kick", "Throw-in") \
                and e["possession"] not in restart:
            restart[e["possession"]] = (e["pass"]["type"]["name"], e["location"][0], e["period"], secs(e["timestamp"]))

    rows = {}
    def blank():
        return dict(passes=0, op_passes=0, op_passes_cmp=0, f3_passes=0, long_op=0, wide_f3=0,
                    box_pass_att=0, crosses_box=0, pressures=0, press_x_sum=0.0, press_opp_half=0,
                    counterpress=0, def_act_ppda=0, opp_passes_ppda=0, def_x_sum=0.0, def_x_n=0,
                    high_regains=0, corners=0, fk_f3=0, throw_f3=0, possessions=0, poss_with_pass=0, poss_secs=0.0, minutes=0.0,
                    shots=0, np_shots=0, npxg=0.0, counter_shots=0, sp_npxg=0.0, goals=0)
    for scope in ("all", "level", "lead", "trail"):
        for tm in teams:
            rows[(tm, scope)] = blank()

    # seconds spent in each game state (from each team's point of view), from event timestamps
    state_secs = {(tm, sc): 0.0 for tm in teams for sc in ("level", "lead", "trail")}
    last = None
    order_t = sorted(range(len(ev)), key=lambda i: (ev[i]["period"], secs(ev[i]["timestamp"])))
    for i in order_t:
        e = ev[i]
        s_ = secs(e["timestamp"])
        h, a = state_of[i]
        if last is not None and last[0] == e["period"]:
            dt = max(0.0, s_ - last[1])
            for tm in teams:
                state_secs[(tm, state(tm, *last[2]))] += dt
        last = (e["period"], s_, (h, a))
    total_secs = sum(period_len.values())

    for i, e in enumerate(ev):
        t = e["type"]["name"]
        team = e["team"]["name"]
        if team not in teams:
            continue
        opp = away if team == home else home
        h, a = state_of[i]
        st = state(team, h, a)
        loc = e.get("location")
        x, y = (loc[0], loc[1]) if loc else (None, None)
        for scope in ("all", st):
            r, ro = rows[(team, scope)], rows[(opp, FLIP[scope])]
            if t == "Pass":
                p = e["pass"]
                ptype = p.get("type", {}).get("name")
                r["passes"] += 1
                if ptype == "Corner":
                    r["corners"] += 1
                elif ptype == "Free Kick" and x is not None and x >= 80:
                    r["fk_f3"] += 1
                elif ptype == "Throw-in" and x is not None and x >= 80:
                    r["throw_f3"] += 1
                if ptype not in SET_PIECE_TYPES:
                    r["op_passes"] += 1
                    if "outcome" not in p:
                        r["op_passes_cmp"] += 1
                    if p.get("length", 0) >= 35:
                        r["long_op"] += 1
                    if x is not None and x >= 80:
                        r["f3_passes"] += 1
                        if y < 18 or y > 62:
                            r["wide_f3"] += 1
                    end = p.get("end_location")
                    if end and x is not None and not in_box(x, y) and in_box(end[0], end[1]):
                        r["box_pass_att"] += 1
                        if p.get("cross"):
                            r["crosses_box"] += 1
                    if x is not None and x <= 72:
                        ro["opp_passes_ppda"] += 1
            elif t == "Pressure":
                r["pressures"] += 1
                if x is not None:
                    r["press_x_sum"] += x
                    if x >= 60:
                        r["press_opp_half"] += 1
                if e.get("counterpress"):
                    r["counterpress"] += 1
            is_def = t in DEF_ACTIONS or (t == "Duel" and e["duel"].get("type", {}).get("name") == "Tackle")
            if is_def and x is not None and x >= 48:
                r["def_act_ppda"] += 1
            pos = e.get("position", {}).get("name", "")
            if (is_def or t in ("Clearance", "Block", "Ball Recovery")) and x is not None and "Back" in pos:
                r["def_x_sum"] += x; r["def_x_n"] += 1
            if t == "Ball Recovery" and not e.get("ball_recovery", {}).get("recovery_failure") and x is not None and x >= 80:
                r["high_regains"] += 1
            if t == "Interception" and x is not None and x >= 80 and \
                    e["interception"].get("outcome", {}).get("name") in ("Won", "Success In Play", "Success Out"):
                r["high_regains"] += 1
            if t == "Shot":
                sh = e["shot"]
                pen = sh["type"]["name"] == "Penalty"
                if sh["type"]["name"] == "Free Kick":
                    r["fk_f3"] += 1
                r["shots"] += 1
                if sh["outcome"]["name"] == "Goal":
                    r["goals"] += 1
                if not pen:
                    r["np_shots"] += 1
                    r["npxg"] += sh["statsbomb_xg"]
                    if e["play_pattern"]["name"] == "From Counter":
                        r["counter_shots"] += 1
                    if is_set_piece_shot(e, restart):
                        r["sp_npxg"] += sh["statsbomb_xg"]
        if t == "Shot":
            sh = e["shot"]
            rs = restart.get(e["possession"])
            shots.append(dict(match_id=mid, team=team, opp=opp, period=e["period"], minute=e["minute"],
                              second=e["second"], possession=e["possession"], play_pattern=e["play_pattern"]["name"],
                              shot_type=sh["type"]["name"], xg=sh["statsbomb_xg"],
                              set_piece=int(is_set_piece_shot(e, restart)),
                              restart_type=rs[0] if rs else None,
                              goal=int(sh["outcome"]["name"] == "Goal"), x=x, y=y,
                              body_part=sh.get("body_part", {}).get("name"),
                              gd_before=(h - a) if team == home else (a - h)))
        if t == "Own Goal Against":
            shots.append(dict(match_id=mid, team=opp, opp=team, period=e["period"], minute=e["minute"],
                              second=e["second"], possession=e["possession"], play_pattern=e["play_pattern"]["name"],
                              shot_type="Own Goal", xg=0.0, goal=1, x=None, y=None, body_part=None,
                              gd_before=(h - a) if opp == home else (a - h)))

    for pid, (pt, npass) in poss.items():
        if pt not in teams:
            continue
        r = rows[(pt, "all")]
        r["possessions"] += 1
        if npass > 0:
            r["poss_with_pass"] += 1
    for tm in teams:
        for sc in ("all", "level", "lead", "trail"):
            rows[(tm, sc)]["poss_secs"] = poss_secs[(tm, sc)]

    out = []
    for (tm, scope), r in rows.items():
        r.update(match_id=mid, team=tm, opp=away if tm == home else home, home=int(tm == home), scope=scope,
                 minutes=(total_secs if scope == "all" else state_secs[(tm, scope)]) / 60)
        out.append(r)
    hm = m["home_team"].get("managers") or []
    am = m["away_team"].get("managers") or []
    mrow = dict(match_id=mid, date=m["match_date"], week=m.get("match_week"), home=home, away=away,
                home_score=m["home_score"], away_score=m["away_score"],
                home_mgr="/".join(x["name"] for x in hm), away_mgr="/".join(x["name"] for x in am),
                minutes=total_secs / 60)
    return mrow, shots, out


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    SRC, COMP, SEASON, OUT = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(SRC, "matches", str(COMP), f"{SEASON}.json"), encoding="utf-8") as f:
        matches = json.load(f)
    with Pool(2) as pool:
        res = [r for r in pool.map(match_rows, [(SRC, m) for m in matches], chunksize=4) if r]
    pd.DataFrame([dict(match_id=m["match_id"], date=m["match_date"], home=m["home_team"]["home_team_name"],
                       away=m["away_team"]["away_team_name"], home_score=m["home_score"], away_score=m["away_score"])
                  for m in matches]).sort_values(["date", "match_id"]).to_csv(os.path.join(OUT, "matches_all.csv"), index=False)
    pd.DataFrame([r[0] for r in res]).sort_values(["date", "match_id"]).to_csv(os.path.join(OUT, "matches_mgr.csv"), index=False)
    pd.DataFrame([s for r in res for s in r[1]]).to_csv(os.path.join(OUT, "shots_all.csv"), index=False)
    pd.DataFrame([x for r in res for x in r[2]]).to_csv(os.path.join(OUT, "team_match.csv"), index=False)
    print(OUT, len(res), "matches")
