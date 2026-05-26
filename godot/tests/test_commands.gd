## Command dispatch tests per SPEC.md AC-21, AC-22, AC-27, AC-37
## (SPEC_GODOT.md AC-46, AC-49). Mirrors `tests/test_commands.py`.
##
## Sibling subsystems (pathfinding, gather, combat, building, visibility)
## are stub-injected via `Commands.set_module()` so this leaf is exercised
## in isolation without depending on wave-1 siblings that have not landed
## yet. The stub scripts live as inner classes below; each records calls in
## a public dict the tests inspect.

extends GutTest

const Contract = preload("res://sim/contract.gd")
const Commands = preload("res://sim/commands.gd")


# ---------------------------------------------------------------------------
# Stub sibling modules
# ---------------------------------------------------------------------------

class StubPathfinding extends RefCounted:
    static var _move_state: Dictionary = {}
    static var _start_returns: bool = true
    static func reset() -> void:
        _move_state.clear()
        _start_returns = true
    static func start_move(_g, eid: int, target) -> bool:
        if _start_returns:
            _move_state[eid] = target
        return _start_returns
    static func cancel_move(eid: int) -> void:
        _move_state.erase(eid)
    static func is_moving(eid: int) -> bool:
        return _move_state.has(eid)


class StubGather extends RefCounted:
    static var _gather_state: Dictionary = {}
    static var _start_returns: bool = true
    static func reset() -> void:
        _gather_state.clear()
        _start_returns = true
    static func start_gather(_g, eid: int, node_id: int) -> bool:
        if _start_returns:
            _gather_state[eid] = node_id
        return _start_returns
    static func cancel_gather(eid: int) -> void:
        _gather_state.erase(eid)
    static func is_gathering(eid: int) -> bool:
        return _gather_state.has(eid)


class StubCombat extends RefCounted:
    static var _attack_state: Dictionary = {}
    static var _start_returns: bool = true
    static func reset() -> void:
        _attack_state.clear()
        _start_returns = true
    static func start_attack(_g, eid: int, target_id: int) -> bool:
        if _start_returns:
            _attack_state[eid] = target_id
        return _start_returns
    static func cancel_attack(eid: int) -> void:
        _attack_state.erase(eid)
    static func is_attacking(eid: int) -> bool:
        return _attack_state.has(eid)


class StubBuilding extends RefCounted:
    static var _build_calls: Array = []
    static var _train_calls: Array = []
    static var _build_returns: bool = true
    static var _train_returns: bool = true
    static func reset() -> void:
        _build_calls.clear()
        _train_calls.clear()
        _build_returns = true
        _train_returns = true
    static func start_build(_g, eid: int, bkind: String, tile) -> bool:
        _build_calls.append([eid, bkind, tile])
        return _build_returns
    static func start_train(_g, bid: int, ukind: String) -> bool:
        _train_calls.append([bid, ukind])
        return _train_returns


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

func before_each() -> void:
    StubPathfinding.reset()
    StubGather.reset()
    StubCombat.reset()
    StubBuilding.reset()
    Commands.reset_module_state()
    Commands.set_module("pathfinding", StubPathfinding)
    Commands.set_module("gather", StubGather)
    Commands.set_module("combat", StubCombat)
    Commands.set_module("building", StubBuilding)


func after_each() -> void:
    # Clear the stub registry so subsequent test files (test_game,
    # test_umbrella) get real sibling modules from Commands._resolve(),
    # not the stubs injected above.
    Commands.reset_module_state()


func _make_game() -> Contract.Game:
    var g = Contract.Game.new()
    var p0 = Contract.Player.new()
    p0.player_id = 0
    var p1 = Contract.Player.new()
    p1.player_id = 1
    g.players = [p0, p1]
    g.entities = []
    g.over = false
    # 80x60 visibility grid, all "visible" for both players (so we exercise
    # the fog code path without each test having to set tiles individually).
    g.visibility = []
    for pid in range(2):
        var col: Array = []
        for x in range(Contract.MAP_W):
            var row: Array = []
            for y in range(Contract.MAP_H):
                row.append("visible")
            col.append(row)
        g.visibility.append(col)
    return g


func _make_entity(eid: int, kind: String, owner: int, pos: Vector2i) -> Contract.Entity:
    var e = Contract.Entity.new()
    e.entity_id = eid
    e.kind = kind
    e.owner = owner
    e.pos = pos
    e.hp = 100
    e.max_hp = 100
    return e


func _cmd(kind: String, issuer: int) -> Contract.Command:
    var c = Contract.Command.new()
    c.kind = kind
    c.issuing_player = issuer
    return c


# ---------------------------------------------------------------------------
# Tests (mirrors tests/test_commands.py)
# ---------------------------------------------------------------------------

# Authority: command against an opponent-owned entity is silently dropped.
func test_authority_mismatch_drops_move():
    var g = _make_game()
    var p1_vil = _make_entity(7, "villager", 1, Vector2i(10, 10))
    g.entities.append(p1_vil)
    var c = _cmd("move", 0)
    c.entity_id = 7
    c.target_tile = Vector2i(11, 10)
    assert_false(Commands.apply_command(g, c))


# AC-21 post-1cc5e95: move INTO an unseen tile is allowed (scout pattern).
func test_move_into_unseen_tile_allowed():
    var g = _make_game()
    var v = _make_entity(1, "villager", 0, Vector2i(5, 5))
    g.entities.append(v)
    var target = Vector2i(70, 50)
    g.visibility[0][target.x][target.y] = "unseen"
    var c = _cmd("move", 0)
    c.entity_id = 1
    c.target_tile = target
    assert_true(Commands.apply_command(g, c))
    assert_true(StubPathfinding.is_moving(1))


# AC-22: fog_cheat waives the fog gate for attack.
func test_fog_cheat_bypasses_fog_for_attack():
    var g = _make_game()
    g.players[0].fog_cheat = true
    var attacker = _make_entity(1, "soldier", 0, Vector2i(5, 5))
    var enemy = _make_entity(2, "villager", 1, Vector2i(70, 50))
    g.entities.append(attacker)
    g.entities.append(enemy)
    g.visibility[0][enemy.pos.x][enemy.pos.y] = "unseen"
    var c = _cmd("attack", 0)
    c.entity_id = 1
    c.target_entity_id = 2
    assert_true(Commands.apply_command(g, c))
    assert_true(StubCombat.is_attacking(1))


# AC-21: attack targeting an unseen enemy is dropped (no fog_cheat).
func test_attack_unseen_enemy_blocked():
    var g = _make_game()
    var attacker = _make_entity(1, "soldier", 0, Vector2i(5, 5))
    var enemy = _make_entity(2, "villager", 1, Vector2i(70, 50))
    g.entities.append(attacker)
    g.entities.append(enemy)
    g.visibility[0][enemy.pos.x][enemy.pos.y] = "unseen"
    var c = _cmd("attack", 0)
    c.entity_id = 1
    c.target_entity_id = 2
    assert_false(Commands.apply_command(g, c))


# gather on a visible resource succeeds and installs gather state.
func test_gather_visible_tree_succeeds():
    var g = _make_game()
    var v = _make_entity(1, "villager", 0, Vector2i(5, 5))
    var tree = _make_entity(99, "tree", 0, Vector2i(6, 5))
    g.entities.append(v)
    g.entities.append(tree)
    var c = _cmd("gather", 0)
    c.entity_id = 1
    c.resource_node_id = 99
    assert_true(Commands.apply_command(g, c))
    assert_true(StubGather.is_gathering(1))


# Subsystem False (e.g., villager attack with dps=0) propagates as False.
func test_attack_subsystem_false_propagates():
    var g = _make_game()
    var attacker = _make_entity(1, "villager", 0, Vector2i(5, 5))
    var enemy = _make_entity(2, "villager", 1, Vector2i(6, 5))
    g.entities.append(attacker)
    g.entities.append(enemy)
    StubCombat._start_returns = false
    var c = _cmd("attack", 0)
    c.entity_id = 1
    c.target_entity_id = 2
    assert_false(Commands.apply_command(g, c))


# Authority: train on opponent-owned building is dropped.
func test_train_wrong_owner_drops():
    var g = _make_game()
    var p1_tc = _make_entity(50, "town_center", 1, Vector2i(70, 50))
    g.entities.append(p1_tc)
    var c = _cmd("train", 0)
    c.building_id = 50
    c.unit_kind = "villager"
    assert_false(Commands.apply_command(g, c))


# Train on own TC dispatches to building.start_train.
func test_train_own_tc_dispatches():
    var g = _make_game()
    var p0_tc = _make_entity(50, "town_center", 0, Vector2i(10, 10))
    g.entities.append(p0_tc)
    var c = _cmd("train", 0)
    c.building_id = 50
    c.unit_kind = "villager"
    assert_true(Commands.apply_command(g, c))
    assert_eq(StubBuilding._train_calls.size(), 1)


# AC-27: stop cancels all three subsystems for the entity.
func test_stop_cancels_all_state():
    var g = _make_game()
    var v = _make_entity(1, "villager", 0, Vector2i(5, 5))
    g.entities.append(v)
    StubPathfinding._move_state[1] = Vector2i(6, 5)
    StubGather._gather_state[1] = 99
    StubCombat._attack_state[1] = 2
    var c = _cmd("stop", 0)
    c.entity_id = 1
    assert_true(Commands.apply_command(g, c))
    assert_false(StubPathfinding.is_moving(1))
    assert_false(StubGather.is_gathering(1))


# AC-37: any command when game.over==true is dropped.
func test_game_over_drops_all_commands():
    var g = _make_game()
    g.over = true
    var v = _make_entity(1, "villager", 0, Vector2i(5, 5))
    g.entities.append(v)
    var c = _cmd("move", 0)
    c.entity_id = 1
    c.target_tile = Vector2i(6, 5)
    assert_false(Commands.apply_command(g, c))


# Unknown kind is silently dropped (AC-27).
func test_unknown_kind_drops():
    var g = _make_game()
    var v = _make_entity(1, "villager", 0, Vector2i(5, 5))
    g.entities.append(v)
    var c = _cmd("teleport", 0)
    c.entity_id = 1
    assert_false(Commands.apply_command(g, c))


# Build dispatches to building.start_build with the right arguments.
func test_build_dispatches_with_args():
    var g = _make_game()
    var v = _make_entity(1, "villager", 0, Vector2i(5, 5))
    g.entities.append(v)
    var c = _cmd("build", 0)
    c.entity_id = 1
    c.building_kind = "house"
    c.target_tile = Vector2i(6, 5)
    assert_true(Commands.apply_command(g, c))
    assert_eq(StubBuilding._build_calls[0][1], "house")


# Successful move cancels gather + attack for the entity.
func test_move_cancels_other_states():
    var g = _make_game()
    var v = _make_entity(1, "villager", 0, Vector2i(5, 5))
    g.entities.append(v)
    StubGather._gather_state[1] = 99
    StubCombat._attack_state[1] = 2
    var c = _cmd("move", 0)
    c.entity_id = 1
    c.target_tile = Vector2i(6, 5)
    assert_true(Commands.apply_command(g, c))
    assert_false(StubGather.is_gathering(1))


# apply_commands returns count of accepted commands (AC-27).
func test_apply_commands_returns_success_count():
    var g = _make_game()
    var v0 = _make_entity(1, "villager", 0, Vector2i(5, 5))
    var v1 = _make_entity(2, "villager", 1, Vector2i(70, 50))
    var p1_tc = _make_entity(50, "town_center", 1, Vector2i(71, 50))
    g.entities.append(v0)
    g.entities.append(v1)
    g.entities.append(p1_tc)
    var good = _cmd("move", 0)
    good.entity_id = 1
    good.target_tile = Vector2i(6, 5)
    var bad_auth = _cmd("stop", 0)
    bad_auth.entity_id = 2
    var bad_train = _cmd("train", 0)
    bad_train.building_id = 50
    bad_train.unit_kind = "villager"
    assert_eq(Commands.apply_commands(g, [good, bad_auth, bad_train]), 1)
