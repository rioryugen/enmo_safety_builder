"""
Enmo Safety lab — model providers with a response cache.

    copilot:<id>   GitHub Copilot models through the Copilot SDK (copilot_bridge.mjs).
                   The system message is replaced and tools are disabled, so the
                   model sees exactly the condition under test.
    octagram:<id>  Strata Octagram (local, OpenAI-compatible). Key from the
                   OCTAGRAM_API_KEY env var, or the same name in the Windows user
                   environment (HKCU\\Environment). Never logged or written.

Every response is cached by sha(model, system, user, run) under lab/cache/, so
re-analysis and resumed runs never re-bill a call. Different `run` values are
independent samples.

Author:   m03 (Intel)
Revision: 1.1

Revision History:
    1.0 — Initial version: Copilot SDK bridge pool, Octagram client, retries,
          disk cache, live-model discovery.
    1.1 — Platform content-filter rejections (400/422 "flagged") are recorded as
          platform blocks, not retried; retries are logged; bridges run from the
          lab state dir outside git and synced folders.
"""

from __future__ import annotations

import json
import os
import queue
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

from common import CACHE, LAB, RUNS, STATE, jread, jwrite, sha

OCTAGRAM_URL = os.environ.get("OCTAGRAM_URL", "http://10.138.143.62:8080/v1")
OCTAGRAM_MODEL = "swift-1.5-iq2_xs"


class PlatformBlock(RuntimeError):
    """The serving platform's own content filter rejected the request."""


def octagram_key() -> Optional[str]:
    key = os.environ.get("OCTAGRAM_API_KEY")
    if key:
        return key
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return winreg.QueryValueEx(k, "OCTAGRAM_API_KEY")[0] or None
    except (ImportError, OSError):
        return None


class Bridge:
    """One long-lived node process speaking JSONL to the Copilot SDK."""

    def __init__(self) -> None:
        STATE.mkdir(parents=True, exist_ok=True)
        # Run outside any git repo / synced folder: the CLI does per-request repo work otherwise.
        self.proc = subprocess.Popen(
            ["node", str(LAB / "copilot_bridge.mjs"), "--serve"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", bufsize=1, cwd=str(STATE))
        self.n = 0

    def ask(self, model: str, system: str, user: str, timeout_ms: int) -> dict:
        self.n += 1
        req = {"id": str(self.n), "model": model, "system": system, "prompt": user,
               "timeout_ms": timeout_ms}
        self.proc.stdin.write(json.dumps(req) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("copilot bridge exited")
        return json.loads(line)

    def close(self) -> None:
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=30)
        except Exception:
            self.proc.kill()


class Providers:
    def __init__(self, workers: int = 4) -> None:
        self.workers = workers
        self._pool: "queue.Queue[Bridge]" = queue.Queue()
        self._made = 0
        self._lock = threading.Lock()
        self.calls = {"copilot": 0, "octagram": 0, "cached": 0}

    # ---------- discovery ----------
    def live_models(self) -> List[str]:
        out = subprocess.run(["node", str(LAB / "copilot_bridge.mjs"), "--list"],
                             capture_output=True, text=True, encoding="utf-8", timeout=180)
        models = []
        for line in out.stdout.splitlines():
            if line.startswith("["):
                for m in json.loads(line):
                    if m.get("policy") in (None, "enabled"):
                        models.append(f"copilot:{m['id']}")
        live = [m for m in models if self._ping(m)]
        if octagram_key() and self._ping(f"octagram:{OCTAGRAM_MODEL}"):
            live.append(f"octagram:{OCTAGRAM_MODEL}")
        return live

    def _ping(self, model: str) -> bool:
        try:
            r = self.complete(model, "You are concise.", "Reply with the word OK.", run="ping")
            return bool(r["text"].strip())
        except Exception:
            return False

    # ---------- completion ----------
    def complete(self, model: str, system: str, user: str, run: object = 0,
                 timeout_ms: int = 180000) -> Dict:
        key = sha(model, system, user, run)
        path = CACHE / key[:2] / f"{key}.json"
        hit = jread(path)
        if hit is not None:
            with self._lock:
                self.calls["cached"] += 1
            return {**hit, "cached": True}
        vendor, mid = model.split(":", 1)
        last = None
        for attempt in range(4):
            try:
                if vendor == "copilot":
                    res = self._copilot(mid, system, user, timeout_ms)
                elif vendor == "octagram":
                    res = self._octagram(mid, system, user, timeout_ms)
                else:
                    raise ValueError(f"unknown vendor {vendor}")
                break
            except PlatformBlock as exc:
                res = {"text": "", "latency_ms": 0, "platform_block": str(exc)[:200]}
                break
            except Exception as exc:  # retry transient failures with backoff
                last = exc
                with self._lock, (RUNS / "retries.log").open("a", encoding="utf-8") as f:
                    f.write(f"{time.strftime('%H:%M:%S')} {model} attempt {attempt}: {str(exc)[:160]}\n")
                time.sleep(3 * (2 ** attempt))
        else:
            raise RuntimeError(f"{model} failed after retries: {last}")
        with self._lock:
            self.calls[vendor] += 1
        rec = {"text": res["text"], "latency_ms": res.get("latency_ms", 0), "model": model,
               "platform_block": res.get("platform_block")}
        jwrite(path, rec)
        return {**rec, "cached": False}

    def _bridge(self) -> Bridge:
        try:
            return self._pool.get_nowait()
        except queue.Empty:
            with self._lock:
                if self._made < self.workers:
                    self._made += 1
                    return Bridge()
            return self._pool.get()

    def _copilot(self, mid: str, system: str, user: str, timeout_ms: int) -> Dict:
        b = self._bridge()
        try:
            r = b.ask(mid, system, user, timeout_ms)
        except Exception:
            b.close()
            with self._lock:
                self._made -= 1
            raise
        self._pool.put(b)
        if not r.get("ok"):
            err = r.get("error", "copilot error")
            if "flagged" in err.lower() and ("422" in err or "400" in err):
                raise PlatformBlock(err)
            raise RuntimeError(err)
        return r

    def _octagram(self, mid: str, system: str, user: str, timeout_ms: int) -> Dict:
        key = octagram_key()
        if not key:
            raise RuntimeError("OCTAGRAM_API_KEY not set")
        body = json.dumps({"model": mid, "max_tokens": 1024,
                           "messages": [{"role": "system", "content": system},
                                        {"role": "user", "content": user}]}).encode("utf-8")
        req = urllib.request.Request(f"{OCTAGRAM_URL}/chat/completions", data=body, headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {key}"})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        t0 = time.time()
        with opener.open(req, timeout=timeout_ms / 1000) as r:
            data = json.loads(r.read().decode("utf-8"))
        text = data["choices"][0]["message"].get("content") or ""
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
        return {"text": text, "latency_ms": int((time.time() - t0) * 1000)}

    def close(self) -> None:
        while not self._pool.empty():
            self._pool.get_nowait().close()
