"""Tests for sim.combat — combat tick + death cleanup (AC-14, AC-25).

Originally stubbed `sim.entities` and `sim.pathfinding` via `sys.modules`
injection. Now patches functions on the real modules so the stubs do not
leak across test files (which used to break `pytest tests/` collection or
later tests that re-bound `sim.<leaf>` attributes on the `sim` package).
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

import sim.entities
import sim.pathfinding
import sim.combat as combat
from sim.contract import Entity, Game, Map, Player, TICK_HZ


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


@pytest.fixture(autouse=True)
def stubs(monkeypatch):
    move_state: dict[int, tuple[int, int]] = {}

    def start_move(game, entity_id, target_tile):
        move_state[entity_id] = tuple(target_tile)
        return True

    def cancel_move(entity_id):
        move_state.pop(entity_id, None)

    def is_moving(entity_id):
        return entity_id in move_state

    monkeypatch.setattr(sim.entities, "get_stats", lambda kind: _STATS_BY_KIND[kind])
    monkeypatch.setattr(sim.pathfinding, "start_move", start_move)
    monkeypatch.setattr(sim.pathfinding, "cancel_move", cancel_move)
    monkeypatch.setattr(sim.pathfinding, "is_moving", is_moving)

    combat._attack_state.clear()
    yield {"move_state": move_state}
    combat._attack_state.clear()


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


def test_start_attack_same_owner_returns_false():
    a = _ent(1, "soldier", owner=0, pos=(5, 5))
    b = _ent(2, "soldier", owner=0, pos=(6, 5))
    g = _make_game([a, b])
    assert combat.start_attack(g, 1, 2) is False
    assert combat.is_attacking(1) is False


def test_start_attack_villager_returns_false():
    v = _ent(1, "villager", owner=0, pos=(5, 5))
    enemy = _ent(2, "soldier", owner=1, pos=(6, 5))
    g = _make_game([v, enemy])
    assert combat.start_attack(g, 1, 2) is False


def test_start_attack_valid_installs_state():
    a = _ent(1, "soldier", owner=0, pos=(5, 5))
    b = _ent(2, "soldier", owner=1, pos=(6, 5))
    g = _make_game([a, b])
    assert combat.start_attack(g, 1, 2) is True
    assert combat.is_attacking(1) is True


def test_adjacent_soldiers_one_second_damage():
    """AC-14: after TICK_HZ ticks (1s), target hp == max_hp - damage_per_sec."""
    a = _ent(1, "soldier", owner=0, pos=(5, 5))
    b = _ent(2, "soldier", owner=1, pos=(6, 5))
    g = _make_game([a, b])
    combat.start_attack(g, 1, 2)
    for _ in range(TICK_HZ):
        combat.tick_combat(g)
    assert b.hp == 60 - 8


def test_target_killed_removed_from_entities():
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
    a = _ent(1, "archer", owner=0, pos=(0, 0))
    b = _ent(2, "soldier", owner=1, pos=(15, 15))
    g = _make_game([a, b])
    combat.start_attack(g, 1, 2)
    combat.tick_combat(g)
    assert 1 in stubs["move_state"]
    assert stubs["move_state"][1] == (15, 15)


def test_cancel_attack_clears_state():
    a = _ent(1, "soldier", owner=0, pos=(5, 5))
    b = _ent(2, "soldier", owner=1, pos=(6, 5))
    g = _make_game([a, b])
    combat.start_attack(g, 1, 2)
    combat.cancel_attack(1)
    assert combat.is_attacking(1) is False
    combat.cancel_attack(999)


def test_archer_in_range_does_damage():
    a = _ent(1, "archer", owner=0, pos=(5, 5))
    b = _ent(2, "soldier", owner=1, pos=(9, 8))  # Chebyshev = 4, range 5
    g = _make_game([a, b])
    combat.start_attack(g, 1, 2)
    for _ in range(TICK_HZ):
        combat.tick_combat(g)
    assert b.hp == 60 - 5
