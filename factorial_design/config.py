"""Loading and validation of design configuration JSON."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from .errors import ConfigError


@dataclass(frozen=True)
class Factor:
    name: str
    low: float
    high: float
    role: str  # "basic" or "generated"
    generator: tuple[str, ...] = ()
    sign: int = 1


@dataclass(frozen=True)
class DesignConfig:
    factors: tuple[Factor, ...]
    replicates: int
    seed: int

    @property
    def basic_factors(self) -> tuple[Factor, ...]:
        return tuple(f for f in self.factors if f.role == "basic")

    @property
    def generated_factors(self) -> tuple[Factor, ...]:
        return tuple(f for f in self.factors if f.role == "generated")


def _is_finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _parse_factor(index: int, raw: object) -> Factor:
    where = f"factors[{index}]"
    if not isinstance(raw, dict):
        raise ConfigError(f"{where}: 必须是对象")
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ConfigError(f"{where}.name: 因素名称必须是非空字符串")
    name = name.strip()
    low = raw.get("low")
    high = raw.get("high")
    if not _is_finite_number(low):
        raise ConfigError(f"{where}.low: 因素 {name!r} 的低水平必须是有限数值")
    if not _is_finite_number(high):
        raise ConfigError(f"{where}.high: 因素 {name!r} 的高水平必须是有限数值")
    if not low < high:
        raise ConfigError(f"{where}: 因素 {name!r} 的低水平必须小于高水平")
    role = raw.get("role", "basic")
    if role not in ("basic", "generated"):
        raise ConfigError(f"{where}.role: 因素 {name!r} 的 role 必须是 'basic' 或 'generated'")
    if role == "basic":
        return Factor(name=name, low=float(low), high=float(high), role="basic")
    generator = raw.get("generator")
    if (
        not isinstance(generator, list)
        or len(generator) < 2
        or not all(isinstance(g, str) and g.strip() for g in generator)
    ):
        raise ConfigError(
            f"{where}.generator: 生成因素 {name!r} 的 generator 必须是不少于两个因素名的列表"
        )
    generator = tuple(g.strip() for g in generator)
    if len(set(generator)) != len(generator):
        raise ConfigError(f"{where}.generator: 生成因素 {name!r} 的引用存在重复")
    sign = raw.get("sign", 1)
    if sign not in (1, -1):
        raise ConfigError(f"{where}.sign: 生成因素 {name!r} 的 sign 必须是 1 或 -1")
    return Factor(
        name=name, low=float(low), high=float(high), role="generated",
        generator=generator, sign=sign,
    )


def parse_config(data: object) -> DesignConfig:
    if not isinstance(data, dict):
        raise ConfigError("配置根节点必须是对象")
    raw_factors = data.get("factors")
    if not isinstance(raw_factors, list):
        raise ConfigError("factors: 必须是因素列表")
    if not 2 <= len(raw_factors) <= 8:
        raise ConfigError(f"factors: 因素个数必须在 2 到 8 之间，当前为 {len(raw_factors)}")
    factors = tuple(_parse_factor(i, raw) for i, raw in enumerate(raw_factors))
    names = [f.name for f in factors]
    if len(set(names)) != len(names):
        duplicates = sorted({n for n in names if names.count(n) > 1})
        raise ConfigError(f"factors: 因素名称重复: {', '.join(duplicates)}")
    by_name = {f.name: f for f in factors}
    for factor in factors:
        if factor.role != "generated":
            continue
        for ref in factor.generator:
            if ref not in by_name:
                raise ConfigError(
                    f"因素 {factor.name!r} 的 generator 引用了未知因素 {ref!r}"
                )
            if by_name[ref].role != "basic":
                raise ConfigError(
                    f"因素 {factor.name!r} 的 generator 不能引用生成因素 {ref!r}"
                )
    basics = [f for f in factors if f.role == "basic"]
    if len(basics) < 2:
        raise ConfigError(f"factors: 基本因素至少需要两个，当前为 {len(basics)}")
    replicates = data.get("replicates", 1)
    if not isinstance(replicates, int) or isinstance(replicates, bool) or replicates < 1:
        raise ConfigError("replicates: 必须是正整数")
    seed = data.get("seed", 0)
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ConfigError("seed: 必须是整数")
    return DesignConfig(factors=factors, replicates=replicates, seed=seed)


def load_config(path: str | Path) -> DesignConfig:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ConfigError(f"无法读取配置文件 {path}: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"配置文件 {path} 不是合法 JSON: 第 {exc.lineno} 行第 {exc.colno} 列: {exc.msg}") from exc
    return parse_config(data)
