import unittest

from factorial_design.config import parse_config
from factorial_design.design import build_standard_design
from factorial_design.diagnostics import build_diagnostics

from tests.test_config import basic, generated


class DiagnosticsTest(unittest.TestCase):
    def test_full_factorial_has_no_relations(self):
        cfg = parse_config({"factors": [basic("A"), basic("B"), basic("C")]})
        diag = build_diagnostics(build_standard_design(cfg))
        self.assertIsNone(diag["resolution"])
        self.assertTrue(diag["full_factorial"])
        self.assertEqual(diag["defining_relations"], [])
        self.assertEqual(len(diag["alias_groups"]), 1 + 3 + 3)
        for group in diag["alias_groups"]:
            self.assertEqual(len(group["members"]), 1)

    def test_resolution_four_negative_generator(self):
        cfg = parse_config({"factors": [basic("A"), basic("B"), basic("C"),
                                        generated("D", ["A", "B", "C"], -1)]})
        diag = build_diagnostics(build_standard_design(cfg))
        self.assertEqual(diag["resolution"], 4)
        self.assertFalse(diag["full_factorial"])
        relations = diag["defining_relations"]
        self.assertEqual(relations, [{"word": "A*B*C*D",
                                      "factors": ["A", "B", "C", "D"],
                                      "sign": -1}])

    def test_opposite_columns_share_group_with_sign(self):
        cfg = parse_config({"factors": [basic("A"), basic("B"), basic("C"),
                                        generated("D", ["A", "B", "C"], -1)]})
        groups = build_diagnostics(build_standard_design(cfg))["alias_groups"]
        ab_group = next(g for g in groups if g["representative"] == "A*B")
        members = {m["effect"]: m["sign"] for m in ab_group["members"]}
        self.assertEqual(members, {"A*B": 1, "C*D": -1})

    def test_resolution_three_main_aliases_interaction(self):
        cfg = parse_config({"factors": [basic("A"), basic("B"),
                                        generated("C", ["A", "B"], 1)]})
        diag = build_diagnostics(build_standard_design(cfg))
        self.assertEqual(diag["resolution"], 3)
        self.assertEqual(
            {(c["main"], c["interaction"]): c["sign"]
             for c in diag["confounding"]["main_interaction"]},
            {("A", "B*C"): 1, ("B", "A*C"): 1, ("C", "A*B"): 1})

    def test_intercept_group_first_and_groups_sorted(self):
        cfg = parse_config({"factors": [basic("A"), basic("B"),
                                        generated("C", ["A", "B"], 1)]})
        groups = build_diagnostics(build_standard_design(cfg))["alias_groups"]
        self.assertEqual(groups[0]["representative"], "I")
        reps = [g["representative"] for g in groups]
        self.assertEqual(reps, sorted(reps, key=lambda k: (
            (0, ()) if k == "I" else (len(k.split("*")), tuple(k.split("*"))))))

    def test_negative_sign_main_main_aliasing(self):
        # D = -AB makes D identical to -A*B; instead build C = AB and use
        # generators so two main effects are exact opposites: C = AB and
        # D = -AB gives C = -D (main-main, negative correlation).
        cfg = parse_config({"factors": [basic("A"), basic("B"),
                                        generated("C", ["A", "B"], 1),
                                        generated("D", ["A", "B"], -1)]})
        diag = build_diagnostics(build_standard_design(cfg))
        pairs = {(c["left"], c["right"]): c["sign"]
                 for c in diag["confounding"]["main_main"]}
        self.assertEqual(pairs[("C", "D")], -1)


if __name__ == "__main__":
    unittest.main()
