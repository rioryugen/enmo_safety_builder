"""
Enmo Safety lab — before/after evaluation matrix.

models x conditions x benchmarks x runs on one split. Conditions:

    bare   neutral system prompt, untrusted content inlined (no harness)
    v0     the static seed harness (enmo_safety/harness/versions/v0)
    vN     the evolved harness (enmo_safety/harness, or --vn <dir>)

Rows are appended to lab/runs/<name>/rows.jsonl and the run is resumable: a row
whose key already exists is skipped. Raw replies stay in lab/runs (gitignored).

Flags:
    --name NAME          run folder (default: main)
    --models a,b         default: every live model the providers discover
    --conditions ...     default: bare,v0,vN
    --benchmarks ...     default: all six
    --runs N             independent samples per item (default 3)
    --split S            test | dev | evolve (default test)
    --n N                cap items per benchmark (smoke tests)
    --workers N          parallel requests (default 6)
    --vn DIR             evolved harness dir
    --dry-run            print the plan and the call budget, call nothing

Author:   m03 (Intel)
Revision: 1.0

Revision History:
    1.0 — Initial version: resumable matrix, guarded/unguarded conditions,
          cross-judging, call-budget dry run.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

from common import DATA, RUNS, SAFETY, jread, jsonl_append, jsonl_read  # noqa: I001 (sets sys.path)
import safety_runtime as rt
from judge import judge, judge_for
from providers import Providers

ALL_BENCH = ("harmbench", "advbench", "jbb", "xstest", "agentharm", "injection")


def load_items(split: str, benches: List[str], n: Optional[int]) -> List[Dict]:
    data = jread(DATA / "benchmarks.json")
    if data is None:
        sys.exit("run bench_data.py first")
    items = []
    for b in benches:
        rows = data["benchmarks"][b][split]
        items += rows[:n] if n else rows
    return items


def harness_for(cond: str, vn_dir: Optional[str]):
    if cond == "bare":
        return None
    if cond == "v0":
        return rt.load_harness(SAFETY / "harness" / "versions" / "v0")
    return rt.load_harness(Path(vn_dir) if vn_dir else SAFETY / "harness")


def one(providers: Providers, model: str, cond: str, harness, item: Dict, run: int,
        judge_model: str, judges: List[str] = ()) -> Dict:
    untrusted = item.get("untrusted")
    if harness is None:
        system, user = rt.bare(item["prompt"], untrusted)
        assessment = {}
    else:
        system, user, assessment = rt.prepare(harness, item["prompt"], untrusted)
    r = providers.complete(model, system, user, run=run)
    reply, blocked = r["text"], False
    if harness is not None:
        reply, blocked = rt.guard_output(reply, assessment, harness["rules"])
    verdict = judge(providers, judge_model, item, reply, run, cond,
                    fallback=next((j for j in judges if j != judge_model), None))
    return {
        "key": f"{model}|{cond}|{item['id']}|{run}",
        "model": model, "cond": cond, "bench": item["bench"], "id": item["id"],
        "kind": item["kind"], "category": item.get("category", ""),
        "template": item.get("template"), "run": run, "split": item["split"],
        "harness_version": None if harness is None else harness["version"],
        "assessment": {k: v for k, v in assessment.items()},
        "output_blocked": blocked, "platform_block": bool(r.get("platform_block")),
        "latency_ms": r["latency_ms"], "cached": r["cached"],
        "system_chars": len(system), "reply": reply,
        "label": verdict["label"], "heuristic_refusal": verdict["heuristic_refusal"],
        "llm": verdict["llm"], "tool_calls": verdict["tool_calls"], "judge": judge_model,
    }


def evaluate(providers: Providers, models: List[str], conds: List[str], items: List[Dict],
             runs: int, out: Path, workers: int, vn_dir: Optional[str], judges: List[str],
             harnesses: Optional[Dict] = None, quiet: bool = False) -> List[Dict]:
    done = {r["key"] for r in jsonl_read(out)}
    harnesses = harnesses or {c: harness_for(c, vn_dir) for c in conds}
    jobs = [(m, c, it, k) for m in models for c in conds for it in items for k in range(runs)
            if f"{m}|{c}|{it['id']}|{k}" not in done]
    if not quiet:
        print(f"{len(jobs)} job(s) to run ({len(done)} already done) -> {out}")
    lock = threading.Lock()
    t0, finished, errors = time.time(), 0, 0
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(one, providers, m, c, harnesses[c], it, k, judge_for(m, judges), judges): (m, c, it["id"], k)
                for m, c, it, k in jobs}
        for f in cf.as_completed(futs):
            try:
                row = f.result()
            except Exception as exc:
                errors += 1
                print(f"  ERROR {futs[f]}: {str(exc)[:160]}")
                continue
            with lock:
                jsonl_append(out, [row])
                finished += 1
                if finished % 25 == 0 and not quiet:
                    rate = finished / max(1e-6, time.time() - t0)
                    print(f"  {finished}/{len(jobs)}  {rate:.2f}/s  calls={providers.calls}")
    if not quiet or errors:
        print(f"done: {finished} rows, {errors} error(s), calls={providers.calls}")
    return jsonl_read(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Enmo Safety before/after evaluation")
    ap.add_argument("--name", default="main")
    ap.add_argument("--models", default="")
    ap.add_argument("--judges", default="copilot:gpt-5.3-codex,copilot:claude-haiku-4.5")
    ap.add_argument("--conditions", default="bare,v0,vN")
    ap.add_argument("--benchmarks", default=",".join(ALL_BENCH))
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--split", default="test")
    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--vn", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    providers = Providers(workers=args.workers)
    try:
        models = [m for m in args.models.split(",") if m] or providers.live_models()
        conds = [c for c in args.conditions.split(",") if c]
        benches = [b for b in args.benchmarks.split(",") if b]
        items = load_items(args.split, benches, args.n)
        judges = [j for j in args.judges.split(",") if j]
        n_gen = len(models) * len(conds) * len(items) * args.runs
        print(f"models: {models}\nconditions: {conds}\nitems: {len(items)} x runs {args.runs}"
              f"\ngeneration calls (upper bound): {n_gen}; judge calls <= {n_gen}")
        if args.dry_run:
            return 0
        evaluate(providers, models, conds, items, args.runs, RUNS / args.name / "rows.jsonl",
                 args.workers, args.vn, judges)
    finally:
        providers.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
