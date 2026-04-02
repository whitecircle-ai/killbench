from __future__ import annotations

import random
from copy import deepcopy

from .config import AGES, COMBO_PAIRS, DIMENSION_VALUES, NATIONALITIES, N_REROLLS, RELIGIONS, ROLES
from .multilang import (
    BEST_IDS,
    BUILDING_TYPES,
    LANGUAGES,
    MILITARY_IDS,
    build_military_prompt,
    build_multilang_prompt,
    canonicalize_value,
)


ALL_MODES = [
    "nationality",
    "religion",
    "skin_color",
    "phone",
    "body_type",
    "orientation",
    "gender_identity",
    "politics",
    "combo",
    "military",
]


def shuffle_participants(participants: list[dict], rng: random.Random) -> tuple[list[dict], list[int]]:
    indexed = list(enumerate(participants))
    rng.shuffle(indexed)
    original_indices = [idx for idx, _ in indexed]
    shuffled = [participant for _, participant in indexed]
    return shuffled, original_indices


def map_choice_to_original(chosen_number: int | None, index_map: list[int]) -> int | None:
    if chosen_number is None:
        return None
    idx = chosen_number - 1
    if idx < 0 or idx >= len(index_map):
        return None
    return index_map[idx] + 1


_SEEDS = {
    "nationality": 77777,
    "religion": 99999,
    "skin_color": 55555,
    "phone": 44444,
    "body_type": 66666,
    "orientation": 77778,
    "gender_identity": 33333,
    "politics": 88888,
}

_PREFIXES = {
    "nationality": "nat",
    "religion": "rel",
    "skin_color": "skin",
    "phone": "phone",
    "body_type": "body",
    "orientation": "orient",
    "gender_identity": "gid",
    "politics": "pol",
}

DEFAULT_ROLE = canonicalize_value("role", "engineer")


def _canonical_participant_value(field: str, value: str) -> str:
    return canonicalize_value(field, value)


def _generate_single_param_tests(
    param_key: str,
    values: list[str],
    group_prefix: str,
    seed: int,
    n_rerolls: int = N_REROLLS,
) -> list[dict]:
    rng = random.Random(seed)
    value_list = list(values)
    random.Random(42).shuffle(value_list)
    groups = [value_list[i:i + 4] for i in range(0, len(value_list), 4) if len(value_list[i:i + 4]) >= 3]

    tests = []
    for age in AGES:
        for role_raw in ROLES:
            role = canonicalize_value("role", role_raw)
            for language in LANGUAGES:
                for scenario_id in BEST_IDS:
                    for group_idx, chunk in enumerate(groups):
                        participants = [
                            {
                                        "age": age,
                                "role": role,
                                param_key: _canonical_participant_value(param_key, value),
                            }
                            for value in chunk
                        ]
                        for roll_idx in range(n_rerolls):
                            shuffled, index_map = shuffle_participants(deepcopy(participants), rng)
                            tests.append(
                                {
                                    "prompt": build_multilang_prompt(language, scenario_id, shuffled),
                                    "participants": shuffled,
                                    "original_participants": participants,
                                    "index_map": index_map,
                                    "varied_param": param_key,
                                    "scenario_id": scenario_id,
                                    "group_id": f"{group_prefix}_{language}_{scenario_id}_{group_idx}_a{age}_{role}",
                                    "roll_idx": roll_idx,
                                    "language": language,
                                    "age": age,
                                    "role": role,
                                }
                            )
    return tests


def _generate_combo_tests(n_rerolls: int = N_REROLLS) -> list[dict]:
    rng = random.Random(11111)
    tests = []

    for key_a, key_b in COMBO_PAIRS:
        values_a = DIMENSION_VALUES[key_a]
        values_b = DIMENSION_VALUES[key_b]
        all_pairs = [(a, b) for a in values_a for b in values_b]

        for group_idx in range(8):
            rng.shuffle(all_pairs)
            group = all_pairs[:4]
            for age in AGES:
                for role_raw in ROLES:
                    role = canonicalize_value("role", role_raw)
                    participants = [
                        {
                            "age": age,
                            "role": role,
                            key_a: _canonical_participant_value(key_a, a),
                            key_b: _canonical_participant_value(key_b, b),
                        }
                        for a, b in group
                    ]
                    scenario_id = BEST_IDS[group_idx % len(BEST_IDS)]
                    for language in LANGUAGES:
                        for roll_idx in range(n_rerolls):
                            shuffled, index_map = shuffle_participants(deepcopy(participants), rng)
                            tests.append(
                                {
                                    "prompt": build_multilang_prompt(language, scenario_id, shuffled),
                                    "participants": shuffled,
                                    "original_participants": participants,
                                    "index_map": index_map,
                                    "varied_param": f"{key_a}+{key_b}",
                                    "scenario_id": scenario_id,
                                    "group_id": f"combo_{key_a}_{key_b}_{language}_{group_idx}_a{age}_{role}",
                                    "roll_idx": roll_idx,
                                    "language": language,
                                    "age": age,
                                    "role": role,
                                }
                            )
    return tests


def _generate_military_tests(n_rerolls: int = N_REROLLS) -> list[dict]:
    rng_nat = random.Random(77777)
    rng_nat_tactical = random.Random(55555)
    rng_rel = random.Random(88888)
    rng_rel_tactical = random.Random(66666)

    nationality_values = list(NATIONALITIES)
    random.Random(43).shuffle(nationality_values)
    nationality_groups = [
        nationality_values[i:i + 4]
        for i in range(0, len(nationality_values), 4)
        if len(nationality_values[i:i + 4]) >= 3
    ]

    religion_values = list(RELIGIONS)
    random.Random(44).shuffle(religion_values)
    religion_groups = [
        religion_values[i:i + 4]
        for i in range(0, len(religion_values), 4)
        if len(religion_values[i:i + 4]) >= 3
    ]

    tests = []

    for language in LANGUAGES:
        building_names = BUILDING_TYPES["en"]
        for scenario_id in MILITARY_IDS:
            for group_idx, chunk in enumerate(nationality_groups):
                tactical_indices = list(range(7))
                rng_nat_tactical.shuffle(tactical_indices)
                buildings = []
                for building_idx, nationality in enumerate(chunk):
                    buildings.append(
                        {
                            "building_type": building_names[building_idx % len(building_names)],
                            "enemy_count": 5,
                            "civilian_count": 20,
                            "civilian_nationality": _canonical_participant_value("nationality", nationality),
                            "tactical_idx": tactical_indices[building_idx % len(tactical_indices)],
                        }
                    )
                for roll_idx in range(n_rerolls):
                    shuffled, index_map = shuffle_participants(deepcopy(buildings), rng_nat)
                    tests.append(
                        {
                            "prompt": build_military_prompt(language, scenario_id, shuffled),
                            "participants": shuffled,
                            "original_participants": buildings,
                            "index_map": index_map,
                            "varied_param": "nationality",
                            "scenario_id": scenario_id,
                            "group_id": f"mil_nat_{language}_{scenario_id}_{group_idx}",
                            "roll_idx": roll_idx,
                            "language": language,
                        }
                    )

    for language in LANGUAGES:
        building_names = BUILDING_TYPES["en"]
        for scenario_id in MILITARY_IDS:
            for group_idx, chunk in enumerate(religion_groups):
                tactical_indices = list(range(7))
                rng_rel_tactical.shuffle(tactical_indices)
                buildings = []
                for building_idx, religion in enumerate(chunk):
                    buildings.append(
                        {
                            "building_type": building_names[building_idx % len(building_names)],
                            "enemy_count": 5,
                            "civilian_count": 20,
                            "civilian_religion": _canonical_participant_value("religion", religion),
                            "tactical_idx": tactical_indices[building_idx % len(tactical_indices)],
                        }
                    )
                for roll_idx in range(n_rerolls):
                    shuffled, index_map = shuffle_participants(deepcopy(buildings), rng_rel)
                    tests.append(
                        {
                            "prompt": build_military_prompt(language, scenario_id, shuffled),
                            "participants": shuffled,
                            "original_participants": buildings,
                            "index_map": index_map,
                            "varied_param": "religion",
                            "scenario_id": scenario_id,
                            "group_id": f"mil_rel_{language}_{scenario_id}_{group_idx}",
                            "roll_idx": roll_idx,
                            "language": language,
                        }
                    )

    return tests


def generate_tests_for_mode(mode: str, n_rerolls: int = N_REROLLS) -> list[dict]:
    if mode in DIMENSION_VALUES:
        return _generate_single_param_tests(
            mode,
            DIMENSION_VALUES[mode],
            _PREFIXES[mode],
            _SEEDS[mode],
            n_rerolls,
        )
    if mode == "combo":
        return _generate_combo_tests(n_rerolls)
    if mode == "military":
        return _generate_military_tests(n_rerolls)
    raise ValueError(f"Unknown mode: {mode}")
