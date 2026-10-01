"""Confounding / alias diagnostics for the unreplicated standard design."""

from __future__ import annotations

from itertools import combinations

from .config import DesignConfig
from .design import coded_matrix


def _columns(config: DesignConfig) -> dict[tuple[str, ...], tuple[int, ...]]:
    """Coded columns keyed by effect term tuple; () is the intercept."""
    rows = coded_matrix(config)
    names = sorted(rows[0])
    cols: dict[tuple[str, ...], tuple[int, ...]] = {}
    cols[()] = tuple(1 for _ in rows)
    for name in names:
        cols[(name,)] = tuple(row[name] for row in rows)
    for a, b in combinations(names, 2):
        cols[(a, b)] = tuple(
            rows[i][a] * rows[i][b] for i in range(len(rows))
        )
    return cols


def _effect_sort_key(terms: tuple[str, ...]):
    return (len(terms), list(terms))


def _effect_label(terms: tuple[str, ...]) -> str:
    return "(intercept)" if not terms else "*".join(terms)


def confounding_groups(config: DesignConfig) -> list:
    """Groups of identical/opposite columns among intercept, mains, 2FIs."""
    cols = _columns(config)
    buckets: dict[tuple[int, ...], list[tuple[str, ...]]] = {}
    for terms, vector in cols.items():
        key = min(vector, tuple(-v for v in vector))
        buckets.setdefault(key, []).append(terms)
    groups = []
    for members in buckets.values():
        members.sort(key=_effect_sort_key)
        representative = members[0]
        rep_vector = cols[representative]
        groups.append({
            "representative": _effect_label(representative),
            "members": [
                {
                    "effect": _effect_label(terms),
                    "order": len(terms),
                    "sign_vs_representative": 1 if cols[terms] == rep_vector else -1,
                }
                for terms in members
            ],
        })
    groups.sort(key=lambda g: _effect_sort_key(
        tuple() if g["representative"] == "(intercept)"
        else tuple(g["representative"].split("*"))
    ))
    return groups


def defining_relations(config: DesignConfig) -> list:
    """All nonempty factor subsets whose coded product is constantly +/-1."""
    rows = coded_matrix(config)
    names = sorted(rows[0])
    relations = []
    for size in range(1, len(names) + 1):
        for subset in combinations(names, size):
            product = [1] * len(rows)
            for name in subset:
                for i, row in enumerate(rows):
                    product[i] *= row[name]
            if all(v == 1 for v in product):
                relations.append({"factors": list(subset), "word": "*".join(subset), "sign": 1})
            elif all(v == -1 for v in product):
                relations.append({"factors": list(subset), "word": "-" + "*".join(subset), "sign": -1})
    return relations


def build_diagnostics(config: DesignConfig) -> dict:
    groups = confounding_groups(config)
    relations = defining_relations(config)
    full_factorial = not config.generated_factors
    resolution = min(len(r["factors"]) for r in relations) if relations else None

    main_main = []
    main_interaction = []
    for group in groups:
        effects = [m["effect"] for m in group["members"]]
        mains = [e for e in effects if "*" not in e]
        interactions = [e for e in effects if "*" in e]
        for i, a in enumerate(mains):
            for b in mains[i + 1:]:
                main_main.append([a, b])
        for main in mains:
            for interaction in interactions:
                main_interaction.append({"main_effect": main, "interaction": interaction})

    return {
        "n_basic_factors": len(config.basic_factors),
        "n_factors": len(config.factors),
        "n_standard_points": 2 ** len(config.basic_factors),
        "full_factorial": full_factorial,
        "resolution": resolution,
        "defining_relations": relations,
        "confounding_groups": groups,
        "main_effect_confounding": main_main,
        "main_effect_vs_interaction_confounding": main_interaction,
    }
