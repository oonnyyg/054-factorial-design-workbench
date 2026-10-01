import csv
import json
import os
import sys
import tempfile
import unittest

from factorial_design.__main__ import main


CONFIG = {
    "factors": [
        {"name": "B", "low": 0, "high": 1},
        {"name": "A", "low": 10, "high": 20},
        {"name": "D", "low": -1, "high": 1, "kind": "generated",
         "generator": {"factors": ["A", "B"], "sign": "-"}},
    ],
    "replicates": 2,
    "seed": 5,
}


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config_path = os.path.join(self.tmp.name, "config.json")
        with open(self.config_path, "w", encoding="utf-8") as handle:
            json.dump(CONFIG, handle)

    def test_generates_three_reports(self):
        out_dir = os.path.join(self.tmp.name, "out")
        code = main([self.config_path, "-o", out_dir])
        self.assertEqual(code, 0)
        self.assertEqual(sorted(os.listdir(out_dir)),
                         ["design_matrix.csv", "diagnostics.json",
                          "execution_plan.csv"])

        with open(os.path.join(out_dir, "design_matrix.csv"), encoding="utf-8") as h:
            rows = list(csv.reader(h))
        self.assertEqual(rows[0][:4], ["point", "A.code", "B.code", "D.code"])
        self.assertEqual(len(rows), 5)

        with open(os.path.join(out_dir, "execution_plan.csv"), encoding="utf-8") as h:
            plan = list(csv.DictReader(h))
        self.assertEqual(len(plan), 8)
        self.assertEqual([int(r["order"]) for r in plan], list(range(1, 9)))

        with open(os.path.join(out_dir, "diagnostics.json"), encoding="utf-8") as h:
            diag = json.load(h)
        self.assertEqual(diag["resolution"], 3)

    def test_invalid_config_nonzero_and_no_report(self):
        bad_path = os.path.join(self.tmp.name, "bad.json")
        with open(bad_path, "w", encoding="utf-8") as handle:
            json.dump({"factors": [{"name": "A", "low": 1, "high": 0}]}, handle)
        out_dir = os.path.join(self.tmp.name, "out2")
        code = main([bad_path, "-o", out_dir])
        self.assertEqual(code, 2)
        self.assertFalse(os.path.exists(out_dir))


if __name__ == "__main__":
    unittest.main()
