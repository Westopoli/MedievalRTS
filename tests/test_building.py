"""Tests for sim.building — construction + training queues (AC-10, AC-11)."""

from __future__ import annotations

import sys
import types

import pytest

from sim.contract import Entity, Game, Map, Player, POP_CAP_MAX, TICK_HZ


# ---------------------------------------------------------------------------
# Sibling-API stubs (sim.entities, sim.pathfinding). Real impls land in other
# leaves; we monkeypatch minimal versions for this leaf's unit tests.
# ---------------------------------------------------------------------------


_NEXT_ID = [1000]


def _stats_for(kind: str) -> dict:
    table = {
        "villager": {"hp": 40, "max_hp": 40},
        "scout": {"hp": 30, "max_hp": 30},
        "soldier": {"hp": 60, "max_hp": 60},
        "archer": {"hp": 40, "max_hp": 40},
        "town_center": {"hp": 1000, "max_hp": 1000},
        "house": {"hp": 200, "max_hp": 200},
        "barracks": {"hp": 500, "max_hp": 500},
        "wall": {"hp": 200, "max_hp": 200},
        "gate": {"hp": 200, "max_hp": 200},
    }
    return table[kind]


def _spawn_unit(game: Game, kind: str, owner: int, pos: tuple[int, int]) -> Entity:
    s = _stats_for(kind)
    _NEXT_ID[0] += 1
    e = Entity(entity_id=_NEXT_ID[0], kind=kind, owner=owner, pos=pos,
               hp=s["hp"], max_hp=s["max_hp"])
    game.entities.append(e)
    return e


def _spawn_building(game: Game, kind: str, owner: int, pos: tuple[int, int]) -> Entity:
    s = _stats_for(kind)
    _NEXT_ID[0] += 1
    e = Entity(entity_id=_NEXT_ID[0], kind=kind, owner=owner, pos=pos,
               hp=s["hp"], max_hp=s["max_hp"])
    game.entities.append(e)
    return e


_BUILDING_KINDS = {"town_center", "house", "barracks", "wall", "gate"}
_UNIT_KINDS = {"villager", "soldier", "archer", "scout"}


def _is_building(e: Entity) -> bool:
    return e.kind in _BUILDING_KINDS


def _is_unit(e: Entity) -> bool:
    return e.kind in _UNIT_KINDS


def _get_stats(kind: str) -> dict:
    return _stats_for(kind)


_MOVING: dict[int, tuple[int, int]] = {}


def _start_move(game: Game, entity_id: int, target: tuple[int, int]) -> bool:
    _MOVING[entity_id] = target
    return True


def _is_moving(game: Game, entity_id: int) -> bool:
    return entity_id in _MOVING


@pytest.fixture(autouse=True)
def _install_sibling_stubs(monkeypatch):
    # Reset state.
    _NEXT_ID[0] = 1000
    _MOVING.clear()

    ents_mod = types.ModuleType("sim.entities")
    ents_mod.spawn_unit = _spawn_unit
    ents_mod.spawn_building = _spawn_building
    ents_mod.is_building = _is_building
    ents_mod.is_unit = _is_unit
    ents_mod.get_stats = _get_stats
    monkeypatch.setitem(sys.modules, "sim.entities", ents_mod)

    path_mod = types.ModuleType("sim.pathfinding")
    path_mod.start_move = _start_move
    path_mod.is_moving = _is_moving
    monkeypatch.setitem(sys.modules, "sim.pathfinding", path_mod)

    # Reset building module state if already imported.
    if "sim.building" in sys.modules:
        b = sys.modules["sim.building"]
        if hasattr(b, "_construction"):
            b._construction.clear()
        if hasattr(b, "_training"):
            b._training.clear()
    yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_game(wood: int = 300, gold: int = 150) -> Game:
    terrain = [["grass"] * 30 for _ in range(30)]
    m = Map(width=30, height=30, terrain=terrain)
    players = [Player(player_id=0, wood=wood, gold=gold, pop_cap=5),
               Player(player_id=1, wood=wood, gold=gold, pop_cap=5)]
    return Game(players=players, entities=[], map=m)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_constants_exist():
    from sim import building as B
    assert B.BUILD_COSTS["house"] == (30, 0, 10)
    assert B.TRAIN_COSTS["villager"] == (50, 0, 12, "town_center")
    assert B.TRAIN_COSTS["soldier"][3] == "barracks" and B.BUILDING_FOOTPRINT["barracks"] == (3, 3)


def test_start_build_insufficient_wood_returns_false():
    from sim import building as B
    g = _make_game(wood=10)
    villager = _spawn_unit(g, "villager", 0, (5, 5))
    assert B.start_build(g, villager.entity_id, "house", (8, 8)) is False
    assert g.players[0].wood == 10  # no deduction on failure


def test_start_build_house_success_deducts_and_installs():
    from sim import building as B
    g = _make_game(wood=100)
    villager = _spawn_unit(g, "villager", 0, (5, 5))
    assert B.start_build(g, villager.entity_id, "house", (8, 8)) is True
    assert g.players[0].wood == 70 and villager.entity_id in B._construction


def test_house_completes_after_10s_with_full_hp():
    from sim import building as B
    g = _make_game(wood=100)
    villager = _spawn_unit(g, "villager", 0, (8, 8))  # already adjacent
    B.start_build(g, villager.entity_id, "house", (8, 8))
    for _ in range(TICK_HZ * 10):
        B.tick_construction(g)
    houses = [e for e in g.entities if e.kind == "house"]
    assert len(houses) == 1 and houses[0].hp == 200
    assert villager.entity_id not in B._construction


def test_house_completion_bumps_pop_cap():
    from sim import building as B
    g = _make_game(wood=100)
    villager = _spawn_unit(g, "villager", 0, (8, 8))
    B.start_build(g, villager.entity_id, "house", (8, 8))
    for _ in range(TICK_HZ * 10):
        B.tick_construction(g)
    assert g.players[0].pop_cap == 10


def test_pop_cap_clamped_at_max():
    from sim import building as B
    g = _make_game(wood=10000)
    g.players[0].pop_cap = POP_CAP_MAX - 2
    villager = _spawn_unit(g, "villager", 0, (8, 8))
    B.start_build(g, villager.entity_id, "house", (8, 8))
    for _ in range(TICK_HZ * 10):
        B.tick_construction(g)
    assert g.players[0].pop_cap == POP_CAP_MAX


def test_start_train_villager_at_tc():
    from sim import building as B
    g = _make_game(wood=100)
    tc = _spawn_building(g, "town_center", 0, (10, 10))
    assert B.start_train(g, tc.entity_id, "villager") is True
    assert g.players[0].wood == 50 and tc.entity_id in B._training


def test_second_train_blocked_while_queue_full():
    from sim import building as B
    g = _make_game(wood=200)
    tc = _spawn_building(g, "town_center", 0, (10, 10))
    B.start_train(g, tc.entity_id, "villager")
    assert B.start_train(g, tc.entity_id, "villager") is False
    assert g.players[0].wood == 150  # only one deduction


def test_training_completes_and_spawns_adjacent_unit():
    from sim import building as B
    g = _make_game(wood=100)
    tc = _spawn_building(g, "town_center", 0, (10, 10))
    B.start_train(g, tc.entity_id, "villager")
    for _ in range(TICK_HZ * 12):
        B.tick_training(g)
    villagers = [e for e in g.entities if e.kind == "villager" and e.owner == 0]
    assert len(villagers) == 1
    v = villagers[0]
    assert max(abs(v.pos[0] - 10), abs(v.pos[1] - 10)) == 1
    assert tc.entity_id not in B._training


def test_training_blocked_when_pop_full():
    from sim import building as B
    g = _make_game(wood=500)
    g.players[0].pop_cap = 2
    _spawn_unit(g, "villager", 0, (5, 5))
    _spawn_unit(g, "villager", 0, (5, 6))
    tc = _spawn_building(g, "town_center", 0, (10, 10))
    assert B.start_train(g, tc.entity_id, "villager") is False
    assert g.players[0].wood == 500


def test_place_building_immediate_no_cost_full_hp():
    from sim import building as B
    g = _make_game(wood=50)
    e = B.place_building_immediate(g, kind="house", tile=(8, 8), owner=0)
    assert e.kind == "house" and e.owner == 0
    assert e.hp == e.max_hp == 200
    assert g.players[0].wood == 50  # no deduction


def test_start_build_rejects_invalid_kind():
    from sim import building as B
    g = _make_game()
    villager = _spawn_unit(g, "villager", 0, (5, 5))
    # town_center not player-buildable.
    assert B.start_build(g, villager.entity_id, "town_center", (8, 8)) is False


def test_start_train_rejects_wrong_building():
    from sim import building as B
    g = _make_game()
    barracks = _spawn_building(g, "barracks", 0, (10, 10))
    # villager trained at TC, not barracks.
    assert B.start_train(g, barracks.entity_id, "villager") is False
