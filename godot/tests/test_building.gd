## Construction + training tests per SPEC.md AC-10, AC-11, AC-26 (mirrors
## tests/test_building.py 13 cases). Stubs `entities` + `pathfinding` siblings
## via Building.entities_override / pathfinding_override (AC-49 late-bind).

extends GutTest

const Contract = preload("res://sim/contract.gd")
const Building = preload("res://sim/building.gd")


# -------------- stub sibling scripts (entities + pathfinding) ------------

class _EntitiesStub:
    extends RefCounted
    static var next_id: int = 1000
    static var _stats := {
        "villager": {"hp": 40, "max_hp": 40},
        "scout": {"hp": 30, "max_hp": 30},
        "soldier": {"hp": 60, "max_hp": 60},
        "archer": {"hp": 40, "max_hp": 40},
        "town_center": {"hp": 1000, "max_hp": 1000},
        "house": {"hp": 200, "max_hp": 200},
        "barracks": {"hp": 500, "max_hp": 500},
        "wall": {"hp": 200, "max_hp": 200},
        "gate": {"hp": 200, "max_hp": 200},
    }
    static var _building_kinds := {"town_center": 1, "house": 1, "barracks": 1, "wall": 1, "gate": 1}
    static var _unit_kinds := {"villager": 1, "soldier": 1, "archer": 1, "scout": 1}

    static func get_stats(kind: String) -> Dictionary:
        return _stats[kind]

    static func is_unit(e) -> bool:
        return _unit_kinds.has(e.kind)

    static func is_building(e) -> bool:
        return _building_kinds.has(e.kind)

    static func spawn_unit(game, kind: String, owner: int, pos: Vector2i):
        return _spawn(game, kind, owner, pos)

    static func spawn_building(game, kind: String, owner: int, pos: Vector2i):
        return _spawn(game, kind, owner, pos)

    static func _spawn(game, kind: String, owner: int, pos: Vector2i):
        var s: Dictionary = _stats[kind]
        next_id += 1
        var e := Contract.Entity.new()
        e.entity_id = next_id
        e.kind = kind
        e.owner = owner
        e.pos = pos
        e.hp = s["hp"]
        e.max_hp = s["max_hp"]
        game.entities.append(e)
        return e


class _PathfindingStub:
    extends RefCounted
    static var last_target: Vector2i = Vector2i.ZERO

    static func start_move(_game, _eid: int, target: Vector2i) -> bool:
        last_target = target
        return true


# ---------------------------- helpers ------------------------------------

func before_each() -> void:
    _EntitiesStub.next_id = 1000
    Building.entities_override = _EntitiesStub
    Building.pathfinding_override = _PathfindingStub
    Building.reset_module_state()


func after_each() -> void:
    Building.entities_override = null
    Building.pathfinding_override = null
    Building.reset_module_state()


func _make_game(wood: int = 300, gold: int = 150):
    var m := Contract.Map.new()
    m.width = 30
    m.height = 30
    var terrain: Array = []
    for x in range(30):
        var col: Array = []
        for y in range(30):
            col.append("grass")
        terrain.append(col)
    m.terrain = terrain
    var p0 := Contract.Player.new()
    p0.player_id = 0
    p0.wood = wood
    p0.gold = gold
    p0.pop_cap = 5
    var p1 := Contract.Player.new()
    p1.player_id = 1
    p1.wood = wood
    p1.gold = gold
    p1.pop_cap = 5
    var g := Contract.Game.new()
    g.players = [p0, p1]
    g.entities = []
    g.map_ = m
    return g


func _spawn_unit(g, kind: String, owner: int, pos: Vector2i):
    return _EntitiesStub.spawn_unit(g, kind, owner, pos)


func _spawn_building(g, kind: String, owner: int, pos: Vector2i):
    return _EntitiesStub.spawn_building(g, kind, owner, pos)


# ---------------------------- tests --------------------------------------

func test_constants_exist():
    assert_eq(Building.BUILD_COSTS["house"], [30, 0, 10])
    assert_eq(Building.TRAIN_COSTS["villager"], [50, 0, 12, "town_center"])
    assert_eq(Building.BUILDING_FOOTPRINT["barracks"], Vector2i(3, 3))


func test_start_build_insufficient_wood_returns_false():
    var g = _make_game(10)
    var v = _spawn_unit(g, "villager", 0, Vector2i(5, 5))
    assert_false(Building.start_build(g, v.entity_id, "house", Vector2i(8, 8)))
    assert_eq(g.players[0].wood, 10)


func test_start_build_house_success_deducts_and_installs():
    var g = _make_game(100)
    var v = _spawn_unit(g, "villager", 0, Vector2i(5, 5))
    assert_true(Building.start_build(g, v.entity_id, "house", Vector2i(8, 8)))
    assert_eq(g.players[0].wood, 70)


func test_house_completes_after_10s_with_full_hp():
    var g = _make_game(100)
    var v = _spawn_unit(g, "villager", 0, Vector2i(8, 8))
    Building.start_build(g, v.entity_id, "house", Vector2i(8, 8))
    for _i in range(Contract.TICK_HZ * 10):
        Building.tick_construction(g)
    var houses: Array = []
    for e in g.entities:
        if e.kind == "house":
            houses.append(e)
    assert_eq(houses.size(), 1)
    assert_eq(houses[0].hp, 200)


func test_house_completion_bumps_pop_cap():
    var g = _make_game(100)
    var v = _spawn_unit(g, "villager", 0, Vector2i(8, 8))
    Building.start_build(g, v.entity_id, "house", Vector2i(8, 8))
    for _i in range(Contract.TICK_HZ * 10):
        Building.tick_construction(g)
    assert_eq(g.players[0].pop_cap, 10)


func test_pop_cap_clamped_at_max():
    var g = _make_game(10000)
    g.players[0].pop_cap = Contract.POP_CAP_MAX - 2
    var v = _spawn_unit(g, "villager", 0, Vector2i(8, 8))
    Building.start_build(g, v.entity_id, "house", Vector2i(8, 8))
    for _i in range(Contract.TICK_HZ * 10):
        Building.tick_construction(g)
    assert_eq(g.players[0].pop_cap, Contract.POP_CAP_MAX)


func test_start_train_villager_at_tc():
    var g = _make_game(100)
    var tc = _spawn_building(g, "town_center", 0, Vector2i(10, 10))
    assert_true(Building.start_train(g, tc.entity_id, "villager"))
    assert_true(Building._training.has(tc.entity_id))


func test_second_train_blocked_while_queue_full():
    var g = _make_game(200)
    var tc = _spawn_building(g, "town_center", 0, Vector2i(10, 10))
    Building.start_train(g, tc.entity_id, "villager")
    assert_false(Building.start_train(g, tc.entity_id, "villager"))


func test_training_completes_and_spawns_adjacent_unit():
    var g = _make_game(100)
    var tc = _spawn_building(g, "town_center", 0, Vector2i(10, 10))
    Building.start_train(g, tc.entity_id, "villager")
    for _i in range(Contract.TICK_HZ * 12):
        Building.tick_training(g)
    var villagers: Array = []
    for e in g.entities:
        if e.kind == "villager" and e.owner == 0:
            villagers.append(e)
    assert_eq(villagers.size(), 1)
    var v = villagers[0]
    assert_eq(maxi(absi(v.pos.x - 10), absi(v.pos.y - 10)), 1)


func test_training_blocked_when_pop_full():
    var g = _make_game(500)
    g.players[0].pop_cap = 2
    _spawn_unit(g, "villager", 0, Vector2i(5, 5))
    _spawn_unit(g, "villager", 0, Vector2i(5, 6))
    var tc = _spawn_building(g, "town_center", 0, Vector2i(10, 10))
    assert_false(Building.start_train(g, tc.entity_id, "villager"))
    assert_eq(g.players[0].wood, 500)


func test_place_building_immediate_no_cost_full_hp():
    var g = _make_game(50)
    var e = Building.place_building_immediate(g, "house", Vector2i(8, 8), 0)
    assert_eq(e.hp, 200)
    assert_eq(g.players[0].wood, 50)


func test_start_build_rejects_invalid_kind():
    var g = _make_game()
    var v = _spawn_unit(g, "villager", 0, Vector2i(5, 5))
    assert_false(Building.start_build(g, v.entity_id, "town_center", Vector2i(8, 8)))


func test_start_train_rejects_wrong_building():
    var g = _make_game()
    var b = _spawn_building(g, "barracks", 0, Vector2i(10, 10))
    assert_false(Building.start_train(g, b.entity_id, "villager"))
