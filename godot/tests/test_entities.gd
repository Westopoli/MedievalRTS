## leaf-03 parity tests for godot/sim/entities.gd
##
## Mirrors sim/entities.py + SPEC.md § 6 (AC-46, AC-50).
## Brief: briefs_godot/leaf-03.md. Stat values follow Python (canonical);
## see briefs_godot/leaf-03.ASSUMPTIONS.md for the house/barracks deviation
## from the brief's literal expected values.

extends GutTest

const Contract = preload("res://sim/contract.gd")
const Entities = preload("res://sim/entities.gd")


func _make_game():
    var g = Contract.Game.new()
    g.entities = []
    return g


# ---- Stats table parity (AC-50) ----

func test_unit_stats_parity():
    assert_eq(Entities.get_stats("villager")["max_hp"], 25)
    assert_eq(Entities.get_stats("soldier")["damage_per_sec"], 8)
    assert_eq(Entities.get_stats("soldier")["attack_range_tiles"], 1)
    assert_eq(Entities.get_stats("archer")["damage_per_sec"], 5)
    assert_eq(Entities.get_stats("archer")["attack_range_tiles"], 5)
    assert_eq(Entities.get_stats("scout")["sight_tiles"], 10)
    assert_almost_eq(float(Entities.get_stats("scout")["speed_tiles_per_sec"]), 4.0, 0.0001)


func test_building_stats_parity():
    # NB: house=100, barracks=300 follow Python/SPEC, not brief literal.
    assert_eq(Entities.get_stats("town_center")["max_hp"], 800)
    assert_eq(Entities.get_stats("town_center")["sight_tiles"], 8)
    assert_eq(Entities.get_stats("house")["max_hp"], 100)
    assert_eq(Entities.get_stats("barracks")["max_hp"], 300)
    assert_eq(Entities.get_stats("wall")["max_hp"], 200)


# ---- Spawn factories ----

func test_spawn_unit_fresh_game():
    var g = _make_game()
    var e = Entities.spawn_unit(g, "villager", 0, Vector2i(5, 5))
    assert_eq(e.entity_id, 0)
    assert_eq(e.kind, "villager")
    assert_eq(e.hp, 25)


func test_spawn_unit_assigns_next_id():
    var g = _make_game()
    Entities.spawn_unit(g, "villager", 0, Vector2i(5, 5))
    var e2 = Entities.spawn_unit(g, "soldier", 0, Vector2i(6, 5))
    assert_eq(e2.entity_id, 1)


func test_spawn_building_owner_and_hp():
    var g = _make_game()
    var e = Entities.spawn_building(g, "barracks", 1, Vector2i(70, 28))
    assert_eq(e.owner, 1)
    assert_eq(e.hp, 300)  # NB: deviates from brief literal (500); Python canonical.


# ---- Classification (AC-46) ----

func test_classification():
    var g = _make_game()
    var v = Entities.spawn_unit(g, "villager", 0, Vector2i(1, 1))
    var b = Entities.spawn_building(g, "house", 0, Vector2i(2, 2))
    assert_true(Entities.is_unit(v))
    assert_true(Entities.is_building(b))
    assert_true(Entities.is_resource("tree"))


# ---- Wrong-kind rejection (asserts/error path) ----

func test_spawn_unit_rejects_non_unit_kind():
    var g = _make_game()
    var e = Entities.spawn_unit(g, "house", 0, Vector2i(3, 3))
    assert_eq(e, null)
