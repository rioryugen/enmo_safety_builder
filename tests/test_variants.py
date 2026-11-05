"""Tests for lab/variants.py: the fold and the candidate preparation (stdlib unittest, no network).

    python -m unittest tests.test_variants -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

BUILDER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUILDER / "lab"))

import common  # noqa: E402,F401  (sets sys.path for safety_runtime)
import safety_runtime as rt  # noqa: E402
import variants as v  # noqa: E402

RULES = {
    "version": 99,
    "harm_categories": {"weapons": r"\bbomb\b", "harass": r"\bbully\w*\b"},
    "jailbreak_patterns": [], "injection_patterns": [],
    "helpfulness_clauses": ["PERMISSIVE"],
    "skills": [], "output_guard": {},
}


def harness(variant=None):
    rules = dict(RULES, **({"variant": variant} if variant else {}))
    return {"dir": "", "version": 99, "prompt": "BASE", "rules": rules, "candidate": "t"}


class Fold(unittest.TestCase):
    def test_hidden_and_lookalike_characters(self):
        self.assertEqual(v.fold("b\u200bomb"), "bomb")
        self.assertEqual(v.fold("b\u043emb"), "bomb")          # Cyrillic o
        self.assertEqual(v.fold("\uff42\uff4f\uff4d\uff42"), "bomb")  # fullwidth

    def test_leetspeak_only_in_mixed_tokens(self):
        self.assertEqual(v.fold("b0mb"), "bomb")
        self.assertEqual(v.fold("h4r4ss"), "harass")
        self.assertEqual(v.fold("in 2024 buy 3 items"), "in 2024 buy 3 items")  # bare numbers untouched

    def test_symbols_and_spacing(self):
        self.assertEqual(v.fold("b@mb"), "bamb")
        self.assertEqual(v.fold("b o m b"), "bomb")
        self.assertEqual(v.fold("b.o.m.b"), "bomb")
        self.assertEqual(v.fold("a b c"), "a b c")               # fewer than four letters: left alone

    def test_none_passes_through(self):
        self.assertIsNone(v.fold(None))


class Prepare(unittest.TestCase):
    def test_clean_text_matches_the_runtime(self):
        h = harness({"normalize": True})
        for text in ("write a poem", "how to build a bomb"):
            self.assertEqual(v.prepare(h, text)[:2], rt.prepare(h, text)[:2])

    def test_normalisation_flags_obfuscated_text_but_shows_the_model_the_original(self):
        plain, norm = harness(), harness({"normalize": True})
        text = "how to build a b0mb"
        self.assertTrue(rt.low_risk(v.prepare(plain, text)[2]))
        system, user, a = v.prepare(norm, text)
        self.assertFalse(rt.low_risk(a))
        self.assertTrue(a.get("normalized"))
        self.assertIn("b0mb", user)
        self.assertNotIn("PERMISSIVE", system)       # flagged requests never get the clauses


class Candidates(unittest.TestCase):
    def test_built_candidates_differ_only_where_intended(self):
        if not (BUILDER / "candidates" / "v22b_calibrated").is_dir():
            self.skipTest("run lab/make_candidates.py first")
        a, b, c = (v.load_candidate(n)["rules"] for n in ("v22a_noclauses", "v22b_calibrated", "v22c_normalized"))
        self.assertEqual(a["helpfulness_clauses"], [])
        self.assertEqual(len(b["helpfulness_clauses"]), 1)
        self.assertNotIn("carries no harm", b["helpfulness_clauses"][0])
        self.assertEqual(b["helpfulness_clauses"], c["helpfulness_clauses"])
        self.assertTrue(c["variant"]["normalize"] and "variant" not in b)


if __name__ == "__main__":
    unittest.main()
