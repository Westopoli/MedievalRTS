## Wall passability tests per SPEC.md AC-23, AC-24, AC-25 (SPEC_GODOT.md AC-46, AC-50).

extends GutTest

const Contract = preload("res://sim/contract.gd")
const Walls = preload("res://sim/walls.gd")


func _make_game() -> Contract.Game:
    var g = Contract.Game.new()
    g.entities = []
    return g


func _make_entity(kind: String, owner: int, pos: Vector2i, hp: int) -> Contract.Entity:
    var e = Contract.Entity.new()
    e.kind = kind
    e.owner = owner
    e.pos = pos
    e.hp = hp
    e.max_hp = hp if hp > 0 else 100
    return e


# AC-23: empty game has no blockers
func test_empty_game_is_passable():
    var g = _make_game()
    assert_true(Walls.is_passable_for(g, Vector2i(5, 5), 0))


# AC-23: live wall blocks owner
func test_wall_blocks_owner():
    var g = _make_game()
    g.entities.append(_make_entity("wall", 0, Vector2i(5, 5), 100))
    assert_false(Walls.is_passable_for(g, Vector2i(5, 5), 0))


# AC-23: live wall blocks enemy
func test_wall_blocks_enemy():
    var g = _make_game()
    g.entities.append(_make_entity("wall", 0, Vector2i(5, 5), 100))
    assert_false(Walls.is_passable_for(g, Vector2i(5, 5), 1))


# AC-24: gate passable for owner
func test_gate_passable_for_owner():
    var g = _make_game()
    g.entities.append(_make_entity("gate", 0, Vector2i(5, 5), 100))
    assert_true(Walls.is_passable_for(g, Vector2i(5, 5), 0))


# AC-24: gate blocks enemy
func test_gate_blocks_enemy():
    var g = _make_game()
    g.entities.append(_make_entity("gate", 0, Vector2i(5, 5), 100))
    assert_false(Walls.is_passable_for(g, Vector2i(5, 5), 1))


# AC-25: dead wall does not block
func test_dead_wall_is_passable():
    var g = _make_game()
    g.entities.append(_make_entity("wall", 0, Vector2i(5, 5), 0))
    assert_true(Walls.is_passable_for(g, Vector2i(5, 5), 0))


# wall_or_gate_at returns the entity if live wall present
func test_wall_or_gate_at_returns_wall():
    var g = _make_game()
    var w = _make_entity("wall", 0, Vector2i(5, 5), 100)
    g.entities.append(w)
    assert_eq(Walls.wall_or_gate_at(g, Vector2i(5, 5)), w)


# wall_or_gate_at returns null when nothing there
func test_wall_or_gate_at_returns_null_when_empty():
    var g = _make_game()
    assert_eq(Walls.wall_or_gate_at(g, Vector2i(5, 5)), null)


# wall_or_gate_at returns null for dead wall (AC-25)
func test_wall_or_gate_at_returns_null_for_dead_wall():
    var g = _make_game()
    g.entities.append(_make_entity("wall", 0, Vector2i(5, 5), 0))
    assert_eq(Walls.wall_or_gate_at(g, Vector2i(5, 5)), null)
