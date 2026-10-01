"""Command-line entry point: python -m factorial_design."""

import argparse
import os
import sys

from .config import load_config
from .design import build_standard_design
from .diagnostics import build_diagnostics
from .errors import ConfigError
from .plan import build_execution_plan
from .report import write_design_matrix, write_diagnostics, write_execution_plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m factorial_design",
        description="Turn two-level factor settings into an executable, "
                    "randomized run order with confounding diagnostics.")
    parser.add_argument("config", help="path to design configuration JSON")
    parser.add_argument("-o", "--output-dir", required=True,
                        help="directory for generated reports")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        design = build_standard_design(config)
        diagnostics = build_diagnostics(design, config)
        runs = build_execution_plan(config, design)
    except ConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2

    os.makedirs(args.output_dir, exist_ok=True)
    write_design_matrix(os.path.join(args.output_dir, "design_matrix.csv"), design)
    write_execution_plan(
        os.path.join(args.output_dir, "execution_plan.csv"), runs, design["names"])
    write_diagnostics(os.path.join(args.output_dir, "diagnostics.json"), diagnostics)

    print(f"wrote design_matrix.csv, execution_plan.csv and diagnostics.json "
          f"to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
