"""Build analysis tables from StatsBomb (Hudl) open event data.

Data source: https://github.com/hudl/open-data (free, public; credit StatsBomb/Hudl when publishing).

Usage
    python build_tables.py <path/to/open-data/data or URL> <competition_id> <season_id> <output_folder>

Examples
    python build_tables.py open-data/data 2 27  data/epl_2015_16      # Premier League 2015/16
    python build_tables.py open-data/data 11 27 data/laliga_2015_16   # La Liga 2015/16
    python build_tables.py open-data/data 12 27 data/seriea_2015_16   # Serie A 2015/16
    python build_tables.py open-data/data 7 27  data/ligue1_2015_16   # Ligue 1 2015/16
    python build_tables.py open-data/data 37 281 data/wsl_2023_24     # FA Women's Super League 2023/24

Time handling
    StatsBomb restarts the clock at 45:00 for the second half, so first-half stoppage time and the
    first minutes of the second half share clock values. Every time below is converted to *elapsed
    playing time*: first half = clock; second half = length of first half + (clock - 45).
    Bins use the match clock (0-15, 15-30, 30-45+, 45-60, 60-75, 75-90+), with stoppage time
    folded into the last bin of each half.

Outputs (CSV)
    matches        one row per match (all results, has_events flag): teams, score, length of each half
    player_match   one row per player per match played: on/off times, exit reason, minutes, counts
    player_bins    one row per player per match per 15-minute clock bin: exposure and counts
    pressures      one row per pressure event (player, elapsed time) for time-on-pitch analyses
    shots          one row per non-penalty shot with StatsBomb xG
    squads         everyone named in each matchday squad (played = 1 if they got on the pitch)
    subs           every substitution event with its recorded reason (Tactical / Injury)
    injury_subs    substitutions recorded as caused by injury, with time and time already on the pitch
    stoppages      injury stoppages attributed to a player
    goals          every goal (including penalties and own goals) with elapsed time, for game state
"""
import json, os, sys, time, urllib.request
import numpy as np
import pandas as pd

if len(sys.argv) != 5:
    sys.exit(__doc__)
SOURCE, COMP, SEASON, OUT = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
os.makedirs(OUT, exist_ok=True)
BIN_LABELS = ["0-15", "15-30", "30-45+", "45-60", "60-75", "75-90+"]


def read_json(rel):
    if not SOURCE.startswith("http"):
        path = os.path.join(SOURCE, rel)
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    for _ in range(3):
        try:
            with urllib.request.urlopen(f"{SOURCE}/{rel}", timeout=60) as r:
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
    if "Back" in name:          # centre backs, full backs, wing backs
        return "DEF"
    if "Midfield" in name:
        return "MID"
    return "FWD"                # wingers, forwards


EXIT_PREFIXES = ("Substitution - Off", "Foul Committed", "Player Off")

matches = read_json(f"matches/{COMP}/{SEASON}.json")
if matches is None:
    sys.exit("match list not found")

out = {k: [] for k in ("matches", "player_match", "player_bins", "pressures", "shots", "squads",
                       "subs", "injury_subs", "stoppages", "goals")}
missing = []
for m in sorted(matches, key=lambda x: (x["match_date"], x["match_id"])):
    mid = m["match_id"]
    events = read_json(f"events/{mid}.json")
    lineups = read_json(f"lineups/{mid}.json")
    home, away = m["home_team"]["home_team_name"], m["away_team"]["away_team_name"]
    base_row = dict(match_id=mid, competition=m["competition"]["competition_name"], season=m["season"]["season_name"],
                    date=m["match_date"], home=home, away=away, home_score=m["home_score"], away_score=m["away_score"])
    if events is None or lineups is None:
        missing.append(mid)
        out["matches"].append(dict(base_row, has_events=0, first_half=None, second_half=None))
        continue
    events = [e for e in events if e["period"] in (1, 2)]          # league matches: no extra time
    end_clock = {p: max(e["minute"] + e["second"] / 60 for e in events if e["period"] == p) for p in (1, 2)}
    L1, L2 = end_clock[1], end_clock[2] - 45
    LEN = L1 + L2

    def el(period, c):
        return c if period == 1 else L1 + (c - 45)

    edges = [0, 15, 30, L1, L1 + 15, L1 + 30, LEN]                  # clock bins in elapsed time
    out["matches"].append(dict(base_row, has_events=1, first_half=round(L1, 3), second_half=round(L2, 3)))

    rows = {}
    for team in lineups:
        for p in team["lineup"]:
            name = p.get("player_nickname") or p["player_name"]
            segs = p["positions"]
            out["squads"].append(dict(match_id=mid, team=team["team_name"], player_id=p["player_id"],
                                      player=name, played=int(bool(segs))))
            if not segs:
                continue
            seg_t = []
            for s in segs:
                a = el(s.get("from_period") or 1, clock(s["from"]))
                b = el(s.get("to_period") or 2, clock(s["to"])) if s["to"] else LEN
                seg_t.append((a, b, s))
            seg_t.sort(key=lambda x: x[0])
            started = int(seg_t[0][2]["start_reason"] == "Starting XI")
            on = 0.0 if started else seg_t[0][0]
            # the player's exit is the end of their last segment (temporary 'Player Off' / 'Player On'
            # treatment breaks inside a match are ignored)
            last_a, last_b, last_s = seg_t[-1]
            if last_s["to"]:
                off, reason = last_b, last_s["end_reason"]
                if not reason.startswith(EXIT_PREFIXES):
                    reason = "Other: " + reason
            else:
                off, reason = LEN, "Final Whistle"
            off = min(max(off, on), LEN)
            if off - on <= 0:
                continue
            dur = {}
            for a, b, s in seg_t:
                dur[s["position"]] = dur.get(s["position"], 0.0) + max(0.0, min(b, LEN) - a)
            pos = max(dur, key=dur.get)
            rows[p["player_id"]] = dict(
                match_id=mid, team=team["team_name"], player_id=p["player_id"], player=name, position=pos,
                position_group=position_group(pos), started=started,
                on=round(on, 3), off=round(off, 3), exit=reason, match_length=round(LEN, 3),
                minutes=round(off - on, 3), passes=0, pressures=0, ball_recoveries=0, duels=0, carries=0,
                shots=0, goals=0, npxg=0.0, xa=0.0, assists=0, key_passes=0)

    bins = {pid: {"p": np.zeros(6), "pa": np.zeros(6), "d": np.zeros(6)} for pid in rows}
    shot_xg = {e["id"]: e["shot"].get("statsbomb_xg", 0.0) for e in events
               if e["type"]["name"] == "Shot" and e["shot"]["type"]["name"] != "Penalty"}
    for e in events:
        kind = e["type"]["name"]
        t = el(e["period"], e["minute"] + e["second"] / 60)
        team_name = e["team"]["name"]
        if kind == "Substitution":
            reason = e["substitution"].get("outcome", {}).get("name", "Unknown")
            out["subs"].append(dict(match_id=mid, team=team_name, player_id=e["player"]["id"],
                                    replacement_id=e["substitution"]["replacement"]["id"], reason=reason,
                                    period=e["period"], el=round(t, 3)))
            if reason == "Injury":
                r = rows.get(e["player"]["id"], {})
                out["injury_subs"].append(dict(
                    match_id=mid, team=team_name, player_id=e["player"]["id"], player=e["player"]["name"],
                    position=(e.get("position") or {}).get("name"), period=e["period"],
                    clock=round(e["minute"] + e["second"] / 60, 3), el=round(t, 3),
                    started=r.get("started"), time_on_pitch=round(t - r.get("on", 0.0), 3)))
        elif kind == "Injury Stoppage" and e.get("player"):
            out["stoppages"].append(dict(match_id=mid, team=team_name, player_id=e["player"]["id"], el=round(t, 3)))
        if kind == "Shot" and e["shot"]["outcome"]["name"] == "Goal":
            out["goals"].append(dict(match_id=mid, team=team_name, el=round(t, 3)))
        elif kind == "Own Goal For":
            out["goals"].append(dict(match_id=mid, team=team_name, el=round(t, 3)))
        pid = (e.get("player") or {}).get("id")
        if pid not in rows:
            continue
        r, b = rows[pid], min(int(np.searchsorted(edges, t, side="right")) - 1, 5)
        if kind == "Pass":
            r["passes"] += 1; bins[pid]["pa"][b] += 1
            ps = e["pass"]
            if ps.get("goal_assist"):
                r["assists"] += 1
            if ps.get("shot_assist") or ps.get("goal_assist"):
                r["key_passes"] += 1
            if ps.get("assisted_shot_id"):
                r["xa"] += shot_xg.get(ps["assisted_shot_id"], 0.0)
        elif kind == "Pressure":
            r["pressures"] += 1; bins[pid]["p"][b] += 1
            out["pressures"].append(dict(match_id=mid, player_id=pid, el=round(t, 3)))
        elif kind == "Duel":
            r["duels"] += 1; bins[pid]["d"][b] += 1
        elif kind == "Carry":
            r["carries"] += 1
        elif kind == "Ball Recovery":
            if not (e.get("ball_recovery") or {}).get("recovery_failure"):
                r["ball_recoveries"] += 1
        elif kind == "Shot" and e["shot"]["type"]["name"] != "Penalty":
            xg = e["shot"].get("statsbomb_xg", 0.0)
            goal = int(e["shot"]["outcome"]["name"] == "Goal")
            r["shots"] += 1; r["goals"] += goal; r["npxg"] += xg
            out["shots"].append(dict(match_id=mid, player_id=pid, player=r["player"], team=r["team"],
                                     el=round(t, 3), xg=xg, goal=goal))

    for pid, r in rows.items():
        out["player_match"].append(r)
        for i in range(6):
            expo = max(0.0, min(r["off"], edges[i + 1]) - max(r["on"], edges[i]))
            if expo > 0:
                out["player_bins"].append(dict(match_id=mid, player_id=pid, team=r["team"], started=r["started"],
                                               on=r["on"], bin=BIN_LABELS[i], exposure=round(expo, 3),
                                               pressures=int(bins[pid]["p"][i]), passes=int(bins[pid]["pa"][i]),
                                               duels=int(bins[pid]["d"][i])))

for k, v in out.items():
    pd.DataFrame(v).to_csv(f"{OUT}/{k}.csv", index=False)
print(f"{COMP}/{SEASON}: {len(matches) - len(missing)} of {len(matches)} matches with event data; missing {missing}")
print({k: len(v) for k, v in out.items()})
