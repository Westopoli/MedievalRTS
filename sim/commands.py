"""Command validation + dispatch (SPEC.md §10, AC-21, AC-27).

`apply_command` is the single entry point. Validates authority + fog, then
dispatches to the wave-1 sibling subsystem. Returns True on success, False on
silent drop. Never raises on validation failure — but DOES propagate true bugs
from helpers (no try/except wrapping of subsystem calls).
"""

from __future__ import annotations

from sim.contract import Command, Game
from sim import building, combat, gather, pathfinding, visibility


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _find_entity(game: Game, entity_id: int):
    if entity_id is None or entity_id < 0:
        return None
    for e in game.entities:
        if e.entity_id == entity_id:
            return e
    return None


def _valid_player(game: Game, pid: int) -> bool:
    return isinstance(pid, int) and 0 <= pid < len(game.players)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def apply_command(game: Game, cmd: Command) -> bool:
    """Validate + dispatch a single command. Returns True if applied, False if
    silently dropped (AC-27). Never raises on validation failure."""
    if cmd is None:
        return False
    if not _valid_player(game, cmd.issuing_player):
        return False

    issuer = cmd.issuing_player

    # Authority: entity_id (when given and exists) must be owned by issuer.
    if cmd.entity_id is not None and cmd.entity_id >= 0:
        ent = _find_entity(game, cmd.entity_id)
        if ent is not None and ent.owner != issuer:
            return False

    # Authority: building_id (when given and exists) must be owned by issuer.
    if cmd.building_id is not None and cmd.building_id >= 0:
        bld = _find_entity(game, cmd.building_id)
        if bld is not None and bld.owner != issuer:
            return False

    kind = cmd.kind

    # Fog gate (AC-21/AC-22): move + attack
    if kind == "move":
        if cmd.target_tile is None:
            return False
        if not visibility.is_command_visible(game, issuer, cmd.target_tile):
            return False
    elif kind == "attack":
        if cmd.target_entity_id is None:
            return False
        target = _find_entity(game, cmd.target_entity_id)
        if target is None:
            return False
        if not visibility.is_command_visible(game, issuer, target.pos):
            return False

    # Dispatch
    if kind == "move":
        ok = pathfinding.start_move(game, cmd.entity_id, cmd.target_tile)
        if ok:
            gather.cancel_gather(cmd.entity_id)
            combat.cancel_attack(cmd.entity_id)
        return ok

    if kind == "attack":
        ok = combat.start_attack(game, cmd.entity_id, cmd.target_entity_id)
        if ok:
            gather.cancel_gather(cmd.entity_id)
            pathfinding.cancel_move(cmd.entity_id)
        return ok

    if kind == "gather":
        if cmd.resource_node_id is None:
            return False
        ok = gather.start_gather(game, cmd.entity_id, cmd.resource_node_id)
        if ok:
            combat.cancel_attack(cmd.entity_id)
            # gather.start_gather already installs its own move; don't cancel it
        return ok

    if kind == "build":
        if cmd.building_kind is None or cmd.target_tile is None:
            return False
        # cancel before so start_build can install its own move
        combat.cancel_attack(cmd.entity_id)
        gather.cancel_gather(cmd.entity_id)
        pathfinding.cancel_move(cmd.entity_id)
        ok = building.start_build(game, cmd.entity_id, cmd.building_kind, cmd.target_tile)
        return ok

    if kind == "train":
        if cmd.building_id is None or cmd.unit_kind is None:
            return False
        return building.start_train(game, cmd.building_id, cmd.unit_kind)

    if kind == "stop":
        if cmd.entity_id is None or cmd.entity_id < 0:
            return False
        pathfinding.cancel_move(cmd.entity_id)
        gather.cancel_gather(cmd.entity_id)
        combat.cancel_attack(cmd.entity_id)
        return True

    return False


def apply_commands(game: Game, cmds: list[Command]) -> int:
    """Apply commands in order. Returns count of successes (AC-27)."""
    n = 0
    for c in cmds:
        if apply_command(game, c):
            n += 1
    return n
