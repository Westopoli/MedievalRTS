## Tests for sim/gather.gd (AC-5..AC-9, AC-46..AC-50).
##
## Mirrors `tests/test_gather.py`. Stubs the late-bound sim.pathfinding
## module via gather._pf_override so start_move teleports the entity to
## the requested tile, is_moving returns false, cancel_move is a noop.

extends GutTest

const Contract = preload("res://sim/contract.gd")
const Gather = preload("res://sim/gather.gd")


# ---- pathfinding stub --------------------------------------------------

class _PathStub extends RefCounted:
    func start_move(game, entity_id: int, target_tile) -> bool:
        var t = target_tile
        if typeof(t) != TYPE_VECTOR2I:
            t = Vector2i(t.x, t.y)
        for e in game.entities:
            if e.entity_id == entity_id:
                e.pos = t
                return true
        return false

    func cancel_move(_entity_id: int) -> void:
        pass

    func is_moving(_entity_id: int) -> bool:
        return false


# ---- fixtures ---------------------------------------------------------

func before_each() -> void:
    Gather.reset_module_state()
    Gather._pf_override = _PathStub.new()


func after_each() -> void:
    Gather.reset_module_state()


func _ent(eid: int, kind: String, owner: int, pos: Vector2i, hp: int = 25, max_hp: int = 25):
    var e = Contract.Entity.new()
    e.entity_id = eid
    e.kind = kind
    e.owner = owner
    e.pos = pos
    e.hp = hp
    e.max_hp = max_hp
    return e


func _make_game(entities: Array):
    var terrain: Array = []
    for _y in range(20):
        var row: Array = []
        for _x in range(20):
            row.append("grass")
        terrain.append(row)
    var m = Contract.Map.new()
    m.width = 20
    m.height = 20
    m.terrain = terrain
    var p0 = Contract.Player.new(); p0.player_id = 0
    var p1 = Contract.Player.new(); p1.player_id = 1
    var g = Contract.Game.new()
    g.players = [p0, p1]
    g.entities = entities
    g.map_ = m
    return g


# ---- tests ------------------------------------------------------------

func test_start_gather_bad_ids_returns_false():
    var v = _ent(1, "villager", 0, Vector2i(5, 5))
    var tree = _ent(2, "tree", 0, Vector2i(10, 10), 40, 40)
    var g = _make_game([v, tree])
    assert_false(Gather.start_gather(g, 999, 2))
    assert_false(Gather.start_gather(g, 1, 999))
    var tc = _ent(3, "town_center", 0, Vector2i(3, 3), 800, 800)
    var g2 = _make_game([v, tc])
    assert_false(Gather.start_gather(g2, 1, 3))
    assert_false(Gather.is_gathering(1))


func test_gather_tree_increases_wood():
    var v = _ent(1, "villager", 0, Vector2i(5, 5))
    var tree = _ent(2, "tree", 0, Vector2i(10, 10), 40, 40)
    var tc = _ent(3, "town_center", 0, Vector2i(0, 0), 800, 800)
    var g = _make_game([v, tree, tc])
    assert_true(Gather.start_gather(g, 1, 2))
    for _i in range(Contract.TICK_HZ * (Contract.CARRY_CAP + 5)):
        Gather.tick_gather(g)
    assert_true(g.players[0].wood >= 1)
    assert_true(v.carry_amount <= Contract.CARRY_CAP)


func test_gather_sets_carrying_wood_for_tree():
    var v = _ent(1, "villager", 0, Vector2i(10, 10))
    var tree = _ent(2, "tree", 0, Vector2i(10, 10), 40, 40)
    var g = _make_game([v, tree])
    assert_true(Gather.start_gather(g, 1, 2))
    for _i in range(Contract.TICK_HZ + 2):
        Gather.tick_gather(g)
    assert_eq(v.carrying, "wood")


func test_gather_sets_carrying_gold_for_gold_mine():
    var v = _ent(1, "villager", 0, Vector2i(10, 10))
    var mine = _ent(2, "gold_mine", 0, Vector2i(10, 10), 200, 200)
    var g = _make_game([v, mine])
    assert_true(Gather.start_gather(g, 1, 2))
    for _i in range(Contract.TICK_HZ + 2):
        Gather.tick_gather(g)
    assert_eq(v.carrying, "gold")


func test_second_start_gather_replaces_first():
    var v = _ent(1, "villager", 0, Vector2i(5, 5))
    var t1 = _ent(2, "tree", 0, Vector2i(10, 10), 40, 40)
    var t2 = _ent(3, "tree", 0, Vector2i(15, 15), 40, 40)
    var g = _make_game([v, t1, t2])
    assert_true(Gather.start_gather(g, 1, 2))
    assert_true(Gather.start_gather(g, 1, 3))
    assert_eq(Gather._gather_state[1].node_id, 3)


func test_tree_hp_decrements_and_clears_on_death():
    var v = _ent(1, "villager", 0, Vector2i(10, 10))
    var tree = _ent(2, "tree", 0, Vector2i(10, 10), 3, 40)
    var g = _make_game([v, tree])
    assert_true(Gather.start_gather(g, 1, 2))
    var start_hp = tree.hp
    for _i in range(Contract.TICK_HZ + 1):
        Gather.tick_gather(g)
    assert_eq(tree.hp, start_hp - 1)
    for _i in range(Contract.TICK_HZ * 5):
        Gather.tick_gather(g)
    assert_true(tree.hp <= 0)
    assert_false(Gather.is_gathering(1))
