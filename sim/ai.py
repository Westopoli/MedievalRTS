"""Deterministic AI player (leaf-10). SPEC.md §11 (lines 175-189).

Pure planner: queries fog-filtered visibility + reads sibling state (without
mutating it) and emits a list of `Command`s every 2 sim seconds. The orchestrator
applies commands separately. Internal bookkeeping lives in `_ai_state` keyed by
`player_id`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sim.contract import MAP_H, MAP_W, Command, Entity, Game, TICK_HZ
from sim.building import BUILD_COSTS, TRAIN_COSTS
from sim.visibility import visible_entities_for


@dataclass
class _AIState:
    last_emit_tick: Optional[int] = None
    gather_alt: int = 0
    scout_last_dispatch_tick: int = -10_000
    walls_built_by_us: int = 0
    designated_gate_idx: int = 4


_ai_state: dict[int, _AIState] = {}
_EMIT_PERIOD = 2 * TICK_HZ
_SCOUT_PERIOD = 4 * TICK_HZ
_UNIT_KINDS = frozenset({"villager", "soldier", "archer", "scout"})
_MILITARY = frozenset({"soldier", "archer"})


def _spiral_offsets(radius: int) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for r in range(1, radius + 1):
        for dx in range(-r, r + 1): out.append((dx, -r))
        for dy in range(-r + 1, r + 1): out.append((r, dy))
        for dx in range(r - 1, -r - 1, -1): out.append((dx, r))
        for dy in range(r - 1, -r, -1): out.append((-r, dy))
    return out


_HOUSE_SPIRAL = _spiral_offsets(6)
_WALL_ARC_OFFSETS = ((3, -3), (3, -2), (3, -1), (3, 0),
                     (3, 1), (3, 2), (3, 3), (4, 0))


def _is_busy(eid: int) -> bool:
    from sim import pathfinding as _pf, gather as _g, combat as _c, building as _b
    return (_pf.is_moving(eid) or _g.is_gathering(eid)
            or _c.is_attacking(eid) or eid in _b._construction)


def _footprint_clear(game: Game, t: tuple[int, int], w: int, h: int) -> bool:
    occupied = {e.pos for e in game.entities if e.hp > 0}
    for dx in range(w):
        for dy in range(h):
            x, y = t[0] + dx, t[1] + dy
            if not (0 <= x < MAP_W and 0 <= y < MAP_H): return False
            if game.map.terrain[x][y] != "grass": return False
            if (x, y) in occupied: return False
    return True


def _find_build_tile(game: Game, tc: tuple[int, int],
                     w: int, h: int) -> Optional[tuple[int, int]]:
    for dx, dy in _HOUSE_SPIRAL:
        t = (tc[0] + dx, tc[1] + dy)
        if _footprint_clear(game, t, w, h):
            return t
    return None


def _idle_villager(own: list[Entity]) -> Optional[Entity]:
    for e in own:
        if e.kind == "villager" and not _is_busy(e.entity_id):
            return e
    for e in own:
        if e.kind == "villager":
            return e
    return None


def _nearest_node(origin: tuple[int, int], resource: str,
                  visible: list[Entity]) -> Optional[Entity]:
    target = "tree" if resource == "wood" else "gold_mine"
    best, best_d = None, 10**9
    for e in visible:
        if e.kind != target or e.hp <= 0: continue
        d = max(abs(origin[0] - e.pos[0]), abs(origin[1] - e.pos[1]))
        if d < best_d: best, best_d = e, d
    return best


def _nearest_unseen(game: Game, pid: int,
                    origin: tuple[int, int]) -> Optional[tuple[int, int]]:
    if pid >= len(game.visibility): return None
    grid = game.visibility[pid]
    best, best_d = None, 10**9
    for x in range(MAP_W):
        col = grid[x]
        for y in range(MAP_H):
            if col[y] == "unseen":
                d = max(abs(x - origin[0]), abs(y - origin[1]))
                if d < best_d: best, best_d = (x, y), d
    return best


def ai_tick(game: Game, player_id: int, tick: int) -> list[Command]:
    """Return commands the AI wants to emit on this tick. Pure (no mutation)."""
    st = _ai_state.setdefault(player_id, _AIState())
    if st.last_emit_tick is not None and (tick - st.last_emit_tick) < _EMIT_PERIOD:
        return []
    st.last_emit_tick = tick

    out: list[Command] = []
    own = [e for e in game.entities if e.owner == player_id and e.hp > 0]
    tc = next((e for e in own if e.kind == "town_center"), None)
    if tc is None: return out
    p = game.players[player_id]
    visible = visible_entities_for(game, player_id)

    def n(k: str) -> int: return sum(1 for e in own if e.kind == k)
    vill_n, scout_n, sol_n, arch_n = n("villager"), n("scout"), n("soldier"), n("archer")
    barracks = [e for e in own if e.kind == "barracks"]
    wall_n = n("wall") + n("gate")
    pop_used = sum(1 for e in own if e.kind in _UNIT_KINDS)

    from sim import building as _b
    house_in_progress = any(c.owner == player_id and c.kind == "house"
                            for c in _b._construction.values())
    tc_free = tc.entity_id not in _b._training
    free_b = next((b for b in barracks if b.entity_id not in _b._training), None)

    structural = False
    # Track villagers claimed by emit_build/scout-dispatch/military-move this
    # AI tick so rules 8/9/10 don't re-task them with gather/move/attack
    # inside the same command batch.
    claimed_eids: set[int] = set()

    def emit_build(kind: str, w: int, h: int, tile: Optional[tuple[int, int]] = None) -> bool:
        if tile is None:
            tile = _find_build_tile(game, tc.pos, w, h)
        builder = _idle_villager([e for e in own if e.entity_id not in claimed_eids])
        if tile is None or builder is None: return False
        claimed_eids.add(builder.entity_id)
        out.append(Command(
            kind="build", issuing_player=player_id,
            entity_id=builder.entity_id, target_tile=tile,
            building_kind=kind))
        return True

    def emit_train(building_id: int, unit_kind: str) -> None:
        out.append(Command(
            kind="train", issuing_player=player_id,
            building_id=building_id, unit_kind=unit_kind))

    # Rule 1: house (pop>=pop_cap and wood + no house in progress)
    if (pop_used >= p.pop_cap and p.wood >= BUILD_COSTS["house"][0]
            and not house_in_progress and emit_build("house", 2, 2)):
        structural = True

    # Rule 2: first barracks
    if not structural and len(barracks) == 0 and p.wood >= BUILD_COSTS["barracks"][0]:
        if emit_build("barracks", 3, 3): structural = True

    # Rule 3: train villager — but reserve 80 wood toward first barracks.
    # Without this, training drains wood below the barracks threshold
    # forever and military never spawns.
    villager_cost = TRAIN_COSTS["villager"][0]
    barracks_cost = BUILD_COSTS["barracks"][0]
    villager_reserve = barracks_cost if len(barracks) == 0 else 0
    if (not structural and tc_free and vill_n < 10
            and p.wood >= villager_cost + villager_reserve):
        emit_train(tc.entity_id, "villager"); structural = True

    # Rule 4: train scout — defer until barracks exists (early game,
    # scouts are dead-weight: nothing to discover within sight of TC,
    # and they burn 30 wood + 20 gold that should go to barracks).
    if (not structural and tc_free and scout_n < 2 and len(barracks) >= 1
            and p.wood >= TRAIN_COSTS["scout"][0]
            and p.gold >= TRAIN_COSTS["scout"][1]):
        emit_train(tc.entity_id, "scout"); structural = True

    # Rule 5: train soldier
    if (not structural and free_b is not None and sol_n < 8
            and p.wood >= TRAIN_COSTS["soldier"][0]
            and p.gold >= TRAIN_COSTS["soldier"][1]):
        emit_train(free_b.entity_id, "soldier"); structural = True

    # Rule 6: train archer
    if (not structural and free_b is not None and arch_n < 4
            and p.wood >= TRAIN_COSTS["archer"][0]
            and p.gold >= TRAIN_COSTS["archer"][1]):
        emit_train(free_b.entity_id, "archer"); structural = True

    # Rule 7: wall arc (1 wall/gate per AI tick)
    if (not structural and len(barracks) >= 1 and wall_n < 8
            and p.wood >= BUILD_COSTS["wall"][0]):
        idx = st.walls_built_by_us
        if idx < len(_WALL_ARC_OFFSETS):
            dx, dy = _WALL_ARC_OFFSETS[idx]
            tile = (tc.pos[0] + dx, tc.pos[1] + dy)
            kind = "gate" if idx == st.designated_gate_idx else "wall"
            if 0 <= tile[0] < MAP_W and 0 <= tile[1] < MAP_H \
                    and _footprint_clear(game, tile, 1, 1):
                if emit_build(kind, 1, 1, tile):
                    st.walls_built_by_us += 1
                    structural = True

    # Rules 8-10 always run (unit assignment), independent of structural rule.

    # Rule 8: scouts → nearest UNSEEN (rate-limited to 4 sim sec)
    if (tick - st.scout_last_dispatch_tick) >= _SCOUT_PERIOD:
        dispatched = False
        for e in own:
            if e.kind != "scout" or _is_busy(e.entity_id) or e.entity_id in claimed_eids:
                continue
            tgt = _nearest_unseen(game, player_id, e.pos)
            if tgt is not None:
                claimed_eids.add(e.entity_id)
                out.append(Command(kind="move", issuing_player=player_id,
                                   entity_id=e.entity_id, target_tile=tgt))
                dispatched = True
        if dispatched:
            st.scout_last_dispatch_tick = tick

    # Rule 9: attack enemy TC once combined military (soldiers + archers) >= 3.
    # Earlier soldier-only threshold of 6 fired too late: in default-vs-idle
    # the 6th soldier didn't spawn until ~488 sim sec, leaving only 112 sec
    # to traverse a 60-tile map at 2 tiles/sec. Including archers and lowering
    # the bar gets the army marching by ~180 sim sec.
    if (sol_n + arch_n) >= 3:
        enemy_v = next((e for e in visible
                        if e.kind == "town_center" and e.owner != player_id and e.hp > 0),
                       None)
        snap = None
        if player_id < len(game.explored_snapshots):
            snap = next((s for s in game.explored_snapshots[player_id].values()
                         if s.kind == "town_center" and s.owner != player_id), None)
        if enemy_v is not None:
            tid, ttile = enemy_v.entity_id, enemy_v.pos
        elif snap is not None:
            tid, ttile = snap.entity_id, snap.pos
        else:
            tid, ttile = None, (MAP_W // 2, MAP_H // 2)
        for e in own:
            if e.kind not in _MILITARY or _is_busy(e.entity_id) or e.entity_id in claimed_eids:
                continue
            claimed_eids.add(e.entity_id)
            if tid is not None:
                out.append(Command(kind="attack", issuing_player=player_id,
                                   entity_id=e.entity_id, target_entity_id=tid))
            else:
                out.append(Command(kind="move", issuing_player=player_id,
                                   entity_id=e.entity_id, target_tile=ttile))

    # Rule 10: idle villagers gather (alternate wood/gold per AI tick)
    resource = "wood" if st.gather_alt == 0 else "gold"
    st.gather_alt = 1 - st.gather_alt
    for e in own:
        if e.kind != "villager" or _is_busy(e.entity_id) or e.entity_id in claimed_eids:
            continue
        node = _nearest_node(e.pos, resource, visible)
        if node is None:
            node = _nearest_node(e.pos, "gold" if resource == "wood" else "wood", visible)
        if node is not None:
            claimed_eids.add(e.entity_id)
            out.append(Command(kind="gather", issuing_player=player_id,
                               entity_id=e.entity_id, resource_node_id=node.entity_id))

    return out
