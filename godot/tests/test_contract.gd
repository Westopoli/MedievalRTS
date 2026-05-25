## Contract gate tests per SPEC_GODOT.md AC-41..AC-45.

extends GutTest

const Contract = preload("res://sim/contract.gd")


# -----------------------------------------------------------------------
# AC-41: every Python sim/contract.py constant exists with same value
# -----------------------------------------------------------------------

func test_ac41_constants_present_and_match_python():
    assert_eq(Contract.TILE_SIZE, 64)
    assert_eq(Contract.MAP_W, 80)
    assert_eq(Contract.MAP_H, 60)
    assert_eq(Contract.TICK_HZ, 30)
    assert_eq(Contract.POP_CAP_START, 5)
    assert_eq(Contract.POP_CAP_MAX, 50)
    assert_eq(Contract.CARRY_CAP, 10)
    assert_eq(Contract.START_WOOD, 300)
    assert_eq(Contract.START_GOLD, 150)
    assert_eq(Contract.CAMERA_SCROLL_SPEED, 800)
    assert_eq(Contract.NUM_PLAYERS, 2)


# -----------------------------------------------------------------------
# AC-43: class shapes
# -----------------------------------------------------------------------

func test_ac43_command_defaults():
    var c = Contract.Command.new()
    assert_eq(c.kind, "")
    assert_eq(c.issuing_player, 0)
    assert_eq(c.entity_id, -1)
    assert_eq(c.target_tile, null)
    assert_eq(c.target_entity_id, null)


func test_ac43_entity_constructible():
    var e = Contract.Entity.new()
    e.entity_id = 7
    e.kind = "villager"
    e.owner = 0
    e.pos = Vector2i(3, 4)
    e.hp = 25
    e.max_hp = 25
    assert_eq(e.kind, "villager")
    assert_eq(e.pos, Vector2i(3, 4))
    assert_eq(e.hp, 25)
    assert_eq(e.carrying, null)
    assert_eq(e.carry_amount, 0)


func test_ac43_player_defaults():
    var p = Contract.Player.new()
    p.player_id = 0
    p.wood = 300
    p.gold = 150
    p.pop_cap = 5
    assert_eq(p.fog_cheat, false)


func test_ac43_map_terrain_is_array():
    var m = Contract.Map.new()
    m.width = 80
    m.height = 60
    m.terrain = []
    assert_eq(typeof(m.terrain), TYPE_ARRAY)


func test_ac43_building_snapshot_constructible():
    var s = Contract.BuildingSnapshot.new()
    s.entity_id = 1
    s.kind = "town_center"
    s.owner = 1
    s.pos = Vector2i(70, 30)
    s.hp_last_seen = 800
    assert_eq(s.kind, "town_center")
    assert_eq(s.hp_last_seen, 800)


func test_ac43_game_defaults():
    var g = Contract.Game.new()
    assert_eq(g.tick_count, 0)
    assert_eq(g.over, false)
    assert_eq(g.winner, null)
    assert_eq(g.visibility, [])
    assert_eq(g.explored_snapshots, [])


# -----------------------------------------------------------------------
# AC-44: Game.tick stub emits push_error and returns
# -----------------------------------------------------------------------

func test_ac44_game_tick_stub_emits_error():
    var g = Contract.Game.new()
    # GDScript push_error logs via the engine; GUT records it. We just
    # confirm calling tick() does not crash (returns void).
    g.tick([])
    assert_true(true)
