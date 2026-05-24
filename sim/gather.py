"""Resource gather state machine for villagers (AC-5..AC-9).

Per SPEC.md:
- Villager moves to a tree or gold_mine, gathers +1 carry/sim-second,
  walks to the nearest owned town_center when full (CARRY_CAP), deposits
  into the owner's wood/gold pool, then returns to the node.
- A new gather target cancels the prior one (AC-8).
- Carry never exceeds CARRY_CAP.

This module imports `sim.pathfinding.start_move / cancel_move / is_moving`
lazily (per-call) so sibling leaves can be monkeypatched in unit tests
without import-time coupling.
"""

from __future__ import annotations

from dataclasses import dataclass

from sim.contract import CARRY_CAP, TICK_HZ, Entity, Game, ResourceKind


@dataclass
class _GatherState:
    node_id: int
    resource_kind: ResourceKind
    gather_progress: int = 0  # ticks accumulated toward next +1 carry


_gather_state: dict[int, _GatherState] = {}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _find_entity(game: Game, eid: int) -> Entity | None:
    for e in game.entities:
        if e.entity_id == eid:
            return e
    return None


def _is_alive(e: Entity | None) -> bool:
    return e is not None and e.hp > 0


def _chebyshev(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def _nearest_owned_tc(game: Game, owner: int, pos: tuple[int, int]) -> Entity | None:
    best: Entity | None = None
    best_d = 10**9
    for e in game.entities:
        if e.kind == "town_center" and e.owner == owner and e.hp > 0:
            d = _chebyshev(e.pos, pos)
            if d < best_d:
                best_d = d
                best = e
    return best


def _resource_kind_for(kind: str) -> ResourceKind | None:
    if kind == "tree":
        return "wood"
    if kind == "gold_mine":
        return "gold"
    return None


def _start_move(game: Game, eid: int, target: tuple[int, int]) -> bool:
    from sim import pathfinding  # late-bind for test monkeypatching
    return pathfinding.start_move(game, eid, target)


_ADJ_8 = ((0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1))


def _start_move_adjacent_to(
    game: Game, eid: int, target: tuple[int, int]
) -> bool:
    """Move toward a tile adjacent to ``target`` — first reachable wins.

    Resource nodes (tree, gold_mine) and buildings are blocked by the
    pathfinder, so a unit cannot path *onto* them. Gather/build flows must
    instead path to one of the 8 surrounding tiles. Returns True if any
    adjacent tile became the movement goal; False if all 8 are blocked or
    unreachable.
    """
    for dx, dy in _ADJ_8:
        cand = (target[0] + dx, target[1] + dy)
        if _start_move(game, eid, cand):
            return True
    return False


def _is_moving(eid: int) -> bool:
    from sim import pathfinding
    return pathfinding.is_moving(eid)


def _cancel_move(eid: int) -> None:
    from sim import pathfinding
    pathfinding.cancel_move(eid)


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------


def start_gather(game: Game, entity_id: int, resource_node_id: int) -> bool:
    villager = _find_entity(game, entity_id)
    node = _find_entity(game, resource_node_id)
    if not _is_alive(villager) or villager.kind != "villager":
        return False
    if not _is_alive(node):
        return False
    rkind = _resource_kind_for(node.kind)
    if rkind is None:
        return False
    # Idempotent re-issue: if already gathering the same node, preserve
    # state. Reissuing the same gather command each tick (umbrella pattern)
    # must NOT reset gather_progress or movement.
    existing = _gather_state.get(entity_id)
    if existing is not None and existing.node_id == resource_node_id:
        return True
    # New target — cancel prior state (AC-8) and install fresh.
    _gather_state.pop(entity_id, None)
    _gather_state[entity_id] = _GatherState(
        node_id=resource_node_id, resource_kind=rkind, gather_progress=0
    )
    _start_move_adjacent_to(game, entity_id, node.pos)
    return True


def cancel_gather(entity_id: int) -> None:
    _gather_state.pop(entity_id, None)


def is_gathering(entity_id: int) -> bool:
    return entity_id in _gather_state


def tick_gather(game: Game) -> None:
    # Snapshot ids so we can mutate the dict mid-iteration if needed.
    for vid in list(_gather_state.keys()):
        state = _gather_state.get(vid)
        if state is None:
            continue
        villager = _find_entity(game, vid)
        if not _is_alive(villager) or villager.kind != "villager":
            _gather_state.pop(vid, None)
            continue
        # Villager currently pathing — let movement leaf advance them.
        if _is_moving(vid):
            continue

        # Carry full → walk to nearest TC and deposit on arrival.
        if villager.carry_amount >= CARRY_CAP:
            tc = _nearest_owned_tc(game, villager.owner, villager.pos)
            if tc is None:
                # Nowhere to deposit; just sit on the resource until a TC exists.
                continue
            if _chebyshev(villager.pos, tc.pos) <= 1:
                # Deposit.
                player = game.players[villager.owner]
                if villager.carrying == "wood":
                    player.wood += villager.carry_amount
                elif villager.carrying == "gold":
                    player.gold += villager.carry_amount
                villager.carry_amount = 0
                villager.carrying = None
                state.gather_progress = 0
                # Re-issue move back to the node if still alive, else clear state.
                node = _find_entity(game, state.node_id)
                if _is_alive(node):
                    _start_move_adjacent_to(game, vid, node.pos)
                else:
                    _gather_state.pop(vid, None)
            else:
                _start_move_adjacent_to(game, vid, tc.pos)
            continue

        node = _find_entity(game, state.node_id)
        if not _is_alive(node):
            _gather_state.pop(vid, None)
            continue

        if _chebyshev(villager.pos, node.pos) <= 1:
            # Gather: +1 carry every TICK_HZ ticks.
            state.gather_progress += 1
            if state.gather_progress >= TICK_HZ:
                state.gather_progress = 0
                villager.carrying = state.resource_kind
                villager.carry_amount = min(villager.carry_amount + 1, CARRY_CAP)
                node.hp -= 1
                if node.hp <= 0:
                    _gather_state.pop(vid, None)
                    continue
                # If just hit cap, head to nearest TC.
                if villager.carry_amount >= CARRY_CAP:
                    tc = _nearest_owned_tc(game, villager.owner, villager.pos)
                    if tc is not None:
                        _start_move_adjacent_to(game, vid, tc.pos)
        else:
            # Not at node, not moving → re-issue toward an adjacent tile.
            _start_move_adjacent_to(game, vid, node.pos)
