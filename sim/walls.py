"""Wall/gate passability lookup (AC-23, AC-24, AC-25).

Pure read-only helpers. No mutation, no pathfinding. The pathfinder leaf
composes this check with terrain/other-entity checks.
"""

from __future__ import annotations

from sim.contract import Entity, Game


def wall_or_gate_at(game: Game, tile: tuple[int, int]) -> Entity | None:
    """Return the first live wall or gate entity at `tile`, else None.

    Dead (hp <= 0) wall/gate entities are treated as absent (AC-25).
    """
    for ent in game.entities:
        if ent.pos == tile and ent.kind in ("wall", "gate") and ent.hp > 0:
            return ent
    return None


def is_passable_for(game: Game, tile: tuple[int, int], owner: int) -> bool:
    """Return True if `tile` is passable for a unit owned by `owner`.

    Only considers wall/gate entities at the tile. Trees, mines, other
    buildings, and terrain are out of scope for this helper.

    Rules:
    - No live wall/gate at tile -> passable (AC-25 also: dead = absent).
    - Live wall -> impassable for everyone (AC-23).
    - Live gate -> passable iff gate.owner == owner (AC-24).
    """
    blocker = wall_or_gate_at(game, tile)
    if blocker is None:
        return True
    if blocker.kind == "wall":
        return False
    # gate
    return blocker.owner == owner
