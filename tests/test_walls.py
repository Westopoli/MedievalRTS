"""Tests for sim.walls — passability lookup for walls/gates (AC-23..AC-25)."""

from __future__ import annotations

from sim.contract import Entity, Game, Map, Player
from sim.walls import is_passable_for, wall_or_gate_at


def _make_game(entities: list[Entity]) -> Game:
    terrain = [["grass"] * 10 for _ in range(10)]
    m = Map(width=10, height=10, terrain=terrain)
    players = [Player(player_id=0, wood=0, gold=0, pop_cap=5),
               Player(player_id=1, wood=0, gold=0, pop_cap=5)]
    return Game(players=players, entities=entities, map=m)


def _ent(eid: int, kind: str, owner: int, pos: tuple[int, int], hp: int = 200) -> Entity:
    return Entity(entity_id=eid, kind=kind, owner=owner, pos=pos, hp=hp, max_hp=200)


def test_empty_tile_passable():
    g = _make_game([])
    assert is_passable_for(g, (5, 5), 0) is True
    assert wall_or_gate_at(g, (5, 5)) is None


def test_wall_blocks_all_owners():
    w = _ent(1, "wall", owner=0, pos=(5, 5), hp=200)
    g = _make_game([w])
    assert is_passable_for(g, (5, 5), 0) is False
    assert is_passable_for(g, (5, 5), 1) is False
    assert wall_or_gate_at(g, (5, 5)) is w


def test_gate_passable_for_owner_only():
    gate = _ent(2, "gate", owner=0, pos=(5, 5), hp=200)
    g = _make_game([gate])
    assert is_passable_for(g, (5, 5), 0) is True
    assert is_passable_for(g, (5, 5), 1) is False
    assert wall_or_gate_at(g, (5, 5)) is gate


def test_destroyed_wall_passable():
    w = _ent(3, "wall", owner=0, pos=(5, 5), hp=0)
    g = _make_game([w])
    assert is_passable_for(g, (5, 5), 0) is True
    assert is_passable_for(g, (5, 5), 1) is True
    assert wall_or_gate_at(g, (5, 5)) is None


def test_destroyed_gate_passable():
    gate = _ent(4, "gate", owner=0, pos=(5, 5), hp=0)
    g = _make_game([gate])
    assert is_passable_for(g, (5, 5), 1) is True
    assert wall_or_gate_at(g, (5, 5)) is None


def test_non_wall_entities_ignored():
    # A tree at the tile is NOT a wall/gate — this helper returns passable.
    tree = _ent(5, "tree", owner=-1, pos=(5, 5), hp=50)
    g = _make_game([tree])
    assert is_passable_for(g, (5, 5), 0) is True
    assert wall_or_gate_at(g, (5, 5)) is None
