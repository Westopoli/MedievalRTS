## Deterministic AI player (leaf-11). SPEC.md §11 + SPEC_GODOT.md AC-64..AC-66.
##
## Pure planner: returns an Array of Command per AI tick. No mutation of
## sibling state. Plays under symmetric fog (AC-22 default, AC-65).
##
## Port of `sim/ai.py` post-commit `1cc5e95`:
## - Rule 9 trigger is `(sol_n + arch_n) >= 3`.
## - `claimed_eids` prevents one rule from re-tasking units claimed by another.
## - Rule 3 reserves 80 wood for first barracks.
## - Rule 4 (scout) gated on `barracks_count >= 1`.
##
## Late-binds sibling modules per AC-49: `load("res://sim/<module>.gd")`
## inside function bodies, never at top-level.

extends RefCounted

const Contract = preload("res://sim/contract.gd")
const TICK_HZ = Contract.TICK_HZ
const MAP_W = Contract.MAP_W
const MAP_H = Contract.MAP_H

const _EMIT_PERIOD: int = TICK_HZ * 2
const _SCOUT_PERIOD: int = TICK_HZ * 4
const _MILITARY: Array[String] = ["soldier", "archer"]
const _UNIT_KINDS: Array[String] = ["villager", "soldier", "archer", "scout"]

# Mirrors `sim/ai.py::_WALL_ARC_OFFSETS` verbatim.
const _WALL_ARC_OFFSETS: Array[Vector2i] = [
    Vector2i(3, -3), Vector2i(3, -2), Vector2i(3, -1), Vector2i(3, 0),
    Vector2i(3, 1), Vector2i(3, 2), Vector2i(3, 3), Vector2i(4, 0),
]

# BUILD_COSTS / TRAIN_COSTS mirror sim/building.py constants for AI planning.
const _BUILD_COSTS: Dictionary = {
    "house": [30, 0, 10],
    "barracks": [80, 0, 15],
    "wall": [5, 0, 3],
    "gate": [25, 5, 5],
}
const _TRAIN_COSTS: Dictionary = {
    "villager": [50, 0, 12, "town_center"],
    "scout": [30, 20, 10, "town_center"],
    "soldier": [40, 20, 15, "barracks"],
    "archer": [25, 35, 18, "barracks"],
}

# Per-player AI bookkeeping. Keys: player_id (int). Values: Dictionary with
# fields {last_emit_tick:int|null, gather_alt:int, scout_last_dispatch_tick:int,
# walls_built_by_us:int, designated_gate_idx:int}.
static var _ai_state: Dictionary = {}


static func reset_module_state() -> void:
    _ai_state.clear()


static func _new_state() -> Dictionary:
    return {
        "last_emit_tick": null,
        "gather_alt": 0,
        "scout_last_dispatch_tick": -10000,
        "walls_built_by_us": 0,
        "designated_gate_idx": 4,
    }


static func _spiral_offsets(radius: int) -> Array:
    var out: Array = []
    for r in range(1, radius + 1):
        for dx in range(-r, r + 1):
            out.append(Vector2i(dx, -r))
        for dy in range(-r + 1, r + 1):
            out.append(Vector2i(r, dy))
        for dx2 in range(r - 1, -r - 1, -1):
            out.append(Vector2i(dx2, r))
        for dy2 in range(r - 1, -r, -1):
            out.append(Vector2i(-r, dy2))
    return out


static func _load_or_null(path: String):
    if ResourceLoader.exists(path):
        return load(path)
    return null


static func _is_busy(eid: int) -> bool:
    var pf = _load_or_null("res://sim/pathfinding.gd")
    if pf != null and pf.has_method("is_moving") and pf.is_moving(eid):
        return true
    var g = _load_or_null("res://sim/gather.gd")
    if g != null and g.has_method("is_gathering") and g.is_gathering(eid):
        return true
    var c = _load_or_null("res://sim/combat.gd")
    if c != null and c.has_method("is_attacking") and c.is_attacking(eid):
        return true
    var b = _load_or_null("res://sim/building.gd")
    if b != null:
        if b._construction.has(eid):
            return true
        if b._training.has(eid):
            return true
    return false


static func _footprint_clear(game, t: Vector2i, w: int, h: int) -> bool:
    var occupied: Dictionary = {}
    for e in game.entities:
        if e.hp > 0:
            occupied[e.pos] = true
    for dx in range(w):
        for dy in range(h):
            var x: int = t.x + dx
            var y: int = t.y + dy
            if x < 0 or x >= MAP_W or y < 0 or y >= MAP_H:
                return false
            if game.map_.terrain[x][y] != "grass":
                return false
            if Vector2i(x, y) in occupied:
                return false
    return true


static func _find_build_tile(game, tc_pos: Vector2i, w: int, h: int):
    var spiral = _spiral_offsets(6)
    for off in spiral:
        var t = Vector2i(tc_pos.x + off.x, tc_pos.y + off.y)
        if _footprint_clear(game, t, w, h):
            return t
    return null


static func _idle_villager(own: Array):
    for e in own:
        if e.kind == "villager" and not _is_busy(e.entity_id):
            return e
    for e in own:
        if e.kind == "villager":
            return e
    return null


static func _nearest_node(origin: Vector2i, resource: String, visible: Array):
    var target = "tree" if resource == "wood" else "gold_mine"
    var best = null
    var best_d: int = 1000000000
    for e in visible:
        if e.kind != target or e.hp <= 0:
            continue
        var d: int = max(abs(origin.x - e.pos.x), abs(origin.y - e.pos.y))
        if d < best_d:
            best = e
            best_d = d
    return best


static func _nearest_unseen(game, pid: int, origin: Vector2i):
    if pid >= game.visibility.size():
        return null
    var grid = game.visibility[pid]
    var best = null
    var best_d: int = 1000000000
    for x in range(MAP_W):
        var col = grid[x]
        for y in range(MAP_H):
            if col[y] == "unseen":
                var d: int = max(abs(x - origin.x), abs(y - origin.y))
                if d < best_d:
                    best = Vector2i(x, y)
                    best_d = d
    return best


static func _visible_for(game, pid: int) -> Array:
    var vis_mod = _load_or_null("res://sim/visibility.gd")
    if vis_mod != null and vis_mod.has_method("visible_entities_for"):
        return vis_mod.visible_entities_for(game, pid)
    # Fallback for tests without visibility leaf: own entities are visible.
    var out: Array = []
    for e in game.entities:
        if e.owner == pid or e.kind in ["tree", "gold_mine"]:
            out.append(e)
    return out


static func _construction_for(player_id: int) -> Array:
    var b = _load_or_null("res://sim/building.gd")
    if b == null:
        return []
    var out: Array = []
    for c in b._construction.values():
        if c.owner == player_id:
            out.append(c)
    return out


static func _is_training(building_id: int) -> bool:
    var b = _load_or_null("res://sim/building.gd")
    if b == null:
        return false
    return b._training.has(building_id)


## Return commands the AI wants to emit on this tick. Pure (no mutation).
static func ai_tick(game, player_id: int, tick: int) -> Array:
    if not _ai_state.has(player_id):
        _ai_state[player_id] = _new_state()
    var st: Dictionary = _ai_state[player_id]
    if st["last_emit_tick"] != null and (tick - int(st["last_emit_tick"])) < _EMIT_PERIOD:
        return []
    st["last_emit_tick"] = tick

    var out: Array = []
    var own: Array = []
    for e in game.entities:
        if e.owner == player_id and e.hp > 0:
            own.append(e)
    var tc = null
    for e in own:
        if e.kind == "town_center":
            tc = e
            break
    if tc == null:
        return out
    var p = game.players[player_id]
    var visible: Array = _visible_for(game, player_id)

    var vill_n: int = 0
    var scout_n: int = 0
    var sol_n: int = 0
    var arch_n: int = 0
    var wall_n: int = 0
    var pop_used: int = 0
    var barracks: Array = []
    for e in own:
        match e.kind:
            "villager": vill_n += 1
            "scout": scout_n += 1
            "soldier": sol_n += 1
            "archer": arch_n += 1
            "wall", "gate": wall_n += 1
            "barracks": barracks.append(e)
        if e.kind in _UNIT_KINDS:
            pop_used += 1

    var house_in_progress: bool = false
    for c in _construction_for(player_id):
        if c.kind == "house":
            house_in_progress = true
            break
    var tc_free: bool = not _is_training(tc.entity_id)
    var free_b = null
    for b in barracks:
        if not _is_training(b.entity_id):
            free_b = b
            break

    var structural: bool = false
    var claimed_eids: Dictionary = {}
    # Pre-claim any villager already in construction or training so subsequent
    # rules don't re-task them. Mirrors the semantic intent of `_is_busy` on
    # the Python side and prevents the AI from thrashing builds on the same
    # villager every emit period.
    var _b_mod = _load_or_null("res://sim/building.gd")
    if _b_mod != null:
        for bid in _b_mod._construction.keys():
            var con: Dictionary = _b_mod._construction[bid]
            if con.has("owner") and int(con["owner"]) == player_id:
                claimed_eids[bid] = true

    # Rule 1: house
    if (pop_used >= p.pop_cap and p.wood >= int(_BUILD_COSTS["house"][0])
            and not house_in_progress):
        if _emit_build(game, tc, own, player_id, out, claimed_eids, "house", 2, 2, null):
            structural = true

    # Rule 2: first barracks
    if (not structural and barracks.size() == 0
            and p.wood >= int(_BUILD_COSTS["barracks"][0])):
        if _emit_build(game, tc, own, player_id, out, claimed_eids, "barracks", 3, 3, null):
            structural = true

    # Rule 3: train villager — reserve 80 wood for first barracks.
    var villager_cost: int = int(_TRAIN_COSTS["villager"][0])
    var barracks_cost: int = int(_BUILD_COSTS["barracks"][0])
    var villager_reserve: int = barracks_cost if barracks.size() == 0 else 0
    if (not structural and tc_free and vill_n < 10
            and p.wood >= villager_cost + villager_reserve):
        _emit_train(out, player_id, tc.entity_id, "villager")
        structural = true

    # Rule 4: train scout — gated on barracks_count >= 1.
    if (not structural and tc_free and scout_n < 2 and barracks.size() >= 1
            and p.wood >= int(_TRAIN_COSTS["scout"][0])
            and p.gold >= int(_TRAIN_COSTS["scout"][1])):
        _emit_train(out, player_id, tc.entity_id, "scout")
        structural = true

    # Rule 5: train soldier
    if (not structural and free_b != null and sol_n < 8
            and p.wood >= int(_TRAIN_COSTS["soldier"][0])
            and p.gold >= int(_TRAIN_COSTS["soldier"][1])):
        _emit_train(out, player_id, free_b.entity_id, "soldier")
        structural = true

    # Rule 6: train archer
    if (not structural and free_b != null and arch_n < 4
            and p.wood >= int(_TRAIN_COSTS["archer"][0])
            and p.gold >= int(_TRAIN_COSTS["archer"][1])):
        _emit_train(out, player_id, free_b.entity_id, "archer")
        structural = true

    # Rule 7: wall arc
    if (not structural and barracks.size() >= 1 and wall_n < 8
            and p.wood >= int(_BUILD_COSTS["wall"][0])):
        var idx: int = int(st["walls_built_by_us"])
        if idx < _WALL_ARC_OFFSETS.size():
            var off = _WALL_ARC_OFFSETS[idx]
            var tile = Vector2i(tc.pos.x + off.x, tc.pos.y + off.y)
            var kind: String = "gate" if idx == int(st["designated_gate_idx"]) else "wall"
            if (tile.x >= 0 and tile.x < MAP_W and tile.y >= 0 and tile.y < MAP_H
                    and _footprint_clear(game, tile, 1, 1)):
                if _emit_build(game, tc, own, player_id, out, claimed_eids, kind, 1, 1, tile):
                    st["walls_built_by_us"] = idx + 1
                    structural = true

    # Rule 8: scouts → nearest UNSEEN
    if (tick - int(st["scout_last_dispatch_tick"])) >= _SCOUT_PERIOD:
        var dispatched: bool = false
        for e in own:
            if e.kind != "scout" or _is_busy(e.entity_id) or claimed_eids.has(e.entity_id):
                continue
            var tgt = _nearest_unseen(game, player_id, e.pos)
            if tgt != null:
                claimed_eids[e.entity_id] = true
                var cmd = Contract.Command.new()
                cmd.kind = "move"
                cmd.issuing_player = player_id
                cmd.entity_id = e.entity_id
                cmd.target_tile = tgt
                out.append(cmd)
                dispatched = true
        if dispatched:
            st["scout_last_dispatch_tick"] = tick

    # Rule 9: attack enemy TC when (sol_n + arch_n) >= 3.
    if (sol_n + arch_n) >= 3:
        var enemy_v = null
        for e in visible:
            if e.kind == "town_center" and e.owner != player_id and e.hp > 0:
                enemy_v = e
                break
        var snap = null
        if player_id < game.explored_snapshots.size():
            for s in game.explored_snapshots[player_id].values():
                if s.kind == "town_center" and s.owner != player_id:
                    snap = s
                    break
        var tid = null
        var ttile: Vector2i = Vector2i(MAP_W / 2, MAP_H / 2)
        if enemy_v != null:
            tid = enemy_v.entity_id
            ttile = enemy_v.pos
        elif snap != null:
            tid = snap.entity_id
            ttile = snap.pos
        for e in own:
            if not (e.kind in _MILITARY) or _is_busy(e.entity_id) or claimed_eids.has(e.entity_id):
                continue
            claimed_eids[e.entity_id] = true
            var cmd2 = Contract.Command.new()
            cmd2.issuing_player = player_id
            cmd2.entity_id = e.entity_id
            if tid != null:
                cmd2.kind = "attack"
                cmd2.target_entity_id = tid
            else:
                cmd2.kind = "move"
                cmd2.target_tile = ttile
            out.append(cmd2)

    # Rule 10: idle villagers gather (alternate wood/gold).
    var resource: String = "wood" if int(st["gather_alt"]) == 0 else "gold"
    st["gather_alt"] = 1 - int(st["gather_alt"])
    for e in own:
        if e.kind != "villager" or _is_busy(e.entity_id) or claimed_eids.has(e.entity_id):
            continue
        var node = _nearest_node(e.pos, resource, visible)
        if node == null:
            var alt: String = "gold" if resource == "wood" else "wood"
            node = _nearest_node(e.pos, alt, visible)
        if node != null:
            claimed_eids[e.entity_id] = true
            var cmd3 = Contract.Command.new()
            cmd3.kind = "gather"
            cmd3.issuing_player = player_id
            cmd3.entity_id = e.entity_id
            cmd3.resource_node_id = node.entity_id
            out.append(cmd3)

    return out


static func _emit_build(game, tc, own: Array, player_id: int, out: Array,
        claimed_eids: Dictionary, kind: String, w: int, h: int, tile) -> bool:
    if tile == null:
        tile = _find_build_tile(game, tc.pos, w, h)
    var candidates: Array = []
    for e in own:
        if not claimed_eids.has(e.entity_id):
            candidates.append(e)
    var builder = _idle_villager(candidates)
    if tile == null or builder == null:
        return false
    claimed_eids[builder.entity_id] = true
    var cmd = Contract.Command.new()
    cmd.kind = "build"
    cmd.issuing_player = player_id
    cmd.entity_id = builder.entity_id
    cmd.target_tile = tile
    cmd.building_kind = kind
    out.append(cmd)
    return true


static func _emit_train(out: Array, player_id: int, building_id: int, unit_kind: String) -> void:
    var cmd = Contract.Command.new()
    cmd.kind = "train"
    cmd.issuing_player = player_id
    cmd.building_id = building_id
    cmd.unit_kind = unit_kind
    out.append(cmd)
