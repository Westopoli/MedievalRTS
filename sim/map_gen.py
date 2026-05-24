"""Deterministic map generation and starting-entity placement.

Implements SPEC.md §12 (AC-28..AC-34). Pure functions only — no global RNG.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from sim.contract import MAP_H, MAP_W, Entity, Game, Map

if TYPE_CHECKING:
    from sim.contract import TerrainKind  # noqa: F401


TC0: tuple[int, int] = (10, 30)
TC1: tuple[int, int] = (70, 30)

_FORESTS_PER_SIDE = 4
_TREES_PER_FOREST = 6  # 4*6 = 24 trees per side -> within range(20, 31)
_GOLD_MINES_PER_SIDE = 2
_TREE_RADIUS = 12  # Chebyshev distance from TC for forest centers + trees
_GOLD_RADIUS = 10  # Chebyshev distance from TC for gold mines


def _villager_ring(tc: tuple[int, int]) -> list[tuple[int, int]]:
    cx, cy = tc
    return [(cx + dx, cy + dy)
            for dx in (-1, 0, 1) for dy in (-1, 0, 1)
            if not (dx == 0 and dy == 0)]


def _in_bounds(x: int, y: int) -> bool:
    return 0 <= x < MAP_W and 0 <= y < MAP_H


def _place_cluster_trees(rng: random.Random, terrain: list[list[str]],
                         tc: tuple[int, int], blocked: set[tuple[int, int]]) -> None:
    """Place 4 forests x ~6 trees, each tile within _TREE_RADIUS Chebyshev of tc."""
    placed_total = 0
    target = _FORESTS_PER_SIDE * _TREES_PER_FOREST
    forest_centers: list[tuple[int, int]] = []
    # Pick 4 forest centers within tree radius but not too close to TC (>= 4 away)
    attempts = 0
    while len(forest_centers) < _FORESTS_PER_SIDE and attempts < 500:
        attempts += 1
        dx = rng.randint(-_TREE_RADIUS + 2, _TREE_RADIUS - 2)
        dy = rng.randint(-_TREE_RADIUS + 2, _TREE_RADIUS - 2)
        cx, cy = tc[0] + dx, tc[1] + dy
        if not _in_bounds(cx, cy):
            continue
        if max(abs(dx), abs(dy)) < 4:
            continue
        forest_centers.append((cx, cy))

    for (fx, fy) in forest_centers:
        placed_in_forest = 0
        f_attempts = 0
        while placed_in_forest < _TREES_PER_FOREST and f_attempts < 200:
            f_attempts += 1
            tx = fx + rng.randint(-2, 2)
            ty = fy + rng.randint(-2, 2)
            if not _in_bounds(tx, ty):
                continue
            if (tx, ty) in blocked:
                continue
            if terrain[tx][ty] != "grass":
                continue
            # Ensure within TC radius
            if max(abs(tx - tc[0]), abs(ty - tc[1])) > _TREE_RADIUS:
                continue
            terrain[tx][ty] = "tree"
            blocked.add((tx, ty))
            placed_in_forest += 1
            placed_total += 1
            if placed_total >= target:
                return


def _place_gold_mines(rng: random.Random, terrain: list[list[str]],
                      tc: tuple[int, int], blocked: set[tuple[int, int]]) -> None:
    placed = 0
    attempts = 0
    while placed < _GOLD_MINES_PER_SIDE and attempts < 500:
        attempts += 1
        dx = rng.randint(-_GOLD_RADIUS, _GOLD_RADIUS)
        dy = rng.randint(-_GOLD_RADIUS, _GOLD_RADIUS)
        gx, gy = tc[0] + dx, tc[1] + dy
        if not _in_bounds(gx, gy):
            continue
        if max(abs(dx), abs(dy)) < 3:
            continue
        if (gx, gy) in blocked:
            continue
        if terrain[gx][gy] != "grass":
            continue
        terrain[gx][gy] = "gold_mine"
        blocked.add((gx, gy))
        placed += 1


def generate_map(seed: int) -> Map:
    """Deterministic 80x60 terrain grid. AC-28..AC-31, AC-34."""
    rng = random.Random(seed)
    terrain: list[list[str]] = [["grass" for _ in range(MAP_H)] for _ in range(MAP_W)]

    # Blocked = TC anchors + villager spawn ring for both players.
    blocked: set[tuple[int, int]] = set()
    for tc in (TC0, TC1):
        blocked.add(tc)
        for p in _villager_ring(tc):
            blocked.add(p)

    # Place per side; order is deterministic (player 0 first, then player 1).
    for tc in (TC0, TC1):
        _place_cluster_trees(rng, terrain, tc, blocked)
        _place_gold_mines(rng, terrain, tc, blocked)

    return Map(width=MAP_W, height=MAP_H, terrain=terrain)  # type: ignore[arg-type]


def place_starting_entities(game: Game, seed: int) -> None:
    """Mutate game.entities in place. AC-29, AC-32, plus tree/gold_mine entities."""
    next_id = len(game.entities)

    def add(kind: str, owner: int, pos: tuple[int, int], hp: int) -> None:
        nonlocal next_id
        game.entities.append(Entity(
            entity_id=next_id, kind=kind, owner=owner,  # type: ignore[arg-type]
            pos=pos, hp=hp, max_hp=hp,
        ))
        next_id += 1

    # Town centers
    add("town_center", 0, TC0, 800)
    add("town_center", 1, TC1, 800)

    # Villagers — 5 per player on adjacent ring, deterministic order
    for pid, tc in [(0, TC0), (1, TC1)]:
        ring = _villager_ring(tc)
        for pos in ring[:5]:
            add("villager", pid, pos, 25)

    # Trees + gold mines from terrain
    terrain = game.map.terrain
    for x in range(game.map.width):
        for y in range(game.map.height):
            t = terrain[x][y]
            if t == "tree":
                add("tree", -1, (x, y), 40)
            elif t == "gold_mine":
                add("gold_mine", -1, (x, y), 200)
