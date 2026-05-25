## Resource gather state machine for villagers (AC-5..AC-9, AC-46..AC-50).
##
## Ports `sim/gather.py` (commit 6deed4b+) symbol-for-symbol. Preserves the
## three landed bug fixes:
##   1. Adjacent-tile pathing — pathfinder blocks tree/mine tiles, so move
##      goal is one of the 8 surrounding tiles (`_start_move_adjacent_to`).
##   2. Idempotent re-issue — start_gather on the SAME node preserves
##      gather_progress (umbrella loops re-issue the command each tick).
##   3. Walk-back-to-TC after carry full — on deposit, re-issue move to
##      the original resource node so the villager loops.
##
## Late-binds `sim.pathfinding` via `load("res://sim/pathfinding.gd")` per
## AC-49 so sibling leaves can be stubbed by tests (`_pf_override`).

extends RefCounted

const Contract = preload("res://sim/contract.gd")


# File-level state (AC-47). Keys: entity_id (int).
# Values: Dictionary { node_id: int, resource_kind: String, gather_progress: int }.
static var _gather_state: Dictionary = {}

# Test-injection seam for the late-bound pathfinding module. When null, the
# real `res://sim/pathfinding.gd` is loaded per AC-49. Tests assign a stub
# script/object that exposes start_move / cancel_move / is_moving.
static var _pf_override = null


const _ADJ_8 = [
    Vector2i(0, 1), Vector2i(1, 0), Vector2i(0, -1), Vector2i(-1, 0),
    Vector2i(1, 1), Vector2i(1, -1), Vector2i(-1, 1), Vector2i(-1, -1),
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


static func _find_entity(game, eid: int):
    for e in game.entities:
        if e.entity_id == eid:
            return e
    return null


static func _is_alive(e) -> bool:
    return e != null and e.hp > 0


static func _chebyshev(a: Vector2i, b: Vector2i) -> int:
    return max(abs(a.x - b.x), abs(a.y - b.y))


static func _nearest_owned_tc(game, owner: int, pos: Vector2i):
    var best = null
    var best_d = 1000000000
    for e in game.entities:
        if e.kind == "town_center" and e.owner == owner and e.hp > 0:
            var d = _chebyshev(e.pos, pos)
            if d < best_d:
                best_d = d
                best = e
    return best


static func _resource_kind_for(kind: String):
    if kind == "tree":
        return "wood"
    if kind == "gold_mine":
        return "gold"
    return null


static func _pf():
    if _pf_override != null:
        return _pf_override
    return load("res://sim/pathfinding.gd")


static func _start_move(game, eid: int, target: Vector2i) -> bool:
    return _pf().start_move(game, eid, target)


static func _start_move_adjacent_to(game, eid: int, target: Vector2i) -> bool:
    for d in _ADJ_8:
        var cand = Vector2i(target.x + d.x, target.y + d.y)
        if _start_move(game, eid, cand):
            return true
    return false


static func _is_moving(eid: int) -> bool:
    return _pf().is_moving(eid)


static func _cancel_move(eid: int) -> void:
    _pf().cancel_move(eid)


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------


static func start_gather(game, entity_id: int, resource_node_id: int) -> bool:
    var villager = _find_entity(game, entity_id)
    var node = _find_entity(game, resource_node_id)
    if not _is_alive(villager) or villager.kind != "villager":
        return false
    if not _is_alive(node):
        return false
    var rkind = _resource_kind_for(node.kind)
    if rkind == null:
        return false
    # Idempotent re-issue: same node preserves gather_progress.
    if _gather_state.has(entity_id):
        var existing = _gather_state[entity_id]
        if existing.node_id == resource_node_id:
            return true
    # New target: drop prior state, install fresh.
    _gather_state.erase(entity_id)
    _gather_state[entity_id] = {
        "node_id": resource_node_id,
        "resource_kind": rkind,
        "gather_progress": 0,
    }
    _start_move_adjacent_to(game, entity_id, node.pos)
    return true


static func cancel_gather(entity_id: int) -> void:
    _gather_state.erase(entity_id)


static func is_gathering(entity_id: int) -> bool:
    return _gather_state.has(entity_id)


static func tick_gather(game) -> void:
    for vid in _gather_state.keys().duplicate():
        if not _gather_state.has(vid):
            continue
        var state = _gather_state[vid]
        var villager = _find_entity(game, vid)
        if not _is_alive(villager) or villager.kind != "villager":
            _gather_state.erase(vid)
            continue
        if _is_moving(vid):
            continue

        # Carry full -> walk to nearest owned TC and deposit on arrival.
        if villager.carry_amount >= Contract.CARRY_CAP:
            var tc = _nearest_owned_tc(game, villager.owner, villager.pos)
            if tc == null:
                continue
            if _chebyshev(villager.pos, tc.pos) <= 1:
                var player = game.players[villager.owner]
                if villager.carrying == "wood":
                    player.wood += villager.carry_amount
                elif villager.carrying == "gold":
                    player.gold += villager.carry_amount
                villager.carry_amount = 0
                villager.carrying = null
                state.gather_progress = 0
                var node2 = _find_entity(game, state.node_id)
                if _is_alive(node2):
                    _start_move_adjacent_to(game, vid, node2.pos)
                else:
                    _gather_state.erase(vid)
            else:
                _start_move_adjacent_to(game, vid, tc.pos)
            continue

        var node = _find_entity(game, state.node_id)
        if not _is_alive(node):
            _gather_state.erase(vid)
            continue

        if _chebyshev(villager.pos, node.pos) <= 1:
            state.gather_progress += 1
            if state.gather_progress >= Contract.TICK_HZ:
                state.gather_progress = 0
                villager.carrying = state.resource_kind
                villager.carry_amount = min(villager.carry_amount + 1, Contract.CARRY_CAP)
                node.hp -= 1
                if node.hp <= 0:
                    _gather_state.erase(vid)
                    continue
                if villager.carry_amount >= Contract.CARRY_CAP:
                    var tc2 = _nearest_owned_tc(game, villager.owner, villager.pos)
                    if tc2 != null:
                        _start_move_adjacent_to(game, vid, tc2.pos)
        else:
            _start_move_adjacent_to(game, vid, node.pos)


static func reset_module_state() -> void:
    _gather_state.clear()
    _pf_override = null
