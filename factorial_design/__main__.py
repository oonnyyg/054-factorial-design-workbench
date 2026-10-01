"""Command line entry: python -m factorial_design CONFIG.json -o OUT_DIR"""

from __future__ import annotations

import argparse
import sys

from .errors import ConfigError
from .load_cli import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m factorial_design",
        description="两水平筛选试验设计工具：生成设计矩阵、执行计划与混杂诊断。",
    )
    parser.add_argument("config", help="设计配置 JSON 文件路径")
    parser.add_argument("-o", "--output-dir", required=True, help="报告输出目录")
    args = parser.parse_args(argv)
    try:
        paths = run(args.config, args.output_dir)
    except ConfigError as exc:
        print(f"配置错误: {exc}", file=sys.stderr)
        return 2
    for filename, path in paths.items():
        print(f"{filename}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
