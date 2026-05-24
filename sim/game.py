"""Game.tick orchestrator + new_game factory + scripted player command source.

Implements SPEC §9 (tick loop) and §13 (win condition).

This module is the integration layer that wires every wave-1 + wave-2 sim
module into a working simulation. It monkey-patches `sim.contract.Game.tick`
to dispatch to `_tick(game, inputs)`, so any Game instance constructed
through `new_game` (or via the contract dataclass directly) has a working
tick after this module is imported.
"""

from __future__ import annotations

from sim import ai as _ai  # noqa: F401  (re-export for callers if needed)
from sim import building as _building
from sim import combat as _combat
from sim import commands as _commands
from sim import contract as _contract
from sim import gather as _gather
from sim import map_gen as _map_gen
from sim import pathfinding as _pathfinding
from sim import visibility as _visibility
from sim.contract import (
    Command,
    Game,
    NUM_PLAYERS,
    POP_CAP_START,
    START_GOLD,
    START_WOOD,
    Map,
    Player,
)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def new_game(seed: int = 42, num_players: int = NUM_PLAYERS) -> Game:
    """Construct a fully-initialized Game and return it."""
    world_map: Map = _map_gen.generate_map(seed=seed)
    players = [
        Player(player_id=i, wood=START_WOOD, gold=START_GOLD, pop_cap=POP_CAP_START)
        for i in range(num_players)
    ]
    g = Game(
        players=players,
        entities=[],
        map=world_map,
        tick_count=0,
        over=False,
        winner=None,
        visibility=[],
        explored_snapshots=[],
    )
    _map_gen.place_starting_entities(g, seed=seed)
    _visibility.init_visibility(g)
    _visibility.recompute_visibility(g)
    return g


# ---------------------------------------------------------------------------
# Tick orchestrator (monkey-patched onto Game)
# ---------------------------------------------------------------------------


def _sweep_dead_entities(game: Game) -> None:
    """Remove any entity whose hp has dropped to <= 0.

    Combat already removes targets it kills; this catches directly-zeroed
    entities (tests / external triggers) so the win check sees an accurate
    entity list.
    """
    game.entities[:] = [e for e in game.entities if e.hp > 0]


def _check_winner(game: Game) -> None:
    """Set game.winner + game.over if at most one player still has a TC."""
    if game.over:
        return
    tc_owners = {e.owner for e in game.entities if e.kind == "town_center"}
    surviving = [p.player_id for p in game.players if p.player_id in tc_owners]
    if len(surviving) <= 1:
        if len(surviving) == 1:
            game.winner = surviving[0]
        else:
            # Tiebreaker (both TCs gone same tick): lower player_id wins.
            game.winner = min(p.player_id for p in game.players)
        game.over = True


def _tick(game: Game, inputs: list[Command]) -> None:
    # 1. Bail if already over (AC-37) — do NOT increment tick_count.
    if game.over:
        return

    # 2. Apply commands (per-command authority + fog + dispatch).
    _commands.apply_commands(game, inputs)

    # 3. Movement step.
    _pathfinding.tick_movement(game)

    # 4. Gather (walk back + deposit handled inside).
    _gather.tick_gather(game)

    # 5. Construction + training timers.
    _building.tick_construction(game)
    _building.tick_training(game)

    # 6. Combat (damage + death cleanup for kills inside combat).
    _combat.tick_combat(game)

    # 7. Sweep entities zeroed by direct hp manipulation (tests, edge cases).
    _sweep_dead_entities(game)

    # 8. Recompute fog of war for every player + update snapshots.
    _visibility.recompute_visibility(game)

    # 9. Win condition.
    _check_winner(game)

    # 10. Increment tick counter.
    game.tick_count += 1


# Install the orchestrator on the contract dataclass.
_contract.Game.tick = _tick  # type: ignore[method-assign]


# ---------------------------------------------------------------------------
# Scripted player commands (umbrella driver)
# ---------------------------------------------------------------------------


def _find_own_tc(game: Game, player_id: int):
    for e in game.entities:
        if e.kind == "town_center" and e.owner == player_id and e.hp > 0:
            return e
    return None


def _find_own_barracks(game: Game, player_id: int):
    for e in game.entities:
        if e.kind == "barracks" and e.owner == player_id and e.hp > 0:
            return e
    return None


def _find_own_villager(game: Game, player_id: int):
    for e in game.entities:
        if e.kind == "villager" and e.owner == player_id and e.hp > 0:
            return e
    return None


def _own_military(game: Game, player_id: int) -> list:
    return [
        e for e in game.entities
        if e.owner == player_id and e.hp > 0 and e.kind in ("soldier", "archer")
    ]


def _last_seen_enemy_tc(game: Game, player_id: int):
    """Return (entity_id, pos) for the most recently observed enemy TC, or None."""
    snaps = game.explored_snapshots[player_id] if game.explored_snapshots else {}
    for snap in snaps.values():
        if snap.kind == "town_center" and snap.owner != player_id:
            return snap.entity_id, snap.pos
    # fallback: currently visible enemy TC
    for e in game.entities:
        if e.kind == "town_center" and e.owner != player_id and e.hp > 0:
            if game.visibility[player_id][e.pos[0]][e.pos[1]] == "visible":
                return e.entity_id, e.pos
    return None


def scripted_player_commands(
    game: Game, player_id: int, tick: int
) -> list[Command]:
    """Deterministic test-only command stream for the umbrella."""
    out: list[Command] = []
    if game.over:
        return out
    pid = player_id

    if tick == 60:
        tc = _find_own_tc(game, pid)
        villager = _find_own_villager(game, pid)
        if tc and villager:
            out.append(Command(
                kind="build", issuing_player=pid,
                entity_id=villager.entity_id, building_kind="house",
                target_tile=(tc.pos[0] + 2, tc.pos[1] + 2),
            ))
    elif tick == 300:
        tc = _find_own_tc(game, pid)
        villager = _find_own_villager(game, pid)
        if tc and villager:
            out.append(Command(
                kind="build", issuing_player=pid,
                entity_id=villager.entity_id, building_kind="barracks",
                target_tile=(tc.pos[0] + 3, tc.pos[1] - 3),
            ))
    elif tick == 600:
        tc = _find_own_tc(game, pid)
        villager = _find_own_villager(game, pid)
        if tc and villager:
            mid_x = (tc.pos[0] + 70) // 2 if pid == 0 else (10 + tc.pos[0]) // 2
            arc_x = tc.pos[0] + 5 if pid == 0 else tc.pos[0] - 5
            out.append(Command(
                kind="build", issuing_player=pid, entity_id=villager.entity_id,
                building_kind="wall", target_tile=(arc_x, tc.pos[1] - 2),
            ))
            out.append(Command(
                kind="build", issuing_player=pid, entity_id=villager.entity_id,
                building_kind="wall", target_tile=(arc_x, tc.pos[1] + 2),
            ))
            out.append(Command(
                kind="build", issuing_player=pid, entity_id=villager.entity_id,
                building_kind="gate", target_tile=(arc_x, tc.pos[1]),
            ))
    elif tick == 900:
        tc = _find_own_tc(game, pid)
        if tc:
            out.append(Command(
                kind="train", issuing_player=pid,
                building_id=tc.entity_id, unit_kind="scout",
            ))
    elif tick in (1200, 1400, 1600):
        b = _find_own_barracks(game, pid)
        if b:
            out.append(Command(
                kind="train", issuing_player=pid,
                building_id=b.entity_id, unit_kind="soldier",
            ))
    elif tick in (1800, 2000):
        b = _find_own_barracks(game, pid)
        if b:
            out.append(Command(
                kind="train", issuing_player=pid,
                building_id=b.entity_id, unit_kind="archer",
            ))
    elif tick == 3000:
        for u in _own_military(game, pid):
            out.append(Command(
                kind="move", issuing_player=pid,
                entity_id=u.entity_id, target_tile=(45, 30),
            ))
    elif tick == 4500:
        target = _last_seen_enemy_tc(game, pid)
        for u in _own_military(game, pid):
            if target is not None:
                tid, _tpos = target
                out.append(Command(
                    kind="attack", issuing_player=pid,
                    entity_id=u.entity_id, target_entity_id=tid,
                ))
            else:
                enemy_tc_pos = (70, 30) if pid == 0 else (10, 30)
                out.append(Command(
                    kind="move", issuing_player=pid,
                    entity_id=u.entity_id, target_tile=enemy_tc_pos,
                ))
    return out
