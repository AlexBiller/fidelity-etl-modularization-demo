"""Invariants for the synthetic seed data. Run: python3 -m unittest discover tests"""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LABEL = "Unofficial demo built with Devin - synthetic data"


class SeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "data" / "seed.json").read_text())
        cls.mods = {m["id"]: m for m in cls.data["modules"]}

    def test_seed_is_deterministic_and_committed(self):
        before = (ROOT / "data" / "seed.json").read_text()
        subprocess.run([sys.executable, str(ROOT / "scripts" / "seed.py")], check=True, capture_output=True)
        self.assertEqual(before, (ROOT / "data" / "seed.json").read_text(), "data/seed.json is stale; re-run scripts/seed.py")

    def test_dependency_graph_is_acyclic_and_closed(self):
        seen, stack = set(), set()

        def visit(mid):
            self.assertNotIn(mid, stack, f"cycle at {mid}")
            if mid in seen:
                return
            stack.add(mid)
            for up in self.mods[mid]["upstream"]:
                self.assertIn(up, self.mods)
                visit(up)
            stack.discard(mid)
            seen.add(mid)

        for mid in self.mods:
            visit(mid)

    def test_downstream_mirrors_upstream(self):
        for mid, m in self.mods.items():
            for d in m["downstream"]:
                self.assertIn(mid, self.mods[d]["upstream"])

    def test_risk_scores_and_bands(self):
        for m in self.mods.values():
            self.assertTrue(0 <= m["risk_score"] <= 99)
            self.assertIn(m["risk_band"], {"Low", "Medium", "High", "Critical"})
        self.assertGreaterEqual(len({m["risk_band"] for m in self.mods.values()}), 4)

    def test_every_module_has_code_and_tests(self):
        for m in self.mods.values():
            self.assertNotEqual(m["code_before"], m["code_after"])
            self.assertNotIn("__", re.sub(r"__(name|init)__", "", m["code_after"]), f"unrendered token in {m['id']}")
            self.assertGreaterEqual(len(m["tests"]), 5)
            self.assertTrue(any(t["type"] == "parity" for t in m["tests"]))

    def test_label_on_every_page(self):
        for page in ["index.html", "standalone.html"]:
            self.assertIn(f'class="banner" role="note">{LABEL}<', (ROOT / page).read_text())
        self.assertEqual(self.data["meta"]["label"], LABEL)


if __name__ == "__main__":
    unittest.main()
