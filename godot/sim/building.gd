## Construction + unit training queues (AC-10, AC-11, AC-26).
##
## Ports `sim/building.py` symbol-for-symbol per SPEC_GODOT.md AC-46, AC-47,
## AC-49, AC-50. Module-level Python dicts (`_construction`, `_training`)
## become `static var` declarations per AC-47. Sibling module access
## (`sim.entities`, `sim.pathfinding`) is late-bound via `load()` inside
## function bodies per AC-49; tests inject stubs via `entities_override` /
## `pathfinding_override`.

extends RefCounted

const Contract = preload("res://sim/contract.gd")


# (wood, gold, time_seconds). town_center NOT player-buildable in v0.
const BUILD_COSTS: Dictionary = {
    "house": [30, 0, 10],
    "barracks": [80, 0, 15],
    "wall": [5, 0, 3],
    "gate": [25, 5, 5],
}

# (wood, gold, time_seconds, trained_at_building_kind).
const TRAIN_COSTS: Dictionary = {
    "villager": [50, 0, 12, "town_center"],
    "scout": [30, 20, 10, "town_center"],
    "soldier": [40, 20, 15, "barracks"],
    "archer": [25, 35, 18, "barracks"],
}

# Tile footprint per building kind.
const BUILDING_FOOTPRINT: Dictionary = {
    "town_center": Vector2i(3, 3),
    "house": Vector2i(2, 2),
    "barracks": Vector2i(3, 3),
    "wall": Vector2i(1, 1),
    "gate": Vector2i(1, 1),
}

# Adjacency order for unit spawn: N, E, S, W, NE, SE, SW, NW.
const _ADJ_OFFSETS: Array = [
    Vector2i(0, -1), Vector2i(1, 0), Vector2i(0, 1), Vector2i(-1, 0),
    Vector2i(1, -1), Vector2i(1, 1), Vector2i(-1, 1), Vector2i(-1, -1),
]


# Module-level state per AC-47. Keys are villager_id / building_id.
# _construction values: {kind, tile: Vector2i, owner, progress (counts up), timer (counts down)}.
# _training values:     {unit_kind, owner, timer}.
static var _construction: Dictionary = {}
static var _training: Dictionary = {}

# Sibling-module late-bind overrides (AC-49). Tests assign script refs with
# matching static methods so we never need to load real sibling files.
static var entities_override = null
static var pathfinding_override = null


static func _entities():
    if entities_override != null:
        return entities_override
    return load("res://sim/entities.gd")


static func _pathfinding():
    if pathfinding_override != null:
        return pathfinding_override
    return load("res://sim/pathfinding.gd")


static func _find_entity(game, eid: int):
    for e in game.entities:
        if e.entity_id == eid:
            return e
    return null


static func _footprint_tiles(kind: String, tile: Vector2i) -> Array:
    var fp: Vector2i = BUILDING_FOOTPRINT[kind]
    var out: Array = []
    for dx in range(fp.x):
        for dy in range(fp.y):
            out.append(Vector2i(tile.x + dx, tile.y + dy))
    return out


static func _footprint_center(kind: String, tile: Vector2i) -> Vector2i:
    var fp: Vector2i = BUILDING_FOOTPRINT[kind]
    return Vector2i(tile.x + fp.x / 2, tile.y + fp.y / 2)


static func _in_bounds(game, tile: Vector2i) -> bool:
    return tile.x >= 0 and tile.x < game.map_.width and tile.y >= 0 and tile.y < game.map_.height


static func _player_unit_count(game, owner: int) -> int:
    var ent = _entities()
    var count := 0
    for e in game.entities:
        if e.owner == owner and ent.is_unit(e) and e.hp > 0:
            count += 1
    return count


static func start_build(game, builder_id: int, kind: String, tile: Vector2i) -> bool:
    if not BUILD_COSTS.has(kind):
        return false
    var builder = _find_entity(game, builder_id)
    if builder == null or builder.hp <= 0 or builder.kind != "villager":
        return false
    var tiles: Array = _footprint_tiles(kind, tile)
    for t in tiles:
        if not _in_bounds(game, t):
            return false
    var occupied := {}
    for t in tiles:
        occupied[t] = true
    for e in game.entities:
        if e.entity_id == builder_id or e.hp <= 0:
            continue
        if occupied.has(e.pos):
            return false
    var cost: Array = BUILD_COSTS[kind]
    var wood_cost: int = cost[0]
    var gold_cost: int = cost[1]
    var time_sec: int = cost[2]
    var player = game.players[builder.owner]
    if player.wood < wood_cost or player.gold < gold_cost:
        return false
    player.wood -= wood_cost
    player.gold -= gold_cost
    _construction[builder_id] = {
        "kind": kind,
        "tile": tile,
        "owner": builder.owner,
        "timer": time_sec * Contract.TICK_HZ,
    }
    _pathfinding().start_move(game, builder_id, _footprint_center(kind, tile))
    return true


static func tick_construction(game) -> void:
    var ent = _entities()
    var completed: Array = []
    for builder_id in _construction.keys():
        var con: Dictionary = _construction[builder_id]
        var builder = _find_entity(game, builder_id)
        if builder == null or builder.hp <= 0:
            completed.append(builder_id)
            continue
        var center: Vector2i = _footprint_center(con["kind"], con["tile"])
        var dx := absi(builder.pos.x - center.x)
        var dy := absi(builder.pos.y - center.y)
        if maxi(dx, dy) > 1:
            continue
        con["timer"] -= 1
        if con["timer"] <= 0:
            var new_b = ent.spawn_building(game, con["kind"], con["owner"], con["tile"])
            var stats: Dictionary = ent.get_stats(con["kind"])
            new_b.hp = stats["max_hp"]
            new_b.max_hp = stats["max_hp"]
            if con["kind"] == "house":
                var player = game.players[con["owner"]]
                player.pop_cap = mini(player.pop_cap + 5, Contract.POP_CAP_MAX)
            completed.append(builder_id)
    for bid in completed:
        _construction.erase(bid)


static func start_train(game, building_id: int, unit_kind: String) -> bool:
    if not TRAIN_COSTS.has(unit_kind):
        return false
    var building = _find_entity(game, building_id)
    if building == null or building.hp <= 0:
        return false
    if building.owner < 0 or building.owner >= game.players.size():
        return false
    var cost: Array = TRAIN_COSTS[unit_kind]
    var wood_cost: int = cost[0]
    var gold_cost: int = cost[1]
    var time_sec: int = cost[2]
    var required_kind: String = cost[3]
    if building.kind != required_kind:
        return false
    if _training.has(building_id):
        return false
    var player = game.players[building.owner]
    if player.wood < wood_cost or player.gold < gold_cost:
        return false
    if _player_unit_count(game, building.owner) >= player.pop_cap:
        return false
    player.wood -= wood_cost
    player.gold -= gold_cost
    _training[building_id] = {
        "unit_kind": unit_kind,
        "owner": building.owner,
        "timer": time_sec * Contract.TICK_HZ,
    }
    return true


static func _free_adjacent_tile(game, building):
    var occupied := {}
    for e in game.entities:
        if e.hp > 0:
            occupied[e.pos] = true
    var fp_tiles: Array = _footprint_tiles(building.kind, building.pos)
    var fp_set := {}
    for t in fp_tiles:
        fp_set[t] = true
    var seen := {}
    for off in _ADJ_OFFSETS:
        for fp in fp_tiles:
            var cand := Vector2i(fp.x + off.x, fp.y + off.y)
            if fp_set.has(cand) or seen.has(cand):
                continue
            seen[cand] = true
            if not _in_bounds(game, cand):
                continue
            if occupied.has(cand):
                continue
            return cand
    return null


static func tick_training(game) -> void:
    var ent = _entities()
    var completed: Array = []
    for building_id in _training.keys():
        var tr: Dictionary = _training[building_id]
        var building = _find_entity(game, building_id)
        if building == null or building.hp <= 0:
            completed.append(building_id)
            continue
        if tr["timer"] <= 1:
            var spawn_tile = _free_adjacent_tile(game, building)
            if spawn_tile == null:
                continue
            ent.spawn_unit(game, tr["unit_kind"], tr["owner"], spawn_tile)
            completed.append(building_id)
        else:
            tr["timer"] -= 1
    for bid in completed:
        _training.erase(bid)


static func place_building_immediate(game, kind: String, tile: Vector2i, owner: int):
    var ent = _entities()
    var new_b = ent.spawn_building(game, kind, owner, tile)
    var stats: Dictionary = ent.get_stats(kind)
    new_b.hp = stats["max_hp"]
    new_b.max_hp = stats["max_hp"]
    return new_b


static func reset_module_state() -> void:
    _construction.clear()
    _training.clear()
    entities_override = null
    pathfinding_override = null
