## 8-direction A* pathfinding + per-tick movement execution.
##
## Ports `sim/pathfinding.py` per SPEC_GODOT.md AC-46, AC-47, AC-49, AC-50.
## Implements AC-13 (8-dir A* with buildings/resources blocking) and the
## walls/gates portion of AC-23/AC-24 via late-bound `sim.walls.is_passable_for`.
##
## Module-level `_move_state` holds in-flight movement; reset via
## `reset_module_state()` for test isolation (AC-47).

extends RefCounted

const Contract = preload("res://sim/contract.gd")

const _BLOCKING_BUILDING_KINDS = ["tree", "gold_mine", "town_center", "house", "barracks"]

# (dx, dy, cost)
const _DIRS = [
    [1, 0, 1.0], [-1, 0, 1.0], [0, 1, 1.0], [0, -1, 1.0],
    [1, 1, 1.41], [1, -1, 1.41], [-1, 1, 1.41], [-1, -1, 1.41],
]

# Module-level mutable state (AC-47).
static var _move_state: Dictionary = {}

# Test-only hook overrides. When non-null, used instead of the live-loaded
# sibling modules. The default (null) path uses load("res://sim/<mod>.gd")
# per AC-49. See test_pathfinding.gd.
static var _test_passable_override: Callable = Callable()
static var _test_get_stats_override: Callable = Callable()


static func _in_bounds(tile: Vector2i) -> bool:
    return tile.x >= 0 and tile.x < Contract.MAP_W and tile.y >= 0 and tile.y < Contract.MAP_H


static func _building_blocks(game, tile: Vector2i) -> bool:
    for e in game.entities:
        if e.hp > 0 and e.pos == tile and e.kind in _BLOCKING_BUILDING_KINDS:
            return true
    return false


static func _passable(game, tile: Vector2i, owner: int) -> bool:
    if _test_passable_override.is_valid():
        return bool(_test_passable_override.call(game, tile, owner))
    var walls = load("res://sim/walls.gd")
    return walls.is_passable_for(game, tile, owner)


static func _is_blocked(game, tile: Vector2i, owner: int) -> bool:
    if not _in_bounds(tile):
        return true
    if _building_blocks(game, tile):
        return true
    if not _passable(game, tile, owner):
        return true
    return false


static func _chebyshev(a: Vector2i, b: Vector2i) -> float:
    return float(max(abs(a.x - b.x), abs(a.y - b.y)))


# Binary min-heap on (f, counter) keyed entries. Each entry: [f, counter, Vector2i].
static func _heap_push(heap: Array, item: Array) -> void:
    heap.append(item)
    var i = heap.size() - 1
    while i > 0:
        var parent = (i - 1) / 2
        if _heap_less(heap[i], heap[parent]):
            var t = heap[i]
            heap[i] = heap[parent]
            heap[parent] = t
            i = parent
        else:
            break


static func _heap_pop(heap: Array) -> Array:
    var top = heap[0]
    var last = heap.pop_back()
    if heap.size() > 0:
        heap[0] = last
        var i = 0
        var n = heap.size()
        while true:
            var l = 2 * i + 1
            var r = 2 * i + 2
            var smallest = i
            if l < n and _heap_less(heap[l], heap[smallest]):
                smallest = l
            if r < n and _heap_less(heap[r], heap[smallest]):
                smallest = r
            if smallest == i:
                break
            var t = heap[i]
            heap[i] = heap[smallest]
            heap[smallest] = t
            i = smallest
    return top


static func _heap_less(a: Array, b: Array) -> bool:
    if a[0] < b[0]:
        return true
    if a[0] > b[0]:
        return false
    return a[1] < b[1]


## Return Array of Vector2i waypoints from start (exclusive) to goal (inclusive).
## Empty array if start == goal. Empty array if unreachable or goal blocked.
static func find_path(game, start: Vector2i, goal: Vector2i, owner: int) -> Array:
    if not _in_bounds(goal) or _is_blocked(game, goal, owner):
        return []
    if start == goal:
        return []
    if not _in_bounds(start):
        return []

    var open_heap: Array = []
    var counter = 0
    _heap_push(open_heap, [_chebyshev(start, goal), counter, start])
    var came_from: Dictionary = {}
    var g_score: Dictionary = {start: 0.0}
    var closed: Dictionary = {}

    while open_heap.size() > 0:
        var top = _heap_pop(open_heap)
        var current: Vector2i = top[2]
        if current in closed:
            continue
        if current == goal:
            var path: Array = []
            var node = current
            while node != start:
                path.append(node)
                node = came_from[node]
            path.reverse()
            return path
        closed[current] = true
        for d in _DIRS:
            var nb := Vector2i(current.x + d[0], current.y + d[1])
            if nb in closed or not _in_bounds(nb):
                continue
            if nb != goal and _is_blocked(game, nb, owner):
                continue
            var tentative: float = g_score[current] + d[2]
            var prev_g: float = g_score.get(nb, INF)
            if tentative < prev_g:
                came_from[nb] = current
                g_score[nb] = tentative
                var f: float = tentative + _chebyshev(nb, goal)
                counter += 1
                _heap_push(open_heap, [f, counter, nb])
    return []


static func _find_entity(game, entity_id: int):
    for e in game.entities:
        if e.entity_id == entity_id:
            return e
    return null


static func start_move(game, entity_id: int, target_tile: Vector2i) -> bool:
    var ent = _find_entity(game, entity_id)
    if ent == null:
        return false
    var path = find_path(game, ent.pos, target_tile, ent.owner)
    if path.is_empty():
        return false
    _move_state[entity_id] = {"path": path.duplicate(), "progress": 0.0}
    return true


static func cancel_move(entity_id: int) -> void:
    _move_state.erase(entity_id)


static func is_moving(entity_id: int) -> bool:
    return _move_state.has(entity_id)


static func _stats_for(kind: String):
    if _test_get_stats_override.is_valid():
        return _test_get_stats_override.call(kind)
    var entities_mod = load("res://sim/entities.gd")
    return entities_mod.get_stats(kind)


static func tick_movement(game) -> void:
    for eid in _move_state.keys().duplicate():
        var state: Dictionary = _move_state[eid]
        var ent = _find_entity(game, eid)
        if ent == null or (state["path"] as Array).is_empty():
            _move_state.erase(eid)
            continue
        var speed = 0.0
        var stats = _stats_for(ent.kind)
        if stats != null:
            speed = float(stats.speed_tiles_per_sec)
        if speed <= 0.0:
            _move_state.erase(eid)
            continue
        state["progress"] = float(state["progress"]) + speed / float(Contract.TICK_HZ)
        var aborted = false
        while float(state["progress"]) >= 1.0 and not (state["path"] as Array).is_empty():
            var next_tile: Vector2i = (state["path"] as Array)[0]
            if _is_blocked(game, next_tile, ent.owner):
                _move_state.erase(eid)
                aborted = true
                break
            ent.pos = next_tile
            (state["path"] as Array).pop_front()
            state["progress"] = float(state["progress"]) - 1.0
        if aborted:
            continue
        if (state["path"] as Array).is_empty():
            _move_state.erase(eid)


static func reset_module_state() -> void:
    _move_state.clear()
    _test_passable_override = Callable()
    _test_get_stats_override = Callable()
