"""Tests for sim.gather — resource gather/deposit (AC-5..AC-9, AC-8).

`start_move` is patched on the real `sim.pathfinding` module to teleport
the entity to its target so we can focus on gather logic. `is_moving`
is patched to always return False so gather_progress accrues each tick.
"""

from __future__ import annotations

import pytest

import sim.entities
import sim.pathfinding
import sim.gather as gather
from sim.contract import CARRY_CAP, TICK_HZ, Entity, Game, Map, Player


@pytest.fixture(autouse=True)
def _siblings(monkeypatch):
    def start_move(game, entity_id, target_tile):
        for e in game.entities:
            if e.entity_id == entity_id:
                e.pos = tuple(target_tile)
                return True
        return False

    def cancel_move(entity_id):
        return None

    def is_moving(entity_id):
        return False

    monkeypatch.setattr(sim.pathfinding, "start_move", start_move)
    monkeypatch.setattr(sim.pathfinding, "cancel_move", cancel_move)
    monkeypatch.setattr(sim.pathfinding, "is_moving", is_moving)
    monkeypatch.setattr(sim.entities, "get_stats",
                        lambda kind: {"hp": 25, "max_hp": 25, "sight": 5})

    gather._gather_state.clear()
    yield
    gather._gather_state.clear()


def _make_game(entities):
    terrain = [["grass"] * 20 for _ in range(20)]
    m = Map(width=20, height=20, terrain=terrain)
    players = [Player(player_id=0, wood=0, gold=0, pop_cap=5),
               Player(player_id=1, wood=0, gold=0, pop_cap=5)]
    return Game(players=players, entities=list(entities), map=m)


def _ent(eid, kind, owner, pos, hp=25, max_hp=25):
    return Entity(entity_id=eid, kind=kind, owner=owner, pos=pos, hp=hp, max_hp=max_hp)


def test_start_gather_bad_ids_returns_false():
    v = _ent(1, "villager", 0, (5, 5))
    tree = _ent(2, "tree", 0, (10, 10), hp=40, max_hp=40)
    g = _make_game([v, tree])
    assert gather.start_gather(g, 999, 2) is False
    assert gather.start_gather(g, 1, 999) is False
    tc = _ent(3, "town_center", 0, (3, 3), hp=800, max_hp=800)
    g2 = _make_game([v, tc])
    assert gather.start_gather(g2, 1, 3) is False
    assert gather.is_gathering(1) is False


def test_gather_tree_increases_wood():
    v = _ent(1, "villager", 0, (5, 5))
    tree = _ent(2, "tree", 0, (10, 10), hp=40, max_hp=40)
    tc = _ent(3, "town_center", 0, (0, 0), hp=800, max_hp=800)
    g = _make_game([v, tree, tc])
    assert gather.start_gather(g, 1, 2) is True
    for _ in range(TICK_HZ * (CARRY_CAP + 5)):
        gather.tick_gather(g)
    assert g.players[0].wood >= 1
    assert v.carry_amount <= CARRY_CAP


def test_gather_sets_carrying_wood_for_tree():
    v = _ent(1, "villager", 0, (10, 10))
    tree = _ent(2, "tree", 0, (10, 10), hp=40, max_hp=40)
    g = _make_game([v, tree])
    assert gather.start_gather(g, 1, 2) is True
    for _ in range(TICK_HZ + 2):
        gather.tick_gather(g)
    assert v.carrying == "wood"


def test_gather_sets_carrying_gold_for_gold_mine():
    v = _ent(1, "villager", 0, (10, 10))
    mine = _ent(2, "gold_mine", 0, (10, 10), hp=200, max_hp=200)
    g = _make_game([v, mine])
    assert gather.start_gather(g, 1, 2) is True
    for _ in range(TICK_HZ + 2):
        gather.tick_gather(g)
    assert v.carrying == "gold"


def test_second_start_gather_replaces_first():
    v = _ent(1, "villager", 0, (5, 5))
    t1 = _ent(2, "tree", 0, (10, 10), hp=40, max_hp=40)
    t2 = _ent(3, "tree", 0, (15, 15), hp=40, max_hp=40)
    g = _make_game([v, t1, t2])
    assert gather.start_gather(g, 1, 2) is True
    assert gather.start_gather(g, 1, 3) is True
    assert gather._gather_state[1].node_id == 3


def test_tree_hp_decrements_and_clears_on_death():
    v = _ent(1, "villager", 0, (10, 10))
    tree = _ent(2, "tree", 0, (10, 10), hp=3, max_hp=40)
    g = _make_game([v, tree])
    assert gather.start_gather(g, 1, 2) is True
    start_hp = tree.hp
    for _ in range(TICK_HZ + 1):
        gather.tick_gather(g)
    assert tree.hp == start_hp - 1
    for _ in range(TICK_HZ * 5):
        gather.tick_gather(g)
    assert tree.hp <= 0
    assert gather.is_gathering(1) is False
