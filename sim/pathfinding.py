"""8-direction A* pathfinding + per-tick movement execution.

Implements AC-13 (8-dir A* with buildings/resources blocking) and the
walls/gates portion of AC-23/AC-24 via `sim.walls.is_passable_for`.

Module-level `_move_state` holds in-flight movement; resets on Python reimport.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sim.contract import MAP_H, MAP_W, TICK_HZ

if TYPE_CHECKING:
    from sim.contract import Entity, Game


_BLOCKING_BUILDING_KINDS = frozenset(
    {"tree", "gold_mine", "town_center", "house", "barracks"}
)

# 8-direction neighbour offsets (dx, dy, step_cost).
_DIRS: tuple[tuple[int, int, float], ...] = (
    (1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
    (1, 1, 1.41), (1, -1, 1.41), (-1, 1, 1.41), (-1, -1, 1.41),
)


@dataclass
class _MoveState:
    path: list[tuple[int, int]] = field(default_factory=list)
    progress: float = 0.0


_move_state: dict[int, _MoveState] = {}


def _in_bounds(tile: tuple[int, int]) -> bool:
    x, y = tile
    return 0 <= x < MAP_W and 0 <= y < MAP_H


def _building_blocks(game: "Game", tile: tuple[int, int]) -> bool:
    for e in game.entities:
        if e.hp > 0 and e.pos == tile and e.kind in _BLOCKING_BUILDING_KINDS:
            return True
    return False


def _is_blocked(game: "Game", tile: tuple[int, int], owner: int) -> bool:
    if not _in_bounds(tile):
        return True
    if _building_blocks(game, tile):
        return True
    from sim.walls import is_passable_for  # lazy: avoid hard sibling dep at import
    if not is_passable_for(game, tile, owner):
        return True
    return False


def _chebyshev(a: tuple[int, int], b: tuple[int, int]) -> float:
    return float(max(abs(a[0] - b[0]), abs(a[1] - b[1])))


def find_path(
    game: "Game",
    start: tuple[int, int],
    goal: tuple[int, int],
    owner: int,
) -> list[tuple[int, int]] | None:
    """Return list of tiles from start (exclusive) to goal (inclusive), or None.

    8-direction A*, diagonal cost 1.41, cardinal 1.0, Chebyshev heuristic.
    Goal must be passable; if it isn't, returns None.
    """
    if not _in_bounds(goal) or _is_blocked(game, goal, owner):
        return None
    if start == goal:
        return []
    if not _in_bounds(start):
        return None

    open_heap: list[tuple[float, int, tuple[int, int]]] = []
    counter = 0
    heapq.heappush(open_heap, (_chebyshev(start, goal), counter, start))
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score: dict[tuple[int, int], float] = {start: 0.0}
    closed: set[tuple[int, int]] = set()

    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        if current in closed:
            continue
        if current == goal:
            path: list[tuple[int, int]] = []
            node = current
            while node != start:
                path.append(node)
                node = came_from[node]
            path.reverse()
            return path
        closed.add(current)
        cx, cy = current
        for dx, dy, step_cost in _DIRS:
            nb = (cx + dx, cy + dy)
            if nb in closed or not _in_bounds(nb):
                continue
            if nb != goal and _is_blocked(game, nb, owner):
                continue
            tentative = g_score[current] + step_cost
            if tentative < g_score.get(nb, float("inf")):
                came_from[nb] = current
                g_score[nb] = tentative
                f = tentative + _chebyshev(nb, goal)
                counter += 1
                heapq.heappush(open_heap, (f, counter, nb))
    return None


def _find_entity(game: "Game", entity_id: int) -> "Entity | None":
    for e in game.entities:
        if e.entity_id == entity_id:
            return e
    return None


def start_move(game: "Game", entity_id: int, target_tile: tuple[int, int]) -> bool:
    ent = _find_entity(game, entity_id)
    if ent is None:
        return False
    path = find_path(game, ent.pos, target_tile, ent.owner)
    if not path:
        return False
    _move_state[entity_id] = _MoveState(path=list(path), progress=0.0)
    return True


def cancel_move(entity_id: int) -> None:
    _move_state.pop(entity_id, None)


def is_moving(entity_id: int) -> bool:
    return entity_id in _move_state


def tick_movement(game: "Game") -> None:
    from sim.entities import get_stats
    for eid in list(_move_state.keys()):
        state = _move_state[eid]
        ent = _find_entity(game, eid)
        if ent is None or not state.path:
            _move_state.pop(eid, None)
            continue
        try:
            speed = float(get_stats(ent.kind).speed_tiles_per_sec)
        except Exception:
            speed = 0.0
        if speed <= 0:
            _move_state.pop(eid, None)
            continue
        state.progress += speed / float(TICK_HZ)
        aborted = False
        while state.progress >= 1.0 and state.path:
            next_tile = state.path[0]
            if _is_blocked(game, next_tile, ent.owner):
                _move_state.pop(eid, None)
                aborted = True
                break
            ent.pos = next_tile
            state.path.pop(0)
            state.progress -= 1.0
        if aborted:
            continue
        if not state.path:
            _move_state.pop(eid, None)
