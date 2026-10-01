from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from factorial_design.config import parse_config
from factorial_design.diagnostics import build_diagnostics
from factorial_design.design import coded_matrix, design_rows, run_order
from factorial_design.errors import ConfigError
from factorial_design.report import write_reports


def basic(name, low=0.0, high=1.0):
    return {"name": name, "low": low, "high": high, "role": "basic"}


def generated(name, gen, sign=1, low=0.0, high=1.0):
    return {
        "name": name, "low": low, "high": high, "role": "generated",
        "generator": gen, "sign": sign,
    }


def make(factors, replicates=1, seed=0):
    return parse_config({"factors": factors, "replicates": replicates, "seed": seed})


def labels(group):
    return [m["effect"] for m in group["members"]]


class DesignMatrixTests(unittest.TestCase):
    def test_full_factorial_enumeration_order(self):
        config = make([basic("B"), basic("A")])
        rows = coded_matrix(config)
        self.assertEqual(len(rows), 4)
        names = [tuple(r[n] for n in ("A", "B")) for r in rows]
        self.assertEqual(names, [(-1, -1), (-1, 1), (1, -1), (1, 1)])

    def test_full_factorial_has_no_defining_relation(self):
        diag = build_diagnostics(make([basic("A"), basic("B"), basic("C")]))
        self.assertIsNone(diag["resolution"])
        self.assertTrue(diag["full_factorial"])
        self.assertEqual(diag["defining_relations"], [])

    def test_negative_generator(self):
        config = make([basic("A"), basic("B"), basic("C"),
                       generated("D", ["A", "B", "C"], sign=-1)])
        rows = coded_matrix(config)
        for row in rows:
            self.assertEqual(row["D"], -row["A"] * row["B"] * row["C"])
        diag = build_diagnostics(config)
        self.assertEqual(diag["resolution"], 4)
        self.assertEqual(diag["defining_relations"][0]["word"], "-A*B*C*D")
        group = next(g for g in diag["confounding_groups"]
                     if labels(g) == ["A*B", "C*D"])
        signs = {m["effect"]: m["sign_vs_representative"] for m in group["members"]}
        self.assertEqual(signs, {"A*B": 1, "C*D": -1})

    def test_multiple_generators_resolution_three(self):
        config = make([
            basic("A"), basic("B"), basic("C"),
            generated("D", ["A", "B"]),
            generated("E", ["A", "C"]),
        ])
        rows = coded_matrix(config)
        self.assertEqual(len(rows), 8)
        for row in rows:
            self.assertEqual(row["D"], row["A"] * row["B"])
            self.assertEqual(row["E"], row["A"] * row["C"])
        diag = build_diagnostics(config)
        self.assertEqual(diag["resolution"], 3)
        words = {r["word"] for r in diag["defining_relations"]}
        self.assertIn("A*B*D", words)
        self.assertIn("A*C*E", words)
        confounded = {(p["main_effect"], p["interaction"])
                      for p in diag["main_effect_vs_interaction_confounding"]}
        self.assertIn(("A", "B*D"), confounded)
        self.assertIn(("D", "A*B"), confounded)

    def test_input_order_does_not_change_matrix(self):
        cfg1 = make([basic("A"), basic("B"), basic("C"),
                     generated("D", ["A", "B", "C"], sign=-1)])
        cfg2 = make([generated("D", ["C", "A", "B"], sign=-1),
                     basic("C"), basic("A"), basic("B")])
        self.assertEqual(coded_matrix(cfg1), coded_matrix(cfg2))
        self.assertEqual(design_rows(cfg1), design_rows(cfg2))
        self.assertEqual(build_diagnostics(cfg1), build_diagnostics(cfg2))

    def test_actual_level_mapping(self):
        config = make([basic("A", low=10, high=20), basic("B", low=0, high=1),
                       generated("C", ["A", "B"], sign=-1, low=5, high=8)])
        rows = design_rows(config)
        coded = coded_matrix(config)
        for actual, code in zip(rows, coded):
            self.assertEqual(actual["A"], 10 if code["A"] == -1 else 20)
            self.assertEqual(actual["C"], 8 if code["C"] == 1 else 5)
            self.assertEqual(list(actual), ["A", "B", "C"])


class InvalidConfigTests(unittest.TestCase):
    def _expect(self, payload, fragment):
        with self.assertRaises(ConfigError) as ctx:
            parse_config(payload)
        self.assertIn(fragment, str(ctx.exception))

    def test_basic_count_and_uniqueness(self):
        self._expect({"factors": [basic("A")]}, "2 到 8")
        self._expect({"factors": [basic("A"), basic("A")]}, "名称重复")
        self._expect({"factors": [{"name": " ", "low": 0, "high": 1},
                                  basic("B")]}, "非空")

    def test_levels(self):
        self._expect({"factors": [basic("A", low=1, high=1), basic("B")]}, "低水平必须小于")
        self._expect({"factors": [{"name": "A", "low": float("inf"), "high": 1},
                                  basic("B")]}, "有限数值")

    def test_generator_rules(self):
        self._expect({"factors": [basic("A"), basic("B"),
                                  generated("C", ["A", "A"])]}, "重复")
        self._expect({"factors": [basic("A"), basic("B"),
                                  generated("C", ["A"])]}, "不少于两个")
        self._expect({"factors": [basic("A"), basic("B"),
                                  generated("C", ["A", "X"])]}, "未知因素")
        self._expect({"factors": [basic("A"), basic("B"),
                                  generated("C", ["A", "B"]),
                                  generated("D", ["A", "C"])]}, "不能引用生成因素")

    def test_replicates_and_seed(self):
        base = {"factors": [basic("A"), basic("B")]}
        self._expect({**base, "replicates": 0}, "正整数")
        self._expect({**base, "seed": 1.5}, "整数")


class RunOrderTests(unittest.TestCase):
    def test_replicates_and_determinism(self):
        config = make([basic("A"), basic("B")], replicates=3, seed=7)
        first = run_order(config)
        second = run_order(config)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 12)
        self.assertEqual(sorted(first),
                         [(p, r) for p in range(1, 5) for r in range(1, 4)])
        self.assertNotEqual([p for p, _ in first], [1, 2, 3, 4] * 3)

    def test_diagnostics_independent_of_replicates(self):
        once = build_diagnostics(make([basic("A"), basic("B")], replicates=1))
        many = build_diagnostics(make([basic("A"), basic("B")], replicates=5))
        self.assertEqual(once, many)


class ReportTests(unittest.TestCase):
    def test_reports_written_and_rereadable(self):
        config = make([basic("A", 10, 20), basic("B", 0, 1),
                       generated("C", ["A", "B"], -1, 5, 8)],
                      replicates=2, seed=3)
        with tempfile.TemporaryDirectory() as tmp:
            paths = write_reports(config, Path(tmp) / "nested" / "out")
            matrix = list(csv.DictReader(io.StringIO(
                paths["design_matrix.csv"].read_text(encoding="utf-8"))))
            plan = list(csv.DictReader(io.StringIO(
                paths["run_plan.csv"].read_text(encoding="utf-8"))))
            diag = json.loads(paths["diagnostics.json"].read_text(encoding="utf-8"))
        self.assertEqual(len(matrix), 4)
        self.assertEqual(len(plan), 8)
        self.assertEqual(diag["resolution"], 3)
        self.assertEqual([row["run_order"] for row in plan], [str(i) for i in range(1, 9)])

    def test_cli_failure_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = root / "bad.json"
            cfg.write_text(json.dumps({"factors": [basic("A")]}), encoding="utf-8")
            out = root / "out"
            result = subprocess.run(
                [sys.executable, "-m", "factorial_design", str(cfg), "-o", str(out)],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("配置错误", result.stderr)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
