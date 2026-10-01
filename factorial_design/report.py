"""CSV / JSON report rendering. Files are written only after full success."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from .config import DesignConfig
from .design import actual_level, coded_matrix, design_rows, run_order
from .diagnostics import build_diagnostics


def _format_number(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return repr(value)


def render_design_matrix_csv(config: DesignConfig) -> str:
    names = sorted(f.name for f in config.factors)
    factors = {f.name: f for f in config.factors}
    coded_rows = coded_matrix(config)
    actual_rows = design_rows(config)
    header = ["point_id"]
    header.extend(f"coded:{name}" for name in names)
    header.extend(f"actual:{name}" for name in names)
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(header)
    for i, (coded, actual) in enumerate(zip(coded_rows, actual_rows), start=1):
        writer.writerow(
            [i]
            + [coded[name] for name in names]
            + [_format_number(actual[name]) for name in names]
    )
    return buf.getvalue()


def render_run_plan_csv(config: DesignConfig) -> str:
    names = sorted(f.name for f in config.factors)
    factors = {f.name: f for f in config.factors}
    coded_rows = coded_matrix(config)
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["run_order", "point_id", "replicate"] + names)
    for order, (point_id, replicate) in enumerate(run_order(config), start=1):
        coded = coded_rows[point_id - 1]
        writer.writerow(
            [order, point_id, replicate]
            + [_format_number(actual_level(factors[name], coded[name])) for name in names]
        )
    return buf.getvalue()


def render_diagnostics_json(config: DesignConfig) -> str:
    return json.dumps(build_diagnostics(config), ensure_ascii=False, indent=2) + "\n"


def write_reports(config: DesignConfig, output_dir: str | Path) -> dict[str, Path]:
    output_dir = Path(output_dir)
    payload = {
        "design_matrix.csv": render_design_matrix_csv(config),
        "run_plan.csv": render_run_plan_csv(config),
        "diagnostics.json": render_diagnostics_json(config),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for filename, content in payload.items():
        path = output_dir / filename
        path.write_text(content, encoding="utf-8")
        paths[filename] = path
    return paths
