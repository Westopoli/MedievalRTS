## Wall/gate passability lookup (AC-23, AC-24, AC-25).
##
## Pure read-only helpers. No mutation, no pathfinding. The pathfinder leaf
## composes this check with terrain/other-entity checks.
##
## Ports `sim/walls.py` symbol-for-symbol per SPEC_GODOT.md AC-46, AC-50.

extends RefCounted

const Contract = preload("res://sim/contract.gd")


## Return the first live wall or gate entity at `tile`, else null.
##
## Dead (hp <= 0) wall/gate entities are treated as absent (AC-25).
static func wall_or_gate_at(game, tile: Vector2i):
    for ent in game.entities:
        if ent.pos == tile and (ent.kind == "wall" or ent.kind == "gate") and ent.hp > 0:
            return ent
    return null


## Return true if `tile` is passable for a unit owned by `owner`.
##
## Only considers wall/gate entities at the tile. Trees, mines, other
## buildings, and terrain are out of scope for this helper.
##
## Rules:
## - No live wall/gate at tile -> passable (AC-25 also: dead = absent).
## - Live wall -> impassable for everyone (AC-23).
## - Live gate -> passable iff gate.owner == owner (AC-24).
static func is_passable_for(game, tile: Vector2i, owner: int) -> bool:
    var blocker = wall_or_gate_at(game, tile)
    if blocker == null:
        return true
    if blocker.kind == "wall":
        return false
    # gate
    return blocker.owner == owner
