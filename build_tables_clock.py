"""Build the tables for Projects 1-3 from StatsBomb (Hudl) open data: FA Women's Super League 2023/24.

These are the tables the women's-game projects were first built on. Minutes are counted on the match clock
(each half from its own clock, so first-half stoppage time is not added on). build_tables.py counts elapsed
playing time instead; project1_3_wsl.py can be re-run on those tables as a sensitivity check.

Data: https://github.com/hudl/open-data (competition_id 37, season_id 281).
Usage:
    python build_tables_clock.py [path/to/open-data/data] [output_folder, default data/wsl_2023_24_clock]
If no local copy is given, files are downloaded from the public repository.
Outputs (CSV): matches, player_match, shots, squads, injury_subs.
"""
import json, os, sys, time, urllib.request
import pandas as pd

COMPETITION_ID, SEASON_ID = 37, 281
REMOTE = "https://raw.githubusercontent.com/hudl/open-data/master/data"
LOCAL = sys.argv[1] if len(sys.argv) > 1 else None
OUT = sys.argv[2] if len(sys.argv) > 2 else "data/wsl_2023_24_clock"
os.makedirs(OUT, exist_ok=True)


def read_json(rel):
    if LOCAL:
        path = os.path.join(LOCAL, rel)
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    for _ in range(3):
        try:
            with urllib.request.urlopen(f"{REMOTE}/{rel}", timeout=60) as r:
                return json.load(r)
        except Exception:
            time.sleep(2)
    return None


def clock(c):
    m, s = c.split(":")
    return int(m) + int(s) / 60


def position_group(name):
    if not isinstance(name, str):
        return "Unknown"
    if "Goalkeeper" in name:
        return "GK"
    if "Back" in name:
        return "DEF"
    if "Midfield" in name:
        return "MID"
    return "FWD"


matches = read_json(f"matches/{COMPETITION_ID}/{SEASON_ID}.json")
match_rows = [dict(match_id=m["match_id"], date=m["match_date"], kick_off=m.get("kick_off"),
                   home=m["home_team"]["home_team_name"], away=m["away_team"]["away_team_name"],
                   home_score=m["home_score"], away_score=m["away_score"]) for m in matches]

pm_rows, shot_rows, squad_rows, inj_rows, missing = [], [], [], [], []
for m in matches:
    mid = m["match_id"]
    events = read_json(f"events/{mid}.json")
    lineups = read_json(f"lineups/{mid}.json")
    if events is None or lineups is None:
        missing.append(mid)
        continue
    last_period = max(e["period"] for e in events)
    match_end = max(e["minute"] + e["second"] / 60 for e in events if e["period"] == last_period)

    rows = {}
    for team in lineups:
        for p in team["lineup"]:
            segs = p["positions"]
            squad_rows.append(dict(match_id=mid, team=team["team_name"], player_id=p["player_id"],
                                   player=p["player_nickname"] or p["player_name"], played=int(bool(segs))))
            if not segs:
                continue
            started = any(s["start_reason"] == "Starting XI" for s in segs)
            if started:
                on = 0.0
            else:
                subs_on = [clock(s["from"]) for s in segs if s["start_reason"].startswith("Substitution - On")]
                on = min(subs_on) if subs_on else min(clock(s["from"]) for s in segs)
            exits = [(clock(s["to"]), s["end_reason"]) for s in segs if s["to"] and (
                s["end_reason"].startswith("Substitution - Off")
                or s["end_reason"] in ("Foul Committed (Second Yellow)", "Foul Committed (Red Card)", "Player Off (Permanent)"))]
            exits = [x for x in exits if x[0] >= on]
            off, off_reason = (min(exits) if exits else (match_end, "Final Whistle"))
            minutes = min(max(off - on, 0.0), match_end)
            if minutes <= 0:
                continue
            by_pos = {}
            for s in segs:
                a = clock(s["from"]); b_ = clock(s["to"]) if s["to"] else match_end
                if 0 <= b_ - a <= match_end:
                    by_pos[s["position"]] = by_pos.get(s["position"], 0.0) + (b_ - a)
            if not by_pos:
                by_pos = {segs[0]["position"]: 1.0}
            rows[p["player_id"]] = dict(
                match_id=mid, player_id=p["player_id"], player=p["player_nickname"] or p["player_name"],
                team=team["team_name"], position=max(by_pos, key=by_pos.get), started=int(started),
                on=round(on, 2), off=round(off, 2), off_reason=off_reason, match_end=round(match_end, 2),
                minutes=round(minutes, 2), passes=0, pressures=0, ball_recoveries=0, duels=0,
                shots=0, goals=0, npxg=0.0, xa=0.0)

    shot_xg = {e["id"]: e["shot"].get("statsbomb_xg", 0.0) for e in events
               if e["type"]["name"] == "Shot" and e["shot"]["type"]["name"] != "Penalty"}
    for e in events:
        kind = e["type"]["name"]
        if kind == "Substitution" and e["substitution"].get("outcome", {}).get("name") == "Injury":
            inj_rows.append(dict(match_id=mid, team=e["team"]["name"], player_id=e["player"]["id"],
                                 player=e["player"]["name"], period=e["period"],
                                 minute=e["minute"] + e["second"] / 60, position=e.get("position", {}).get("name")))
        pid = (e.get("player") or {}).get("id")
        if pid not in rows:
            continue
        r = rows[pid]
        if kind == "Pass":
            r["passes"] += 1
            if e["pass"].get("assisted_shot_id"):
                r["xa"] += shot_xg.get(e["pass"]["assisted_shot_id"], 0.0)
        elif kind == "Pressure":
            r["pressures"] += 1
        elif kind == "Duel":
            r["duels"] += 1
        elif kind == "Ball Recovery":
            if not (e.get("ball_recovery") or {}).get("recovery_failure"):
                r["ball_recoveries"] += 1
        elif kind == "Shot" and e["shot"]["type"]["name"] != "Penalty":
            xg = e["shot"].get("statsbomb_xg", 0.0)
            goal = int(e["shot"]["outcome"]["name"] == "Goal")
            r["shots"] += 1; r["goals"] += goal; r["npxg"] += xg
            shot_rows.append(dict(match_id=mid, player_id=pid, player=r["player"], team=r["team"], xg=xg, goal=goal))
    pm_rows += list(rows.values())

pm = pd.DataFrame(pm_rows)
pm["position_group"] = pm["position"].map(position_group)
pd.DataFrame(match_rows).to_csv(f"{OUT}/matches.csv", index=False)
pm.to_csv(f"{OUT}/player_match.csv", index=False)
pd.DataFrame(shot_rows).to_csv(f"{OUT}/shots.csv", index=False)
pd.DataFrame(squad_rows).to_csv(f"{OUT}/squads.csv", index=False)
pd.DataFrame(inj_rows).to_csv(f"{OUT}/injury_subs.csv", index=False)
print(f"{len(matches) - len(missing)} of {len(matches)} matches with event data; missing: {missing}")
print(f"player-matches {len(pm)}, shots {len(shot_rows)}, injury substitutions {len(inj_rows)}")
