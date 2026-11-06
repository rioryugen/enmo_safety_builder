"""
Enmo Safety paper: render a Markdown draft to a SOEI-style PDF without TeX.

Markdown -> HTML (python-markdown) -> PDF via headless Edge or Chrome. Layout follows
the Soei paper: centered title and subtitle, a column author block, a justified
abstract with keywords, a key-findings box, a two-column contents list, ruled tables,
captioned figures, numbered citations, a numbered reference list and page numbers.

Markdown conventions:
  # Title; first *italic* paragraph = subtitle; paragraph with e-mails = authors;
  next paragraph = meta line; "## Abstract" (a "Keywords:" paragraph inside it is
  split out); "## Key findings" (numbered list, shown as a box); [@key] citations are
  resolved against refs.bib, or a "## References" bullet list is numbered and
  in-text ([arXiv:ID](url)) links are turned into [n].

    python paper/md2pdf.py paper/paper.md paper/trigger_coverage_v0.1.md

Author:   m03 (Intel)
Revision: 2.0

Revision History:
    1.0 - Plain Markdown to PDF.
    2.0 - SOEI-style front matter, contents, key-findings box, ruled tables, figure
          captions, numbered citations and references (refs.bib), page numbers.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from html import escape
from pathlib import Path

import markdown

BROWSERS = [
    shutil.which("msedge"), shutil.which("chrome"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]

CSS = """
@page { size: A4; margin: 17mm 16mm 18mm 16mm; }
:root { --ink:#111; --mute:#555; --rule:#bbb; --accent:#1f4e79; --soft:#f3f6fa; }
html { font-family: "Times New Roman", Cambria, Georgia, serif; font-size: 10.5pt; color: var(--ink); line-height: 1.38; }
body { max-width: 184mm; margin: 0 auto; }
h1 { font-size: 18.5pt; text-align: center; margin: 0 0 4pt; line-height: 1.18; }
.subtitle { text-align: center; font-size: 11.3pt; font-style: italic; margin: 0 6mm 9pt; }
.authors { display: flex; flex-wrap: wrap; justify-content: center; gap: 4pt 9mm; margin: 4pt 0 2pt; font-size: 10.6pt; text-align: center; }
.authors .mail { font-family: Consolas, monospace; font-size: 8.2pt; color: var(--accent); }
.affil { text-align: center; font-size: 9pt; color: var(--mute); margin: 3pt 0 4pt; }
.meta { text-align: center; font-size: 8.4pt; color: var(--mute); margin-bottom: 11pt; }
.abstract { margin: 0 7mm 8pt; font-size: 9.7pt; text-align: justify; }
.abstract b.h { display: block; text-align: center; margin-bottom: 3pt; }
.abstract p { margin: 0 0 4pt; }
.kw { margin: 0 7mm 10pt; font-size: 9.1pt; }
.hl { margin: 0 7mm 12pt; border: 0.8pt solid var(--accent); padding: 6pt 9pt; background: var(--soft); font-size: 9.3pt; break-inside: avoid; }
.hl b.t { color: var(--accent); display: block; margin-bottom: 2pt; }
.hl ol { margin: 0 0 0 14pt; padding: 0; } .hl li { margin-bottom: 1.5pt; }
.toc { columns: 2; font-size: 9.2pt; margin: 0 7mm 10pt; break-inside: avoid; } .toc div { break-inside: avoid; }
.toc a { color: var(--ink); }
h2 { font-size: 12.6pt; margin: 15pt 0 5pt; border-bottom: 0.6pt solid var(--rule); padding-bottom: 2pt; break-after: avoid; }
h3 { font-size: 11pt; margin: 10pt 0 4pt; break-after: avoid; }
h4 { font-size: 10.3pt; margin: 8pt 0 3pt; font-style: italic; break-after: avoid; }
p { margin: 0 0 6pt; text-align: justify; }
ul, ol { margin: 0 0 6pt 16pt; padding: 0; } li { margin-bottom: 2pt; }
table { border-collapse: collapse; width: 100%; margin: 5pt 0 9pt; font-size: 8.5pt; }
th, td { border-top: 0.5pt solid var(--rule); border-bottom: 0.5pt solid var(--rule); padding: 2.6pt 4pt; vertical-align: top; text-align: left; }
thead th { border-top: 1.1pt solid #000; border-bottom: 0.8pt solid #000; background: var(--soft); }
tbody tr:last-child td { border-bottom: 1.1pt solid #000; }
tr { break-inside: avoid; }
td[style*="right"], th[style*="right"] { white-space: nowrap; font-variant-numeric: tabular-nums; }
td code { white-space: normal; word-break: break-all; }
code { font-family: Consolas, "Courier New", monospace; font-size: 8.4pt; }
pre { font-family: Consolas, "Courier New", monospace; font-size: 7.6pt; background: var(--soft); border: 0.5pt solid var(--rule);
      padding: 5pt 7pt; white-space: pre-wrap; word-break: break-all; line-height: 1.28; margin: 4pt 0 8pt; }
pre code { font-size: inherit; }
blockquote { border-left: 2.4pt solid var(--accent); background: var(--soft); padding: 5pt 8pt; margin: 6pt 0 8pt; break-inside: avoid; }
blockquote p { margin: 0; }
figure { margin: 8pt 0 4pt; break-inside: avoid; text-align: center; }
figure img { max-width: 100%; max-height: 118mm; }
figcaption { font-size: 8.9pt; text-align: center; margin: 3pt 4mm 10pt; }
.ref { font-size: 8.9pt; } .ref li { margin-bottom: 2.5pt; }
a { color: var(--accent); text-decoration: none; }
"""


# ---- references ---------------------------------------------------------------------
def _clean(s: str) -> str:
    s = s.replace('{\\"o}', "ö").replace('{\\"u}', "ü").replace('{\\"a}', "ä")
    s = re.sub(r"\\url\{([^}]*)\}", r"\1", s)
    return re.sub(r"[{}]", "", s).strip()


def load_bib(path: Path) -> dict:
    out = {}
    if not path.is_file():
        return out
    txt = path.read_text(encoding="utf-8")
    for m in re.finditer(r"@\w+\{([^,]+),(.*?)\n\}", txt, re.S):
        out[m.group(1).strip()] = {k.lower(): v for k, v in re.findall(r"(\w+)\s*=\s*\{(.*)\},?\s*$", m.group(2), re.M)}
    return out


def _author(a: str) -> str:
    a = _clean(a)
    if "," not in a:
        return a
    last, first = [x.strip() for x in a.split(",", 1)]
    return " ".join(w[0] + "." for w in first.replace("-", " ").split()) + " " + last


def _arxiv(s: str) -> str:
    return re.sub(r"arXiv:(\d{4}\.\d{4,5})", r'<a href="https://arxiv.org/abs/\1">arXiv:\1</a>', s)


def format_ref(f: dict) -> str:
    names = [n.strip() for n in f.get("author", "").split(" and ")]
    more = "others" in names
    names = [_author(n) for n in names if n != "others"]
    who = ", ".join(names[:3]) + (" et al." if more or len(names) > 3 else "")
    title = _clean(f.get("title", "")).rstrip(".")
    venue = _clean(f.get("journal", "") or f.get("howpublished", "") or f.get("booktitle", ""))
    venue = re.sub(r"^arXiv preprint ", "", venue)
    end = "" if title.endswith("?") else "."
    return _arxiv(f"{escape(who)}{'' if who.endswith('.') else '.'} “{escape(title)}{end}” {escape(venue)}, {f.get('year', '')}.")


def resolve_citations(md: str, bib: dict) -> tuple[str, list[str]]:
    order: list[str] = []

    def sub(m: re.Match) -> str:
        nums = []
        for key in re.findall(r"@([\w:.-]+)", m.group(1)):
            if key not in bib:
                raise SystemExit(f"citation key not in refs.bib: {key}")
            if key not in order:
                order.append(key)
            nums.append(order.index(key) + 1)
        return "[" + ", ".join(f'<a href="#ref-{n}">{n}</a>' for n in sorted(set(nums))) + "]"

    return re.sub(r"\[(@[^\]]+)\]", sub, md), order


def number_list_refs(html: str) -> str:
    """Number a bullet-list References section and turn in-text arXiv links into [n]."""
    head, sep, tail = html.partition("<h2>References</h2>")
    if not sep:
        return html
    ids: dict[str, int] = {}
    n = 0

    def li(m: re.Match) -> str:
        nonlocal n
        n += 1
        a = re.search(r"arXiv:(\d{4}\.\d{4,5})", m.group(1))
        if a:
            ids.setdefault(a.group(1), n)
        return f'<li id="ref-{n}">{m.group(1)}</li>'

    tail = re.sub(r"<li>(.*?)</li>", li, tail, flags=re.S)
    tail = tail.replace("<ul>", '<ol class="ref">', 1).replace("</ul>", "</ol>", 1)

    def cite(m: re.Match) -> str:
        k = ids.get(m.group(1))
        return f'<a href="#ref-{k}">[{k}]</a>' if k else m.group(0)

    head = re.sub(r'\(<a href="[^"]*">arXiv:(\d{4}\.\d{4,5})</a>\)', cite, head)
    head = re.sub(r'<a href="[^"]*">arXiv:(\d{4}\.\d{4,5})</a>', cite, head)
    return head + sep + tail


# ---- document assembly --------------------------------------------------------------
def _inline(md: str) -> str:
    return re.sub(r"^<p>|</p>$", "", markdown.markdown(md, extensions=["smarty"]).strip())


def _section(lines: list[str], title: str) -> tuple[list[str], list[str]]:
    """Split out '## title' up to the next '## ' heading. Returns (section body, rest)."""
    for i, ln in enumerate(lines):
        if ln.strip().lower() == f"## {title}".lower():
            j = next((k for k in range(i + 1, len(lines)) if lines[k].startswith("## ")), len(lines))
            return lines[i + 1:j], lines[:i] + lines[j:]
    return [], lines


def _authors_html(para: str) -> tuple[str, str]:
    people = re.findall(r"(?:^|,|\band\b)\s*([A-Z][^(),]*?)\s*\(([^)]*)\)", para)
    aff = re.sub(r"^.*\)\s*,?\s*(?:and\s+)?", "", para).strip() if people else ""
    blocks = []
    for name, mails in people:
        ms = "".join(f'<br><span class="mail">{escape(e.strip())}</span>' for e in mails.split(",") if e.strip())
        blocks.append(f"<div>{escape(name.strip())}{ms}</div>")
    return "".join(blocks), escape(aff or "Intel Corporation")


def build_html(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8-sig")
    bib = load_bib(md_path.with_name("refs.bib"))
    order: list[str] = []
    if re.search(r"\[@[\w:.-]+", text):
        text, order = resolve_citations(text, bib)
    lines = text.splitlines()

    title = re.sub(r"^#\s+", "", lines[0]).strip()
    first_h2 = next(i for i, ln in enumerate(lines) if ln.startswith("## "))
    front = [p.strip() for p in "\n".join(lines[1:first_h2]).split("\n\n") if p.strip()]
    sub = next((p for p in front if p.startswith("*")), "")
    auth = next((p for p in front if "@" in p and "(" in p), "")
    meta = next((p for p in front if p not in (sub, auth)), "")
    rest = lines[first_h2:]
    abstract, rest = _section(rest, "Abstract")
    findings, rest = _section(rest, "Key findings")

    kw = ""
    abs_paras = [p for p in "\n".join(abstract).split("\n\n") if p.strip()]
    for p in list(abs_paras):
        if p.lower().startswith("keywords:"):
            kw = p.split(":", 1)[1].strip()
            abs_paras.remove(p)
    abs_html = markdown.markdown("\n\n".join(abs_paras), extensions=["smarty"])
    blocks, aff = _authors_html(auth)

    body = markdown.markdown("\n".join(rest), extensions=["tables", "smarty"])
    body = re.sub(r"<p>(<img[^>]*>)</p>\s*<p><em>(Figure\s+[\w.]+\.)\s*(.*?)</em></p>",
                  r"<figure>\1<figcaption><b>\2</b> \3</figcaption></figure>", body, flags=re.S)
    body = number_list_refs(body)
    if order and "<h2>References</h2>" not in body:
        items = "".join(f'<li id="ref-{i}">{format_ref(bib[k])}</li>' for i, k in enumerate(order, 1))
        body += f'<h2>References</h2><ol class="ref">{items}</ol>'
    toc = "".join(f'<div><a href="#h{i}">{re.sub("<.*?>", "", h)}</a></div>'
                  for i, h in enumerate(re.findall(r"<h2>(.*?)</h2>", body)))
    k = iter(range(10000))
    body = re.sub(r"<h2>", lambda m: f'<h2 id="h{next(k)}">', body)

    kf = ""
    if findings:
        kf = f'<div class="hl"><b class="t">Key findings</b>{markdown.markdown(chr(10).join(findings), extensions=["smarty"])}</div>'
    subtitle = _inline(sub.strip("*")) if sub.startswith("*") else ""
    return (f"<!doctype html><meta charset='utf-8'><base href='{md_path.resolve().parent.as_uri()}/'>"
            f"<title>{escape(title)}</title><style>{CSS}</style><body>"
            f"<h1>{escape(title)}</h1><div class='subtitle'>{subtitle}</div>"
            f"<div class='authors'>{blocks}</div><div class='affil'>{aff}</div>"
            f"<div class='meta'>{_inline(meta)}</div>"
            f"<div class='abstract'><b class='h'>Abstract</b>{abs_html}</div>"
            + (f"<div class='kw'><b>Keywords:</b> {escape(kw)}</div>" if kw else "")
            + kf + f"<div class='toc'>{toc}</div>{body}</body>")


def add_page_numbers(pdf: Path) -> None:
    try:
        import fitz
    except ImportError:
        return
    doc = fitz.open(pdf)
    for i, page in enumerate(doc):
        w, h = page.rect.width, page.rect.height
        page.insert_text((w / 2 - 3 * len(str(i + 1)), h - 24), str(i + 1), fontsize=8.5, fontname="tiro", color=(0.33, 0.33, 0.33))
    tmp = pdf.with_suffix(".tmp.pdf")
    doc.save(tmp)
    doc.close()
    tmp.replace(pdf)


def render(md_path: Path) -> Path:
    browser = next((b for b in BROWSERS if b and Path(b).is_file()), None)
    if not browser:
        raise SystemExit("no Edge or Chrome found for headless PDF printing")
    pdf = md_path.resolve().with_suffix(".pdf")
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "doc.html"
        src.write_text(build_html(md_path), encoding="utf-8")
        r = subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                            f"--user-data-dir={Path(tmp) / 'profile'}",
                            f"--print-to-pdf={pdf}", src.resolve().as_uri()],
                           capture_output=True, text=True, timeout=120, check=False)
    if not pdf.is_file():
        raise SystemExit(f"{Path(browser).name} exited {r.returncode} without writing {pdf}\n{r.stderr[-800:]}")
    add_page_numbers(pdf)
    return pdf


def main() -> int:
    paths = [Path(p) for p in sys.argv[1:]] or [Path(__file__).with_name("paper.md")]
    for p in paths:
        out = render(p)
        print(f"{out}  ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
