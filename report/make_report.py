"""Build the portfolio PDF from the analysis outputs. Every number in the document comes from output/*.json.
Usage: python report/make_report.py [generic|thun|all]
Needs Node.js with Playwright (render.js) and the Inter font for the PDF; the HTML is written either way.
"""
import json, os, shutil, subprocess, sys
import jinja2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "output")
BUILD = os.path.join(HERE, "build")
RENDER = os.environ.get("RENDER_JS", os.path.join(HERE, "render.js"))
os.makedirs(os.path.join(BUILD, "img"), exist_ok=True)
for f in os.listdir(OUT):
    if f.endswith(".png"):
        shutil.copy(os.path.join(OUT, f), os.path.join(BUILD, "img", f))

load = lambda n: json.load(open(os.path.join(OUT, f"{n}.json")))
ctx = dict(I=load("injury"), F=load("fatigue"), S=load("screening"), FI=load("finishing"), D=load("data"),
           W=load("wsl"), WE=load("wsl_elapsed"))


def signed(x, d):
    s = f"{abs(x):,.{d}f}"
    return ("&minus;" + s) if round(x, d) < 0 else s


env = jinja2.Environment(loader=jinja2.FileSystemLoader(HERE), undefined=jinja2.StrictUndefined, autoescape=False)
env.filters.update(
    pct=lambda x, d=0: f"{100 * x:.{d}f}%",
    f0=lambda x: f"{x:,.0f}", f1=lambda x: f"{x:,.1f}", f2=lambda x: f"{x:.2f}", f3=lambda x: f"{x:.3f}",
    sf1=lambda x: signed(x, 1), sf2=lambda x: signed(x, 2),
    n=lambda x: f"{int(round(x)):,}",
    k=lambda x: f"£{x / 1000:,.0f}k",
    k1=lambda x: f"£{x / 1000:,.1f}k",
)
tpl = env.get_template("template.html")
VERSIONS = {"generic": ("", "your club"),
            "thun": ('<div class="prepared">Prepared for FC Thun</div>', "FC Thun")}
which = sys.argv[1] if len(sys.argv) > 1 else "all"
for name, (prep, club) in VERSIONS.items():
    if which not in ("all", name):
        continue
    html = tpl.render(PREPARED=prep, CLUB=club, **ctx)
    path = os.path.join(BUILD, f"portfolio_{name}.html")
    open(path, "w").write(html)
    if os.path.exists(RENDER):
        subprocess.run(["node", RENDER, path, os.path.join(BUILD, f"portfolio_{name}.pdf")], check=True)
    print("built", name)
