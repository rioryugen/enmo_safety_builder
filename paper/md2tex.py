"""
Enmo Safety paper — convert paper.md prose into body.tex.

Handles the subset paper.md uses: #/##/### headings, paragraphs, - lists,
1. lists, **bold**, *italic*, `code`, [@key] citations, and %. Tables and
code fences in paper.md are skipped (LaTeX tables come from build_tables.py).
The title and abstract come from the first # heading and the "Abstract" section.

Author:   m03 (Intel)
Revision: 1.0

Revision History:
    1.0 — Initial version.
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def inline(s: str) -> str:
    s = s.replace("\\", "\\textbackslash{}")
    codes = []

    def keep(m):
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"

    s = re.sub(r"`([^`]+)`", keep, s)
    s = re.sub(r"\[@([\w:;@ -]+)\]", lambda m: "\\citep{" + ",".join(
        k.strip().lstrip("@") for k in m.group(1).split(";")) + "}", s)
    for ch in ("&", "%", "$", "#", "_"):
        s = re.sub(r"(?<!\\)" + re.escape(ch), "\\" + ch, s) if ch != "_" else s.replace("_", "\\_")
    s = s.replace("\\citep", "\\citep")
    s = re.sub(r"\*\*([^*]+)\*\*", r"\\textbf{\1}", s)
    s = re.sub(r"\*([^*]+)\*", r"\\emph{\1}", s)
    s = s.replace("→", "$\\rightarrow$").replace("±", "$\\pm$").replace("≤", "$\\le$").replace("≥", "$\\ge$")
    for i, c in enumerate(codes):
        c = c.replace("\\", "\\textbackslash{}").replace("_", "\\_").replace("%", "\\%").replace("&", "\\&").replace("#", "\\#").replace("$", "\\$")
        s = s.replace(f"\x00{i}\x00", "\\texttt{" + c + "}")
    s = re.sub(r"\\citep\{([^}]*)\}", lambda m: "\\citep{" + m.group(1).replace("\\_", "_") + "}", s)
    return s


def main() -> int:
    lines = (HERE / "paper.md").read_text(encoding="utf-8").splitlines()
    out, para, in_list, skip = [], [], None, False

    def flush():
        nonlocal para
        if para:
            out.append(inline(" ".join(para)) + "\n")
            para = []

    def close_list():
        nonlocal in_list
        if in_list:
            out.append(f"\\end{{{in_list}}}\n")
            in_list = None

    for line in lines:
        if line.startswith("```"):
            skip = not skip
            continue
        if skip or line.startswith("|") or line.startswith("<!--"):
            continue
        if line.startswith("# "):
            continue
        m = re.match(r"^(#{2,4}) (.*)", line)
        if m:
            flush(); close_list()
            title = re.sub(r"^\d+(\.\d+)*\s+", "", m.group(2))
            if title.lower() == "abstract":
                out.append("\\begin{abstract}\n")
                in_list = "abstract"
                continue
            cmd = {2: "section", 3: "subsection", 4: "paragraph"}[len(m.group(1))]
            out.append(f"\\{cmd}{{{inline(title)}}}\n")
            continue
        lm = re.match(r"^\s*(-|\d+\.)\s+(.*)", line)
        if lm:
            flush()
            env = "itemize" if lm.group(1) == "-" else "enumerate"
            if in_list != env:
                close_list()
                out.append(f"\\begin{{{env}}}\n")
                in_list = env
            out.append("\\item " + inline(lm.group(2)) + "\n")
            continue
        if not line.strip():
            flush()
            if in_list in ("itemize", "enumerate"):
                close_list()
            continue
        if in_list in ("itemize", "enumerate") and line.startswith("  "):
            out[-1] = out[-1].rstrip("\n") + " " + inline(line.strip()) + "\n"
            continue
        para.append(line.strip())
    flush(); close_list()
    (HERE / "body.tex").write_text("\n".join(out), encoding="utf-8")
    print(f"wrote body.tex ({len(out)} blocks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
