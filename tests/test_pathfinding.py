"""Tests for sim/pathfinding.py — leaf-04.

Sibling leaves sim.walls and sim.entities may not yet be on disk. We inject
lightweight stub modules into sys.modules BEFORE importing sim.pathfinding so
the impl's `from sim.walls import is_passable_for` / `from sim.entities import
get_stats` resolve to our controllable stubs. Documented in
briefs/leaf-04.ASSUMPTIONS.md.
"""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass

import pytest

from sim.contract import Entity, Game, Map, MAP_H, MAP_W, Player, TICK_HZ


# ---------------------------------------------------------------------------
# Sibling-API stubs (injected before sim.pathfinding import)
# ---------------------------------------------------------------------------

@dataclass
class _Stats:
    speed_tiles_per_sec: float = 2.0


# Controllable wall predicate; default = no walls.
_wall_blocks: dict[tuple[int, int], int] = {}  # tile -> owner_required (-1 = blocks all)


def _is_passable_for(game, tile, owner):
    if tile not in _wall_blocks:
        return True
    req = _wall_blocks[tile]
    if req == -1:
        return False  # solid wall
    return owner == req  # gate: only owner passes


def _get_stats(kind):
    # Default speed = 2 tiles/sec
    return _Stats(speed_tiles_per_sec=2.0)


def _install_stubs():
    if "sim.walls" not in sys.modules:
        m = types.ModuleType("sim.walls")
        m.is_passable_for = _is_passable_for  # type: ignore[attr-defined]
        sys.modules["sim.walls"] = m
    else:
        sys.modules["sim.walls"].is_passable_for = _is_passable_for  # type: ignore[attr-defined]
    if "sim.entities" not in sys.modules:
        m = types.ModuleType("sim.entities")
        m.get_stats = _get_stats  # type: ignore[attr-defined]
        sys.modules["sim.entities"] = m
    else:
        sys.modules["sim.entities"].get_stats = _get_stats  # type: ignore[attr-defined]


_install_stubs()

from sim import pathfinding  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _empty_game() -> Game:
    terrain = [["grass" for _ in range(MAP_H)] for _ in range(MAP_W)]
    return Game(
        players=[Player(0, 0, 0, 5), Player(1, 0, 0, 5)],
        entities=[],
        map=Map(width=MAP_W, height=MAP_H, terrain=terrain),
    )


def _new_entity(eid: int, kind: str, owner: int, pos: tuple[int, int], hp: int = 10) -> Entity:
    return Entity(entity_id=eid, kind=kind, owner=owner, pos=pos, hp=hp, max_hp=hp)


@pytest.fixture(autouse=True)
def _reset_state():
    _wall_blocks.clear()
    pathfinding._move_state.clear()
    yield
    _wall_blocks.clear()
    pathfinding._move_state.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_diagonal_path_empty_map():
    g = _empty_game()
    path = pathfinding.find_path(g, (0, 0), (5, 5), owner=0)
    assert path is not None
    assert len(path) == 5
    assert path[-1] == (5, 5)


def test_path_none_when_goal_oob():
    g = _empty_game()
    assert pathfinding.find_path(g, (0, 0), (MAP_W, 5), owner=0) is None
    assert pathfinding.find_path(g, (0, 0), (-1, 5), owner=0) is None


def test_path_none_when_goal_is_tree():
    g = _empty_game()
    g.entities.append(_new_entity(1, "tree", -1, (5, 5), hp=40))
    assert pathfinding.find_path(g, (0, 0), (5, 5), owner=0) is None


def test_wall_forces_deviation():
    g = _empty_game()
    _wall_blocks[(3, 3)] = -1
    path = pathfinding.find_path(g, (0, 3), (6, 3), owner=0)
    assert path is not None
    assert (3, 3) not in path


def test_gate_admits_owner():
    g = _empty_game()
    _wall_blocks[(3, 3)] = 0  # gate owned by player 0
    # Wall off rest of column x=3 to force any (0,3)->(6,3) path through (3,3)
    for y in range(MAP_H):
        if y != 3:
            _wall_blocks[(3, y)] = -1
    path = pathfinding.find_path(g, (0, 3), (6, 3), owner=0)
    assert path is not None
    assert (3, 3) in path


def test_gate_rejects_non_owner():
    g = _empty_game()
    _wall_blocks[(3, 3)] = 0  # gate owned by 0
    # Wall off the rest of row 3 to force going through (3,3) or around
    for y in range(MAP_H):
        if y != 3:
            _wall_blocks[(3, y)] = -1
    # Only opening is (3,3) — owner 1 cannot pass
    path = pathfinding.find_path(g, (0, 3), (6, 3), owner=1)
    # Either unreachable, or path avoids the gate
    assert path is None or (3, 3) not in path


def test_start_move_and_tick_reaches_goal():
    g = _empty_game()
    ent = _new_entity(42, "villager", 0, (0, 0))
    g.entities.append(ent)
    ok = pathfinding.start_move(g, 42, (5, 5))
    assert ok is True
    assert pathfinding.is_moving(42)
    # speed 2 tiles/sec, 5 diagonal steps, TICK_HZ=30 → ~75 ticks expected
    max_ticks = int((5 / 2.0) * TICK_HZ) + 10
    for _ in range(max_ticks):
        pathfinding.tick_movement(g)
        if not pathfinding.is_moving(42):
            break
    assert ent.pos == (5, 5)
    assert not pathfinding.is_moving(42)


def test_start_move_unreachable_returns_false():
    g = _empty_game()
    g.entities.append(_new_entity(1, "tree", -1, (5, 5), hp=40))
    ent = _new_entity(7, "villager", 0, (0, 0))
    g.entities.append(ent)
    ok = pathfinding.start_move(g, 7, (5, 5))
    assert ok is False


def test_cancel_move():
    g = _empty_game()
    ent = _new_entity(9, "villager", 0, (0, 0))
    g.entities.append(ent)
    pathfinding.start_move(g, 9, (5, 5))
    assert pathfinding.is_moving(9)
    pathfinding.cancel_move(9)
    assert not pathfinding.is_moving(9)
    # tick after cancel: no-op
    prev = ent.pos
    pathfinding.tick_movement(g)
    assert ent.pos == prev


def test_cancel_move_no_state_noop():
    pathfinding.cancel_move(999)  # should not raise
    assert not pathfinding.is_moving(999)
