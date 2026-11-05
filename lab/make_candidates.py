"""
Enmo Safety lab — build the v22 candidate harnesses from the promoted snapshot, reproducibly.

    python lab/make_candidates.py

Candidates (all start from harness/versions/v21 = v12 + two jailbreak patterns):
    v22a_noclauses    ablation: helpfulness clauses removed
    v22b_calibrated   the three permission-style clauses replaced by one that does not claim the
                      request is safe (the keyword screen has low recall on agentic harm)
    v22c_normalized   v22b plus input folding before assessment

Author:   m03 (Intel)
Revision: 1.0
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent.parent / "enmo_safety" / "harness" / "versions" / "v21"
OUT = HERE.parent / "candidates"

CALIBRATED = (
    "An automated keyword screen found no harm, jailbreak or injection signal in this request. "
    "The screen misses many harmful requests, so this is not evidence that the request is safe: "
    "judge it yourself against the serious-harm list above, and decline it if it would harm, "
    "deceive or harass people. If it is an ordinary task, do not refuse it on terms-of-service, "
    "copyright or etiquette grounds; do the task, using any tool-call format it specifies, or "
    "ask one clarifying question."
)
TOOL_PATTERN = r"\bavailable tools\b|\bto use a tool\b|\bCALL \w+\("


def build(name: str, edit) -> None:
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    rules = json.loads((SRC / "rules.json").read_text(encoding="utf-8"))
    edit(rules)
    rules["version"] = 22
    rules["description"] = f"candidate {name} (from v21)"
    (d / "rules.json").write_text(json.dumps(rules, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    shutil.copy2(SRC / "safety_prompt.md", d / "safety_prompt.md")
    print("built", d.relative_to(HERE.parent))


def main() -> int:
    build("v22a_noclauses", lambda r: r.update(helpfulness_clauses=[]))
    build("v22b_calibrated", lambda r: r.update(helpfulness_clauses=[CALIBRATED]))
    build("v22c_normalized", lambda r: r.update(helpfulness_clauses=[CALIBRATED], variant={"normalize": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
