## Entity stats catalog and factory helpers (leaf-03).
##
## Port of `sim/entities.py`. Values mirror SPEC.md § 6 and the Python sim.
## Per AC-46 / AC-50, public function names and numeric results match Python.

extends RefCounted

const Contract = preload("res://sim/contract.gd")


# ---------------------------------------------------------------------------
# STATS table — values from sim/entities.py (canonical) / SPEC.md § 6.
# Each dict carries both Python-style ("sight", "max_hp") and brief-style
# ("sight_tiles", "hp") keys so sibling leaves authored to either spec work.
# ---------------------------------------------------------------------------


static func _row(max_hp: int, sight: int, dmg: int, rng: int, speed: float) -> Dictionary:
    return {
        "hp": max_hp,
        "max_hp": max_hp,
        "sight": sight,
        "sight_tiles": sight,
        "damage_per_sec": dmg,
        "attack_range_tiles": rng,
        "speed_tiles_per_sec": speed,
    }


const _UNIT_KINDS := ["villager", "soldier", "archer", "scout"]
const _BUILDING_KINDS := ["town_center", "house", "barracks", "wall", "gate"]
const _RESOURCE_KINDS := ["tree", "gold_mine"]


static func _stats_table() -> Dictionary:
    return {
        # Units
        "villager":    _row(25,  5, 0, 0, 2.0),
        "soldier":     _row(60,  4, 8, 1, 2.0),
        "archer":      _row(35,  7, 5, 5, 2.0),
        "scout":       _row(30, 10, 0, 0, 4.0),
        # Buildings
        "town_center": _row(800, 8, 0, 0, 0.0),
        "house":       _row(100, 3, 0, 0, 0.0),
        "barracks":    _row(300, 4, 0, 0, 0.0),
        "wall":        _row(200, 0, 0, 0, 0.0),
        "gate":        _row(200, 0, 0, 0, 0.0),
        # Resources
        "tree":        _row(40,  0, 0, 0, 0.0),
        "gold_mine":   _row(200, 0, 0, 0, 0.0),
    }


static func get_stats(kind: String) -> Dictionary:
    var table := _stats_table()
    if not table.has(kind):
        push_error("entities.get_stats: unknown kind %s" % kind)
        return {}
    return table[kind]


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


static func _coerce_kind(kind_or_entity) -> String:
    if kind_or_entity is String:
        return kind_or_entity
    if kind_or_entity != null and "kind" in kind_or_entity:
        return kind_or_entity.kind
    return ""


static func is_unit(kind_or_entity) -> bool:
    return _coerce_kind(kind_or_entity) in _UNIT_KINDS


static func is_building(kind_or_entity) -> bool:
    return _coerce_kind(kind_or_entity) in _BUILDING_KINDS


static func is_resource(kind_or_entity) -> bool:
    return _coerce_kind(kind_or_entity) in _RESOURCE_KINDS


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


static func _next_entity_id(game) -> int:
    if game.entities.is_empty():
        return 0
    var best := -1
    for e in game.entities:
        if e.entity_id > best:
            best = e.entity_id
    return best + 1


static func _spawn(game, kind: String, owner: int, pos: Vector2i):
    var stats := get_stats(kind)
    if stats.is_empty():
        return null
    var e = Contract.Entity.new()
    e.entity_id = _next_entity_id(game)
    e.kind = kind
    e.owner = owner
    e.pos = pos
    e.hp = int(stats["max_hp"])
    e.max_hp = int(stats["max_hp"])
    game.entities.append(e)
    return e


static func spawn_unit(game, kind: String, owner: int, pos: Vector2i):
    if not (kind in _UNIT_KINDS):
        push_error("entities.spawn_unit: kind %s is not a unit kind" % kind)
        return null
    return _spawn(game, kind, owner, pos)


static func spawn_building(game, kind: String, owner: int, pos: Vector2i):
    if not (kind in _BUILDING_KINDS):
        push_error("entities.spawn_building: kind %s is not a building kind" % kind)
        return null
    return _spawn(game, kind, owner, pos)


# ---------------------------------------------------------------------------
# Module-state reset hook (per AC-47). No mutable module state here, no-op.
# ---------------------------------------------------------------------------


static func reset_module_state() -> void:
    pass
