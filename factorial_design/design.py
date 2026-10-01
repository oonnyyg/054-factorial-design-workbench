"""Standard design matrix construction.

Basic factors are sorted by name; their (-1, +1) combinations are enumerated
in lexicographic order of the coded vectors and numbered starting at 1.
Generated factors are computed as signed products of distinct basic columns
and must never be enumerated independently.
"""

from .config import Config, Factor


def _actual_level(factor: Factor, code: int) -> float:
    return factor.high if code == 1 else factor.low


def build_standard_design(config: Config) -> dict:
    """Return the canonical (unreplicated) design.

    Result keys:
        names: all factor names sorted alphabetically
        points: list of dicts with keys
            point (1-based), coded {name: +/-1}, actual {name: float}
    """
    basics = sorted((f for f in config.factors if not f.generated), key=lambda f: f.name)
    basic_names = [f.name for f in basics]
    by_name = {f.name: f for f in config.factors}

    all_names = sorted(config.factor_names)

    points = []
    num_points = 2 ** len(basics)
    for point_index in range(num_points):
        coded = {}
        # Lexicographic enumeration of coded vectors: first basic factor
        # varies slowest, corresponding to counting bits from the top.
        for col, name in enumerate(basic_names):
            bit_position = len(basics) - 1 - col
            coded[name] = 1 if ((point_index >> bit_position) & 1) else -1

        for factor in config.factors:
            if not factor.generated:
                continue
            product = 1
            for ref in factor.refs:
                product *= coded[ref]
            coded[factor.name] = factor.sign * product

        actual = {name: _actual_level(by_name[name], coded[name]) for name in all_names}
        points.append({
            "point": point_index + 1,
            "coded": {name: coded[name] for name in all_names},
            "actual": actual,
        })

    return {
        "names": all_names,
        "basic_names": basic_names,
        "points": points,
    }


def coded_matrix(design: dict) -> list[list[int]]:
    """Rows of +/-1 coded values with factors in output (sorted) order."""
    names = design["names"]
    return [[point["coded"][name] for name in names] for point in design["points"]]
