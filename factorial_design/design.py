"""Standard design matrix and run-order generation."""

from __future__ import annotations

import itertools
import random

from .config import DesignConfig, Factor


def coded_matrix(config: DesignConfig) -> list:
    """Coded (-1/+1) columns for every factor, one dict per standard point.

    Basic factors are sorted by name and fully enumerated in lexicographic
    order of the coded vector. Generated factors are derived as the signed
    product of their generator columns.
    """
    basics = sorted(config.basic_factors, key=lambda f: f.name)
    generated = sorted(config.generated_factors, key=lambda f: f.name)
    rows = []
    for combo in itertools.product((-1, 1), repeat=len(basics)):
        row = {factor.name: code for factor, code in zip(basics, combo)}
        for factor in generated:
            product = 1
            for ref in factor.generator:
                product *= row[ref]
            row[factor.name] = factor.sign * product
        rows.append(row)
    return rows


def actual_level(factor: Factor, code: int) -> float:
    return factor.low if code == -1 else factor.high


def design_rows(config: DesignConfig) -> list:
    """Actual-level rows for the standard design, factors sorted by name."""
    factors = {f.name: f for f in config.factors}
    names = sorted(factors)
    rows = []
    for coded in coded_matrix(config):
        rows.append({name: actual_level(factors[name], coded[name]) for name in names})
    return rows


def run_order(config: DesignConfig) -> list:
    """Shuffled (point_id, replicate) pairs; point_id is 1-based."""
    n_points = 2 ** len(config.basic_factors)
    pairs = [
        (point_id, replicate)
        for point_id in range(1, n_points + 1)
        for replicate in range(1, config.replicates + 1)
    ]
    random.Random(config.seed).shuffle(pairs)
    return pairs
