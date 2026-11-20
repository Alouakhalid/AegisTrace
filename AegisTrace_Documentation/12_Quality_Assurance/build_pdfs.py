import re, sys, io, pathlib, datetime
import markdown
from pypdf import PdfReader, PdfWriter
from playwright.sync_api import sync_playwright

BASE = pathlib.Path(__file__).parent
DATE = "2026-11-17"

CSS = """
@page { size: A4; }
:root { --navy:#0B1F3A; --blue:#123A63; --cyan:#0E7490; --cyan2:#22A6C4; --ice:#EAF6FB; --ink:#16212E; }
* { box-sizing: border-box; }
html { font-size: 10.5pt; }
body { font-family: %(bodyfont)s; color: var(--ink); line-height: 1.62; margin:0; direction: %(dir)s; text-align: %(align)s; }
h1 { font-family: %(headfont)s; color: var(--navy); font-size: 21pt; border-bottom: 3px solid var(--cyan2); padding-bottom: 6px; margin: 0 0 14px; page-break-before: always; }
h1.first { page-break-before: auto; }
h2 { font-family: %(headfont)s; color: var(--cyan); font-size: 14.5pt; margin: 22px 0 8px; }
h3 { font-family: %(headfont)s; color: var(--blue); font-size: 12pt; margin: 16px 0 6px; }
p { margin: 6px 0 9px; }
table { border-collapse: collapse; width: 100%%; margin: 10px 0 14px; font-size: 9.2pt; page-break-inside: auto; }
tr { page-break-inside: avoid; }
th { background: var(--navy); color: #fff; padding: 6px 8px; text-align: %(align)s; font-weight: 700; }
td { border: 1px solid #C9DCE6; padding: 5px 8px; vertical-align: top; }
tr:nth-child(even) td { background: var(--ice); }
code { font-family: 'JetBrains Mono', 'DejaVu Sans Mono', monospace; font-size: 8.6pt; background: #EEF4F8; padding: 1px 4px; border-radius: 3px; direction: ltr; unicode-bidi: isolate; }
pre { direction: ltr; text-align: left; unicode-bidi: isolate; background: #F5F8FA; border: 1px solid #C9DCE6; border-%(startside)s: 4px solid var(--cyan2); padding: 9px 11px; font-size: 8.3pt; white-space: pre-wrap; word-break: break-word; overflow-wrap: anywhere; page-break-inside: avoid; margin: 10px 0 14px; }
pre code { background: none; padding: 0; font-size: 8.3pt; }
img { max-width: 100%%; max-height: 215mm; display: block; margin: 12px auto; direction: ltr; }
blockquote { border-%(startside)s: 4px solid var(--cyan2); background: var(--ice); margin: 10px 0; padding: 6px 12px; }
.caption { text-align:center; font-size: 9pt; color:#51657A; margin-top:-6px; }
.cover { height: 297mm; width: 210mm; background: linear-gradient(160deg, #07142A 0%%, #0B1F3A 60%%, #123A63 100%%); color:#fff; position: relative; page-break-after: always; overflow:hidden; direction:%(dir)s; }
.cover .bar { position:absolute; top:0; %(startside)s:0; width:14mm; height:100%%; background: var(--cyan2); }
.cover .grid { position:absolute; inset:0; opacity:.07; background-image: linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px); background-size: 12mm 12mm; }
.cover .inner { position:absolute; top:70mm; %(startside)s:32mm; %(endside)s:24mm; }
.cover .brand { font-size: 13pt; letter-spacing: %(ls)s; color: var(--cyan2); font-weight:700; font-family: %(headfont)s; }
.cover h1 { color:#fff; border:none; font-size: 30pt; line-height:1.25; margin:14px 0 10px; page-break-before: auto; }
.cover .sub { font-size: 13pt; color:#BFE6F2; margin-bottom: 40mm; }
.cover table { width:auto; font-size: 10pt; border-collapse: collapse; }
.cover td { border:none; background:none !important; color:#DCEFF7; padding: 3px 14px 3px 0; }
.cover td:first-child { color: var(--cyan2); font-weight:700; }
.cover .foot { position:absolute; bottom:16mm; %(startside)s:32mm; font-size:9pt; color:#8FB6C7; }
.toc { page-break-after: always; }
.toc h1 { page-break-before: auto; }
.toc a { color: var(--navy); text-decoration: none; }
.toc ol { list-style: none; padding: 0; margin: 0; }
.toc li.l1 { font-weight:700; margin-top: 9px; font-family: %(headfont)s; }
.toc li.l2 { margin-%(startpad)s: 18px; font-size: 9.6pt; color:#33485C; }
.note { border:1px solid #F59E0B; background:#FFFBEB; padding:6px 12px; border-radius:4px; }
"""

LANG = {
 "en": dict(dir="ltr", align="left", startside="left", endside="right", startpad="left", ls="4px",
            bodyfont="'DejaVu Sans', sans-serif", headfont="'DejaVu Sans', sans-serif",
            toc="Table of Contents", meta=("Document ID","Version","Date","Status","Classification"),
            status="Engineering baseline - for implementation", cls="Internal / Confidential",
            foot="Proposal-level design. Measured results are not claimed in this document."),
 "ar": dict(dir="rtl", align="right", startside="right", endside="left", startpad="right", ls="0px",
            bodyfont="'Noto Naskh Arabic', 'DejaVu Sans', serif", headfont="'Noto Sans Arabic', 'DejaVu Sans', sans-serif",
            toc="فهرس المحتويات", meta=("رقم الوثيقة","الإصدار","التاريخ","الحالة","التصنيف"),
            status="مرجع هندسي - جاهز للتنفيذ", cls="داخلي / سري",
            foot="تصميم على مستوى المقترح. لا تدّعي هذه الوثيقة نتائج قياس فعلية."),
}

def render_md(text):
    return markdown.markdown(text, extensions=["tables","fenced_code","codehilite","attr_list","sane_lists"],
        extension_configs={"codehilite":{"noclasses":True,"pygments_style":"friendly","guess_lang":False}})

def build(md_path, out_pdf, lang, title, subtitle, docid, version="1.0"):
    L = LANG[lang]
    body = render_md(pathlib.Path(md_path).read_text(encoding="utf-8"))
    # numbering handled in source text; build TOC from h1/h2
    toc_items = []
    def addid(m):
        lvl, inner = m.group(1), m.group(2)
        idx = len(toc_items)
        toc_items.append((lvl, re.sub("<[^>]+>","",inner), f"s{idx}"))
        return f'<h{lvl} id="s{idx}">{inner}</h{lvl}>'
    body = re.sub(r"<h([12])>(.*?)</h\1>", addid, body)
    body = body.replace('<h1 id="s0">', '<h1 class="first" id="s0">',1) if False else body
    toc = "".join(f'<li class="l{l}"><a href="#{i}">{t}</a></li>' for l,t,i in toc_items)
    css = CSS % {**L, "bodyfont":L["bodyfont"], "headfont":L["headfont"]}
    meta = L["meta"]
    cover = f"""<div class="cover"><div class="grid"></div><div class="bar"></div><div class="inner">
      <div class="brand">AEGISTRACE</div><h1>{title}</h1><div class="sub">{subtitle}</div>
      <table><tr><td>{meta[0]}</td><td dir="ltr">{docid}</td></tr><tr><td>{meta[1]}</td><td dir="ltr">{version}</td></tr>
      <tr><td>{meta[2]}</td><td dir="ltr">{DATE}</td></tr><tr><td>{meta[3]}</td><td>{L['status']}</td></tr>
      <tr><td>{meta[4]}</td><td>{L['cls']}</td></tr></table></div>
      <div class="foot">{L['foot']}</div></div>"""
    html_cover = f'<!doctype html><html lang="{lang}" dir="{L["dir"]}"><head><meta charset="utf-8"><style>{css} body{{margin:0}}</style></head><body>{cover}</body></html>'
    html_body = f'<!doctype html><html lang="{lang}" dir="{L["dir"]}"><head><meta charset="utf-8"><title>{title}</title><style>{css}</style></head><body><div class="toc"><h1>{L["toc"]}</h1><ol>{toc}</ol></div>{body}</body></html>'
    tmp = BASE/"tmp"; tmp.mkdir(exist_ok=True)
    hc, hb = tmp/f"{docid}_c.html", tmp/f"{docid}_b.html"
    hc.write_text(html_cover, encoding="utf-8"); hb.write_text(html_body, encoding="utf-8")
    hf = L["headfont"].split(",")[0].strip("'")
    header = f'<div style="font-family:{hf};font-size:7.5px;color:#51657A;width:100%;padding:0 16mm;display:flex;justify-content:space-between;direction:ltr"><span>AegisTrace</span><span>{title[:70]}</span></div>'
    footer = f'<div style="font-family:{hf};font-size:8px;color:#51657A;width:100%;padding:0 16mm;display:flex;justify-content:space-between;direction:ltr"><span>{docid} v{version} - {DATE}</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>'
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page()
        pg.goto(hc.as_uri()); pg.wait_for_timeout(300)
        pg.pdf(path=str(tmp/f"{docid}_c.pdf"), width="210mm", height="297mm", print_background=True, margin=dict(top="0",bottom="0",left="0",right="0"))
        pg.goto(hb.as_uri()); pg.wait_for_timeout(600)
        pg.pdf(path=str(tmp/f"{docid}_b.pdf"), format="A4", print_background=True, display_header_footer=True,
               header_template=header, footer_template=footer, outline=True, tagged=True,
               margin=dict(top="20mm",bottom="18mm",left="16mm",right="16mm"))
        b.close()
    w = PdfWriter()
    w.append(str(tmp/f"{docid}_c.pdf"), import_outline=False)
    w.append(str(tmp/f"{docid}_b.pdf"), import_outline=True)
    w.add_metadata({"/Title": title, "/Author": "AegisTrace Engineering", "/Subject": subtitle})
    # bookmarks from body outline
    out = pathlib.Path(out_pdf); out.parent.mkdir(parents=True, exist_ok=True)
    with open(out,"wb") as fh: w.write(fh)
    return len(w.pages)

if __name__ == "__main__":
    md, out, lang, title, sub, docid = sys.argv[1:7]
    print(build(md,out,lang,title,sub,docid))
