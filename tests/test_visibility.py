"""Tests for sim/visibility.py — per-player fog-of-war."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

import sim.entities
from sim import visibility as vis
from sim.contract import (
    BuildingSnapshot,
    Entity,
    Game,
    Map,
    MAP_H,
    MAP_W,
    Player,
)


@dataclass(frozen=True)
class _Stats:
    sight: int = 5


_SIGHTS = {
    "villager": 5,
    "soldier": 5,
    "archer": 6,
    "scout": 9,
    "town_center": 8,
    "house": 4,
    "barracks": 5,
    "wall": 2,
    "gate": 3,
    "tree": 0,
    "gold_mine": 0,
}


def _fake_get_stats(kind):
    return _Stats(sight=_SIGHTS.get(kind, 0))


@pytest.fixture(autouse=True)
def _patch_entities(monkeypatch):
    monkeypatch.setattr(sim.entities, "get_stats", _fake_get_stats, raising=False)
    yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mk_game(entities=None) -> Game:
    m = Map(width=MAP_W, height=MAP_H, terrain=[["grass"] * MAP_H for _ in range(MAP_W)])
    g = Game(
        players=[Player(0, 0, 0, 5), Player(1, 0, 0, 5)],
        entities=list(entities or []),
        map=m,
    )
    return g


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_init_visibility_shape_and_unseen():
    g = _mk_game()
    vis.init_visibility(g)
    assert len(g.visibility) == 2
    assert len(g.visibility[0]) == MAP_W
    assert len(g.visibility[0][0]) == MAP_H
    assert g.visibility[0][0][0] == "unseen"
    assert g.visibility[1][MAP_W - 1][MAP_H - 1] == "unseen"
    assert g.explored_snapshots == [{}, {}]


def test_init_idempotent():
    g = _mk_game()
    vis.init_visibility(g)
    g.visibility[0][0][0] = "visible"
    vis.init_visibility(g)
    # idempotent: must not wipe existing correct-shape grid
    assert g.visibility[0][0][0] == "visible"


def test_single_villager_chebyshev_5():
    e = Entity(entity_id=0, kind="villager", owner=0, pos=(10, 10), hp=25, max_hp=25)
    g = _mk_game([e])
    vis.init_visibility(g)
    vis.recompute_visibility(g)
    # within Chebyshev 5
    assert g.visibility[0][10][10] == "visible"
    assert g.visibility[0][15][10] == "visible"
    assert g.visibility[0][10][15] == "visible"
    assert g.visibility[0][15][15] == "visible"
    # outside
    assert g.visibility[0][16][10] == "unseen"
    assert g.visibility[0][10][16] == "unseen"
    # player 1 sees nothing
    assert g.visibility[1][10][10] == "unseen"


def test_symmetry_player_1():
    e = Entity(entity_id=0, kind="villager", owner=1, pos=(70, 30), hp=25, max_hp=25)
    g = _mk_game([e])
    vis.init_visibility(g)
    vis.recompute_visibility(g)
    assert g.visibility[1][70][30] == "visible"
    assert g.visibility[0][70][30] == "unseen"


def test_visible_to_explored_on_move_away():
    e = Entity(entity_id=0, kind="villager", owner=0, pos=(10, 10), hp=25, max_hp=25)
    g = _mk_game([e])
    vis.init_visibility(g)
    vis.recompute_visibility(g)
    assert g.visibility[0][10][10] == "visible"
    # move unit far away
    e.pos = (60, 50)
    vis.recompute_visibility(g)
    assert g.visibility[0][10][10] == "explored"
    # new spot is visible
    assert g.visibility[0][60][50] == "visible"


def test_is_command_visible_states():
    g = _mk_game()
    vis.init_visibility(g)
    # unseen
    assert vis.is_command_visible(g, 0, (5, 5)) is False
    g.visibility[0][5][5] = "explored"
    assert vis.is_command_visible(g, 0, (5, 5)) is True
    g.visibility[0][5][5] = "visible"
    assert vis.is_command_visible(g, 0, (5, 5)) is True


def test_is_command_visible_fog_cheat():
    g = _mk_game()
    vis.init_visibility(g)
    g.players[0].fog_cheat = True
    assert vis.is_command_visible(g, 0, (5, 5)) is True
    assert vis.is_command_visible(g, 1, (5, 5)) is False


def test_visible_entities_excludes_unseen_enemy():
    own = Entity(entity_id=0, kind="villager", owner=0, pos=(5, 5), hp=25, max_hp=25)
    enemy = Entity(entity_id=1, kind="villager", owner=1, pos=(70, 50), hp=25, max_hp=25)
    g = _mk_game([own, enemy])
    vis.init_visibility(g)
    vis.recompute_visibility(g)
    seen = vis.visible_entities_for(g, 0)
    assert own in seen
    assert enemy not in seen


def test_visible_entities_includes_visible_enemy():
    own = Entity(entity_id=0, kind="scout", owner=0, pos=(40, 30), hp=20, max_hp=20)
    enemy = Entity(entity_id=1, kind="villager", owner=1, pos=(42, 31), hp=25, max_hp=25)
    g = _mk_game([own, enemy])
    vis.init_visibility(g)
    vis.recompute_visibility(g)
    seen = vis.visible_entities_for(g, 0)
    assert enemy in seen


def test_building_snapshot_recorded():
    own = Entity(entity_id=0, kind="villager", owner=0, pos=(30, 30), hp=25, max_hp=25)
    enemy_bldg = Entity(entity_id=1, kind="house", owner=1, pos=(32, 31), hp=100, max_hp=100)
    g = _mk_game([own, enemy_bldg])
    vis.init_visibility(g)
    vis.recompute_visibility(g)
    snaps = g.explored_snapshots[0]
    assert 1 in snaps
    s = snaps[1]
    assert isinstance(s, BuildingSnapshot)
    assert s.kind == "house"
    assert s.owner == 1
    assert s.pos == (32, 31)
    assert s.hp_last_seen == 100


def test_building_snapshot_persists_after_destruction():
    own = Entity(entity_id=0, kind="villager", owner=0, pos=(30, 30), hp=25, max_hp=25)
    enemy_bldg = Entity(entity_id=1, kind="house", owner=1, pos=(32, 31), hp=100, max_hp=100)
    g = _mk_game([own, enemy_bldg])
    vis.init_visibility(g)
    vis.recompute_visibility(g)
    assert 1 in g.explored_snapshots[0]
    # destroy building
    enemy_bldg.hp = 0
    vis.recompute_visibility(g)
    # snapshot remains
    assert 1 in g.explored_snapshots[0]


def test_building_sight_grants_visibility():
    # A building alone (no unit) should still reveal tiles within its sight.
    bldg = Entity(entity_id=0, kind="town_center", owner=0, pos=(40, 30), hp=800, max_hp=800)
    g = _mk_game([bldg])
    vis.init_visibility(g)
    vis.recompute_visibility(g)
    assert g.visibility[0][40][30] == "visible"
    assert g.visibility[0][48][30] == "visible"  # sight 8
    assert g.visibility[0][49][30] == "unseen"


def test_dead_building_does_not_grant_vision():
    bldg = Entity(entity_id=0, kind="town_center", owner=0, pos=(40, 30), hp=0, max_hp=800)
    g = _mk_game([bldg])
    vis.init_visibility(g)
    vis.recompute_visibility(g)
    assert g.visibility[0][40][30] == "unseen"
