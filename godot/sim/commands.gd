## Command validation + dispatch (SPEC.md §10, AC-21, AC-22, AC-27, AC-37).
##
## Ports `sim/commands.py` symbol-for-symbol per SPEC_GODOT.md AC-46, AC-49.
## `apply_command` is the single entry point. Validates authority + fog, then
## dispatches to the wave-1 sibling subsystem. Returns true on success, false
## on silent drop (AC-27). Never errors on validation failure.
##
## Sibling lookup is late-bound per AC-49 via `_resolve()`. Tests may install
## stub scripts through `set_module(name, script)` to exercise dispatch paths
## without depending on the real subsystem modules.

extends RefCounted

const Contract = preload("res://sim/contract.gd")


# Sibling module registry. Default lookup loads `res://sim/<name>.gd`. Tests
# call `set_module("pathfinding", FakePathfinding)` to inject stubs.
static var _modules: Dictionary = {}


static func set_module(name: String, script) -> void:
    _modules[name] = script


static func reset_module_state() -> void:
    _modules.clear()


static func _resolve(name: String):
    if _modules.has(name):
        return _modules[name]
    return load("res://sim/" + name + ".gd")


static func _find_entity(game, entity_id):
    if entity_id == null or entity_id < 0:
        return null
    for e in game.entities:
        if e.entity_id == entity_id:
            return e
    return null


static func _valid_player(game, pid) -> bool:
    return typeof(pid) == TYPE_INT and pid >= 0 and pid < game.players.size()


## Validate + dispatch a single command. Returns true if applied, false if
## silently dropped (AC-27, AC-37). Never raises on validation failure.
static func apply_command(game, cmd) -> bool:
    if cmd == null:
        return false
    if game.over:
        return false
    if not _valid_player(game, cmd.issuing_player):
        return false

    var issuer: int = cmd.issuing_player
    var kind: String = cmd.kind

    # Authority: entity_id (when set and exists) must be owned by issuer.
    if cmd.entity_id != null and cmd.entity_id >= 0:
        var ent = _find_entity(game, cmd.entity_id)
        if ent != null and ent.owner != issuer:
            return false

    # Authority: building_id (when set and exists) must be owned by issuer.
    if cmd.building_id != null and cmd.building_id >= 0:
        var bld = _find_entity(game, cmd.building_id)
        if bld != null and bld.owner != issuer:
            return false

    # Per-kind precondition + fog gate (AC-21/AC-22).
    # Move into "unseen" tiles is allowed (commit 183316c) — that's how
    # scouting works. Attack/gather still require visibility (or fog_cheat).
    if kind == "move":
        if cmd.target_tile == null:
            return false
    elif kind == "attack":
        if cmd.target_entity_id == null:
            return false
        var target = _find_entity(game, cmd.target_entity_id)
        if target == null:
            return false
        if not _fog_ok(game, issuer, target.pos):
            return false

    var pf = _resolve("pathfinding")
    var gth = _resolve("gather")
    var cmb = _resolve("combat")
    var bld_mod = _resolve("building")

    # Dispatch
    if kind == "move":
        var ok: bool = pf.start_move(game, cmd.entity_id, cmd.target_tile)
        if ok:
            gth.cancel_gather(cmd.entity_id)
            cmb.cancel_attack(cmd.entity_id)
        return ok

    if kind == "attack":
        var ok2: bool = cmb.start_attack(game, cmd.entity_id, cmd.target_entity_id)
        if ok2:
            gth.cancel_gather(cmd.entity_id)
            pf.cancel_move(cmd.entity_id)
        return ok2

    if kind == "gather":
        if cmd.resource_node_id == null:
            return false
        # Fog gate for the resource node tile.
        var node = _find_entity(game, cmd.resource_node_id)
        if node != null and not _fog_ok(game, issuer, node.pos):
            return false
        var ok3: bool = gth.start_gather(game, cmd.entity_id, cmd.resource_node_id)
        if ok3:
            cmb.cancel_attack(cmd.entity_id)
        return ok3

    if kind == "build":
        if cmd.building_kind == null or cmd.target_tile == null:
            return false
        cmb.cancel_attack(cmd.entity_id)
        gth.cancel_gather(cmd.entity_id)
        pf.cancel_move(cmd.entity_id)
        return bld_mod.start_build(game, cmd.entity_id, cmd.building_kind, cmd.target_tile)

    if kind == "train":
        if cmd.building_id == null or cmd.unit_kind == null:
            return false
        return bld_mod.start_train(game, cmd.building_id, cmd.unit_kind)

    if kind == "stop":
        if cmd.entity_id == null or cmd.entity_id < 0:
            return false
        pf.cancel_move(cmd.entity_id)
        gth.cancel_gather(cmd.entity_id)
        cmb.cancel_attack(cmd.entity_id)
        return true

    # Unknown kind -> silent drop.
    return false


static func _fog_ok(game, issuer: int, tile: Vector2i) -> bool:
    if game.players[issuer].fog_cheat:
        return true
    var vis = game.visibility
    if vis == null or vis.size() <= issuer:
        return true  # visibility uninitialised — fail-open (mirrors Python is_command_visible default)
    var col = vis[issuer]
    if col.size() <= tile.x or tile.x < 0:
        return false
    var row = col[tile.x]
    if row.size() <= tile.y or tile.y < 0:
        return false
    var v: String = row[tile.y]
    return v == "visible" or v == "explored"


## Apply commands in order. Returns count of accepted commands (AC-27).
static func apply_commands(game, cmds: Array) -> int:
    var n := 0
    for c in cmds:
        if apply_command(game, c):
            n += 1
    return n
