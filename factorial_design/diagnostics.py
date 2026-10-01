"""Confounding groups, defining relations and design resolution.

All diagnostics operate on the unreplicated standard design; repeat runs do
not change which effects are identifiable.
"""

from itertools import combinations


def _interaction_key(names: tuple[str, ...]) -> str:
    return "*".join(names)


def _effect_sort_key(key: str):
    if key == "I":
        return (0, ())
    factors = tuple(key.split("*"))
    return (len(factors), factors)


def build_effects(design: dict) -> dict[str, list[int]]:
    """Coded columns for intercept, main effects and two-factor interactions."""
    names = design["names"]
    rows = [[point["coded"][name] for name in names] for point in design["points"]]

    effects: dict[str, list[int]] = {"I": [1] * len(rows)}
    for name in names:
        col = names.index(name)
        effects[name] = [row[col] for row in rows]
    for first, second in combinations(names, 2):
        col_first = names.index(first)
        col_second = names.index(second)
        effects[_interaction_key((first, second))] = [
            row[col_first] * row[col_second] for row in rows
        ]
    return effects


def _column_relation(left: list[int], right: list[int]) -> int:
    """Return 1 if columns are identical, -1 if opposite, 0 otherwise."""
    if all(a == b for a, b in zip(left, right)):
        return 1
    if all(a == -b for a, b in zip(left, right)):
        return -1
    return 0


def build_alias_groups(effects: dict[str, list[int]]) -> list[dict]:
    """Group effects whose columns are equal or exact opposites.

    Each member records its sign relative to the group representative.
    Representatives and members are selected by (factor count, name tuple)
    ordering; the intercept always leads its own group. Groups are sorted by
    their representative, singletons included.
    """
    ordered_keys = sorted(effects, key=_effect_sort_key)
    groups: list[dict] = []
    assigned: set[str] = set()

    for representative in ordered_keys:
        if representative in assigned:
            continue
        members = []
        for candidate in ordered_keys:
            if candidate in assigned:
                continue
            relation = _column_relation(effects[representative], effects[candidate])
            if relation != 0:
                members.append({"effect": candidate, "sign": relation})
                assigned.add(candidate)
        groups.append({"representative": representative, "members": members})
    return groups


def _prod(values) -> int:
    result = 1
    for value in values:
        result *= value
    return result


def find_defining_relations(design: dict) -> list[dict]:
    """Non-empty factor subsets whose product column is constantly +/-1."""
    names = design["names"]
    rows = [[point["coded"][name] for name in names] for point in design["points"]]
    relations = []
    for size in range(1, len(names) + 1):
        for subset in combinations(range(len(names)), size):
            column = [_prod(row[i] for i in subset) for row in rows]
            if all(value == 1 for value in column):
                sign = 1
            elif all(value == -1 for value in column):
                sign = -1
            else:
                continue
            factor_names = [names[i] for i in subset]
            word = _interaction_key(tuple(factor_names))
            relations.append({"word": word, "factors": factor_names, "length": size, "sign": sign})
    return relations


def build_confounding_lists(effects: dict[str, list[int]]) -> dict:
    """Main-main and main-by-two-factor-interaction aliasing (sign retained)."""
    names = [key for key in effects if "*" not in key and key != "I"]
    interactions = [key for key in effects if "*" in key]

    main_main = []
    for first, second in combinations(names, 2):
        relation = _column_relation(effects[first], effects[second])
        if relation != 0:
            main_main.append({"left": first, "right": second, "sign": relation})

    main_interaction = []
    for name in names:
        for interaction in interactions:
            relation = _column_relation(effects[name], effects[interaction])
            if relation != 0:
                main_interaction.append({
                    "main": name,
                    "interaction": interaction,
                    "sign": relation,
                })
    main_interaction.sort(key=lambda item: (_effect_sort_key(item["main"]),
                                            _effect_sort_key(item["interaction"])))
    return {"main_main": main_main, "main_interaction": main_interaction}


def build_diagnostics(design: dict, config=None) -> dict:
    effects = build_effects(design)
    groups = build_alias_groups(effects)
    relations = find_defining_relations(design)
    confounding = build_confounding_lists(effects)

    full_factorial = len(relations) == 0
    resolution = None if full_factorial else min(rel["length"] for rel in relations)

    return {
        "num_factors": len(design["names"]),
        "num_points": len(design["points"]),
        "factor_names": design["names"],
        "basic_factors": design["basic_names"],
        "full_factorial": full_factorial,
        "resolution": resolution,
        "defining_relations": [
            {"word": rel["word"], "factors": rel["factors"], "sign": rel["sign"]}
            for rel in relations
        ],
        "alias_groups": [
            {
                "representative": group["representative"],
                "members": group["members"],
            }
            for group in groups
        ],
        "confounding": confounding,
    }
