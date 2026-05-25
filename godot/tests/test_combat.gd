## Combat tests per SPEC.md AC-14, AC-25 (SPEC_GODOT.md AC-46/47/49/50).
## Mirrors tests/test_combat.py (9 tests).

extends GutTest

const Contract = preload("res://sim/contract.gd")
const Combat = preload("res://sim/combat.gd")
const Pathfinding = preload("res://sim/pathfinding.gd")


var combat


func before_each():
    combat = Combat.new()
    Pathfinding.reset_module_state()


func after_each():
    Pathfinding.reset_module_state()


func _make_game(entities: Array):
    var g = Contract.Game.new()
    g.entities = entities
    var p0 = Contract.Player.new(); p0.player_id = 0
    var p1 = Contract.Player.new(); p1.player_id = 1
    g.players = [p0, p1]
    return g


func _ent(eid: int, kind: String, owner: int, pos: Vector2i, hp: int = -1):
    var e = Contract.Entity.new()
    e.entity_id = eid
    e.kind = kind
    e.owner = owner
    e.pos = pos
    var max_hp = {"soldier": 60, "archer": 35, "villager": 25, "wall": 200}[kind]
    e.max_hp = max_hp
    e.hp = hp if hp >= 0 else max_hp
    return e


func test_start_attack_same_owner_returns_false():
    var a = _ent(1, "soldier", 0, Vector2i(5, 5))
    var b = _ent(2, "soldier", 0, Vector2i(6, 5))
    var g = _make_game([a, b])
    assert_false(combat.start_attack(g, 1, 2))
    assert_false(combat.is_attacking(1))


func test_start_attack_villager_returns_false():
    var v = _ent(1, "villager", 0, Vector2i(5, 5))
    var enemy = _ent(2, "soldier", 1, Vector2i(6, 5))
    var g = _make_game([v, enemy])
    assert_false(combat.start_attack(g, 1, 2))


func test_start_attack_valid_installs_state():
    var a = _ent(1, "soldier", 0, Vector2i(5, 5))
    var b = _ent(2, "soldier", 1, Vector2i(6, 5))
    var g = _make_game([a, b])
    assert_true(combat.start_attack(g, 1, 2))
    assert_true(combat.is_attacking(1))


func test_adjacent_soldiers_one_second_damage():
    # AC-14: after TICK_HZ ticks, target hp == max_hp - damage_per_sec.
    var a = _ent(1, "soldier", 0, Vector2i(5, 5))
    var b = _ent(2, "soldier", 1, Vector2i(6, 5))
    var g = _make_game([a, b])
    combat.start_attack(g, 1, 2)
    for i in range(Contract.TICK_HZ):
        combat.tick_combat(g)
    assert_eq(b.hp, 60 - 8)


func test_target_killed_removed_from_entities():
    var a = _ent(1, "soldier", 0, Vector2i(5, 5))
    var b = _ent(2, "soldier", 1, Vector2i(6, 5), 5)
    var g = _make_game([a, b])
    combat.start_attack(g, 1, 2)
    for i in range(Contract.TICK_HZ * 2):
        combat.tick_combat(g)
        if not g.entities.has(b):
            break
    assert_false(g.entities.has(b))


func test_all_attackers_cleared_when_target_dies():
    var a1 = _ent(1, "soldier", 0, Vector2i(5, 5))
    var a2 = _ent(2, "soldier", 0, Vector2i(7, 5))
    var target = _ent(3, "soldier", 1, Vector2i(6, 5), 5)
    var g = _make_game([a1, a2, target])
    combat.start_attack(g, 1, 3)
    combat.start_attack(g, 2, 3)
    for i in range(Contract.TICK_HZ * 2):
        combat.tick_combat(g)
        if not g.entities.has(target):
            break
    assert_false(g.entities.has(target))
    assert_false(combat.is_attacking(1))
    assert_false(combat.is_attacking(2))


func test_out_of_range_attacker_issues_move():
    var a = _ent(1, "archer", 0, Vector2i(0, 0))
    var b = _ent(2, "soldier", 1, Vector2i(15, 15))
    var g = _make_game([a, b])
    combat.start_attack(g, 1, 2)
    combat.tick_combat(g)
    assert_true(Pathfinding.is_moving(1))
    var entry = Pathfinding._move_state[1]
    var path: Array = entry["path"]
    assert_eq(path[path.size() - 1], Vector2i(15, 15))


func test_cancel_attack_clears_state():
    var a = _ent(1, "soldier", 0, Vector2i(5, 5))
    var b = _ent(2, "soldier", 1, Vector2i(6, 5))
    var g = _make_game([a, b])
    combat.start_attack(g, 1, 2)
    combat.cancel_attack(1)
    assert_false(combat.is_attacking(1))
    combat.cancel_attack(999)  # idempotent no-op


func test_archer_in_range_does_damage():
    # Chebyshev = 4, range = 5
    var a = _ent(1, "archer", 0, Vector2i(5, 5))
    var b = _ent(2, "soldier", 1, Vector2i(9, 8))
    var g = _make_game([a, b])
    combat.start_attack(g, 1, 2)
    for i in range(Contract.TICK_HZ):
        combat.tick_combat(g)
    assert_eq(b.hp, 60 - 5)
