"""Tests for sim.combat — combat tick + death cleanup (AC-14, AC-25).

Parallel-leaf siblings `sim.entities` and `sim.pathfinding` are stubbed via
sys.modules so combat can be tested in isolation.
"""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass

import pytest

from sim.contract import Entity, Game, Map, Player, TICK_HZ


# ---------------------------------------------------------------------------
# Sibling stubs (monkeypatched into sys.modules before importing sim.combat)
# ---------------------------------------------------------------------------


@dataclass
class _Stats:
    damage_per_sec: float
    attack_range_tiles: int
    speed_tiles_per_sec: float = 2.0
    sight_tiles: int = 5
    max_hp: int = 60


_STATS_BY_KIND: dict[str, _Stats] = {
    "soldier": _Stats(damage_per_sec=8.0, attack_range_tiles=1, max_hp=60),
    "archer": _Stats(damage_per_sec=5.0, attack_range_tiles=5, max_hp=35),
    "villager": _Stats(damage_per_sec=0.0, attack_range_tiles=0, max_hp=25),
    "wall": _Stats(damage_per_sec=0.0, attack_range_tiles=0, max_hp=200),
}


def _install_stubs() -> dict:
    """Install fake sim.entities + sim.pathfinding into sys.modules.

    Returns a dict tracking pathfinding state for assertions.
    """
    entities_mod = types.ModuleType("sim.entities")
    entities_mod.get_stats = lambda kind: _STATS_BY_KIND[kind]
    sys.modules["sim.entities"] = entities_mod

    move_state: dict[int, tuple[int, int]] = {}

    def start_move(game, entity_id, target_tile):
        move_state[entity_id] = tuple(target_tile)
        return True

    def cancel_move(entity_id):
        move_state.pop(entity_id, None)

    def is_moving(entity_id):
        return entity_id in move_state

    pf_mod = types.ModuleType("sim.pathfinding")
    pf_mod.start_move = start_move
    pf_mod.cancel_move = cancel_move
    pf_mod.is_moving = is_moving
    sys.modules["sim.pathfinding"] = pf_mod

    return {"move_state": move_state}


@pytest.fixture(autouse=True)
def stubs():
    state = _install_stubs()
    # Reset combat module attack state between tests
    if "sim.combat" in sys.modules:
        sys.modules["sim.combat"]._attack_state.clear()
    yield state
    sys.modules.pop("sim.entities", None)
    sys.modules.pop("sim.pathfinding", None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_game(entities: list[Entity]) -> Game:
    terrain = [["grass"] * 20 for _ in range(20)]
    m = Map(width=20, height=20, terrain=terrain)
    players = [Player(player_id=0, wood=0, gold=0, pop_cap=5),
               Player(player_id=1, wood=0, gold=0, pop_cap=5)]
    return Game(players=players, entities=entities, map=m)


def _ent(eid, kind, owner, pos, hp=None):
    stats = _STATS_BY_KIND[kind]
    if hp is None:
        hp = stats.max_hp
    return Entity(entity_id=eid, kind=kind, owner=owner, pos=pos,
                  hp=hp, max_hp=stats.max_hp)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_start_attack_same_owner_returns_false():
    from sim import combat
    a = _ent(1, "soldier", owner=0, pos=(5, 5))
    b = _ent(2, "soldier", owner=0, pos=(6, 5))
    g = _make_game([a, b])
    assert combat.start_attack(g, 1, 2) is False
    assert combat.is_attacking(1) is False


def test_start_attack_villager_returns_false():
    from sim import combat
    v = _ent(1, "villager", owner=0, pos=(5, 5))
    enemy = _ent(2, "soldier", owner=1, pos=(6, 5))
    g = _make_game([v, enemy])
    assert combat.start_attack(g, 1, 2) is False


def test_start_attack_valid_installs_state():
    from sim import combat
    a = _ent(1, "soldier", owner=0, pos=(5, 5))
    b = _ent(2, "soldier", owner=1, pos=(6, 5))
    g = _make_game([a, b])
    assert combat.start_attack(g, 1, 2) is True
    assert combat.is_attacking(1) is True


def test_adjacent_soldiers_one_second_damage():
    """AC-14: after TICK_HZ ticks (1s), target hp == max_hp - damage_per_sec."""
    from sim import combat
    a = _ent(1, "soldier", owner=0, pos=(5, 5))
    b = _ent(2, "soldier", owner=1, pos=(6, 5))
    g = _make_game([a, b])
    combat.start_attack(g, 1, 2)
    for _ in range(TICK_HZ):
        combat.tick_combat(g)
    assert b.hp == 60 - 8


def test_target_killed_removed_from_entities():
    from sim import combat
    a = _ent(1, "soldier", owner=0, pos=(5, 5))
    b = _ent(2, "soldier", owner=1, pos=(6, 5), hp=5)
    g = _make_game([a, b])
    combat.start_attack(g, 1, 2)
    for _ in range(TICK_HZ * 2):
        combat.tick_combat(g)
        if b not in g.entities:
            break
    assert b not in g.entities


def test_all_attackers_cleared_when_target_dies():
    from sim import combat
    a1 = _ent(1, "soldier", owner=0, pos=(5, 5))
    a2 = _ent(2, "soldier", owner=0, pos=(7, 5))
    target = _ent(3, "soldier", owner=1, pos=(6, 5), hp=5)
    g = _make_game([a1, a2, target])
    combat.start_attack(g, 1, 3)
    combat.start_attack(g, 2, 3)
    for _ in range(TICK_HZ * 2):
        combat.tick_combat(g)
        if target not in g.entities:
            break
    assert target not in g.entities
    assert combat.is_attacking(1) is False
    assert combat.is_attacking(2) is False


def test_out_of_range_attacker_issues_move(stubs):
    from sim import combat
    a = _ent(1, "archer", owner=0, pos=(0, 0))
    b = _ent(2, "soldier", owner=1, pos=(15, 15))
    g = _make_game([a, b])
    combat.start_attack(g, 1, 2)
    combat.tick_combat(g)
    assert 1 in stubs["move_state"]
    assert stubs["move_state"][1] == (15, 15)


def test_cancel_attack_clears_state():
    from sim import combat
    a = _ent(1, "soldier", owner=0, pos=(5, 5))
    b = _ent(2, "soldier", owner=1, pos=(6, 5))
    g = _make_game([a, b])
    combat.start_attack(g, 1, 2)
    combat.cancel_attack(1)
    assert combat.is_attacking(1) is False
    combat.cancel_attack(999)  # silent no-op


def test_archer_in_range_does_damage():
    from sim import combat
    a = _ent(1, "archer", owner=0, pos=(5, 5))
    b = _ent(2, "soldier", owner=1, pos=(9, 8))  # Chebyshev = 4, range 5
    g = _make_game([a, b])
    combat.start_attack(g, 1, 2)
    for _ in range(TICK_HZ):
        combat.tick_combat(g)
    assert b.hp == 60 - 5
