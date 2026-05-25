## GUT tests for godot/sim/visibility.gd — mirrors tests/test_visibility.py.
## Stubs `get_stats` via _get_stats_override to verify in isolation (AC-49).

extends GutTest

const Contract = preload("res://sim/contract.gd")
const Visibility = preload("res://sim/visibility.gd")


# ---- Stubbed sight table (mirrors sim/entities.py STATS sight column) ------
const _SIGHT = {
    "villager": 5,
    "soldier": 4,
    "archer": 7,
    "scout": 10,
    "town_center": 8,
    "house": 3,
    "barracks": 4,
    "wall": 0,
    "gate": 0,
    "tree": 0,
    "gold_mine": 0,
}


func _stub_get_stats(kind: String) -> Dictionary:
    return {"sight_tiles": _SIGHT.get(kind, 0)}


func before_each():
    Visibility._get_stats_override = Callable(self, "_stub_get_stats")


func after_each():
    Visibility.reset_module_state()


# ---- Fixtures ---------------------------------------------------------------

func _make_game(n_players: int = 2):
    var g = Contract.Game.new()
    var players: Array = []
    for i in range(n_players):
        var p = Contract.Player.new()
        p.player_id = i
        players.append(p)
    g.players = players
    g.entities = []
    return g


func _make_entity(eid: int, kind: String, owner: int, pos: Vector2i, hp: int = 50):
    var e = Contract.Entity.new()
    e.entity_id = eid
    e.kind = kind
    e.owner = owner
    e.pos = pos
    e.hp = hp
    e.max_hp = hp
    return e


# ---- Tests ------------------------------------------------------------------

func test_init_visibility_shape_and_default():
    var g = _make_game()
    Visibility.init_visibility(g)
    assert_eq(g.visibility.size(), 2)
    assert_eq(g.visibility[0].size(), Contract.MAP_W)
    assert_eq(g.visibility[0][0].size(), Contract.MAP_H)
    assert_eq(g.visibility[0][5][5], "unseen")


func test_init_visibility_idempotent_preserves_state():
    var g = _make_game()
    Visibility.init_visibility(g)
    g.visibility[0][3][4] = "visible"
    Visibility.init_visibility(g)
    assert_eq(g.visibility[0][3][4], "visible")


func test_villager_reveals_chebyshev_5():
    var g = _make_game()
    g.entities.append(_make_entity(1, "villager", 0, Vector2i(10, 10)))
    Visibility.recompute_visibility(g)
    # In-range corner (Chebyshev 5) and out-of-range (Chebyshev 6).
    assert_eq(g.visibility[0][15][15], "visible")
    assert_eq(g.visibility[0][16][10], "unseen")


func test_symmetric_fog_p1_villager_invisible_to_p0():
    var g = _make_game()
    g.entities.append(_make_entity(1, "villager", 1, Vector2i(70, 30)))
    Visibility.recompute_visibility(g)
    assert_eq(g.visibility[1][70][30], "visible")
    assert_eq(g.visibility[0][70][30], "unseen")


func test_visible_demotes_to_explored_after_move():
    var g = _make_game()
    var v = _make_entity(1, "villager", 0, Vector2i(10, 10))
    g.entities.append(v)
    Visibility.recompute_visibility(g)
    assert_eq(g.visibility[0][10][10], "visible")
    # Villager moves far away.
    v.pos = Vector2i(50, 50)
    Visibility.recompute_visibility(g)
    assert_eq(g.visibility[0][10][10], "explored")


func test_is_command_visible_unseen_false():
    var g = _make_game()
    Visibility.init_visibility(g)
    assert_false(Visibility.is_command_visible(g, 0, Vector2i(40, 40)))


func test_is_command_visible_visible_and_explored_true():
    var g = _make_game()
    Visibility.init_visibility(g)
    g.visibility[0][20][20] = "visible"
    g.visibility[0][21][21] = "explored"
    assert_true(Visibility.is_command_visible(g, 0, Vector2i(20, 20)))
    assert_true(Visibility.is_command_visible(g, 0, Vector2i(21, 21)))


func test_fog_cheat_waives_visibility():
    var g = _make_game()
    Visibility.init_visibility(g)
    g.players[0].fog_cheat = true
    assert_true(Visibility.is_command_visible(g, 0, Vector2i(40, 40)))


func test_visible_entities_excludes_unseen_enemy():
    var g = _make_game()
    g.entities.append(_make_entity(1, "villager", 0, Vector2i(10, 10)))
    g.entities.append(_make_entity(2, "villager", 1, Vector2i(70, 30)))
    Visibility.recompute_visibility(g)
    var seen = Visibility.visible_entities_for(g, 0)
    assert_eq(seen.size(), 1)
    assert_eq(seen[0].entity_id, 1)


func test_visible_entities_includes_visible_enemy():
    var g = _make_game()
    g.entities.append(_make_entity(1, "scout", 0, Vector2i(10, 10)))
    g.entities.append(_make_entity(2, "villager", 1, Vector2i(15, 10)))
    Visibility.recompute_visibility(g)
    var seen = Visibility.visible_entities_for(g, 0)
    assert_eq(seen.size(), 2)


func test_enemy_building_snapshot_recorded_when_visible():
    var g = _make_game()
    g.entities.append(_make_entity(1, "scout", 0, Vector2i(20, 20)))
    g.entities.append(_make_entity(2, "town_center", 1, Vector2i(22, 22), 800))
    Visibility.recompute_visibility(g)
    assert_true(g.explored_snapshots[0].has(2))
    assert_eq(g.explored_snapshots[0][2].hp_last_seen, 800)


func test_building_snapshot_persists_after_death():
    var g = _make_game()
    var scout = _make_entity(1, "scout", 0, Vector2i(20, 20))
    var tc = _make_entity(2, "town_center", 1, Vector2i(22, 22), 800)
    g.entities.append(scout)
    g.entities.append(tc)
    Visibility.recompute_visibility(g)
    # Building dies; scout moves away so tile is no longer visible.
    tc.hp = 0
    scout.pos = Vector2i(70, 50)
    Visibility.recompute_visibility(g)
    assert_true(g.explored_snapshots[0].has(2))


func test_standalone_building_reveals_sight():
    var g = _make_game()
    # town_center sight 8.
    g.entities.append(_make_entity(1, "town_center", 0, Vector2i(30, 30), 800))
    Visibility.recompute_visibility(g)
    assert_eq(g.visibility[0][38][30], "visible")
    assert_eq(g.visibility[0][39][30], "unseen")


func test_dead_building_does_not_grant_vision():
    var g = _make_game()
    g.entities.append(_make_entity(1, "town_center", 0, Vector2i(30, 30), 0))
    Visibility.recompute_visibility(g)
    assert_eq(g.visibility[0][35][30], "unseen")
