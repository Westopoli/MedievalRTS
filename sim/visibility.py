"""Per-player fog-of-war computation (SPEC §7, AC-15..AC-22).

Symmetric 3-state visibility (`unseen` / `explored` / `visible`) recomputed each
tick for every player. Buildings observed while a tile was `visible` leave a
`BuildingSnapshot` in `game.explored_snapshots[player_id]` so the frontend can
ghost them in fog (AC-19).

All shared types come from `sim.contract`. The only cross-leaf runtime import is
`sim.entities.get_stats` for per-kind `sight`.
"""

from __future__ import annotations

from sim.contract import (
    BuildingSnapshot,
    Entity,
    Game,
    MAP_H,
    MAP_W,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BUILDING_KINDS = frozenset({"town_center", "house", "barracks", "wall", "gate"})
_UNIT_KINDS = frozenset({"villager", "soldier", "archer", "scout"})


def _get_sight(kind: str) -> int:
    # Imported lazily so tests can monkeypatch sim.entities before first call.
    from sim import entities as _ent
    return int(_ent.get_stats(kind).sight)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def init_visibility(game: Game) -> None:
    """Populate `game.visibility` and `game.explored_snapshots` if not already
    shaped correctly. Idempotent: existing correct-shape grids are preserved."""
    n_players = len(game.players)
    needs_init = (
        len(game.visibility) != n_players
        or any(
            len(grid) != MAP_W or (grid and len(grid[0]) != MAP_H)
            for grid in game.visibility
        )
    )
    if needs_init:
        game.visibility = [
            [["unseen"] * MAP_H for _ in range(MAP_W)] for _ in range(n_players)
        ]
    if len(game.explored_snapshots) != n_players:
        game.explored_snapshots = [{} for _ in range(n_players)]


def recompute_visibility(game: Game) -> None:
    """Recompute per-player visibility and refresh building snapshots."""
    init_visibility(game)
    n_players = len(game.players)

    # Snapshot pass: demote visible -> explored for every player.
    for p in range(n_players):
        grid = game.visibility[p]
        for x in range(MAP_W):
            col = grid[x]
            for y in range(MAP_H):
                if col[y] == "visible":
                    col[y] = "explored"

    # Mark visible from each P-owned unit + alive building.
    for ent in game.entities:
        if ent.kind not in _UNIT_KINDS and ent.kind not in _BUILDING_KINDS:
            continue
        if ent.kind in _BUILDING_KINDS and ent.hp <= 0:
            continue
        sight = _get_sight(ent.kind)
        if sight <= 0:
            # Still mark the entity's own tile so it shows on its owner's map.
            ex, ey = ent.pos
            if 0 <= ex < MAP_W and 0 <= ey < MAP_H:
                game.visibility[ent.owner][ex][ey] = "visible"
            continue
        ex, ey = ent.pos
        x0 = max(0, ex - sight)
        x1 = min(MAP_W - 1, ex + sight)
        y0 = max(0, ey - sight)
        y1 = min(MAP_H - 1, ey + sight)
        grid = game.visibility[ent.owner]
        for x in range(x0, x1 + 1):
            col = grid[x]
            for y in range(y0, y1 + 1):
                col[y] = "visible"

    # Building snapshot refresh: for each player P, any enemy building whose
    # current tile is visible to P gets its snapshot recorded/updated.
    for ent in game.entities:
        if ent.kind not in _BUILDING_KINDS:
            continue
        ex, ey = ent.pos
        if not (0 <= ex < MAP_W and 0 <= ey < MAP_H):
            continue
        for p in range(n_players):
            if p == ent.owner:
                continue
            if game.visibility[p][ex][ey] != "visible":
                continue
            game.explored_snapshots[p][ent.entity_id] = BuildingSnapshot(
                entity_id=ent.entity_id,
                kind=ent.kind,
                owner=ent.owner,
                pos=ent.pos,
                hp_last_seen=ent.hp,
            )
    # Destroyed-but-remembered snapshots are left in place by construction
    # (we only ever add/overwrite; we never delete).


def is_command_visible(
    game: Game, issuing_player: int, target_tile: tuple[int, int]
) -> bool:
    """AC-21/AC-22: a tile is command-targetable if visible or explored, or
    if the issuing player has `fog_cheat` set."""
    if game.players[issuing_player].fog_cheat:
        return True
    x, y = target_tile
    if not (0 <= x < MAP_W and 0 <= y < MAP_H):
        return False
    state = game.visibility[issuing_player][x][y]
    return state == "visible" or state == "explored"


def visible_entities_for(game: Game, viewer_player: int) -> list[Entity]:
    """AC-18: viewer always sees its own entities; enemy entities are included
    only when their current tile is `visible` to viewer. (Enemy building
    snapshots for explored tiles are exposed via `game.explored_snapshots` and
    rendered separately by the frontend.)"""
    grid = game.visibility[viewer_player] if viewer_player < len(game.visibility) else None
    out: list[Entity] = []
    for ent in game.entities:
        if ent.owner == viewer_player:
            out.append(ent)
            continue
        if grid is None:
            continue
        x, y = ent.pos
        if not (0 <= x < MAP_W and 0 <= y < MAP_H):
            continue
        if grid[x][y] == "visible":
            out.append(ent)
    return out
