import unittest

from factorial_design.config import parse_config
from factorial_design.design import build_standard_design
from factorial_design.plan import build_execution_plan

from tests.test_config import basic, generated


class StandardDesignTest(unittest.TestCase):
    def test_full_factorial_lexicographic(self):
        cfg = parse_config({"factors": [basic("B"), basic("A")]})
        design = build_standard_design(cfg)
        self.assertEqual(design["names"], ["A", "B"])
        self.assertEqual(
            [tuple(p["coded"][n] for n in ("A", "B")) for p in design["points"]],
            [(-1, -1), (-1, 1), (1, -1), (1, 1)])

    def test_actual_level_mapping(self):
        cfg = parse_config({
            "factors": [{"name": "A", "low": 10, "high": 20},
                        {"name": "B", "low": 0, "high": 1}]})
        design = build_standard_design(cfg)
        last = design["points"][-1]["actual"]
        self.assertEqual(last, {"A": 20, "B": 1})

    def test_negative_generator_sign(self):
        cfg = parse_config({"factors": [basic("A"), basic("B"), basic("C"),
                                        generated("D", ["A", "B", "C"], sign=-1)]})
        design = build_standard_design(cfg)
        for point in design["points"]:
            expected = -(point["coded"]["A"] * point["coded"]["B"]
                         * point["coded"]["C"])
            self.assertEqual(point["coded"]["D"], expected)

    def test_multiple_generators(self):
        cfg = parse_config({"factors": [basic("A"), basic("B"),
                                        generated("C", ["A", "B"], sign=1),
                                        generated("D", ["A", "B"], sign=-1)]})
        design = build_standard_design(cfg)
        self.assertEqual(len(design["points"]), 4)
        for point in design["points"]:
            ab = point["coded"]["A"] * point["coded"]["B"]
            self.assertEqual(point["coded"]["C"], ab)
            self.assertEqual(point["coded"]["D"], -ab)

    def test_input_order_does_not_change_matrix(self):
        first = parse_config({"factors": [basic("A"), basic("B"), basic("C")]})
        second = parse_config({"factors": [basic("C"), basic("A"), basic("B")]})
        d1 = build_standard_design(first)
        d2 = build_standard_design(second)
        self.assertEqual(
            [[p["coded"][n] for n in d1["names"]] for p in d1["points"]],
            [[p["coded"][n] for n in d2["names"]] for p in d2["points"]])


class ExecutionPlanTest(unittest.TestCase):
    def test_replication_counts_and_determinism(self):
        cfg = parse_config({"factors": [basic("A"), basic("B")],
                            "replicates": 3, "seed": 7})
        design = build_standard_design(cfg)
        runs_one = build_execution_plan(cfg, design)
        runs_two = build_execution_plan(cfg, design)
        self.assertEqual(len(runs_one), 12)
        self.assertEqual([r["order"] for r in runs_one], list(range(1, 13)))
        self.assertEqual([(r["point"], r["replicate"]) for r in runs_one],
                         [(r["point"], r["replicate"]) for r in runs_two])
        for point in range(1, 5):
            self.assertEqual(
                sorted(r["replicate"] for r in runs_one if r["point"] == point),
                [1, 2, 3])

    def test_seed_changes_order(self):
        design = build_standard_design(parse_config(
            {"factors": [basic("A"), basic("B")]}))
        runs_1 = build_execution_plan(parse_config(
            {"factors": [basic("A"), basic("B")], "seed": 1}), design)
        runs_2 = build_execution_plan(parse_config(
            {"factors": [basic("A"), basic("B")], "seed": 2}), design)
        self.assertNotEqual([r["point"] for r in runs_1],
                            [r["point"] for r in runs_2])


if __name__ == "__main__":
    unittest.main()
