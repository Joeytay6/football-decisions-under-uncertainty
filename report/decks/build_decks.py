"""Build one deck per project into decks/. Every number is read from the analysis outputs (output/*.json).

Charts: run each project script twice, once normally (output_doc/) and once with smaller figures for slides:
    FIG_SCALE=0.74 PYTHONPATH=report/decks:. python projectN_*.py   then copy output/*.png to output_deck/
Needs Python Playwright with Chrome, and the Barlow Condensed, Inter and JetBrains Mono fonts.
Usage: python report/decks/build_decks.py [01 02 ... 10]
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from deck import Deck
from render import render

REPO = os.path.dirname(os.path.dirname(HERE))
OUTJ = os.path.join(REPO, "output")
CH = os.path.join(REPO, "output_deck")
DST = os.path.join(REPO, "decks")
os.makedirs(DST, exist_ok=True)


def J(n):
    return json.load(open(os.path.join(OUTJ, n + ".json")))


W, FIN, SCR, INJ, FAT = J("wsl"), J("finishing"), J("screening"), J("injury"), J("fatigue")
TS, CO, GM, SP, DATA = J("team_strength"), J("coaches"), J("game_model"), J("set_pieces"), J("data")


def pc(x, d=0):
    return f"{100 * x:.{d}f}%"


def k(x, d=0):
    return f"£{x / 1000:.{d}f}k"


def f1(x):
    return f"{x:.1f}"


def f2(x):
    return f"{x:.2f}"


def neg(s):
    return s.replace("-", "−")


def ordinal(n):
    n = int(n)
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def img(n, doc=False):
    return os.path.join(os.path.join(REPO, "output_doc") if doc else CH, n + ".png")


MEN = "Data: StatsBomb (Hudl) open data, Premier League, La Liga, Serie A and Ligue 1 2015/16"
WSL = "Data: StatsBomb (Hudl) open data, FA WSL 2023/24"
WSL4 = "FA WSL 2018/19 to 2023/24"

PROJECTS = [
    ("01", "Appraising a signing", "what to pay, and how to structure the deal"),
    ("02", "Finishing: skill or luck?", "a hot season against real skill"),
    ("03", "Measurement science", "which numbers to trust, and when form is real"),
    ("04", "Scouting numbers as screening tests", "which numbers a shortlist should be built on"),
    ("05", "Injuries in matches", "what event data can and can't see"),
    ("06", "A fatigue signal in event data", "do players tire, and when?"),
    ("07", "How good is a team, really?", "judging a club on its chances, not just its points"),
    ("08", "Judging a head coach", "funnel plots, and does a mid-season change work?"),
    ("09", "Measuring a game model", "style KPIs validated like a clinical questionnaire"),
    ("10", "Set pieces as an investment", "a repeatable edge, and what it's worth"),
]
ME = ("<p>Health economist, sport and exercise scientist, trained clinical perfusion scientist and start-up co-founder.</p>"
      "<p><b>Lumanity</b> (2024 to 2026): cost-effectiveness and budget impact models and evidence synthesis behind NICE submissions. "
      "<b>Sport science</b> with the English Institute of Sport (British Triathlon), Barnsley FC and Leeds Rhinos academies. "
      "<b>Oxford University Hospitals</b>: heart-lung bypass in cardiac surgery. <b>Novamint</b>: built a start-up's commercial side from scratch.</p>"
      "<p>Football is a lifelong obsession and where I want to build my career. Every method here runs unchanged on a club's own "
      "event, tracking, GPS, medical and financial data.</p>")
CONTACT = "github.com/Joeytay6/football-decisions-under-uncertainty"


def finish(d, fname):
    d.about(PROJECTS, ME, CONTACT)
    path = os.path.join(DST, fname + ".html")
    open(path, "w").write(d.html())
    issues = render(path, os.path.join(DST, fname + ".pdf"))
    os.remove(path)
    print(fname, len(d.slides), "slides", issues[:6])


# =============================================================== 01 appraising a signing
def deck01():
    s, dl, inp, sx = W["signing"], W["deal"], W["inputs"], W["signing_extra"]
    voi = s["voi"]
    top_voi = voi["Her true level (scouting, more data)"]
    d = Deck("01", "Appraising a signing", "", WSL + ". Fee, wages, injury rates and the value of a point are illustrative.")
    d.cover("Appraising a signing the way NICE appraises a medicine",
            "What should a club pay for a player, how sure can it be, and how should the deal be structured?",
            k(s["walk_away"]), f"walk-away price for a target priced at {k(inp['asking_fee'])}. At the asking price, the deal has a "
            f"{pc(s['p_worth'])} chance of paying off.", "Health technology assessment",
            ["Meta-analysis", "Markov model", "10,000 simulations", "Value of information", "Outcomes-based deal"],
            WSL + ". Fee, wages, injury rates and the value of a point are illustrative.")
    d.table("The question", "Every signing is a decision under uncertainty",
            ["The usual approach", "This approach"],
            [["Rank players on last season's numbers", "Estimate each player's true level, and check which numbers are reliable enough to recruit on"],
             ["Compare a target with an average player", "Compare her with the player she'd actually replace: that's the real gain"],
             ["One valuation, uncertainty left out", "The chance the deal pays off at every fee, and a walk-away price"],
             ["Scout and gather data the same way on everyone", "Value of information shows where extra scouting or medical work pays"],
             ["Argue about one fixed fee", "An outcomes-based deal that pays more only if she delivers"]],
            side="<p>A club makes a handful of big recruitment decisions a year, each with a lot of money and uncertainty attached.</p>"
                 "<p>The NHS faces the same problem every week: is a new medicine worth its price, with incomplete evidence and a fixed budget? "
                 "<b>NICE</b> answers it with a fixed sequence of questions. Each one has a direct football equivalent.</p>")
    d.steps("The approach", "Recruitment as an appraisal, in eight steps", [
        ("01 · SCOPE", "Who would she replace?", "The comparator is the player she'd replace, not an average player. Success is league points."),
        ("02 · EVIDENCE SYNTHESIS", "How good is she really?", "Random-effects meta-analysis, with players in place of trials, shrinks one noisy season towards the truth."),
        ("03 · DECISION MODEL", "What will she add?", "A Markov model of fitness and injury, and a league model that turns goals into points."),
        ("04 · PROBABILISTIC ANALYSIS", "How sure can we be?", "10,000 simulated versions of the signing, every input drawn from its plausible range."),
        ("05 · DECISION RULE", "What should we pay?", "The chance the signing pays off at every fee, and a walk-away price."),
        ("06 · VALUE OF INFORMATION", "What's worth finding out?", "Puts a price on each uncertainty, so scouting and medical budgets go where they pay."),
        ("07 · MANAGED ENTRY", "How should we structure it?", "Outcomes-based add-ons, as the NHS uses when a medicine's benefit is uncertain."),
        ("08 · LAB SCIENCE", "Which numbers can we trust?", "Reliability and reference change values, the checks labs run before acting on a result (project 03)."),
    ], ncol=4)
    d.table("The case", "An illustrative target, and every input with its source",
            ["Input", "Value used", "Basis"],
            [["Points per goal of goal difference", f"{W['league_model']['used_slope']:.2f}", f"Data: the {W['league_model']['teams']}-team table, R² {W['league_model']['r2']:.2f}"],
             ["Her true level (npxG + xA per 90)", f"{s['target_true']:.2f} (SD {s['target_true_sd']:.2f})", "Data: random-effects shrinkage of her season"],
             ["The player she'd replace", f"{s['comparator']:.2f}", f"Data: 25th percentile of {s['n_regular_fwd']} regular forwards"],
             ["Asking fee; extra wages", f"{k(inp['asking_fee'])}; {k(inp['extra_wages_per_season'])} a season", "Illustrative"],
             ["Value of a league point", k(inp["value_per_point"]), "Illustrative: prize money, survival, Europe"],
             ["Injury per match (short / long term)", f"{pc(inp['short_injury'], 1)} / {pc(inp['long_injury'], 1)}", "Illustrative: replace with club records or project 05"],
             ["Share of each match she plays; resale", f"{pc(inp['minutes_share'])}; {pc(inp['resale_share'])} of the fee", "Illustrative"],
             ["Discount rate", pc(inp["discount_rate"], 1) + " a year", "NICE reference case"]],
            side=f"<p>The target is the forward with the highest estimated true level outside the top four: <b>{inp['target_player']}</b> "
                 f"({sx['target_team']}, {sx['target_minutes']:.0f} minutes), at an asking fee of {k(inp['asking_fee'])}.</p>"
                 f"<p>Inputs that are data are estimated in the code. <b>Inputs that are assumptions are labelled illustrative</b>, "
                 f"and each is a slot for the club's own figures.</p>", numeric=[])
    d.table("Results", "From goals to a walk-away price, in six steps",
            ["Question", "Method", "Result"],
            [["What's a goal worth?", "League regression", f"Each goal of goal difference was worth {W['league_model']['used_slope']:.2f} points"],
             ["How good is she really?", "Random-effects meta-analysis", f"Raw {s['target_raw_per90']:.2f} per 90 becomes a true level of {s['target_true']:.2f}, against {s['comparator']:.2f} for the player she'd replace. {pc(sx['i2'])} of the variation between forwards is real"],
             ["How often will she play?", "Markov model", f"Fit for {pc(sx['fit_share'])} of matches over a two-season contract"],
             ["What will she add?", "Decision model", f"{s['points_mean']:.1f} extra points on average"],
             ["How sure can we be?", "10,000 simulations", neg(f"90% of outcomes between {s['points_p5']:.1f} and {s['points_p95']:.1f} points")],
             ["What should we pay?", "Acceptability analysis", f"{pc(s['p_worth'])} chance it pays off at {k(inp['asking_fee'])}. Walk away above {k(s['walk_away'])}"]])
    d.chart("The decision rule", f"At the asking price, it's a coin flip the club slightly loses", img("c1_bid"),
            f"<p>Net benefit = points × {k(inp['value_per_point'])} − net cost, at every possible fee, across the same 10,000 simulations.</p>"
            f"<p><b>{pc(s['p_worth'])}</b> chance the signing pays off at {k(inp['asking_fee'])}. Even on a free transfer it's only a "
            f"{pc(s['p_free'])} bet, because of her wages.</p>"
            f"<div class='callout'>Above <b>{k(s['walk_away'])}</b> the club expects to lose money. A clear walk-away price before "
            f"negotiations start stops a good player becoming a bad deal.</div>")
    d.chart("Value of information", "What's worth finding out before bidding", img("c2_voi"),
            f"<p>Perfect information about everything would be worth up to <b>{k(s['evpi'])}</b> for this one decision, and "
            f"<b>{k(top_voi, 1)}</b> of that is about her true level.</p>"
            f"<p>So: send the scouts again, or buy more data on her. A more detailed medical would add almost nothing here.</p>"
            f"<p>It's the method health economists use to decide which research is worth funding (Strong, Oakley and Brennan, 2014).</p>")
    d.numbers("Deal design", "Bridging the price gap with an outcomes-based deal", [
        (k(inp["asking_fee"]), "The seller's view", f"\"Look at last season.\" She produced {s['target_raw_per90']:.2f} xG + xA per 90, a pace of about {dl['pace_seller']:.0f} goals and assists over two seasons."),
        (k(s["walk_away"]), "The club's view", f"One season overstates her. Her true level is about {s['target_true']:.2f} per 90, so she's worth {k(s['walk_away'])} on average."),
        (f"{k(dl['upfront'])} + {k(dl['bonus'])}", "The deal", f"{k(dl['upfront'])} now, plus {k(dl['bonus'])} if she reaches {dl['hurdle']} goals and assists over two seasons: last season's pace."),
    ], foot=f"The NHS solves the same disagreement with <b>managed entry agreements</b>, where the price depends on results. The bonus is paid in "
            f"{pc(dl['p_hit_ours'])} of simulations, and only when she's delivered: {dl['points_if_hit']:.1f} extra points on average, against "
            f"{dl['points_if_miss']:.1f} when she falls short. On average the club pays its walk-away price.")
    d.chart("Deal design", "Three ways to pay for the same player", img("c3_deal"),
            f"<p>The chance of losing {k(50000)} or more falls from <b>{pc(dl['fixed_ask']['p_big_loss'])}</b> (fixed fee at the asking price) to "
            f"<b>{pc(dl['outcomes']['p_big_loss'])}</b> with the outcomes-based deal.</p>"
            f"<p>When the bonus is triggered, the signing pays off {pc(dl['worth_if_hit'])} of the time.</p>"
            f"<p>Any clause can be tested this way before it's offered: appearances, goals, minutes, sell-on.</p>")
    d.cards("Putting it to work", "What a club could use this for", [
        ("Recruitment", "A walk-away price for every target", "Set before negotiations start, with the chance the deal pays off at each fee."),
        ("Scouting budget", "Spend where it changes the decision", "Value of information says whether another scouting trip, more data or a fuller medical is worth paying for."),
        ("Deal structure", "Test any clause before offering it", "Bonuses, appearance clauses and sell-ons, priced against the club's own uncertainty."),
        ("Multi-club", "The same model across a group", "Run on every target in every club's market, with each club's own value of a point."),
    ], foot="Limits: the model values attacking output only; the money inputs are illustrative; the comparator's level is fixed. "
            "Each is a slot for a club's own data: tracking, medical records, wages and the value of a point in its league position.")
    finish(d, "01_Appraising_a_signing")


# =============================================================== 02 finishing
def deck02():
    fw, fm = W["finishing"], FIN["model"]
    sh = fw["shaw"]
    d = Deck("02", "Finishing: skill or luck?", "", WSL)
    d.cover("Finishing: skill or luck?",
            "When a striker scores far more than her expected goals, how much of it is skill that will carry on, and how much is luck?",
            f"±{100 * fw['spread']:.0f}%", "how much true finishing skill varies between WSL players once luck is removed. "
            "Raw conversion rates suggest far more.", "Evidence synthesis",
            ["Hierarchical Bayesian model", "Shrinkage", "Credible intervals", "Out-of-sample check"], WSL + "; men's top flights 2015/16 as a check")
    d.text("How it works", "One striking season from a small sample is usually partly luck",
           "<p>Each player has a <b>true finishing multiplier</b>: 1.2 means she scores 20% more than her chances deserve. "
           "A Bayesian model estimates how much these multipliers really vary across the league, then uses that to judge each player's season.</p>"
           "<p>Players with few shots are pulled strongly towards the average; players with many keep more of their own record.</p>",
           "<div class='callout'>It's the same logic as a <b>meta-analysis of small trials</b>, or ranking hospitals on small numbers of operations: "
           "one striking result from a small sample is usually partly luck.</div>"
           "<p style='margin-top:5mm'>Model: goals follow a Poisson distribution with mean xG × finishing multiplier; multipliers follow a Gamma "
           "distribution across players, with mean and spread estimated from the data; 4,000 posterior draws per player.</p>")
    d.chart("Women's game", "Raw finishing varies hugely; true finishing skill barely moves", img("c4_finishing"),
            f"<ul><li>Players scored <b>{fw['league_ratio']:.2f}</b> goals per 1.00 xG on average.</li>"
            f"<li>True finishing skill varies by only about <b>±{100 * fw['spread']:.0f}%</b> between players.</li>"
            f"<li>Of {fw['n15']} players with 15+ shots, <b>none</b> had a 90% chance of being a genuinely above-average finisher on one season's evidence.</li></ul>")
    d.chart("Women's game", "Khadija Shaw: probably good, not extraordinary", img("c7_intervals"),
            f"<p>Shaw scored <b>{sh['goals']} from {sh['xg']:.1f} xG</b>, a raw {sh['goals'] / sh['xg']:.2f}.</p>"
            f"<p>Her true finishing is more like <b>{sh['skill']:.2f}</b> (90% interval {sh['lo']:.2f} to {sh['hi']:.2f}): about a "
            f"{pc(sh['p_above'])} chance she's a genuinely above-average finisher.</p>"
            f"<p>Red crosses: what last season says. Green: what the evidence supports once luck is accounted for.</p>")
    d.design("Men's game", "Does it hold up? The same model on four men's leagues", [
        ("Data", f"{FIN['shots']:,} non-penalty shots with StatsBomb xG ({FIN['goals']:,} goals from {FIN['xg']:,.0f} xG) by {fm['players']:,} players, four leagues, 2015/16."),
        ("Model", "The same hierarchical (random-effects) Gamma-Poisson model as for the women's game. Posterior by grid approximation."),
        ("Check", f"Out of sample: does over-performance in the first half of the season predict the second half? {FIN['halves']['players']} players with 20+ shots in each half."),
        ("Code", "project2b_finishing_men.py")],
        side=f"<p>A much bigger sample, and a harder test.</p><p>If finishing were a stable skill, a striker who beats his xG before Christmas "
             f"should keep doing it after.</p>")
    d.chart("Men's game", "Over-performance didn't carry into the second half", img("finishing", doc=True),
            f"<ul><li>Raw spread among the {fm['regulars_40_shots']} players with 40+ shots: <b>±{100 * fm['raw_ratio_sd_regulars']:.0f}%</b>.</li>"
            f"<li>True skill spread: <b>±{100 * fm['spread']:.0f}%</b> (95% interval: almost nothing to {100 * fm['spread_hi']:.1f}%).</li>"
            f"<li>First-half over-performance against second half: <b>r = {neg(f2(FIN['halves']['r_finishing']))}</b>. Shot quality, by contrast: "
            f"r = {f2(FIN['halves']['r_shot_quality'])}.</li></ul>"
            + "".join(f"<p>{p['player']} scored {p['goals']} non-penalty goals from {p['xg']:.1f} xG, a raw {p['goals'] / p['xg']:.2f}; his true finishing "
                      f"is estimated at {p['skill']:.2f} (90% interval {p['skill_lo']:.2f} to {p['skill_hi']:.2f}).</p>" for p in FIN["top12"] if "Ibrahim" in p["player"]), scale=0.62, cols=2)
    d.cards("Putting it to work", "What a club could use this for", [
        ("Recruitment", "Value strikers on their chances", "The quality and volume of chances persist; a hot conversion rate is mostly noise until several seasons say otherwise."),
        ("Contracts", "Don't pay for a lucky season", "A striker coming off a hot finishing year is the classic overpay. The model says how much of it to believe."),
        ("Any small sample", "How much to trust a rate", "The same shrinkage sets how much to trust any per-player rate from limited minutes: academy, loans, new leagues."),
    ], foot="Limits: one season per player; with several seasons, real finishing differences of a few percent may become detectable. Results "
            "depend on the xG model, which doesn't see everything.")
    finish(d, "02_Finishing_skill_or_luck")


# =============================================================== 03 measurement science
def deck03():
    rel = {r["metric"]: r for r in W["reliability"]}
    cr = {r["metric"]: r for r in W["critical"]}
    cw = W["critical_watch"]
    fin = rel["Goals minus xG: finishing (forwards)"]
    fwx = cr["Forwards' npxG + xA"]
    d = Deck("03", "Measurement science", "", WSL + ". Outfield players with 10+ matches of 60+ minutes.")
    d.cover("Measurement science: which numbers to trust, and when form is real",
            "Before a lab acts on a blood test, it asks two questions: is the test reliable, and is the change bigger than normal day-to-day variation? "
            "Football data deserves the same checks.",
            f"{fin['matches_for_07']:.0f}", "matches before finishing (goals minus xG) becomes reliable enough to recruit on: nearly three WSL seasons.",
            "Clinical laboratory science", ["Split-half reliability", "Spearman-Brown", "Reference change values", "False discovery rate"],
            WSL + ". Outfield players with 10+ matches of 60+ minutes.")
    d.text("The question", "Two checks every lab runs, and most football numbers skip",
           "<p><b>1. Is the test reliable?</b> If a metric really measures the player, two random halves of her season should agree. "
           "Split-half reliability, scaled to a full season with the Spearman-Brown formula, says how much of the difference between players is real.</p>"
           "<p><b>2. Is the change real?</b> Labs use reference change values: how big a change must be before it's unlikely to be normal "
           "variation. The same formula applies to a player's match-to-match numbers.</p>",
           "<div class='callout'>A recruitment shortlist built on unreliable numbers is mostly a list of lucky players. "
           "A coaching conversation built on noise wastes everyone's time.</div>"
           f"<p style='margin-top:5mm'>Each player's matches split at random into two halves, 300 times. Reference change value = 1.96 × √2 × "
           f"the player's within-player coefficient of variation (Fraser and Harris, 1989).</p>")
    d.chart("Reliability", "Which numbers can you trust after one season?", img("c5_reliability"),
            f"<p>Passing and pressing settle in about <b>{rel['Passes']['matches_for_07']:.0f} matches</b>.</p>"
            f"<p>Chance quality (npxG + xA) needs about <b>{rel['npxG + xA (forwards)']['matches_for_07']:.0f}</b>.</p>"
            f"<p>Finishing needs about <b>{fin['matches_for_07']:.0f}</b>, nearly three seasons.</p>"
            f"<div class='callout'>Recruit on the reliable numbers. Treat the rest as hypotheses for scouts to test.</div>")
    d.chart("Critical differences", "How big must a change in form be before it's real?", img("c6_critical"),
            f"<p>One match can differ from the last by <b>{pc(cr['Passes']['one'])} to {pc(fwx['one'])}</b> with nothing real behind it.</p>"
            f"<p>Five-match form has to move by <b>{pc(cr['Passes']['five'])} to {pc(fwx['five'])}</b> before it's likely to mean something.</p>")
    d.numbers("A watch-list with false alarms controlled", "Most 'changes in form' are what chance alone produces", [
        (f"{cw['comparisons']}", "End-of-season changes", f"Each of {cw['players']} players' last 5 matches against all her earlier ones, on every metric."),
        (f"{cw['beyond_95']}", "Crossed the usual 95% line", f"About as many as chance alone would produce: {cw['by_chance']}."),
        (f"{cw['survive_fdr']}", "Survived false-discovery control", f"Benjamini-Hochberg at {pc(cw['fdr'])}: a short list of genuine changes worth a conversation."),
    ], foot="Genomics faced the same problem: test thousands of things and some will look significant by chance. Controlling the false "
            "discovery rate keeps the watch-list short and real.")
    d.cards("Putting it to work", "What a club could use this for", [
        ("Recruitment", "Recruit on reliable numbers", "Know which metrics measure the player after a season and which are mostly noise, by position and league."),
        ("Performance and medical", "A short list of real changes", "Flag genuine drops in physical or technical output for a conversation, without reacting to every bad game."),
        ("Coaching", "Judge form on evidence", "A shared rule for when a run of form is real, before it drives selection or contract decisions."),
    ], foot="Next step with a club's data: the same checks on tracking and GPS metrics, where within-player variation is smaller and changes can be detected sooner.")
    finish(d, "03_Measurement_science")


# =============================================================== 04 screening tests
def deck04():
    t = SCR["tests"]
    a, b = t["npxg_xa90_1"], t["ga90_1"]
    npx = t["npxg90_1"]
    dd = SCR["auc_diff_npxgxa_vs_ga"]
    d = Deck("04", "Scouting numbers as screening tests", "", MEN)
    d.cover("Scouting numbers judged like a screening test",
            "If a recruitment team shortlists attackers on their numbers from the first half of a season, how often does the shortlist "
            "contain the players who turn out to be most productive afterwards?",
            f"{a['auc']:.2f} vs {b['auc']:.2f}", "accuracy (AUC) of expected goals and assists against goals and assists, as a screening test "
            "for who performs best later in the season.", "Diagnostic accuracy",
            ["ROC / AUC", "Sensitivity and specificity", "Positive predictive value", "Bootstrap intervals"], MEN)
    d.design("Study design", "A diagnostic accuracy study, with no peeking at the future", [
        ("Design", "Chronological split: the test uses only each team's first 19 league matches, the outcome only the last 19."),
        ("Population", f"{SCR['cohort']['players']} attacking players (forwards, wingers, attacking and wide midfielders) with 900+ minutes in each half of 2015/16."),
        ("Reference standard", f"Top fifth of his league for non-penalty goals + assists per 90 in the second half ({SCR['cohort']['positives']} players)."),
        ("Index tests", "First-half goals + assists, goals, shots, npxG, and npxG + xA, each per 90. 'Positive' = top fifth on that number."),
        ("Measures", "AUC, sensitivity, specificity, PPV, likelihood ratio; 95% intervals from 2,000 bootstrap resamples."),
        ("Code", "project4_screening.py")],
        side="<p>Medicine judges a screening test on one question: of the people it flags, how many really have the condition, and how many does it miss?</p>"
             "<p>A shortlist is a screening test. So each scouting number can be scored the same way.</p>")
    d.chart("Results", "Expected goals ranked future performers better than goals did", img("screening", doc=True),
            f"<p>Picked at random, 1 in 5 shortlisted players would be a future top-fifth performer.</p>"
            f"<p>A shortlist built on goals + assists found <b>{pc(b['ppv'])}</b>; one built on npxG found <b>{pc(npx['ppv'])}</b>.</p>"
            f"<p>Across all thresholds npxG + xA ranked players better: AUC {a['auc']:.2f} against {b['auc']:.2f} "
            f"(difference {dd['diff']:.2f}, 95% CI {dd['lo']:.2f} to {dd['hi']:.2f}).</p>", cols=3, stack=True, scale=0.92)
    rows = []
    for c in ("ga90_1", "goals90_1", "shots90_1", "npxg90_1", "npxg_xa90_1"):
        v = t[c]
        rows.append([v["label"], f"{v['auc']:.2f} ({v['auc_lo']:.2f} to {v['auc_hi']:.2f})", pc(v["sens"]), pc(v["spec"]), pc(v["ppv"]), f"{v['lr_pos']:.1f}"])
    d.table("Results", "Every test, scored the way medicine scores a screen", ["Test (first half of season, per 90)", "AUC (95% CI)", "Sensitivity", "Specificity", "PPV", "LR+"],
            rows, hi=[3, 4], numeric=[1, 2, 3, 4, 5], split="cs",
            side=f"<p><b>Even the best number missed {pc(1 - npx['sens'])} of future top performers.</b></p>"
                 f"<p>With the outcome defined on second-half npxG + xA instead, npxG + xA still ranks best (AUC {SCR['tests_xref']['npxg_xa90_1']['auc']:.2f}).</p>"
                 f"<p>With {SCR['cohort']['players']} players, PPV differences between the better tests are within chance.</p>")
    d.steps("Putting it to work", "Screen in two stages, as medicine does", [
        ("STAGE 1", "A cheap data screen", "Rank every player in every covered league on the numbers that predict. Set the threshold by the cost of missing a player against the cost of a wasted scouting trip."),
        ("STAGE 2", "The confirmatory test", "Live scouting and video on the short list, where the expensive expertise goes."),
        ("CHECK", "Reliable and predictive", "Project 03 says which numbers are stable; this says which ones predict. A shortlist needs both."),
        ("AUDIT", "Score the process", "Track every shortlist's hit rate over time, as a screening programme audits itself."),
    ], foot="Limits: one season, attackers only; team context isn't modelled. Next step: the same study by position, across several seasons, with tracking-based metrics as index tests.")
    finish(d, "04_Scouting_numbers_as_screening_tests")


# =============================================================== 05 injuries
def deck05():
    i = INJ
    tm = {b["bin"]: b for b in i["timing"]}
    last, first = tm["75-90+"], tm["0-15"]
    pos = {p["group"]: p for p in i["position"]}
    lg = {l["league"]: l for l in i["by_league"]}
    rt = i["return"]
    d = Deck("05", "Injuries in matches", "", MEN)
    d.cover("Injuries in matches: what event data can and can't see",
            "How often do players have to come off injured, at what point in the match, and for how long are they missing afterwards? "
            "Can free event data measure this for any player in any covered league?",
            f"{last['rate_observable'] / first['rate_observable']:.1f}×", "the injury risk in the last 15 minutes against the first 15, once a "
            "recording bias is corrected. Taken at face value, the data say the opposite.", "Clinical epidemiology",
            ["Incidence rates", "Poisson regression", "Kaplan-Meier", "Ascertainment bias"], MEN)
    d.design("Study design", "A cohort of every appearance in four complete league seasons", [
        ("Data", f"{i['matches']:,} matches; {i['appearances']:,} appearances; {i['player_hours']:,.0f} player-hours on the pitch."),
        ("Case", f"A substitution recorded as caused by injury ('injury withdrawal'): {i['injury_withdrawals']} cases."),
        ("Exposure", "Minutes on the pitch from on and off times, stoppage time included."),
        ("Analysis", "Rates per 1,000 player-hours with exact Poisson intervals; timing by 15-minute period (Poisson regression); return to the matchday squad (Kaplan-Meier) against players substituted for tactical reasons."),
        ("Bias", "Ascertainment: with three substitutions allowed, once a team has used all three an injured player can't be withdrawn, so the injury never reaches the data. Rates are recalculated using only minutes when the team could still substitute."),
        ("Code", "build_tables.py, project5_injury.py")],
        side=f"<p>Clubs have medical records for their own players. For everyone else, recruitment and opposition staff rely on media reports.</p>"
             f"<p>Event data record every injury substitution, for every player, in every covered league.</p>")
    d.numbers("The headline numbers", "In-match injuries, and the minutes the data can't see", [
        (f"{i['overall_rate']['rate']:.1f}", "per 1,000 player-hours", f"Injury withdrawals (95% CI {i['overall_rate']['lo']:.1f} to {i['overall_rate']['hi']:.1f}), about {i['injury_withdrawals'] / 80:.1f} per team per season."),
        (pc(i["subs"]["share_with_none_left_by_85"]), "Out of substitutes by 85'", f"of teams had used all three substitutions by the 85th minute (median third change: {i['subs']['median_third_sub_clock']:.0f}')."),
        (pc(i["share_of_exposure_unobservable_75_90"]), "Unseen minutes", "of playing time in the last period of matches was time when an injury could not show up as a withdrawal."),
        (f"{i['stoppages']['per_match']:.1f}", "Treatment stoppages per match", f"{pc(i['stoppages']['share_followed_by_withdrawal'])} ended with that player withdrawn within 15 minutes."),
    ])
    d.chart("Timing", "Corrected, the last 15 minutes carry the highest risk of the match", img("inj_timing"),
            f"<p>Taken at face value, the last period looks safer than the one before ({last['rate_crude']:.1f} against {tm['60-75']['rate_crude']:.1f} per 1,000 hours). "
            f"<b>That's an artefact.</b></p>"
            f"<p>Counting only minutes in which an injury could be recorded, the last period's rate is <b>{last['rate_observable']:.1f}</b>, "
            f"{last['rate_observable'] / first['rate_observable']:.1f} times the first 15 minutes.</p>"
            f"<p>Within each half the risk rises by {pc(i['trend']['rr_per_15min_within_half'] - 1)} every 15 minutes, against "
            f"{pc(i['trend_crude']['rr_per_15min_within_half'] - 1)} before the correction. UEFA's injury study found the same rise.</p>")
    d.table("Who and where", "By position and by league", ["Group", "Cases", "Rate per 1,000 h (95% CI)", "Vs midfielders"],
            [["Goalkeepers", pos["GK"]["withdrawals"], f"{pos['GK']['rate']:.1f} ({pos['GK']['lo']:.1f} to {pos['GK']['hi']:.1f})", f"{pos['GK']['rr_vs_mid']:.2f}"],
             ["Defenders", pos["DEF"]["withdrawals"], f"{pos['DEF']['rate']:.1f} ({pos['DEF']['lo']:.1f} to {pos['DEF']['hi']:.1f})", f"{pos['DEF']['rr_vs_mid']:.2f}"],
             ["Midfielders", pos["MID"]["withdrawals"], f"{pos['MID']['rate']:.1f} ({pos['MID']['lo']:.1f} to {pos['MID']['hi']:.1f})", "reference"],
             ["Forwards", pos["FWD"]["withdrawals"], f"{pos['FWD']['rate']:.1f} ({pos['FWD']['lo']:.1f} to {pos['FWD']['hi']:.1f})", f"{pos['FWD']['rr_vs_mid']:.2f}"],
             ["Premier League", lg["Premier League"]["withdrawals"], f"{lg['Premier League']['rate']:.1f}", ""],
             ["La Liga", lg["La Liga"]["withdrawals"], f"{lg['La Liga']['rate']:.1f}", ""],
             ["Serie A", lg["Serie A"]["withdrawals"], f"{lg['Serie A']['rate']:.1f}", ""],
             ["Ligue 1", lg["Ligue 1"]["withdrawals"], f"{lg['Ligue 1']['rate']:.1f}", ""]],
            numeric=[1, 2, 3],
            side="<p>Defenders were withdrawn injured 24% more often per hour than midfielders; goalkeepers rarely.</p>"
                 "<p>Rates differed about 2-fold between leagues, which may reflect playing style, medical practice or how injuries were coded.</p>"
                 f"<p>As a rough check, injury withdrawals ran at {pc(i['share_of_uefa_time_loss'])} of UEFA's match rate for all time-loss injuries: "
                 f"event data seem to capture the injuries that stop a player finishing.</p>")
    d.chart("Afterwards", "How long players withdrawn injured were out", img("inj_return"),
            f"<p><b>{pc(rt['injury']['absent_next'])}</b> of players withdrawn injured missed their team's next league match, against "
            f"{pc(rt['tactical']['absent_next'])} after a tactical substitution.</p>"
            f"<p>{pc(rt['injury']['absent_next4'])} were still out four matches later, against {pc(rt['tactical']['absent_next4'], 1)}.</p>"
            f"<p>Each withdrawal cost about {rt['excess_matches_missed_per_withdrawal']:.1f} extra matches out of the squad over the next {rt['horizon']} league matches: "
            f"around {rt['excess_matches_per_team_season']:.0f} player-matches per team per season from in-match injuries alone.</p>")
    d.cards("Putting it to work", "What a club could use this for", [
        ("In-play", "The value of a substitution in hand", "Risk peaks in the final 15 minutes, just when most teams can no longer replace an injured player."),
        ("Medical and performance", "League-wide benchmarks", "In-match injury by position and period, for any league with event data, to compare a club's own record against."),
        ("Recruitment", "Availability for any target", "A target's injury withdrawals and time back in the squad, feeding availability into a valuation like project 01."),
    ], foot="Limits: no diagnosis or days lost; injuries that don't force a withdrawal are invisible; the time of withdrawal isn't always the time of injury. "
            "Teams now have five substitutions, so the bias is smaller today but still present late in matches.")
    finish(d, "05_Injuries_in_matches")


# =============================================================== 06 fatigue
def deck06():
    f = FAT
    late = f["mh_by_bin"]["75-90+"]
    d = Deck("06", "A fatigue signal in event data", "", MEN)
    d.cover("A fatigue signal in event data",
            "Tracking and GPS studies show high-intensity running falls late in matches, but a club only has that data for its own players. "
            "Can event data show the same thing for any player, including opponents and recruitment targets?",
            f"+{pc(late['rr'] - 1)}", "more pressing from a fresh substitute than from the same player as a starter in the last 15 minutes. "
            "Time-motion studies report a similar gap.", "Exercise physiology",
            ["Within-player design", "Mantel-Haenszel", "Cluster bootstrap", "Confounding"], MEN)
    d.design("Study design", "Each player compared only with himself, in the same situation", [
        ("Design", "Within-player comparison in the same period of matches: each player as a fresh substitute against the same player as a starter."),
        ("Data", f"{DATA['men_total']['pressures']:,.0f} pressures by outfield players in 1,517 matches (2015/16, four leagues), with minutes on the pitch in each 15-minute period."),
        ("Outcome", "Pressures per minute on the pitch: closing down the ball carrier is a repeated high-intensity action."),
        ("Analysis", "Mantel-Haenszel rate ratio, stratified by player × period × score state, so each player is only compared with himself in the same situation. 95% intervals from a cluster bootstrap over players (1,000 resamples)."),
        ("Bias", "Confounding: pressing also depends on tactics and the score (teams that lead sit deeper), and substitutes are different players from starters."),
        ("Code", "project6_fatigue.py")],
        side="<p>The physiology says players tire. The question is whether a signal survives in data that every club has on every player.</p>"
             "<p>The design borrows from epidemiology: stratify, so like is only compared with like.</p>")
    d.chart("Results", "Fresh legs press more, and the gap grows as the match goes on", img("fatigue", doc=True),
            f"<p>Players who completed 90 minutes pressed {pc(1 - f['within_match_decline']['75-90+']['rr'])} less in the last period than in the first 15 minutes.</p>"
            f"<p>Against themselves in the same period and score state, fresh substitutes pressed {pc(f['mh_by_bin']['45-60']['rr'] - 1)} more just after half-time, "
            f"{pc(f['mh_by_bin']['60-75']['rr'] - 1)} more from 60', and <b>{pc(late['rr'] - 1)} more from 75'</b> (95% CI {pc(late['lo'] - 1)} to {pc(late['hi'] - 1)}).</p>"
            f"<p>Without the matching, the gap from 60' looks like {pc(f['crude_late']['rr'] - 1)} rather than {pc(f['mh_late']['rr'] - 1)}.</p>"
            , stack=True, scale=0.8)
    d.numbers("Against the physiology literature", "Event data, with no tracking at all, show the same pattern", [
        (f"+{pc(late['rr'] - 1)}", "Event data, this study", "Fresh substitutes against the same players as starters, last 15 minutes, matched on score state."),
        ("+25%", "Time-motion analysis", "Substitutes covered 25% more high-intensity running than other players in the final 15 minutes (Mohr, Krustrup and Bangsbo, 2003)."),
        (f"+{pc(f['mh_by_position']['FWD']['rr'] - 1)}", "Forwards, this study", "The gap is biggest for forwards on the point estimates, and grows the longer the starter has played."),
    ], foot="Same direction, same timing, from data every club already has on every player in every covered league.")
    d.cards("Putting it to work", "What a club could use this for", [
        ("In-play", "Planned changes in pressing roles", "The signal appears after 60' and is strongest late on, especially in forwards."),
        ("Recruitment and opposition", "A physical proxy without GPS", "A late-match output profile for players a club has no tracking or GPS data on."),
        ("Next step", "Validate against tracking", "Test a player-level version against a club's own tracking data, then use it where tracking isn't available."),
    ], foot="Limits: pressing also depends on how much the opponent has the ball; players aren't randomly chosen to start; substitutes may be told to press; "
            "a reliable player-by-player measure isn't yet established.")
    finish(d, "06_A_fatigue_signal_in_event_data")


# =============================================================== 07 team strength
def deck07():
    lu, rel, pr = TS["luck"], TS["reliability"], TS["prognostic"]
    tab = {r["team"]: r for r in TS["season_table"]}
    lei, atl, tou = tab["Leicester City"], tab["Atlético Madrid"], tab["Toulouse"]
    wom = TS.get("women", {})
    d = Deck("07", "How good is a team, really?", "", MEN)
    d.cover("How good is a team, really?",
            "When a club is assessed for an acquisition, a partnership or a season review, how much of its league position is the quality "
            "of its football, and how much is chance? Which numbers tell you, and after how many matches?",
            f"{rel['pts']['m80']:.0f} vs {rel['xgd']['m80']:.0f}", "matches before points, and before expected-goal difference, measure a team "
            "reliably (0.8). A season of points tells you about as much as half a season of chances.", "Risk-adjusted outcomes",
            ["Observed vs expected", "Poisson-binomial", "Reliability", "Prognostic validation"], MEN + "; " + WSL4 + " as a check")
    d.text("The question", "Hospitals are judged on risk-adjusted outcomes. Clubs can be too.",
           "<p>The NHS doesn't judge a cardiac surgeon on raw death rates: a surgeon who takes the hardest cases would look worst. "
           "It compares <b>observed outcomes against expected</b>, given each patient's risk, and asks whether the gap is bigger than chance.</p>"
           "<p>A league table is a raw outcome. Expected points are the risk adjustment: what the chances each team created and conceded "
           "would earn on average.</p>",
           "<p><b>Who needs the answer:</b></p><ul>"
           "<li>Ownership and multi-club groups doing football due diligence on an acquisition or partner club.</li>"
           "<li>A technical director reviewing a season, or a head coach.</li>"
           "<li>Recruitment, judging the level of a selling club and its league.</li></ul>")
    d.steps("Method", "Expected points, built from every chance", [
        ("01", "Every shot", "Each shot's StatsBomb expected goals (penalties included; own goals carry no xG)."),
        ("02", "Possessions, not shots", "Shots in the same possession combined, 1 − ∏(1 − xG), so a rebound isn't a second, independent chance."),
        ("03", "Goals as a distribution", "Each team's goals follow a Poisson-binomial distribution over its chances; the two combine into P(win), P(draw), P(loss)."),
        ("04", "Expected points and their spread", "3 × P(win) + P(draw) per match, summed over the season, with the variance chance alone would produce."),
    ], lead=f"{TS['luck']['teams']} teams in four leagues, {TS['luck']['matches_per_team']:.0f} matches each, plus "
            f"{wom.get('team_seasons', 0)} team-seasons in the WSL as a check.")
    d.chart("Observed against expected", "Most of the gap between the table and the chances is chance", img("c7_table"),
            f"<p>The spread of points minus expected points was <b>{lu['sd_obs']:.1f}</b> points a season. Chance alone, given the chances "
            f"each team had, would produce <b>{lu['sd_chance']:.1f}</b>.</p>"
            f"<p>So about <b>{pc(lu['share_chance'])}</b> of the gap between where teams finished and where their chances put them is luck.</p>"
            f"<p>{lu['outside95']} teams sat outside the 95% band, against {lu['expected_outside95']:.0f} expected by chance: "
            f"elite finishing or goalkeeping, game management, or luck.</p>")
    d.numbers("Cases", "Three seasons the table told differently", [
        (f"{lei['pts']} vs {lei['xpts']:.0f}", "Leicester City, Premier League", f"Champions on {lei['pts']} points; their chances were worth {lei['xpts']:.0f}, {ordinal(lei['rank_xpts'])} in the league. Genuinely good, and lucky."),
        (f"{atl['pts']} vs {atl['xpts']:.0f}", "Atlético Madrid, La Liga", f"The biggest over-performance in four leagues: {atl['ga']} goals conceded from {atl['npxga']:.1f} non-penalty xG against. Chances {ordinal(atl['rank_xpts'])}, table {ordinal(atl['rank_pts'])}."),
        (f"{tou['pts']} vs {tou['xpts']:.0f}", "Toulouse, Ligue 1", f"The biggest under-performance: chances worth {ordinal(tou['rank_xpts'])} place; they finished {ordinal(tou['rank_pts'])}."),
    ], foot=f"In {lu['rank_changes']} of {lu['teams']} cases a team's league position differed from its rank on expected points.")
    d.chart("Reliability", "How many matches before the numbers measure the team?", img("c7_reliability"),
            f"<p>Split-half reliability, as in project 03: random halves of each team's season, 300 times.</p>"
            f"<p><b>Points</b> need {rel['pts']['m70']:.0f} matches to reach 0.7 and {rel['pts']['m80']:.0f} to reach 0.8.</p>"
            f"<p><b>Expected-goal difference</b> needs {rel['xgd']['m70']:.0f} and {rel['xgd']['m80']:.0f}.</p>"
            f"<div class='callout'>A full season of points (reliability {rel['pts']['season']:.2f}) tells you about as much as "
            f"{rel['xgd']['m80']:.0f} matches of expected-goal difference.</div>")
    dd = TS["prognostic_diff_xgd_vs_pts"]
    d.chart("Prognostic validation", "Which first-half number best predicts the second half?", img("c7_prognostic"),
            f"<p>Chronological split, as a prognostic model is validated: first 19 matches against points per game in the last 19.</p>"
            f"<p>Expected-goal difference: r = <b>{pr['xgd']['r']:.2f}</b>. Points: r = <b>{pr['pts']['r']:.2f}</b>.</p>"
            f"<p>Calibrated out of sample (leave one league out), the typical error over 19 matches was {pr['xgd']['mae_pts19']:.1f} points against "
            f"{pr['pts']['mae_pts19']:.1f}.</p>"
            f"<p>The difference in correlation ({dd['diff']:.2f}, 95% CI {neg(f2(dd['lo']))} to {dd['hi']:.2f}) is within chance with 80 teams: "
            f"chance quality is at least as good a guide as points, and arrives sooner.</p>")
    d.cards("Putting it to work", "A due diligence report on any club with event data", [
        ("True level", "How good is it, really?", "Expected-goal difference with its uncertainty, against the league, not just the table."),
        ("Luck", "What did the table flatter?", "Points against expected points, and whether the gap is bigger than chance."),
        ("Evidence", "How much can we trust it?", "How many matches of evidence there are, and how reliable each number is at that sample size."),
        ("Style and set pieces", "How does it play?", "The game-model profile from project 09 and the set-piece edge from project 10."),
    ], foot=f"Women's game check ({', '.join(wom.get('seasons', []))}): the spread of points minus expected points was {wom.get('sd_obs', 0):.1f} against "
            f"{wom.get('sd_chance', 0):.1f} from chance alone. Limits: xG doesn't see everything (finishing and goalkeeping skill, game state); one season of men's data.")
    finish(d, "07_How_good_is_a_team_really")


# =============================================================== 08 coaches
def deck08():
    ba = CO["before_after"]
    r = ba["results"]
    d = Deck("08", "Judging a head coach", "", MEN + ". Head coaches as named in StatsBomb's match data.")
    d.cover("Judging a head coach",
            "Which head coaches got more, or less, from their teams' chances than chance alone explains? And when a club changes its coach "
            "mid-season, do results improve because of the change, or would they have bounced back anyway?",
            neg(f"{r['pts']['effect'][0]:+.2f}"), f"points per match: the effect of a mid-season change of head coach, against teams in the same "
            f"slump that kept theirs ({ba['changes']} changes; 95% CI {neg(f2(r['pts']['effect'][1]))} to {r['pts']['effect'][2]:+.2f}).",
            "Funnel plots and regression to the mean", ["Funnel plot", "Controlled before-and-after", "Matched controls", "Regression to the mean"],
            MEN + ". Head coaches as named in StatsBomb's match data.")
    d.text("The method", "Heart surgeons are judged on funnel plots, so chance isn't mistaken for skill",
           "<p>Since the Bristol heart inquiry, UK cardiac surgery has published risk-adjusted outcomes by hospital, and since 2005 by named "
           "surgeon, using <b>funnel plots</b> to spot outliers: observed against expected outcomes, plotted against how many operations each did. "
           "Control limits narrow as the evidence grows, so a surgeon with a few bad cases isn't hounded, and a real outlier stands out.</p>"
           "<p>A head coach is judged on a small, noisy sample too. Here: each coaching spell's points against expected points "
           "(project 07), per match, against matches in charge.</p>",
           "<div class='callout'>Points above expected aren't all coaching. They include finishing, goalkeeping and game management, "
           "and luck. The funnel says which gaps are <b>bigger than luck alone</b>.</div>"
           f"<p style='margin-top:5mm'>{CO['spells']} coaching spells of 5+ league matches across four leagues in 2015/16.</p>")
    d.chart("Funnel plot", "Few coaching spells stand out from chance", img("c8_funnel"),
            f"<p><b>{CO['outside95']}</b> of {CO['spells']} spells sat outside the 95% limits, against {CO['expected_outside95']:.0f} expected by chance; "
            f"none outside the 99.8% limits.</p>"
            f"<p>Above: Ranieri (Leicester), Simeone (Atlético Madrid) and Marcelino (Villarreal) over full seasons; Zidane, Spalletti and Hantz in half-seasons at Real Madrid, Roma and Montpellier.</p>"
            f"<p>Below: Sherwood (Aston Villa), Moyes (Real Sociedad), Arribagé (Toulouse) and Castori (Carpi). <b>All four were replaced that season.</b></p>")
    d.design("Study design", "Does a mid-season change work? A controlled before-and-after study", [
        ("Changes", f"Every mid-season change of head coach in four leagues, 2015/16: {ba['changes']} with {ba['window']} league matches either side ({', '.join(f'{v} {k}' for k, v in ba['by_league'].items())})."),
        ("Comparison", f"Team-moments with no change within {ba['window']} matches either side, matched on points from the previous {ba['window']} matches and, among those, the {ba['controls_per_change']} closest on expected points."),
        ("Outcomes", "Points per match, and expected points per match (chance quality), before and after."),
        ("Analysis", "Difference in change, changed against matched controls, with bootstrap 95% intervals over the changes."),
        ("Bias", "Regression to the mean: clubs change coach after a bad run, and bad runs end on their own. Without a comparison group, every change looks like it works."),
        ("Code", "project8_coaches.py")],
        side=f"<p>Before the change, teams averaged <b>{ba['ppg_pre']:.2f}</b> points per match, against a league average of {ba['league_ppg']:.2f}.</p>"
             f"<p>They were also unlucky: <b>{neg(f2(ba['pre_luck']))}</b> points per match below what their chances deserved.</p>")
    d.chart("Results", "Results recovered after a change, and just as much without one", img("c8_before_after"),
            f"<p>Teams that changed coach went from <b>{ba['ppg_pre']:.2f}</b> to <b>{ba['ppg_post']:.2f}</b> points per match.</p>"
            f"<p>Teams in the same slump that kept their coach went from <b>{ba['c_ppg_pre']:.2f}</b> to <b>{ba['c_ppg_post']:.2f}</b>.</p>"
            f"<p>Effect of the change: <b>{neg(format(r['pts']['effect'][0], '+.2f'))}</b> points per match "
            f"(95% CI {neg(f2(r['pts']['effect'][1]))} to {r['pts']['effect'][2]:+.2f}). On chance quality: {r['xpts']['effect'][0]:+.2f} "
            f"({neg(f2(r['xpts']['effect'][1]))} to {r['xpts']['effect'][2]:+.2f}).</p>")
    d.statement("What it means", "Most of the 'new manager bounce' is <em>regression to the mean</em>.",
                "Clubs tend to change coach at the bottom of a run that was partly bad luck. Results then recover, with or without a new coach. "
                "That doesn't mean coaches don't matter: it means a few bad weeks of points can't tell a club whether its coach is the problem.")
    d.cards("Putting it to work", "What a technical director could use this for", [
        ("Coach evaluation", "Judge the process, with limits", "Track chance quality for and against on a funnel, so a run of results is read against what chance alone produces."),
        ("Decision rule", "Before changing coach", "Ask whether the slump is in the chances or only in the results. If the chances are fine, the evidence says wait."),
        ("Hiring", "Read a candidate's record properly", "Over- or under-performance in a short spell is mostly noise; a long spell outside the limits is worth understanding."),
    ], foot=f"Limits: {ba['changes']} changes in one season, so effects of a few tenths of a point per match can't be ruled in or out; coaches aren't changed at "
            f"random; points above expected also reflect players. Next step: more seasons and leagues, and the same design for academy and women's teams.")
    finish(d, "08_Judging_a_head_coach")


# =============================================================== 09 game model
def deck09():
    rel, gs, K = GM["reliability"], GM["game_state"], GM["kpis"]
    pca, comp, resp = GM["pca"], GM["composite"], GM["responsiveness"]
    wom = GM.get("women", {})
    fast = [c for c in rel if rel[c]["m80"] <= 12]
    slow = [c for c in rel if rel[c]["m80"] > 38]
    d = Deck("09", "Measuring a game model", "", MEN + "; " + WSL4)
    d.cover("Measuring a game model",
            "A club's methodology says how its teams should play. Can free event data measure that well enough to check a team is playing "
            "the intended way, compare teams across a group, and find players and partner clubs from similar systems?",
            f"{len(rel)} KPIs", f"validated the way a clinical questionnaire is: {len(fast)} measure a team's style within about 12 matches, "
            f"{len(slow)} are still mostly noise after a season.", "Measurement validation (COSMIN)",
            ["Reliability", "Construct validity", "Factor structure", "Responsiveness", "Men's and women's game"], MEN + "; " + WSL4)
    d.text("The question", "A game model is only useful if you can measure it",
           "<p>Medicine doesn't use a questionnaire to measure pain or quality of life until it has been <b>validated</b>: is it reliable, "
           "does it measure what it claims, does it move when the patient changes? The COSMIN checklist sets out the tests.</p>"
           "<p>Style KPIs are a club's questionnaire for its game model. Pressing height, directness, possession: the same tests apply.</p>",
           "<p><b>Five checks, each with a football question:</b></p><ul>"
           "<li><b>Reliability</b>: after how many matches does a KPI measure the team rather than the opponent and the day?</li>"
           "<li><b>Stability</b>: does it agree between the two halves of a season, and across seasons?</li>"
           "<li><b>Construct validity</b>: does it move with game state the way every coach knows teams do?</li>"
           "<li><b>Structure</b>: how many separate dimensions of style are there?</li>"
           "<li><b>Responsiveness</b>: does it pick up a change of head coach?</li></ul>")
    dims = {}
    for c in ["poss", "tilt", "ppp", "tempo", "long", "ppda", "press_h", "line", "cp", "regain", "width", "cross", "counter", "xg_shot", "sp"]:
        dims.setdefault(K[c]["dim"], []).append(K[c]["label"])
    d.cards("The instrument", f"{len(rel)} style KPIs from event data, in four intended dimensions",
            [(f"{len(v)} KPIs", dname, "<br>".join(v)) for dname, v in dims.items()],
            lead="Every KPI is computed per team per match from StatsBomb events, for 80 men's teams and 47 WSL team-seasons.",
            foot="PPDA: opponent passes in their own 60% of the pitch per defensive action there. Heights are measured in yards from the team's "
                 "own goal line. Set-piece and counter-attack shares use the same definitions as projects 07 and 10.")
    d.chart("Reliability", "Build-up style shows in a month; pressing takes a season", img("c9_reliability"),
            f"<p><b>Fast:</b> passes per possession ({rel['ppp']['m80']:.0f} matches), long-ball share ({rel['long']['m80']:.0f}), tempo "
            f"({rel['tempo']['m80']:.0f}), possession ({rel['poss']['m80']:.0f}).</p>"
            f"<p><b>Slow:</b> PPDA ({rel['ppda']['m80']:.0f}), pressure height ({rel['press_h']['m80']:.0f}), line height ({rel['line']['m80']:.0f}), "
            f"counterpressing ({rel['cp']['m80']:.0f}).</p>"
            f"<p><b>Not yet a team measure:</b> high regains ({rel['regain']['m80']:.0f}), set-piece share ({rel['sp']['m80']:.0f}), "
            f"counter-attack share ({rel['counter']['m80']:.0f}).</p>"
            f"<div class='callout'>A new coach's pressing can't be judged on a month of data. His build-up can.</div>", cols=4, scale=0.9)
    d.chart("Construct validity", "The KPIs move with the score exactly as coaches expect", img("c9_game_state"),
            f"<p>When trailing rather than leading, the same teams had more of the ball (<b>{pc(gs['poss']['lead'])} → {pc(gs['poss']['trail'])}</b>, "
            f"{pc(gs['poss']['share_teams_same_direction'])} of teams), more territory ({pc(gs['tilt']['lead'])} → {pc(gs['tilt']['trail'])}), "
            f"pressed {gs['press_h']['diff']:.1f} yards higher ({pc(gs['press_h']['share_teams_same_direction'])} of teams) and defended "
            f"{gs['line']['diff']:.1f} yards higher ({pc(gs['line']['share_teams_same_direction'])}).</p>"
            f"<p>A valid measure has to show the shifts everyone knows happen. It also means style must be compared at the same score.</p>")
    most = ", ".join(x["team"] for x in comp["most_press_for_control"][:5])
    least = ", ".join(x["team"] for x in comp["least_press_for_control"][:4])
    d.chart("Structure", "Two main dimensions: control with the ball, pressing without it", img("c9_style_map"),
            f"<p>One dimension explains <b>{pc(pca['var_explained'][0])}</b> of the variation between teams: control (possession, territory, "
            f"patient build-up, a high line). The next explains {pc(pca['var_explained'][1])}.</p>"
            f"<p>Control and pressing go together (r = {comp['r_control_press']:.2f}), so the identity is in the gap: "
            f"<b>{most}</b> pressed more than their control predicts; {least} pressed less.</p>")
    tw = GM["twins"]
    d.table("Application", "Style twins: which clubs play most like each other?", ["Team", "Most similar styles, across four leagues"],
            [[t, ", ".join(f"{x['team']}" for x in tw[t][:4])] for t in tw],
            side="<p>Distance across all KPIs, standardised. Because the comparison is on style, not quality, it works across leagues.</p>"
                 "<p>For a multi-club group: which partner club plays closest to the parent club's model, so a player can move between them "
                 "with the least adaptation. For recruitment: which systems a target already knows.</p>", split="cs")
    rf = resp["fast_kpis"]
    d.numbers("Stability and responsiveness", "Style persists, and a new coach rarely changes it fast", [
        (f"{wom.get('season_to_season', {}).get('poss', 0):.2f}", "Possession, season to season (WSL)",
         f"Team style carried from one season to the next: territory {wom.get('season_to_season', {}).get('tilt', 0):.2f}, passes per possession "
         f"{wom.get('season_to_season', {}).get('ppp', 0):.2f}, pressure height {wom.get('season_to_season', {}).get('press_h', 0):.2f} ({wom.get('pairs', 0)} team pairs)."),
        (f"{rel['ppp']['test_retest']:.2f}", "First half vs second half (men)", f"Passes per possession; pressing KPIs {rel['ppda']['test_retest']:.2f} to {rel['press_h']['test_retest']:.2f}."),
        (f"{rf['ratio']:.2f}×", "Style shift after a coach change", f"Against normal 6-match drift, on the fast KPIs (95% CI {rf['ratio_lo']:.2f} to {rf['ratio_hi']:.2f}; {rf['changes']} changes)."),
    ], foot="Mid-season changes mostly didn't change how teams played within six matches, which fits project 08: the bounce in results wasn't "
            "a new style, it was the bad luck ending.")
    d.cards("Putting it to work", "What a club could use this for", [
        ("Methodology", "Is the team playing our way?", "A validated KPI set for the game model across men's, women's and academy teams, with the matches each needs."),
        ("Coach hiring", "Does a candidate's football fit?", "A candidate's teams profiled on the same KPIs, compared at the same game state."),
        ("Multi-club", "Align a group", "Which partner clubs play closest to the model, and which players would adapt fastest between them."),
        ("Recruitment", "System fit", "Players from teams with similar styles; style-adjusted numbers for those from different ones."),
    ], foot="Limits: event data, not tracking (no off-ball positions); one men's season; KPIs measured over all game states except where stated. "
            "Next step: the same validation on tracking-based KPIs and a club's own coded game-model moments.")
    finish(d, "09_Measuring_a_game_model")


# =============================================================== 10 set pieces
def deck10():
    m, w = SP["men"], SP.get("women", {})
    r, e, vq = m["rel"], m["edge"], m["volume_quality"]
    d = Deck("10", "Set pieces as an investment", "", MEN + "; " + WSL4)
    d.cover("Set pieces as an investment",
            "Is a team's set-piece quality a repeatable characteristic, and so something coaching can change? If it is, how big is the gap "
            "between good and poor set-piece teams, in goals and points a season?",
            pc(m["share_np_goals"]), "of non-penalty goals in four men's top flights came from set pieces, from "
            f"{pc(m['share_shots'])} of shots.", "Reliability and cost-effectiveness",
            ["Split-half reliability", "Signal and noise", "Points per goal", "Men's and women's game"], MEN + "; " + WSL4)
    d.text("Definitions", "What counts as a set piece, and what's measured",
           "<p>A set-piece shot is a direct free kick or corner, or a shot within 20 seconds of a corner, free kick or throw-in taken "
           "in the final third, in the same possession. Penalties are excluded throughout.</p>"
           f"<p>Teams took about <b>{vq['sp_per_match']:.0f}</b> attacking set pieces a match (corners, final-third free kicks and throw-ins), "
           f"worth <b>{vq['xg_per_100_sp']:.1f}</b> xG per 100.</p>",
           "<p><b>Three questions:</b></p><ul><li>Is set-piece xG, for and against, a stable characteristic of a team, or mostly noise?</li>"
           "<li>How much of it is simply dominance (better teams win more corners), and how much is the quality of each delivery?</li>"
           "<li>What is a realistic edge worth, in goals and points?</li></ul>")
    d.chart("Reliability", "Set-piece numbers are real, but noisier than open play", img("c10_reliability"),
            f"<p>Over a season, set-piece xG difference had a reliability of <b>{r['xgd_sp']['season']:.2f}</b>, against "
            f"{r['xgd_op']['season']:.2f} for open play. It needs about {r['xgd_sp']['m80']:.0f} matches to reach 0.8, against {r['xgd_op']['m80']:.0f}.</p>"
            f"<p>Defending set pieces was the least stable: {r['xg_sp_a']['season']:.2f}.</p>")
    d.numbers("Volume and quality", "Much of a set-piece edge is dominance; delivery quality is the coachable part", [
        (f"{vq['r_volume_openplay']:.2f}", "Volume follows dominance", "Correlation between set pieces won (minus conceded) and open-play xG difference: better teams simply win more of them."),
        (f"{vq['rel_q_for']['season']:.2f}", "Attacking delivery quality", f"Season reliability of xG per attacking set piece, almost unrelated to dominance (r = {vq['r_qfor_openplay']:.2f})."),
        (f"{vq['rel_q_against']['season']:.2f}", "Defending quality", "Season reliability of xG conceded per set piece: mostly noise within one season."),
    ], foot=f"The teams' observed attacking quality ranged from {vq['q_for_p10']:.1f} to {vq['q_for_p90']:.1f} xG per 100 set pieces (10th to 90th percentile). "
            f"After removing noise, one standard deviation of true quality is worth about {vq['goals_season_1sd_q_for']:.1f} goals a season.")
    d.chart("The edge", "Who had it in 2015/16", img("c10_map"),
            f"<p>Best set-piece xG difference per match: {', '.join(x['team'] for x in m['best'][:3])}.</p>"
            f"<p>Worst: {', '.join(x['team'] for x in m['worst'][:3])}.</p>"
            f"<p>{m['best'][0]['team']} scored {m['best'][0]['goals_for']} non-penalty set-piece goals and conceded {m['best'][0]['goals_against']}; "
            f"{m['worst'][0]['team']} scored {m['worst'][0]['goals_for']} and conceded {m['worst'][0]['goals_against']}.</p>")
    d.numbers("What it's worth", "A realistic edge, in goals and points", [
        (f"{e['p90_vs_p10_goals']:.0f} goals", "Best vs worst teams", f"Gap in true set-piece xG difference a season between the 90th and 10th percentile team, after removing noise."),
        (f"{e['p90_vs_p10_points']:.1f} pts", "In league points", f"At {m['points_per_goal']:.2f} points per goal of goal difference, estimated from the four league tables."),
        (f"{vq['goals_season_1sd_q_for']:.1f} goals", "Better delivery alone", "One standard deviation of true attacking quality per set piece, at average volume."),
    ], foot="Money is left out: what a point is worth depends on where a club sits. With a club's own figures this becomes a cost-effectiveness "
            "question, as in health economics: the cost per extra point from set-piece coaching, against the cost per point of a signing (project 01).")
    d.cards("Putting it to work", "What a club could use this for", [
        ("Investment case", "Is a set-piece specialist worth it?", "Expected goals and points from a realistic improvement, against the cost."),
        ("Measurement", "Judge the coach on the right number", "xG per delivery, not goals, and over enough matches: one season is not enough for defending."),
        ("Due diligence", "Read a team's set-piece record", "Separate an edge that follows dominance from one that is genuinely coached (project 07)."),
    ], foot=f"Women's game ({w.get('label', '')}): {pc(w.get('share_np_goals', 0))} of non-penalty goals from set pieces; set-piece xG difference more reliable "
            f"({w.get('rel', {}).get('xgd_sp', {}).get('season', 0):.2f}) but closely tied to dominance (r = {w.get('volume_quality', {}).get('r_spd_openplay', 0):.2f}). "
            f"Limits: xG, not delivery or tracking data; one men's season.")
    finish(d, "10_Set_pieces_as_an_investment")


if __name__ == "__main__":
    which = sys.argv[1:] or ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"]
    for w_ in which:
        globals()["deck" + w_]()
