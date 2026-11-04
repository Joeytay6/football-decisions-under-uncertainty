"""Summary of the data used: one row per competition (feeds the 'Data' page of the portfolio)."""
import os
import pandas as pd
from common import MEN, WOMEN, DATA, available, load, write_numbers

rows = []
for folder, name in {**MEN, **WOMEN}.items():
    if folder not in available({**MEN, **WOMEN}):
        continue
    m = load(folder, "matches"); pm = load(folder, "player_match"); sh = load(folder, "shots")
    pr = load(folder, "pressures"); inj = load(folder, "injury_subs")
    rows.append(dict(folder=folder, competition=name, season=str(m["season"].iat[0]), gender="Women" if folder in WOMEN else "Men",
                     matches=int(len(m)), with_events=int(m["has_events"].sum()), appearances=int(len(pm)),
                     players=int(pm["player_id"].nunique()), player_hours=float(pm["minutes"].sum() / 60),
                     shots=int(len(sh)), goals_np=int(sh["goal"].sum()), xg=float(sh["xg"].sum()),
                     pressures=int(len(pr)), injury_withdrawals=int(len(inj))))
d = pd.DataFrame(rows)
tot = d[d["gender"] == "Men"].sum(numeric_only=True).to_dict()
write_numbers("data", dict(rows=rows, men_total=tot, all_total=d.sum(numeric_only=True).to_dict()))
print(d.to_string())
