from __future__ import annotations

import json
from pathlib import Path

from agent import normalize as package_normalize
from tools import normalize as shim_normalize


def test_promoted_normalizer_matches_golden_fixture() -> None:
    fixture = Path(__file__).parent / 'fixtures' / 'normalize_golden.json'
    pairs = json.loads(fixture.read_text())
    for pair in pairs:
        assert package_normalize.normalize(pair['input']) == pair['normalized']


def test_shim_exports_same_functions_as_package() -> None:
    assert shim_normalize.normalize is package_normalize.normalize
    assert shim_normalize.bare_interjection is package_normalize.bare_interjection
    assert shim_normalize.is_empty is package_normalize.is_empty
    assert shim_normalize.NORMALIZE is package_normalize.NORMALIZE
    assert shim_normalize.CORE is package_normalize.CORE


def test_repeat_collapse_bounds_a_run_at_two_and_leaves_a_double_alone() -> None:
    """Pin the shape of the collapse rule, not one example of it.

    The golden fixture only carries runs of exactly three (`bagusss`, `aaminnn`,
    `susahhh`), which is why the module docstring could claim "4+ repeats to a
    run of 3" for a while without a single test noticing. A run of any length
    three or more collapses to exactly two.

    A double must survive: `alhamdulillah` and `allahuakbar` are whole spellings
    the table matches on, and `(\\w)\\1+ -> \\1` would rewrite them to
    `alahamdulilah` / `alahuakbar`, which no entry carries.
    """
    for repeats in (3, 4, 5, 6):
        assert package_normalize.normalize("bagu" + "s" * repeats) == "baguss"
    assert package_normalize.normalize("alhamdulillah") == "alhamdulillah"
    assert package_normalize.normalize("allahuakbar") == "allahuakbar"


def test_normalize_rule_order_has_no_cascades() -> None:
    later_keys = list(package_normalize.NORMALIZE.keys())
    for index, output in enumerate(package_normalize.NORMALIZE.values()):
        assert output not in later_keys[index + 1 :]
    assert package_normalize.normalize('doakan') == 'doa kan'
    assert package_normalize.normalize('doa') == 'doa'
    assert package_normalize.normalize('doa kan') == 'doa kan'
    assert package_normalize.normalize('nak mohon') == 'nak mohon'
    assert package_normalize.normalize('nak moham') == 'nak moham'
