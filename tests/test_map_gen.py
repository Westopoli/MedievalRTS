"""Tests for sim/map_gen.py — AC-28..AC-34."""

from __future__ import annotations

from sim.contract import MAP_H, MAP_W, Game, Map, Player
from sim.map_gen import generate_map, place_starting_entities


TC0 = (10, 30)
TC1 = (70, 30)


def _cheb(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def _fresh_game(seed: int) -> Game:
    m = generate_map(seed)
    players = [Player(player_id=0, wood=0, gold=0, pop_cap=5),
               Player(player_id=1, wood=0, gold=0, pop_cap=5)]
    return Game(players=players, entities=[], map=m)


def test_ac28_deterministic_terrain():
    assert generate_map(42).terrain == generate_map(42).terrain


def test_ac28_map_dimensions():
    m = generate_map(42)
    assert m.width == MAP_W and m.height == MAP_H


def test_ac29_town_centers_placed():
    g = _fresh_game(42)
    place_starting_entities(g, 42)
    tcs = [e for e in g.entities if e.kind == "town_center"]
    assert len(tcs) == 2
    by_owner = {e.owner: e for e in tcs}
    assert by_owner[0].pos == TC0
    assert by_owner[1].pos == TC1


def test_ac30_tree_count_and_proximity():
    m = generate_map(42)
    trees_p0 = []
    trees_p1 = []
    for x in range(MAP_W):
        for y in range(MAP_H):
            if m.terrain[x][y] == "tree":
                d0 = _cheb((x, y), TC0)
                d1 = _cheb((x, y), TC1)
                if d0 <= 12:
                    trees_p0.append((x, y))
                if d1 <= 12:
                    trees_p1.append((x, y))
    assert len(trees_p0) in range(20, 31)
    assert len(trees_p1) in range(20, 31)


def test_ac31_gold_mines():
    m = generate_map(42)
    gm_p0 = [(x, y) for x in range(MAP_W) for y in range(MAP_H)
             if m.terrain[x][y] == "gold_mine" and _cheb((x, y), TC0) <= 10]
    gm_p1 = [(x, y) for x in range(MAP_W) for y in range(MAP_H)
             if m.terrain[x][y] == "gold_mine" and _cheb((x, y), TC1) <= 10]
    assert len(gm_p0) == 2
    assert len(gm_p1) == 2


def test_ac32_villagers_adjacent_to_tc():
    g = _fresh_game(42)
    place_starting_entities(g, 42)
    occupied = {e.pos for e in g.entities if e.kind in ("town_center", "tree", "gold_mine")}
    for pid, tc in [(0, TC0), (1, TC1)]:
        vils = [e for e in g.entities if e.kind == "villager" and e.owner == pid]
        assert len(vils) == 5
        for v in vils:
            assert _cheb(v.pos, tc) == 1
            assert v.pos not in occupied


def test_ac34_other_tiles_are_grass():
    m = generate_map(42)
    for x in range(MAP_W):
        for y in range(MAP_H):
            t = m.terrain[x][y]
            assert t in ("grass", "tree", "gold_mine")


def test_place_starting_entities_deterministic():
    g1 = _fresh_game(42)
    g2 = _fresh_game(42)
    place_starting_entities(g1, 42)
    place_starting_entities(g2, 42)
    a = [(e.kind, e.owner, e.pos) for e in g1.entities]
    b = [(e.kind, e.owner, e.pos) for e in g2.entities]
    assert a == b
