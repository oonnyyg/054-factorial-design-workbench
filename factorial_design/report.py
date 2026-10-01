"""CSV and JSON report writing."""

import csv
import json


def _format_number(value: float):
    if float(value).is_integer():
        return str(int(value))
    return repr(value)


def write_design_matrix(path: str, design: dict) -> None:
    names = design["names"]
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        header = ["point"]
        header.extend(f"{name}.code" for name in names)
        header.extend(f"{name}.level" for name in names)
        writer.writerow(header)
        for point in design["points"]:
            row = [point["point"]]
            row.extend(point["coded"][name] for name in names)
            row.extend(_format_number(point["actual"][name]) for name in names)
            writer.writerow(row)


def write_execution_plan(path: str, runs: list[dict], names: list[str]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["order", "point", "replicate"] + [f"{name}.level" for name in names])
        for run in runs:
            writer.writerow(
                [run["order"], run["point"], run["replicate"]]
                + [_format_number(run["actual"][name]) for name in names]
            )


def write_diagnostics(path: str, diagnostics: dict) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(diagnostics, handle, ensure_ascii=False, indent=2, sort_keys=False)
        handle.write("\n")
