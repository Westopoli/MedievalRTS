"""Tests for sim/entities.py — stats catalog + factory helpers."""

from sim.contract import Entity, Game, Map, Player
from sim import entities as ent


ALL_KINDS = [
    "villager", "soldier", "archer", "scout",
    "town_center", "house", "barracks", "wall", "gate",
    "tree", "gold_mine",
]


def _make_game() -> Game:
    m = Map(width=10, height=10, terrain=[["grass"] * 10 for _ in range(10)])
    return Game(players=[Player(0, 0, 0, 5), Player(1, 0, 0, 5)], entities=[], map=m)


def test_stats_contains_all_kinds():
    for k in ALL_KINDS:
        assert k in ent.STATS


def test_stat_spot_checks():
    assert ent.get_stats("villager").max_hp == 25
    assert ent.get_stats("soldier").damage_per_sec == 8
    assert ent.get_stats("archer").attack_range_tiles == 5
    assert ent.get_stats("scout").speed_tiles_per_sec == 4.0
    assert ent.get_stats("town_center").max_hp == 800
    assert ent.get_stats("town_center").sight == 8
    assert ent.get_stats("house").max_hp == 100
    assert ent.get_stats("wall").speed_tiles_per_sec == 0
    assert ent.get_stats("tree").max_hp == 40
    assert ent.get_stats("gold_mine").max_hp == 200


def test_spawn_unit_basic():
    g = _make_game()
    e = ent.spawn_unit(g, "villager", 0, (5, 5))
    assert isinstance(e, Entity)
    assert e.kind == "villager"
    assert e.owner == 0
    assert e.pos == (5, 5)
    assert e.hp == 25
    assert e.max_hp == 25
    assert g.entities[-1] is e


def test_spawn_sequential_ids():
    g = _make_game()
    a = ent.spawn_unit(g, "villager", 0, (1, 1))
    b = ent.spawn_unit(g, "soldier", 0, (2, 2))
    assert a.entity_id == 0
    assert b.entity_id == 1
    c = ent.spawn_building(g, "house", 0, (3, 3))
    assert c.entity_id == 2


def test_classification_helpers():
    assert ent.is_unit("villager") is True
    assert ent.is_unit("house") is False
    assert ent.is_building("gate") is True
    assert ent.is_unit("tree") is False
    assert ent.is_building("tree") is False
