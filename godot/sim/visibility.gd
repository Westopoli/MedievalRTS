## Per-player fog-of-war (SPEC §7, AC-15..AC-22, SPEC_GODOT.md AC-46/AC-50).
##
## Symmetric 3-state visibility (`unseen` / `explored` / `visible`) recomputed
## each tick for every player. Buildings observed while a tile was `visible`
## leave a `BuildingSnapshot` in `game.explored_snapshots[player_id]` so the
## frontend can ghost them in fog (AC-19). All shared types come from
## `res://sim/contract.gd`. Entity sight is fetched via lazy
## `load("res://sim/entities.gd")` inside function bodies per AC-49.

extends RefCounted

const Contract = preload("res://sim/contract.gd")

const _BUILDING_KINDS = ["town_center", "house", "barracks", "wall", "gate"]
const _UNIT_KINDS = ["villager", "soldier", "archer", "scout"]

# Test seam: tests may set this to a Callable taking (kind: String) -> Dictionary
# to stub out the sibling-leaf `entities.gd::get_stats` dependency.
static var _get_stats_override: Callable = Callable()


static func _is_building(kind: String) -> bool:
    return _BUILDING_KINDS.has(kind)


static func _is_unit(kind: String) -> bool:
    return _UNIT_KINDS.has(kind)


static func _get_sight(kind: String) -> int:
    var stats
    if _get_stats_override.is_valid():
        stats = _get_stats_override.call(kind)
    else:
        var ent_mod = load("res://sim/entities.gd")
        stats = ent_mod.get_stats(kind)
    if stats == null:
        return 0
    if stats is Dictionary:
        return int(stats.get("sight_tiles", 0))
    # Fallback: object with .sight_tiles property.
    return int(stats.sight_tiles)


static func init_visibility(game) -> void:
    var n_players: int = game.players.size()
    var needs_init: bool = game.visibility.size() != n_players
    if not needs_init:
        for grid in game.visibility:
            if grid.size() != Contract.MAP_W:
                needs_init = true
                break
            if grid.size() > 0 and grid[0].size() != Contract.MAP_H:
                needs_init = true
                break
    if needs_init:
        var new_vis: Array = []
        for p in range(n_players):
            var grid: Array = []
            for x in range(Contract.MAP_W):
                var col: Array = []
                col.resize(Contract.MAP_H)
                for y in range(Contract.MAP_H):
                    col[y] = "unseen"
                grid.append(col)
            new_vis.append(grid)
        game.visibility = new_vis
    if game.explored_snapshots.size() != n_players:
        var snaps: Array = []
        for p in range(n_players):
            snaps.append({})
        game.explored_snapshots = snaps


static func recompute_visibility(game) -> void:
    init_visibility(game)
    var n_players: int = game.players.size()

    # Demote visible -> explored for every player.
    for p in range(n_players):
        var grid = game.visibility[p]
        for x in range(Contract.MAP_W):
            var col = grid[x]
            for y in range(Contract.MAP_H):
                if col[y] == "visible":
                    col[y] = "explored"

    # Mark visible from every P-owned alive unit/building.
    for ent in game.entities:
        var is_unit_kind: bool = _is_unit(ent.kind)
        var is_bldg_kind: bool = _is_building(ent.kind)
        if not is_unit_kind and not is_bldg_kind:
            continue
        if is_bldg_kind and ent.hp <= 0:
            continue
        var sight: int = _get_sight(ent.kind)
        var ex: int = ent.pos.x
        var ey: int = ent.pos.y
        if sight <= 0:
            if ex >= 0 and ex < Contract.MAP_W and ey >= 0 and ey < Contract.MAP_H:
                game.visibility[ent.owner][ex][ey] = "visible"
            continue
        var x0: int = max(0, ex - sight)
        var x1: int = min(Contract.MAP_W - 1, ex + sight)
        var y0: int = max(0, ey - sight)
        var y1: int = min(Contract.MAP_H - 1, ey + sight)
        var grid2 = game.visibility[ent.owner]
        for x in range(x0, x1 + 1):
            var col = grid2[x]
            for y in range(y0, y1 + 1):
                col[y] = "visible"

    # Building snapshots: every enemy building on a tile visible to P.
    for ent in game.entities:
        if not _is_building(ent.kind):
            continue
        var ex: int = ent.pos.x
        var ey: int = ent.pos.y
        if ex < 0 or ex >= Contract.MAP_W or ey < 0 or ey >= Contract.MAP_H:
            continue
        for p in range(n_players):
            if p == ent.owner:
                continue
            if game.visibility[p][ex][ey] != "visible":
                continue
            var snap = Contract.BuildingSnapshot.new()
            snap.entity_id = ent.entity_id
            snap.kind = ent.kind
            snap.owner = ent.owner
            snap.pos = ent.pos
            snap.hp_last_seen = ent.hp
            game.explored_snapshots[p][ent.entity_id] = snap


static func is_command_visible(game, issuing_player: int, target_tile: Vector2i) -> bool:
    if game.players[issuing_player].fog_cheat:
        return true
    var x: int = target_tile.x
    var y: int = target_tile.y
    if x < 0 or x >= Contract.MAP_W or y < 0 or y >= Contract.MAP_H:
        return false
    var state = game.visibility[issuing_player][x][y]
    return state == "visible" or state == "explored"


static func visible_entities_for(game, viewer_player: int) -> Array:
    var grid = null
    if viewer_player < game.visibility.size():
        grid = game.visibility[viewer_player]
    var out: Array = []
    for ent in game.entities:
        if ent.owner == viewer_player:
            out.append(ent)
            continue
        if grid == null:
            continue
        var x: int = ent.pos.x
        var y: int = ent.pos.y
        if x < 0 or x >= Contract.MAP_W or y < 0 or y >= Contract.MAP_H:
            continue
        if grid[x][y] == "visible":
            out.append(ent)
    return out


static func reset_module_state() -> void:
    _get_stats_override = Callable()
