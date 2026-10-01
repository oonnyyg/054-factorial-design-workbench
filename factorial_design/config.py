"""Loading and validation of design configuration JSON."""

import json
import math
from dataclasses import dataclass, field

from .errors import ConfigError


@dataclass
class Factor:
    name: str
    low: float
    high: float
    generated: bool
    sign: int = 1
    refs: list[str] = field(default_factory=list)


@dataclass
class Config:
    factors: list[Factor]
    replicates: int
    seed: int

    @property
    def factor_names(self) -> list[str]:
        return [f.name for f in self.factors]


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_finite_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _parse_sign(value, loc) -> int:
    if value is None:
        return 1
    if _is_int(value) and value in (1, -1):
        return value
    if isinstance(value, str) and value in ("+", "-"):
        return 1 if value == "+" else -1
    raise ConfigError("generator sign must be 1, -1, '+' or '-'", loc)


def load_config(path: str) -> Config:
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            raw = json.load(handle)
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {path}")
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON: {exc.msg} (line {exc.lineno}, column {exc.colno})")
    return parse_config(raw)


def parse_config(raw) -> Config:
    if not isinstance(raw, dict):
        raise ConfigError("top-level configuration must be a JSON object", "$")

    factors_raw = raw.get("factors")
    if not isinstance(factors_raw, list):
        raise ConfigError("'factors' must be a list", "$.factors")
    if not 2 <= len(factors_raw) <= 8:
        raise ConfigError("number of factors must be between 2 and 8", "$.factors")

    factors: list[Factor] = []
    seen_names: set[str] = set()
    for index, item in enumerate(factors_raw):
        loc = f"$.factors[{index}]"
        if not isinstance(item, dict):
            raise ConfigError("factor definition must be an object", loc)

        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ConfigError("factor 'name' must be a non-empty string", f"{loc}.name")
        if name in seen_names:
            raise ConfigError(f"duplicate factor name {name!r}", f"{loc}.name")
        seen_names.add(name)

        low = item.get("low")
        high = item.get("high")
        if not _is_finite_number(low):
            raise ConfigError("'low' must be a finite number", f"{loc}.low")
        if not _is_finite_number(high):
            raise ConfigError("'high' must be a finite number", f"{loc}.high")
        if not low < high:
            raise ConfigError("'low' must be strictly less than 'high'", loc)

        kind = item.get("kind", "basic")
        if not isinstance(kind, str):
            raise ConfigError("'kind' must be a string", f"{loc}.kind")

        if kind == "basic":
            if "generator" in item:
                raise ConfigError("basic factor must not define a 'generator'", f"{loc}.generator")
            factors.append(Factor(name=name, low=float(low), high=float(high), generated=False))
        elif kind == "generated":
            generator = item.get("generator")
            gloc = f"{loc}.generator"
            if not isinstance(generator, dict):
                raise ConfigError("generated factor requires a 'generator' object", gloc)
            refs = generator.get("factors")
            if not isinstance(refs, list):
                raise ConfigError("generator 'factors' must be a list", f"{gloc}.factors")
            if len(refs) < 2:
                raise ConfigError("generator must multiply at least two factors", f"{gloc}.factors")
            parsed_refs: list[str] = []
            for ref_index, ref in enumerate(refs):
                if not isinstance(ref, str) or not ref:
                    raise ConfigError("generator reference must be a non-empty string",
                                      f"{gloc}.factors[{ref_index}]")
                if ref in parsed_refs:
                    raise ConfigError(f"duplicate reference {ref!r} in generator",
                                      f"{gloc}.factors[{ref_index}]")
                parsed_refs.append(ref)
            sign = _parse_sign(generator.get("sign"), f"{gloc}.sign")
            factors.append(Factor(name=name, low=float(low), high=float(high),
                                  generated=True, sign=sign, refs=parsed_refs))
        else:
            raise ConfigError(f"unknown factor kind {kind!r}; use 'basic' or 'generated'",
                              f"{loc}.kind")

    basic_names = {f.name for f in factors if not f.generated}
    generated_names = {f.name for f in factors if f.generated}
    if len(basic_names) < 2:
        raise ConfigError("at least two basic factors are required", "$.factors")

    for fct in factors:
        if not fct.generated:
            continue
        loc = next(f"$.factors[{i}].generator.factors" for i, f in enumerate(factors) if f is fct)
        for ref in fct.refs:
            if ref in generated_names:
                raise ConfigError(
                    f"generated factor {fct.name!r} must not reference generated factor {ref!r}",
                    loc)
            if ref not in basic_names:
                raise ConfigError(f"unknown factor reference {ref!r}", loc)

    replicates = raw.get("replicates", 1)
    if not _is_int(replicates) or replicates < 1:
        raise ConfigError("'replicates' must be a positive integer", "$.replicates")

    seed = raw.get("seed", 0)
    if not _is_int(seed):
        raise ConfigError("'seed' must be an integer", "$.seed")

    return Config(factors=factors, replicates=replicates, seed=seed)
