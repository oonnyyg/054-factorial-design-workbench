import unittest

from factorial_design.config import parse_config
from factorial_design.errors import ConfigError


def basic(name, low=-1, high=1):
    return {"name": name, "low": low, "high": high, "kind": "basic"}


def generated(name, refs, sign=1):
    return {"name": name, "low": -1, "high": 1, "kind": "generated",
            "generator": {"factors": refs, "sign": sign}}


class ConfigValidationTest(unittest.TestCase):
    def expect_error(self, raw, fragment):
        with self.assertRaises(ConfigError) as ctx:
            parse_config(raw)
        self.assertIn(fragment, str(ctx.exception))

    def test_valid_basic_defaults(self):
        cfg = parse_config({"factors": [basic("A"), basic("B")]})
        self.assertEqual(cfg.replicates, 1)
        self.assertEqual(cfg.seed, 0)

    def test_factor_count_bounds(self):
        self.expect_error({"factors": [basic("A")]}, "$.factors")
        self.expect_error({"factors": [basic(chr(65 + i)) for i in range(9)]},
                          "$.factors")

    def test_empty_or_duplicate_names(self):
        self.expect_error({"factors": [{"name": "  ", "low": 0, "high": 1},
                                       basic("B")]}, "non-empty")
        self.expect_error({"factors": [basic("A"), basic("A")]}, "duplicate")

    def test_level_order_and_finiteness(self):
        self.expect_error({"factors": [{"name": "A", "low": 1, "high": 0},
                                       basic("B")]}, "strictly less")
        self.expect_error({"factors": [{"name": "A", "low": 0, "high": 0},
                                       basic("B")]}, "strictly less")
        self.expect_error({"factors": [{"name": "A", "low": float("nan"),
                                        "high": 1}, basic("B")]}, "finite")

    def test_generator_rules(self):
        self.expect_error({"factors": [basic("A"), basic("B"),
                                       generated("C", ["A"])]}, "at least two")
        self.expect_error({"factors": [basic("A"), basic("B"),
                                       generated("C", ["A", "A", "B"])]},
                          "duplicate reference")
        self.expect_error({"factors": [basic("A"), basic("B"),
                                       generated("C", ["A", "X"])]},
                          "unknown factor reference")
        self.expect_error(
            {"factors": [basic("A"), basic("B"),
                         generated("C", ["A", "B"]),
                         generated("D", ["A", "C"])]},
            "must not reference generated")

    def test_at_least_two_basics(self):
        self.expect_error({"factors": [basic("A"),
                                       generated("C", ["A", "B"])]},
                          "at least two basic")

    def test_bad_sign_replicates_seed(self):
        self.expect_error({"factors": [basic("A"), basic("B"),
                                       generated("C", ["A", "B"], sign=2)]},
                          "generator sign")
        self.expect_error({"factors": [basic("A"), basic("B")], "replicates": 0},
                          "$.replicates")
        self.expect_error({"factors": [basic("A"), basic("B")], "replicates": True},
                          "$.replicates")
        self.expect_error({"factors": [basic("A"), basic("B")], "seed": 1.5},
                          "$.seed")


if __name__ == "__main__":
    unittest.main()
