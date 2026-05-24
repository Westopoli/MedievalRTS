"""Tests for sim.gather — resource gather/deposit (AC-5..AC-9, AC-8).

Sibling leaves (sim.pathfinding, sim.entities) may not be present yet, so
we monkeypatch the symbols sim.gather imports at runtime: start_move is
made to teleport the entity to its target so we can focus on gather logic.
"""

from __future__ import annotations

import sys
import types

import pytest

from sim.contract import CARRY_CAP, TICK_HZ, Entity, Game, Map, Player


def _install_sibling_stubs(monkeypatch):
    """Create in-memory sim.pathfinding and sim.entities modules if missing."""
    # pathfinding: start_move teleports, is_moving returns False, cancel_move noop
    pf = types.ModuleType("sim.pathfinding")

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

    pf.start_move = start_move
    pf.cancel_move = cancel_move
    pf.is_moving = is_moving
    monkeypatch.setitem(sys.modules, "sim.pathfinding", pf)

    ents = types.ModuleType("sim.entities")

    def get_stats(kind):
        return {"hp": 25, "max_hp": 25, "sight": 5}

    ents.get_stats = get_stats
    monkeypatch.setitem(sys.modules, "sim.entities", ents)


@pytest.fixture(autouse=True)
def _siblings(monkeypatch):
    _install_sibling_stubs(monkeypatch)
    # Reload sim.gather so it re-binds to patched siblings
    if "sim.gather" in sys.modules:
        del sys.modules["sim.gather"]
    yield


def _make_game(entities):
    terrain = [["grass"] * 20 for _ in range(20)]
    m = Map(width=20, height=20, terrain=terrain)
    players = [Player(player_id=0, wood=0, gold=0, pop_cap=5),
               Player(player_id=1, wood=0, gold=0, pop_cap=5)]
    return Game(players=players, entities=list(entities), map=m)


def _ent(eid, kind, owner, pos, hp=25, max_hp=25):
    return Entity(entity_id=eid, kind=kind, owner=owner, pos=pos, hp=hp, max_hp=max_hp)


def test_start_gather_bad_ids_returns_false():
    from sim.gather import is_gathering, start_gather
    v = _ent(1, "villager", 0, (5, 5))
    tree = _ent(2, "tree", 0, (10, 10), hp=40, max_hp=40)
    g = _make_game([v, tree])
    assert start_gather(g, 999, 2) is False
    assert start_gather(g, 1, 999) is False
    # wrong kind: villager-as-resource and tc-as-villager
    tc = _ent(3, "town_center", 0, (3, 3), hp=800, max_hp=800)
    g2 = _make_game([v, tc])
    assert start_gather(g2, 1, 3) is False
    assert is_gathering(1) is False


def test_gather_tree_increases_wood():
    from sim.gather import start_gather, tick_gather
    v = _ent(1, "villager", 0, (5, 5))
    tree = _ent(2, "tree", 0, (10, 10), hp=40, max_hp=40)
    tc = _ent(3, "town_center", 0, (0, 0), hp=800, max_hp=800)
    g = _make_game([v, tree, tc])
    assert start_gather(g, 1, 2) is True
    # Plenty of ticks to: move to tree, gather CARRY_CAP, move to tc, deposit.
    for _ in range(TICK_HZ * (CARRY_CAP + 5)):
        tick_gather(g)
    assert g.players[0].wood >= 1
    assert v.carry_amount <= CARRY_CAP


def test_gather_sets_carrying_wood_for_tree():
    from sim.gather import start_gather, tick_gather
    v = _ent(1, "villager", 0, (10, 10))
    tree = _ent(2, "tree", 0, (10, 10), hp=40, max_hp=40)
    g = _make_game([v, tree])
    assert start_gather(g, 1, 2) is True
    for _ in range(TICK_HZ + 2):
        tick_gather(g)
    assert v.carrying == "wood"


def test_gather_sets_carrying_gold_for_gold_mine():
    from sim.gather import start_gather, tick_gather
    v = _ent(1, "villager", 0, (10, 10))
    mine = _ent(2, "gold_mine", 0, (10, 10), hp=200, max_hp=200)
    g = _make_game([v, mine])
    assert start_gather(g, 1, 2) is True
    for _ in range(TICK_HZ + 2):
        tick_gather(g)
    assert v.carrying == "gold"


def test_second_start_gather_replaces_first():
    from sim.gather import _gather_state, start_gather
    v = _ent(1, "villager", 0, (5, 5))
    t1 = _ent(2, "tree", 0, (10, 10), hp=40, max_hp=40)
    t2 = _ent(3, "tree", 0, (15, 15), hp=40, max_hp=40)
    g = _make_game([v, t1, t2])
    assert start_gather(g, 1, 2) is True
    assert start_gather(g, 1, 3) is True
    assert _gather_state[1].node_id == 3


def test_tree_hp_decrements_and_clears_on_death():
    from sim.gather import is_gathering, start_gather, tick_gather
    v = _ent(1, "villager", 0, (10, 10))
    tree = _ent(2, "tree", 0, (10, 10), hp=3, max_hp=40)
    g = _make_game([v, tree])
    assert start_gather(g, 1, 2) is True
    start_hp = tree.hp
    # First gather tick fires after TICK_HZ ticks
    for _ in range(TICK_HZ + 1):
        tick_gather(g)
    assert tree.hp == start_hp - 1
    # Drain the tree
    for _ in range(TICK_HZ * 5):
        tick_gather(g)
    assert tree.hp <= 0
    assert is_gathering(1) is False
