import sys, asyncio
from playwright.sync_api import sync_playwright

def render(html_path, pdf_path, w="338.67mm", h="190.5mm", check=True):
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        pg = b.new_page(viewport={"width": 1400, "height": 900})
        pg.goto("file://" + html_path); pg.wait_for_load_state("networkidle")
        pg.evaluate("document.fonts.ready")
        pg.emulate_media(media="print")
        issues = []
        if check:
            issues = pg.evaluate("""()=>{const out=[];document.querySelectorAll('section.s').forEach((s,i)=>{
              const sr=s.getBoundingClientRect();
              s.querySelectorAll('.body, .body *, .ti, .hero, .chips').forEach(e=>{const r=e.getBoundingClientRect();
                if(r.width&&r.height&&(r.bottom>sr.bottom-13*3.78||r.right>sr.right-8*3.78)) out.push((i+1)+': '+(e.className||e.tagName)+' bottom '+((r.bottom-sr.top)/3.78).toFixed(1)+'mm');});
              const b=s.querySelector('.body'); if(b&&(b.scrollHeight>b.clientHeight+2)) out.push((i+1)+': body overflow '+(b.scrollHeight-b.clientHeight));
            });return [...new Set(out)].slice(0,40)}""")
        pg.pdf(path=pdf_path, width=w, height=h, print_background=True, margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        b.close()
    return issues

if __name__ == "__main__":
    print(render(sys.argv[1], sys.argv[2]))
