"""Construction + unit training queues (AC-10, AC-11). SPEC.md lines 80-104."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sim.contract import Entity, EntityKind, Game, POP_CAP_MAX, TICK_HZ


# (wood, gold, time_seconds). town_center NOT player-buildable in v0.
BUILD_COSTS: dict[EntityKind, tuple[int, int, int]] = {
    "house": (30, 0, 10),
    "barracks": (80, 0, 15),
    "wall": (5, 0, 3),
    "gate": (25, 5, 5),
}

# (wood, gold, time_seconds, trained_at_building_kind).
TRAIN_COSTS: dict[EntityKind, tuple[int, int, int, EntityKind]] = {
    "villager": (50, 0, 12, "town_center"),
    "scout": (30, 20, 10, "town_center"),
    "soldier": (40, 20, 15, "barracks"),
    "archer": (25, 35, 18, "barracks"),
}

# (width, height) tile footprint per building kind.
BUILDING_FOOTPRINT: dict[EntityKind, tuple[int, int]] = {
    "house": (2, 2),
    "barracks": (3, 3),
    "wall": (1, 1),
    "gate": (1, 1),
    "town_center": (2, 2),
}


@dataclass
class _Construction:
    builder_id: int
    kind: EntityKind
    tile: tuple[int, int]
    owner: int
    timer: int


@dataclass
class _Training:
    building_id: int
    unit_kind: EntityKind
    owner: int
    timer: int


_construction: dict[int, _Construction] = {}
_training: dict[int, _Training] = {}

# Adjacency order for unit spawn: N, E, S, W, NE, SE, SW, NW.
_ADJ_OFFSETS: tuple[tuple[int, int], ...] = (
    (0, -1), (1, 0), (0, 1), (-1, 0),
    (1, -1), (1, 1), (-1, 1), (-1, -1),
)


def _find_entity(game: Game, eid: int) -> Optional[Entity]:
    for e in game.entities:
        if e.entity_id == eid:
            return e
    return None


def _footprint_tiles(kind: EntityKind, tile: tuple[int, int]) -> list[tuple[int, int]]:
    w, h = BUILDING_FOOTPRINT[kind]
    return [(tile[0] + dx, tile[1] + dy) for dx in range(w) for dy in range(h)]


def _footprint_center(kind: EntityKind, tile: tuple[int, int]) -> tuple[int, int]:
    w, h = BUILDING_FOOTPRINT[kind]
    return (tile[0] + w // 2, tile[1] + h // 2)


def _in_bounds(game: Game, tile: tuple[int, int]) -> bool:
    return 0 <= tile[0] < game.map.width and 0 <= tile[1] < game.map.height


def _player_unit_count(game: Game, owner: int) -> int:
    from sim.entities import is_unit
    return sum(1 for e in game.entities if e.owner == owner and is_unit(e) and e.hp > 0)


def start_build(game: Game, builder_id: int, kind: EntityKind, tile: tuple[int, int]) -> bool:
    if kind not in BUILD_COSTS:
        return False
    builder = _find_entity(game, builder_id)
    if builder is None or builder.hp <= 0 or builder.kind != "villager":
        return False
    tiles = _footprint_tiles(kind, tile)
    for t in tiles:
        if not _in_bounds(game, t):
            return False
    occupied = set(tiles)
    for e in game.entities:
        if e.entity_id == builder_id or e.hp <= 0:
            continue
        if e.pos in occupied:
            return False
    wood_cost, gold_cost, time_sec = BUILD_COSTS[kind]
    player = game.players[builder.owner]
    if player.wood < wood_cost or player.gold < gold_cost:
        return False
    player.wood -= wood_cost
    player.gold -= gold_cost
    _construction[builder_id] = _Construction(
        builder_id=builder_id, kind=kind, tile=tile, owner=builder.owner,
        timer=time_sec * TICK_HZ,
    )
    from sim.pathfinding import start_move
    start_move(game, builder_id, _footprint_center(kind, tile))
    return True


def tick_construction(game: Game) -> None:
    from sim.entities import spawn_building, get_stats
    completed: list[int] = []
    for builder_id, con in list(_construction.items()):
        builder = _find_entity(game, builder_id)
        if builder is None or builder.hp <= 0:
            completed.append(builder_id)
            continue
        center = _footprint_center(con.kind, con.tile)
        if max(abs(builder.pos[0] - center[0]), abs(builder.pos[1] - center[1])) > 1:
            continue
        con.timer -= 1
        if con.timer <= 0:
            new_b = spawn_building(game, kind=con.kind, owner=con.owner, pos=con.tile)
            stats = get_stats(con.kind)
            new_b.hp = stats["max_hp"]
            new_b.max_hp = stats["max_hp"]
            if con.kind == "house":
                player = game.players[con.owner]
                player.pop_cap = min(player.pop_cap + 5, POP_CAP_MAX)
            completed.append(builder_id)
    for bid in completed:
        _construction.pop(bid, None)


def start_train(game: Game, building_id: int, unit_kind: EntityKind) -> bool:
    if unit_kind not in TRAIN_COSTS:
        return False
    building = _find_entity(game, building_id)
    if building is None or building.hp <= 0:
        return False
    if building.owner < 0 or building.owner >= len(game.players):
        return False
    wood_cost, gold_cost, time_sec, required_kind = TRAIN_COSTS[unit_kind]
    if building.kind != required_kind:
        return False
    if building_id in _training:
        return False
    player = game.players[building.owner]
    if player.wood < wood_cost or player.gold < gold_cost:
        return False
    if _player_unit_count(game, building.owner) >= player.pop_cap:
        return False
    player.wood -= wood_cost
    player.gold -= gold_cost
    _training[building_id] = _Training(
        building_id=building_id, unit_kind=unit_kind, owner=building.owner,
        timer=time_sec * TICK_HZ,
    )
    return True


def _free_adjacent_tile(game: Game, building: Entity) -> Optional[tuple[int, int]]:
    occupied = {e.pos for e in game.entities if e.hp > 0}
    fp_tiles = _footprint_tiles(building.kind, building.pos)
    fp_set = set(fp_tiles)
    seen: set[tuple[int, int]] = set()
    for dx, dy in _ADJ_OFFSETS:
        for fx, fy in fp_tiles:
            cand = (fx + dx, fy + dy)
            if cand in fp_set or cand in seen:
                continue
            seen.add(cand)
            if not _in_bounds(game, cand):
                continue
            if cand in occupied:
                continue
            return cand
    return None


def tick_training(game: Game) -> None:
    from sim.entities import spawn_unit
    completed: list[int] = []
    for building_id, tr in list(_training.items()):
        building = _find_entity(game, building_id)
        if building is None or building.hp <= 0:
            completed.append(building_id)
            continue
        if tr.timer <= 1:
            spawn_tile = _free_adjacent_tile(game, building)
            if spawn_tile is None:
                continue
            spawn_unit(game, kind=tr.unit_kind, owner=tr.owner, pos=spawn_tile)
            completed.append(building_id)
        else:
            tr.timer -= 1
    for bid in completed:
        _training.pop(bid, None)


def place_building_immediate(game: Game, kind: EntityKind, tile: tuple[int, int], owner: int) -> Entity:
    """UMBRELLA-ONLY: bypass cost/timer. Used by tests/test_umbrella.py."""
    from sim.entities import spawn_building, get_stats
    new_b = spawn_building(game, kind=kind, owner=owner, pos=tile)
    stats = get_stats(kind)
    new_b.hp = stats["max_hp"]
    new_b.max_hp = stats["max_hp"]
    return new_b
