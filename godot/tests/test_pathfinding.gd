## Tests for godot/sim/pathfinding.gd — leaf-05.
##
## Mirrors tests/test_pathfinding.py. Stubs walls.is_passable_for and
## entities.get_stats via module-level Callable overrides (test-only
## escape hatch on pathfinding.gd; impl still late-binds via load()
## when overrides are unset per SPEC_GODOT.md AC-49).

extends GutTest

const Contract = preload("res://sim/contract.gd")
const Pathfinding = preload("res://sim/pathfinding.gd")


var _wall_blocks: Dictionary = {}  # Vector2i -> owner_required (-1 = blocks all)


func _is_passable_for(_game, tile: Vector2i, owner: int) -> bool:
    if not _wall_blocks.has(tile):
        return true
    var req: int = _wall_blocks[tile]
    if req == -1:
        return false
    return owner == req


func _get_stats(_kind: String):
    var s = RefCounted.new()
    s.set_meta("speed_tiles_per_sec", 2.0)
    # Return a duck-typed object exposing .speed_tiles_per_sec via a stub class.
    return _Stats.new()


class _Stats:
    var speed_tiles_per_sec: float = 2.0


func _empty_game():
    var g = Contract.Game.new()
    var p0 = Contract.Player.new()
    p0.player_id = 0
    p0.pop_cap = 5
    var p1 = Contract.Player.new()
    p1.player_id = 1
    p1.pop_cap = 5
    g.players = [p0, p1]
    g.entities = []
    var m = Contract.Map.new()
    m.width = Contract.MAP_W
    m.height = Contract.MAP_H
    var terrain: Array = []
    for x in range(Contract.MAP_W):
        var col: Array = []
        for y in range(Contract.MAP_H):
            col.append("grass")
        terrain.append(col)
    m.terrain = terrain
    g.map_ = m
    return g


func _new_entity(eid: int, kind: String, owner: int, pos: Vector2i, hp: int = 10):
    var e = Contract.Entity.new()
    e.entity_id = eid
    e.kind = kind
    e.owner = owner
    e.pos = pos
    e.hp = hp
    e.max_hp = hp
    return e


func before_each():
    _wall_blocks.clear()
    Pathfinding.reset_module_state()
    Pathfinding._test_passable_override = Callable(self, "_is_passable_for")
    Pathfinding._test_get_stats_override = Callable(self, "_get_stats")


func after_each():
    _wall_blocks.clear()
    Pathfinding.reset_module_state()


func test_diagonal_path_empty_map():
    var g = _empty_game()
    var path = Pathfinding.find_path(g, Vector2i(0, 0), Vector2i(5, 5), 0)
    assert_eq(path.size(), 5)
    assert_eq(path[-1], Vector2i(5, 5))


func test_path_empty_when_goal_oob():
    var g = _empty_game()
    assert_eq(Pathfinding.find_path(g, Vector2i(0, 0), Vector2i(Contract.MAP_W, 5), 0).size(), 0)
    assert_eq(Pathfinding.find_path(g, Vector2i(0, 0), Vector2i(-1, 5), 0).size(), 0)


func test_path_empty_when_goal_is_tree():
    var g = _empty_game()
    g.entities.append(_new_entity(1, "tree", -1, Vector2i(5, 5), 40))
    var path = Pathfinding.find_path(g, Vector2i(0, 0), Vector2i(5, 5), 0)
    assert_eq(path.size(), 0)


func test_wall_forces_deviation():
    var g = _empty_game()
    _wall_blocks[Vector2i(3, 3)] = -1
    var path = Pathfinding.find_path(g, Vector2i(0, 3), Vector2i(6, 3), 0)
    assert_true(path.size() > 0)
    assert_false(path.has(Vector2i(3, 3)))


func test_gate_admits_owner():
    var g = _empty_game()
    _wall_blocks[Vector2i(3, 3)] = 0  # gate owned by 0
    for y in range(Contract.MAP_H):
        if y != 3:
            _wall_blocks[Vector2i(3, y)] = -1
    var path = Pathfinding.find_path(g, Vector2i(0, 3), Vector2i(6, 3), 0)
    assert_true(path.size() > 0)
    assert_true(path.has(Vector2i(3, 3)))


func test_gate_rejects_non_owner():
    var g = _empty_game()
    _wall_blocks[Vector2i(3, 3)] = 0
    for y in range(Contract.MAP_H):
        if y != 3:
            _wall_blocks[Vector2i(3, y)] = -1
    var path = Pathfinding.find_path(g, Vector2i(0, 3), Vector2i(6, 3), 1)
    assert_false(path.has(Vector2i(3, 3)))


func test_start_move_and_tick_reaches_goal():
    var g = _empty_game()
    var ent = _new_entity(42, "villager", 0, Vector2i(0, 0))
    g.entities.append(ent)
    var ok = Pathfinding.start_move(g, 42, Vector2i(5, 5))
    assert_true(ok)
    assert_true(Pathfinding.is_moving(42))
    var max_ticks = int((5.0 / 2.0) * Contract.TICK_HZ) + 10
    for _i in range(max_ticks):
        Pathfinding.tick_movement(g)
        if not Pathfinding.is_moving(42):
            break
    assert_eq(ent.pos, Vector2i(5, 5))
    assert_false(Pathfinding.is_moving(42))


func test_start_move_unreachable_returns_false():
    var g = _empty_game()
    g.entities.append(_new_entity(1, "tree", -1, Vector2i(5, 5), 40))
    var ent = _new_entity(7, "villager", 0, Vector2i(0, 0))
    g.entities.append(ent)
    var ok = Pathfinding.start_move(g, 7, Vector2i(5, 5))
    assert_false(ok)


func test_cancel_move():
    var g = _empty_game()
    var ent = _new_entity(9, "villager", 0, Vector2i(0, 0))
    g.entities.append(ent)
    Pathfinding.start_move(g, 9, Vector2i(5, 5))
    assert_true(Pathfinding.is_moving(9))
    Pathfinding.cancel_move(9)
    assert_false(Pathfinding.is_moving(9))
    var prev = ent.pos
    Pathfinding.tick_movement(g)
    assert_eq(ent.pos, prev)


func test_cancel_move_no_state_noop():
    Pathfinding.cancel_move(999)
    assert_false(Pathfinding.is_moving(999))
