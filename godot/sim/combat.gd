## Combat tick + death cleanup (SPEC.md AC-14, AC-25; SPEC_GODOT.md AC-46/47/49/50).
##
## Port of `sim/combat.py`. Per-attacker integer-exact damage accumulator:
##   owed = (in_range_ticks * damage_per_sec) / TICK_HZ  (integer division)
##   delta = owed - applied_damage
## This avoids per-tick rounding loss for fractional dps.
##
## Cross-leaf references via late-bind `load()` (AC-49):
##   sim/entities.gd::get_stats(kind) -> { damage_per_sec, attack_range_tiles, ... }
##   sim/pathfinding.gd::start_move(game, entity_id, target_tile) -> bool
##   sim/pathfinding.gd::cancel_move(entity_id) -> void
##   sim/pathfinding.gd::is_moving(entity_id) -> bool

extends RefCounted

const Contract = preload("res://sim/contract.gd")


# File-level state per AC-47. Keys: attacker_id (int).
# Values: Dictionary { target_id, in_range_ticks, applied_damage, move_target }.
var _attack_state: Dictionary = {}


static func _find_entity(game, entity_id: int):
    for e in game.entities:
        if e.entity_id == entity_id:
            return e
    return null


static func _chebyshev(a, b) -> int:
    return max(abs(a.x - b.x), abs(a.y - b.y))


static func _new_state(target_id: int) -> Dictionary:
    return {
        "target_id": target_id,
        "in_range_ticks": 0,
        "applied_damage": 0,
        "move_target": null,
    }


func start_attack(game, attacker_id: int, target_id: int) -> bool:
    var attacker = _find_entity(game, attacker_id)
    var target = _find_entity(game, target_id)
    if attacker == null or attacker.hp <= 0:
        return false
    if target == null or target.hp <= 0:
        return false
    if attacker.owner == target.owner:
        return false
    var entities_mod = load("res://sim/entities.gd")
    var stats = entities_mod.get_stats(attacker.kind)
    if int(stats.damage_per_sec) == 0:
        return false
    # Idempotent re-issue: preserve accumulator for same-target re-issue.
    if _attack_state.has(attacker_id):
        var existing = _attack_state[attacker_id]
        if existing.target_id == target_id:
            return true
    _attack_state[attacker_id] = _new_state(target_id)
    return true


func cancel_attack(entity_id: int) -> void:
    _attack_state.erase(entity_id)


func is_attacking(entity_id: int) -> bool:
    return _attack_state.has(entity_id)


func _clear_all_targeting(target_id: int) -> void:
    var to_remove: Array = []
    for aid in _attack_state.keys():
        if _attack_state[aid].target_id == target_id:
            to_remove.append(aid)
    for aid in to_remove:
        _attack_state.erase(aid)


func tick_combat(game) -> void:
    var pf = load("res://sim/pathfinding.gd")
    var entities_mod = load("res://sim/entities.gd")
    # Snapshot keys — may mutate _attack_state during iteration.
    var attacker_ids: Array = _attack_state.keys().duplicate()
    for attacker_id in attacker_ids:
        if not _attack_state.has(attacker_id):
            continue
        var state = _attack_state[attacker_id]
        var attacker = _find_entity(game, attacker_id)
        if attacker == null or attacker.hp <= 0:
            _attack_state.erase(attacker_id)
            continue
        var target = _find_entity(game, state.target_id)
        if target == null or target.hp <= 0:
            _attack_state.erase(attacker_id)
            continue
        var stats = entities_mod.get_stats(attacker.kind)
        var dist = _chebyshev(attacker.pos, target.pos)
        if dist <= int(stats.attack_range_tiles):
            # In range — stop moving, accumulate damage via integer math.
            if pf.is_moving(attacker_id):
                pf.cancel_move(attacker_id)
            state.move_target = null
            state.in_range_ticks += 1
            var owed: int = (state.in_range_ticks * int(stats.damage_per_sec)) / Contract.TICK_HZ
            var to_apply: int = owed - state.applied_damage
            if to_apply > 0:
                state.applied_damage = owed
                target.hp -= to_apply
                if target.hp <= 0:
                    target.hp = 0
                    var dead_id: int = target.entity_id
                    game.entities.erase(target)
                    _clear_all_targeting(dead_id)
        else:
            # Out of range — chase. Re-path only when not already moving, OR when
            # target shifted beyond chebyshev 1 of cached destination. Comparing
            # move_target (adjacent-fallback) against target.pos directly was
            # always-unequal for buildings, pinning the attacker in place.
            var tgt_tile = target.pos
            var needs_repath: bool = not pf.is_moving(attacker_id)
            if not needs_repath and state.move_target != null:
                if _chebyshev(state.move_target, tgt_tile) > 1:
                    needs_repath = true
            if needs_repath:
                var ok: bool = pf.start_move(game, attacker_id, tgt_tile)
                if not ok:
                    var offsets = [
                        Vector2i(0, 1), Vector2i(1, 0), Vector2i(0, -1), Vector2i(-1, 0),
                        Vector2i(1, 1), Vector2i(1, -1), Vector2i(-1, 1), Vector2i(-1, -1),
                    ]
                    for off in offsets:
                        var cand = Vector2i(tgt_tile.x + off.x, tgt_tile.y + off.y)
                        if pf.start_move(game, attacker_id, cand):
                            tgt_tile = cand
                            break
                state.move_target = tgt_tile


func reset_module_state() -> void:
    _attack_state.clear()
