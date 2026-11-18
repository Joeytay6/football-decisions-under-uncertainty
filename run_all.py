"""Rebuild every table, number and chart in the portfolio, then the PDF.

    python run_all.py <path/to/open-data/data>      # local copy of github.com/hudl/open-data (fastest)
    python run_all.py https://raw.githubusercontent.com/hudl/open-data/master/data   # straight from GitHub (slower)
"""
import subprocess, sys

SOURCE = sys.argv[1] if len(sys.argv) > 1 else "https://raw.githubusercontent.com/hudl/open-data/master/data"
COMPETITIONS = [(2, 27, "epl_2015_16"), (11, 27, "laliga_2015_16"), (12, 27, "seriea_2015_16"),
                (7, 27, "ligue1_2015_16"), (37, 281, "wsl_2023_24")]


def run(*args):
    print(">>", " ".join(map(str, args)), flush=True)
    subprocess.run([sys.executable, *map(str, args)], check=True)


TEAM_COMPETITIONS = COMPETITIONS + [(37, 4, "wsl_2018_19"), (37, 42, "wsl_2019_20"), (37, 90, "wsl_2020_21")]

for comp, season, folder in COMPETITIONS:
    run("build_tables.py", SOURCE, comp, season, f"data/{folder}")
for comp, season, folder in TEAM_COMPETITIONS:   # team-level tables for projects 7-10 (local copy of the data needed)
    run("build_team_tables.py", SOURCE, comp, season, f"data/{folder}")
run("build_tables_clock.py", "" if SOURCE.startswith("http") else SOURCE, "data/wsl_2023_24_clock")
run("data_summary.py")
run("project1_3_wsl.py")              # projects 1-3, women's game
run("project1_3_wsl.py", "elapsed")   # sensitivity check on elapsed-time minutes
for script in ("project2b_finishing_men.py", "project4_screening.py", "project5_injury.py", "project6_fatigue.py",
               "project8_coaches.py", "project7_team_strength.py", "project9_game_model.py", "project10_set_pieces.py"):
    run(script)
run("report/make_report.py", "generic")
