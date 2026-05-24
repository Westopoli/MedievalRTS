"""Combat tick + death cleanup (AC-14, AC-25).

Per-attacker float damage accumulator: each tick we add
`damage_per_sec / TICK_HZ` to the accumulator; when it crosses an integer
threshold we apply the whole-damage portion to the integer hp and keep the
fractional remainder. This avoids per-tick rounding loss for fractional dps.

Cross-leaf imports (deferred to call sites so this module is importable
before parallel siblings exist, and so tests may inject stubs via sys.modules):

    sim.entities.get_stats(kind) -> stats with .damage_per_sec, .attack_range_tiles
    sim.pathfinding.start_move(game, entity_id, target_tile) -> bool
    sim.pathfinding.cancel_move(entity_id) -> None
    sim.pathfinding.is_moving(entity_id) -> bool
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sim.contract import Entity, Game, TICK_HZ


@dataclass
class _AttackState:
    target_id: int
    in_range_ticks: int = 0  # ticks spent in range since attack started (exact integer math)
    applied_damage: int = 0  # whole hp already applied so far
    move_target: tuple[int, int] | None = field(default=None)


_attack_state: dict[int, _AttackState] = {}


def _get_entities():
    import sim.entities as _e
    return _e


def _get_pathfinding():
    import sim.pathfinding as _p
    return _p


def _find_entity(game: Game, entity_id: int) -> Entity | None:
    for e in game.entities:
        if e.entity_id == entity_id:
            return e
    return None


def _chebyshev(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def start_attack(game: Game, attacker_id: int, target_id: int) -> bool:
    attacker = _find_entity(game, attacker_id)
    target = _find_entity(game, target_id)
    if attacker is None or attacker.hp <= 0:
        return False
    if target is None or target.hp <= 0:
        return False
    if attacker.owner == target.owner:
        return False
    stats = _get_entities().get_stats(attacker.kind)
    if stats.damage_per_sec == 0:
        return False
    _attack_state[attacker_id] = _AttackState(target_id=target_id)
    return True


def cancel_attack(entity_id: int) -> None:
    _attack_state.pop(entity_id, None)


def is_attacking(entity_id: int) -> bool:
    return entity_id in _attack_state


def _clear_all_targeting(target_id: int) -> None:
    for aid in [a for a, st in _attack_state.items() if st.target_id == target_id]:
        _attack_state.pop(aid, None)


def tick_combat(game: Game) -> None:
    pf = _get_pathfinding()
    ents = _get_entities()
    # Snapshot ids — we may mutate _attack_state during iteration
    for attacker_id in list(_attack_state.keys()):
        state = _attack_state.get(attacker_id)
        if state is None:
            continue
        attacker = _find_entity(game, attacker_id)
        if attacker is None or attacker.hp <= 0:
            _attack_state.pop(attacker_id, None)
            continue
        target = _find_entity(game, state.target_id)
        if target is None or target.hp <= 0:
            _attack_state.pop(attacker_id, None)
            continue
        stats = ents.get_stats(attacker.kind)
        dist = _chebyshev(attacker.pos, target.pos)
        if dist <= stats.attack_range_tiles:
            # In range — stop moving, accumulate damage via integer math
            if pf.is_moving(attacker_id):
                pf.cancel_move(attacker_id)
            state.move_target = None
            state.in_range_ticks += 1
            owed = (state.in_range_ticks * stats.damage_per_sec) // TICK_HZ
            to_apply = owed - state.applied_damage
            if to_apply > 0:
                state.applied_damage = owed
                target.hp -= to_apply
                if target.hp <= 0:
                    target.hp = 0
                    dead_id = target.entity_id
                    try:
                        game.entities.remove(target)
                    except ValueError:
                        pass
                    _clear_all_targeting(dead_id)
        else:
            # Out of range — chase target's current tile if not already
            tgt_tile = target.pos
            if state.move_target != tgt_tile or not pf.is_moving(attacker_id):
                pf.start_move(game, attacker_id, tgt_tile)
                state.move_target = tgt_tile
