## AI deterministic-script tests (leaf-11) — SPEC_GODOT.md AC-64..AC-66.

extends GutTest

const Contract = preload("res://sim/contract.gd")
const AI = preload("res://sim/ai.gd")


func before_each() -> void:
    AI.reset_module_state()


func _make_terrain() -> Array:
    var t: Array = []
    for x in range(Contract.MAP_W):
        var col: Array = []
        for y in range(Contract.MAP_H):
            col.append("grass")
        t.append(col)
    return t


func _empty_vis(state: String) -> Array:
    var v: Array = []
    for x in range(Contract.MAP_W):
        var col: Array = []
        for y in range(Contract.MAP_H):
            col.append(state)
        v.append(col)
    return v


func _make_entity(eid: int, kind: String, owner: int, pos: Vector2i, hp: int = 100):
    var e = Contract.Entity.new()
    e.entity_id = eid
    e.kind = kind
    e.owner = owner
    e.pos = pos
    e.hp = hp
    e.max_hp = hp if hp > 0 else 100
    return e


func _make_game(wood0: int = 300, gold0: int = 150) -> Contract.Game:
    var g = Contract.Game.new()
    var m = Contract.Map.new()
    m.width = Contract.MAP_W
    m.height = Contract.MAP_H
    m.terrain = _make_terrain()
    g.map_ = m
    g.entities = []
    g.visibility = [_empty_vis("visible"), _empty_vis("visible")]
    g.explored_snapshots = [{}, {}]
    var p0 = Contract.Player.new()
    p0.player_id = 0
    p0.wood = wood0
    p0.gold = gold0
    p0.pop_cap = 5
    var p1 = Contract.Player.new()
    p1.player_id = 1
    p1.wood = wood0
    p1.gold = gold0
    p1.pop_cap = 5
    g.players = [p0, p1]
    return g


func _fresh_p0_setup(g) -> void:
    g.entities.append(_make_entity(100, "town_center", 0, Vector2i(10, 30), 500))
    g.entities.append(_make_entity(101, "town_center", 1, Vector2i(70, 30), 500))
    for i in range(5):
        g.entities.append(_make_entity(1 + i, "villager", 0, Vector2i(11, 30 + i), 25))
    # Some trees + a gold mine so rule 10 has nodes to assign.
    g.entities.append(_make_entity(50, "tree", -1, Vector2i(12, 30), 20))
    g.entities.append(_make_entity(51, "tree", -1, Vector2i(13, 30), 20))
    g.entities.append(_make_entity(52, "gold_mine", -1, Vector2i(12, 32), 200))


# 1. Fresh game, rule 3 fires (train villager). wood=300 covers 50+80 reserve.
func test_rule3_trains_villager_on_fresh_game():
    var g = _make_game(300, 150)
    _fresh_p0_setup(g)
    var cmds = AI.ai_tick(g, 0, 0)
    assert_gt(cmds.size(), 0, "expected non-empty command list")
    var has_train_v = false
    for c in cmds:
        if c.kind == "train" and c.unit_kind == "villager" and c.building_id == 100:
            has_train_v = true
            break
    assert_true(has_train_v, "expected rule-3 villager train command")


# 2. Rule 3 reserves 80 wood for first barracks: with wood==100, no train.
func test_rule3_reserves_80_wood_for_barracks():
    var g = _make_game(100, 0)  # also gold=0 so rule 4/5/6 cannot fire
    _fresh_p0_setup(g)
    var cmds = AI.ai_tick(g, 0, 0)
    for c in cmds:
        if c.kind == "train" and c.unit_kind == "villager":
            fail_test("rule 3 should not fire: 100 < 50+80 reserve")
            return
    assert_true(true)


# 3. Rule 4 (train scout) does NOT fire when barracks_count == 0.
func test_rule4_scout_gated_on_barracks():
    # Block rule 3 by maxing villagers, leaving room only for rules 4/5/6.
    var g = _make_game(100, 100)
    g.entities.append(_make_entity(100, "town_center", 0, Vector2i(10, 30), 500))
    for i in range(10):
        g.entities.append(_make_entity(200 + i, "villager", 0, Vector2i(11, 20 + i), 25))
    var cmds = AI.ai_tick(g, 0, 0)
    for c in cmds:
        if c.kind == "train" and c.unit_kind == "scout":
            fail_test("rule 4 fired without barracks")
            return
    assert_true(true)


# 4. Rule 9 fires when sol_n + arch_n >= 3 and enemy TC is visible.
func test_rule9_attack_fires_at_threshold_3():
    var g = _make_game(0, 0)  # zero resources so rules 1-6 can't fire
    g.entities.append(_make_entity(100, "town_center", 0, Vector2i(10, 30), 500))
    g.entities.append(_make_entity(101, "town_center", 1, Vector2i(70, 30), 500))
    g.entities.append(_make_entity(10, "soldier", 0, Vector2i(11, 30), 50))
    g.entities.append(_make_entity(11, "soldier", 0, Vector2i(12, 30), 50))
    g.entities.append(_make_entity(12, "archer", 0, Vector2i(13, 30), 40))
    var cmds = AI.ai_tick(g, 0, 0)
    var attack_count = 0
    for c in cmds:
        if c.kind == "attack" and c.target_entity_id == 101:
            attack_count += 1
    assert_eq(attack_count, 3, "expected 3 attack commands targeting enemy TC")


# 5. Rule 9 does NOT fire when sol_n + arch_n < 3.
func test_rule9_does_not_fire_below_threshold():
    var g = _make_game(0, 0)
    g.entities.append(_make_entity(100, "town_center", 0, Vector2i(10, 30), 500))
    g.entities.append(_make_entity(101, "town_center", 1, Vector2i(70, 30), 500))
    g.entities.append(_make_entity(10, "soldier", 0, Vector2i(11, 30), 50))
    g.entities.append(_make_entity(11, "archer", 0, Vector2i(12, 30), 40))
    var cmds = AI.ai_tick(g, 0, 0)
    for c in cmds:
        assert_ne(c.kind, "attack", "rule 9 should not fire with only 2 military")


# 6. Rule 10 issues gather commands for idle villagers.
func test_rule10_idle_villagers_gather():
    var g = _make_game(0, 0)  # zero wood so rule 3 cannot eat villagers
    _fresh_p0_setup(g)
    var cmds = AI.ai_tick(g, 0, 0)
    var gather_count = 0
    for c in cmds:
        if c.kind == "gather":
            gather_count += 1
    assert_eq(gather_count, 5, "expected 5 gather commands (one per villager)")


# 7. Determinism: two consecutive calls with same state + tick produce same output.
func test_determinism_same_state_same_commands():
    var g1 = _make_game(300, 150)
    _fresh_p0_setup(g1)
    var c1 = AI.ai_tick(g1, 0, 0)
    AI.reset_module_state()
    var g2 = _make_game(300, 150)
    _fresh_p0_setup(g2)
    var c2 = AI.ai_tick(g2, 0, 0)
    assert_eq(c1.size(), c2.size(), "command count diverged")
    for i in range(c1.size()):
        assert_eq(c1[i].kind, c2[i].kind, "kind diverged at index %d" % i)
        assert_eq(c1[i].entity_id, c2[i].entity_id, "entity_id diverged at index %d" % i)


# 8. Per-player state isolation: ai_tick(g, 0, ...) does not perturb state[1].
func test_ai_state_per_player_keyed():
    var g = _make_game(300, 150)
    _fresh_p0_setup(g)
    AI.ai_tick(g, 0, 0)
    assert_true(AI._ai_state.has(0), "state[0] should be set")
    assert_false(AI._ai_state.has(1), "state[1] must not be set by ai_tick(g, 0, ...)")
