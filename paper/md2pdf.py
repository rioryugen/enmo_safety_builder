"""
Enmo Safety paper — render a Markdown draft to PDF without TeX.

Markdown -> HTML (python-markdown, already installed) -> PDF via a headless
Chromium browser (Edge or Chrome, present on Windows). Used for the working
drafts; the arXiv build still goes through paper.tex.

    python paper/md2pdf.py paper/trigger_coverage_v0.1.md      # -> same name .pdf
    python paper/md2pdf.py paper/*.md                          # several at once

Author:   m03 (Intel)
Revision: 1.0
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
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
@page { size: A4; margin: 22mm 20mm; }
body { font: 10.5pt/1.45 Georgia, "Times New Roman", serif; color: #111; max-width: 170mm; margin: 0 auto; }
h1 { font-size: 17pt; line-height: 1.25; margin: 0 0 6pt; }
h1 + p { font-size: 10.5pt; margin: 0 0 3pt; }
h1 + p + p { color: #555; font-style: italic; font-size: 9.5pt; margin-top: 0; }
h2 { font-size: 12.5pt; margin: 18pt 0 6pt; border-bottom: 1px solid #bbb; padding-bottom: 2pt; }
h3 { font-size: 11pt; margin: 12pt 0 4pt; }
p { margin: 0 0 7pt; text-align: justify; hyphens: auto; }
table { border-collapse: collapse; font-size: 8.3pt; margin: 8pt auto 10pt; max-width: 100%; }
th, td { border-top: 1px solid #ccc; border-bottom: 1px solid #ccc; padding: 2.5pt 5pt; vertical-align: top; }
th { background: #f0f0f0; text-align: left; }
td[style*="right"], th[style*="right"] { white-space: nowrap; }
td code { white-space: normal; word-break: break-all; }
code { font: 8.8pt Consolas, "Courier New", monospace; background: #f4f4f4; padding: 0 2px; }
pre { font-size: 7.4pt; line-height: 1.35; white-space: pre-wrap; word-break: break-all; background: #f7f7f7; padding: 6pt; }
pre code { font-size: inherit; background: none; padding: 0; }
a { color: #1a4d8f; text-decoration: none; }
ul { padding-left: 18pt; } li { margin-bottom: 3pt; }
img { display: block; max-width: 100%; margin: 6pt auto 2pt; }
img + em, p > img + em { display: block; }
.fig { font-size: 9pt; color: #444; text-align: center; margin: 0 0 10pt; }
h2, h3, img { break-inside: avoid; page-break-inside: avoid; }
tr { break-inside: avoid; }
h2, h3 { break-after: avoid; }
"""


def render(md_path: Path) -> Path:
    html = markdown.markdown(md_path.read_text(encoding="utf-8-sig"), extensions=["tables", "smarty"])
    base = md_path.resolve().parent.as_uri() + "/"
    doc = (f"<!doctype html><meta charset='utf-8'><base href='{base}'><title>{md_path.stem}</title>"
           f"<style>{CSS}</style><body>{html}</body>")
    browser = next((b for b in BROWSERS if b and Path(b).is_file()), None)
    if not browser:
        raise SystemExit("no Edge or Chrome found for headless PDF printing")
    pdf = md_path.resolve().with_suffix(".pdf")
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "doc.html"
        src.write_text(doc, encoding="utf-8")
        r = subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                            f"--user-data-dir={Path(tmp) / 'profile'}",
                            f"--print-to-pdf={pdf}", src.resolve().as_uri()],
                           capture_output=True, text=True, timeout=120, check=False)
    if not pdf.is_file():
        raise SystemExit(f"{Path(browser).name} exited {r.returncode} without writing {pdf}\n{r.stderr[-800:]}")
    return pdf


def main() -> int:
    paths = [Path(p) for p in sys.argv[1:]] or [Path(__file__).with_name("paper.md")]
    for p in paths:
        out = render(p)
        print(f"{out}  ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
