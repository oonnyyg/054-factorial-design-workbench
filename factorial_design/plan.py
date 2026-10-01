"""Replicated, randomly ordered execution plan generation."""

import random

from .config import Config


def build_execution_plan(config: Config, design: dict) -> list[dict]:
    """Build and shuffle the run list.

    Every standard point is executed ``replicates`` times. The base list is
    ordered by point number then replicate number, and shuffled with a
    ``random.Random`` seeded from the configuration, so identical inputs give
    identical plans.
    """
    runs = []
    for point in design["points"]:
        for replicate in range(1, config.replicates + 1):
            runs.append({
                "point": point["point"],
                "replicate": replicate,
                "actual": dict(point["actual"]),
            })

    random.Random(config.seed).shuffle(runs)

    for order, run in enumerate(runs, start=1):
        run["order"] = order
    return runs
