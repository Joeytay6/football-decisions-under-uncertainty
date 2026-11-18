"""Slide builders for the project decks (16:9, printed to PDF with Chrome)."""
import base64, html, os, re

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
W, H = 338.67, 190.5
PITCH_DARK = open(os.path.join(ASSETS, "pitch_dark.svg")).read()
PITCH_LIGHT = open(os.path.join(ASSETS, "pitch_light.svg")).read()

CSS = open(os.path.join(ASSETS, "base.css")).read() + f"""
@page{{size:{W}mm {H}mm;margin:0}}
.s{{width:{W}mm;height:{H}mm;position:relative;overflow:hidden;background:var(--paper);page-break-after:always;break-after:page}}
.s.dark{{background:var(--ink);color:var(--chalk)}}
.hd{{position:absolute;left:16mm;right:16mm;top:9mm;display:flex;justify-content:space-between;font-family:var(--mono);font-size:7.2pt;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}}
.dark .hd{{color:var(--chalk2)}}
.hd .pn{{color:var(--green)}} .dark .hd .pn{{color:var(--lime)}}
.ft{{position:absolute;left:16mm;right:16mm;bottom:7.5mm;display:flex;justify-content:space-between;font-family:var(--mono);font-size:6.6pt;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}}
.dark .ft{{color:var(--chalk2)}}
.body{{position:absolute;left:16mm;right:16mm;top:19mm;bottom:15mm;display:flex;flex-direction:column}}
.kick{{font-family:var(--mono);font-size:8.2pt;letter-spacing:.16em;text-transform:uppercase;color:var(--green);margin-bottom:2.5mm}}
.dark .kick{{color:var(--lime)}}
h1.t{{font-family:var(--disp);font-weight:600;font-size:35pt;line-height:1.0;letter-spacing:-.005em;margin-bottom:6.5mm;max-width:290mm}}
h1.t em{{font-style:normal;color:var(--green)}} .dark h1.t em{{color:var(--lime)}}
p.lead{{font-size:13.6pt;line-height:1.5;max-width:270mm;color:#24302b}}
.dark p.lead{{color:var(--chalk)}}
.txt p{{font-size:12.6pt;line-height:1.5;margin-bottom:3.6mm;color:#26312c}}
.dark .txt p{{color:var(--chalk)}}
.txt p b{{color:var(--ink)}} .dark .txt p b{{color:#fff}}
.txt ul{{list-style:none;margin:0 0 3mm}} .txt li{{font-size:12.4pt;line-height:1.48;padding-left:5.5mm;position:relative;margin-bottom:2.2mm;color:#26312c}}
.txt li:before{{content:"";position:absolute;left:0;top:2.6mm;width:2.6mm;height:1mm;background:var(--green)}}
.dark .txt li{{color:var(--chalk)}} .dark .txt li:before{{background:var(--lime)}}
.lbl{{font-family:var(--mono);font-size:7.4pt;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin-bottom:1.6mm}}
.dark .lbl{{color:var(--chalk2)}}
.rule{{border-top:.6pt solid var(--line);margin:3mm 0}} .dark .rule{{border-color:var(--ink3)}}
/* cover */
.cov .pitch{{position:absolute;right:-30mm;top:-6mm;width:250mm;opacity:.9}}
.cov .no{{position:absolute;left:16mm;top:30mm;font-family:var(--disp);font-weight:700;font-size:58pt;line-height:1;color:var(--lime)}}
.cov .ti{{position:absolute;left:16mm;top:54mm;width:205mm}}
.cov .ti h1{{font-family:var(--disp);font-weight:600;font-size:52pt;line-height:.95;color:#fff;margin-bottom:5mm}}
.cov .ti p{{font-size:14.2pt;line-height:1.45;color:var(--chalk);max-width:190mm}}
.cov .hero{{position:absolute;right:16mm;bottom:22mm;width:92mm;border-top:1.2pt solid var(--lime);padding-top:3mm}}
.cov .hero .v{{font-family:var(--disp);font-weight:700;font-size:54pt;line-height:1;color:var(--lime)}}
.cov .hero .l{{font-size:10.6pt;line-height:1.4;color:var(--chalk);margin-top:1.5mm}}
.cov .chips{{position:absolute;left:16mm;bottom:20mm;color:var(--chalk2);width:190mm}}
.cov .method{{position:absolute;left:16mm;top:20mm;font-family:var(--mono);font-size:8pt;letter-spacing:.16em;text-transform:uppercase;color:var(--chalk2)}}
/* layouts */
.cols{{display:grid;gap:9mm}}
.c2{{grid-template-columns:1fr 1fr}} .c3{{grid-template-columns:1fr 1fr 1fr}} .c4{{grid-template-columns:repeat(4,1fr)}}
.cs{{grid-template-columns:1.62fr 1fr}} .cs2{{grid-template-columns:1fr 1.35fr}}
.card{{background:#fff;border:.6pt solid var(--line);padding:6mm 6.5mm}}
.dark .card{{background:var(--ink2);border-color:var(--ink3)}}
.card h3{{font-family:var(--disp);font-weight:600;font-size:19pt;line-height:1.05;margin-bottom:2mm}}
.card p{{font-size:11.6pt;line-height:1.48;color:#2b3631}} .dark .card p{{color:var(--chalk)}}
.tile .v{{font-family:var(--disp);font-weight:700;font-size:46pt;line-height:1;color:var(--green)}}
.dark .tile .v{{color:var(--lime)}}
.tile .u{{font-family:var(--mono);font-size:7.6pt;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin:2mm 0 1.6mm}}
.dark .tile .u{{color:var(--chalk2)}}
.tile p{{font-size:11.4pt;line-height:1.45}}
.chart{{background:#fff;border:.6pt solid var(--line);padding:4mm 5mm;display:flex;flex-direction:column;justify-content:center}}
.chart img{{width:100%;max-height:112mm;object-fit:contain;display:block}}
.cap{{font-size:9pt;line-height:1.4;color:var(--muted);margin-top:2.4mm}}
table.d{{width:100%;border-collapse:collapse}}
table.d td{{border-top:.6pt solid var(--line);padding:2.6mm 3mm 2.6mm 0;vertical-align:top;font-size:11.3pt;line-height:1.45}}
table.d td:first-child{{font-family:var(--mono);font-size:7.6pt;letter-spacing:.12em;text-transform:uppercase;color:var(--green);width:38mm;padding-top:3.3mm}}
table.r{{width:100%;border-collapse:collapse}}
table.r th{{font-family:var(--mono);font-size:7.2pt;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);text-align:left;font-weight:400;padding:0 2.5mm 1.8mm 0;border-bottom:.8pt solid var(--ink)}}
table.r td{{font-size:11.2pt;padding:2.8mm 2.5mm 1.9mm 0;border-bottom:.5pt solid var(--line)}}
table.r td.n{{font-variant-numeric:tabular-nums;text-align:right}} table.r th.n{{text-align:right}}
table.r tr.hi td{{background:#eef6e3;font-weight:600}}
.callout{{border-left:2.4pt solid var(--green);padding:1mm 0 1mm 4.5mm;font-size:12.4pt;line-height:1.5}}
.dark .callout{{border-color:var(--lime)}}
.callout b{{color:var(--green)}} .dark .callout b{{color:var(--lime)}}
.steps{{display:grid;grid-template-columns:repeat(4,1fr);gap:6mm 5mm}}
.step{{border-top:2pt solid var(--green);padding-top:3mm;min-height:36mm}}
.step .n{{font-family:var(--mono);font-size:7.4pt;color:var(--green);letter-spacing:.12em}}
.step h4{{font-family:var(--disp);font-weight:600;font-size:17pt;line-height:1.05;margin:1mm 0 1.4mm}}
.step p{{font-size:11pt;line-height:1.45;color:#2b3631}}
.dark .step{{border-color:var(--lime)}} .dark .step .n{{color:var(--lime)}} .dark .step p{{color:var(--chalk)}}
.big{{font-family:var(--disp);font-weight:600;font-size:48pt;line-height:1.02;color:#fff;max-width:270mm}}
.big em{{font-style:normal;color:var(--lime)}}
.src{{font-size:7pt;line-height:1.45;color:var(--muted)}}
.main{{flex:1;display:flex;flex-direction:column;justify-content:center;min-height:0;padding-bottom:3mm}}
.flow{{column-gap:10mm}} .flow p,.flow .callout,.flow ul,.flow li{{break-inside:avoid}}
.flow .callout{{display:inline-block;width:100%}}
"""


def esc(s):
    return s  # content is written as trusted HTML


def img64(path):
    ext = os.path.splitext(path)[1].lower()
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml"}[ext]
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


class Deck:
    def __init__(self, num, short, title_tag, source):
        self.num, self.short, self.tag, self.source = num, short, title_tag, source
        self.slides = []

    def _frame(self, inner, dark=False, cls="", source=None):
        self.slides.append((inner, dark, cls, source if source is not None else self.source))

    def html(self):
        n = len(self.slides)
        out = []
        for i, (inner, dark, cls, src) in enumerate(self.slides, 1):
            hd = (f'<div class="hd"><span><span class="pn">Project {self.num}</span> &nbsp;·&nbsp; {self.short}</span>'
                  f'<span>Joe Taylor · Football decisions under uncertainty</span></div>') if "cov" not in cls else ""
            ft = f'<div class="ft"><span>{src}</span><span>{i:02d} / {n:02d}</span></div>'
            out.append(f'<section class="s {"dark" if dark else ""} {cls}">{hd}{inner}{ft}</section>')
        return (f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>'
                + "\n".join(out) + "</body></html>")

    # ---------------------------------------------------------------- slide types
    def cover(self, title, question, hero_v, hero_l, method, chips, data_line):
        chips_html = "".join(f'<span class="chip">{c}</span>' for c in chips)
        inner = (f'<div class="pitch">{PITCH_DARK}</div>'
                 f'<div class="method">Football decisions under uncertainty &nbsp;·&nbsp; {method}</div>'
                 f'<div class="no">{self.num}</div>'
                 f'<div class="ti"><h1>{title}</h1><p>{question}</p></div>'
                 f'<div class="hero"><div class="v">{hero_v}</div><div class="l">{hero_l}</div></div>'
                 f'<div class="chips">{chips_html}</div>')
        self._frame(inner, dark=True, cls="cov", source=data_line)

    def text(self, kick, title, left, right=None, dark=False, split="c2", lead=None):
        lead_html = f'<p class="lead" style="margin-bottom:6mm">{lead}</p>' if lead else ""
        if right is None:
            body = f'<div class="txt">{left}</div>'
        else:
            body = f'<div class="cols {split}"><div class="txt">{left}</div><div class="txt">{right}</div></div>'
        self._frame(f'<div class="body"><div class="kick">{kick}</div><h1 class="t">{title}</h1><div class="main">{lead_html}{body}</div></div>', dark)

    def chart(self, kick, title, img, side, caption="", split=None, img_h=None, dark=False, cols=3, stack=None, scale=1.0):
        from PIL import Image
        pw, ph = Image.open(img).size
        want = pw * 0.1228 * scale              # display width (mm) that makes chart text about 12pt
        cap = f'<div class="cap">{caption}</div>' if caption else ""
        if (stack if stack is not None else pw / ph > 2.45):   # wide chart: full width, text below in columns
            wmm = min(want, 285, 92 * pw / ph)
            body = (f'<div class="chart" style="width:{wmm + 10:.0f}mm;align-self:center"><img src="{img64(img)}">{cap}</div>'
                    f'<div class="txt flow" style="columns:{cols};margin-top:6mm">{side}</div>')
        else:
            wmm = min(want, 190, 118 * pw / ph)
            body = (f'<div class="cols" style="grid-template-columns:{wmm + 10:.0f}mm 1fr;gap:10mm;align-items:center">'
                    f'<div class="chart"><img src="{img64(img)}">{cap}</div>'
                    f'<div class="txt">{side}</div></div>')
        self._frame(f'<div class="body"><div class="kick">{kick}</div><h1 class="t">{title}</h1><div class="main">{body}</div></div>', dark)

    def numbers(self, kick, title, tiles, foot="", dark=False, lead=None):
        cols = {2: "c2", 3: "c3", 4: "c4"}[len(tiles)]
        t = "".join(f'<div class="tile card"><div class="v">{v}</div><div class="u">{u}</div><p>{p}</p></div>' for v, u, p in tiles)
        lead_html = f'<p class="lead" style="margin-bottom:7mm">{lead}</p>' if lead else ""
        foot_html = f'<div class="callout" style="margin-top:7mm">{foot}</div>' if foot else ""
        self._frame(f'<div class="body"><div class="kick">{kick}</div><h1 class="t">{title}</h1><div class="main">{lead_html}'
                    f'<div class="cols {cols}" style="gap:6mm">{t}</div>{foot_html}</div></div>', dark)

    def design(self, kick, title, rows, side=None):
        tr = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in rows)
        tbl = f'<table class="d">{tr}</table>'
        body = f'<div class="cols cs2" style="gap:10mm"><div class="txt">{side}</div>{tbl}</div>' if side else tbl
        self._frame(f'<div class="body"><div class="kick">{kick}</div><h1 class="t">{title}</h1><div class="main">{body}</div></div>')

    def cards(self, kick, title, cards, dark=False, lead=None, foot=""):
        cols = {2: "c2", 3: "c3", 4: "c4"}[len(cards)]
        c = "".join(f'<div class="card"><div class="lbl">{l}</div><h3>{h}</h3><p>{p}</p></div>' for l, h, p in cards)
        lead_html = f'<p class="lead" style="margin-bottom:7mm">{lead}</p>' if lead else ""
        foot_html = f'<div class="callout" style="margin-top:7mm">{foot}</div>' if foot else ""
        self._frame(f'<div class="body"><div class="kick">{kick}</div><h1 class="t">{title}</h1><div class="main">{lead_html}'
                    f'<div class="cols {cols}" style="gap:5mm">{c}</div>{foot_html}</div></div>', dark)

    def steps(self, kick, title, steps, dark=False, lead=None, foot="", ncol=None):
        s = "".join(f'<div class="step"><div class="n">{n}</div><h4>{h}</h4><p>{p}</p></div>' for n, h, p in steps)
        cols = ncol or len(steps)
        lead_html = f'<p class="lead" style="margin-bottom:8mm">{lead}</p>' if lead else ""
        foot_html = f'<div class="callout" style="margin-top:8mm">{foot}</div>' if foot else ""
        self._frame(f'<div class="body"><div class="kick">{kick}</div><h1 class="t">{title}</h1><div class="main">{lead_html}'
                    f'<div class="steps" style="grid-template-columns:repeat({cols},1fr)">{s}</div>{foot_html}</div></div>', dark)

    def statement(self, kick, big, sub="", dark=True):
        inner = (f'<div class="pitchbg" style="right:-40mm;bottom:-30mm;width:200mm;opacity:.55">{PITCH_DARK}</div>'
                 f'<div class="body" style="display:flex;flex-direction:column;justify-content:center">'
                 f'<div class="kick">{kick}</div><div class="big">{big}</div>'
                 f'<p class="lead" style="margin-top:7mm;max-width:215mm">{sub}</p></div>')
        self._frame(inner, dark)

    def table(self, kick, title, head, rows, side="", hi=None, numeric=None, split="cs"):
        numeric = numeric or []
        th = "".join(f'<th class="{"n" if i in numeric else ""}">{h}</th>' for i, h in enumerate(head))
        trs = ""
        for j, r in enumerate(rows):
            tds = "".join(f'<td class="{"n" if i in numeric else ""}">{v}</td>' for i, v in enumerate(r))
            trs += f'<tr class="{"hi" if hi and j in hi else ""}">{tds}</tr>'
        tbl = f'<table class="r"><tr>{th}</tr>{trs}</table>'
        body = f'<div class="cols {split}" style="gap:10mm">{tbl}<div class="txt">{side}</div></div>' if side else tbl
        self._frame(f'<div class="body"><div class="kick">{kick}</div><h1 class="t">{title}</h1><div class="main">{body}</div></div>')

    def raw(self, inner, dark=False, source=None):
        self._frame(inner, dark, source=source)

    def about(self, projects, me_html, contact):
        items = ""
        for n, t, q in projects:
            on = n == self.num
            items += (f'<div style="display:grid;grid-template-columns:9mm 1fr;padding:1.9mm 0;border-top:.5pt solid var(--ink3);'
                      f'{"color:var(--lime)" if on else ""}"><span class="mono" style="font-size:7.6pt;padding-top:.8mm">{n}</span>'
                      f'<span style="font-size:10.4pt;line-height:1.3"><b style="font-weight:600">{t}</b>'
                      f'<span style="color:{"var(--lime)" if on else "var(--chalk2)"}"> · {q}</span></span></div>')
        inner = (f'<div class="pitchbg" style="left:-60mm;bottom:-40mm;width:220mm;opacity:.35">{PITCH_DARK}</div>'
                 f'<div class="body"><div class="cols" style="grid-template-columns:1fr 1.25fr;gap:14mm;height:100%">'
                 f'<div><div class="kick">About me</div><h1 class="t" style="color:#fff">Joe Taylor</h1>'
                 f'<div class="txt">{me_html}</div><div class="lbl" style="margin-top:5mm">{contact}</div></div>'
                 f'<div><div class="kick">The full portfolio</div>{items}</div></div></div>')
        self._frame(inner, dark=True, source="Every number in this deck comes from the code; nothing is typed in by hand.")
