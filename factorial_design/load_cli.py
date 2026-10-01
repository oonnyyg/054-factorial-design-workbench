"""Glue between config loading and report writing."""

from __future__ import annotations

from pathlib import Path

from .config import load_config
from .report import write_reports


def run(config_path: str | Path, output_dir: str | Path):
    config = load_config(config_path)
    return write_reports(config, output_dir)
