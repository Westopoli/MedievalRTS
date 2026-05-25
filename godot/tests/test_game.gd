## Tests for godot/sim/game.gd per leaf-12 brief.
##
## Most tests exercise the orchestrator with stubbed siblings (the late-bind
## loader gracefully no-ops when a sibling .gd is absent). The AC-72 parity
## test requires ALL siblings landed (commands, pathfinding, gather, building,
## combat, visibility); if any are missing it is marked pending.

extends GutTest

const Contract = preload("res://sim/contract.gd")
const Game = preload("res://sim/game.gd")

const _SIBLING_PATHS := [
    "res://sim/commands.gd",
    "res://sim/pathfinding.gd",
    "res://sim/gather.gd",
    "res://sim/building.gd",
    "res://sim/combat.gd",
    "res://sim/visibility.gd",
]


static func _siblings_ready() -> bool:
    for p in _SIBLING_PATHS:
        if not ResourceLoader.exists(p):
            return false
    return true


# -----------------------------------------------------------------------
# new_game shape
# -----------------------------------------------------------------------

func test_new_game_returns_two_players():
    var g = Game.new_game(42)
    assert_eq(g.players.size(), 2)
    assert_eq(g.players[0].wood, Contract.START_WOOD)
    assert_eq(g.players[1].gold, Contract.START_GOLD)
    assert_eq(g.players[0].pop_cap, Contract.POP_CAP_START)


func test_new_game_map_dimensions():
    var g = Game.new_game(42)
    assert_eq(g.map_.width, 80)
    assert_eq(g.map_.height, 60)


func test_new_game_has_two_tcs_at_expected_tiles():
    var g = Game.new_game(42)
    var tcs: Array = []
    for e in g.entities:
        if e.kind == "town_center":
            tcs.append(e)
    assert_eq(tcs.size(), 2)
    var positions: Array = [tcs[0].pos, tcs[1].pos]
    assert_true(positions.has(Vector2i(10, 30)))
    assert_true(positions.has(Vector2i(70, 30)))


func test_new_game_five_villagers_per_player():
    var g = Game.new_game(42)
    var v0 := 0
    var v1 := 0
    for e in g.entities:
        if e.kind == "villager":
            if e.owner == 0:
                v0 += 1
            elif e.owner == 1:
                v1 += 1
    assert_eq(v0, 5)
    assert_eq(v1, 5)


func test_new_game_tick_count_zero_and_not_over():
    var g = Game.new_game(42)
    assert_eq(g.tick_count, 0)
    assert_eq(g.over, false)
    assert_eq(g.winner, null)


# -----------------------------------------------------------------------
# Visibility shape (only when visibility.gd exists, which it does)
# -----------------------------------------------------------------------

func test_new_game_visibility_shape_2x80x60():
    if not ResourceLoader.exists("res://sim/visibility.gd"):
        pending("visibility.gd sibling not landed")
        return
    var g = Game.new_game(42)
    assert_eq(g.visibility.size(), 2)
    assert_eq(g.visibility[0].size(), 80)
    assert_eq(g.visibility[0][0].size(), 60)


func test_p0_tc_tile_visible_after_init():
    if not ResourceLoader.exists("res://sim/visibility.gd"):
        pending("visibility.gd sibling not landed")
        return
    var g = Game.new_game(42)
    assert_eq(g.visibility[0][10][30], "visible")


# -----------------------------------------------------------------------
# tick_game basic behavior
# -----------------------------------------------------------------------

func test_tick_game_increments_tick_count():
    var g = Game.new_game(42)
    Game.tick_game(g, [])
    assert_eq(g.tick_count, 1)
    Game.tick_game(g, [])
    assert_eq(g.tick_count, 2)


# -----------------------------------------------------------------------
# Win condition (AC-35..AC-37)
# -----------------------------------------------------------------------

func test_win_when_p1_tc_dies(): # AC-35
    var g = Game.new_game(42)
    # Kill P1's TC by zeroing hp; sweep + winner check happen inside tick.
    for e in g.entities:
        if e.kind == "town_center" and e.owner == 1:
            e.hp = 0
    Game.tick_game(g, [])
    assert_eq(g.over, true)
    assert_eq(g.winner, 0)


func test_tick_count_frozen_after_over(): # AC-37
    var g = Game.new_game(42)
    g.over = true
    var t_before: int = g.tick_count
    Game.tick_game(g, [])
    assert_eq(g.tick_count, t_before)


func test_both_tcs_dead_same_tick_winner_zero():
    var g = Game.new_game(42)
    for e in g.entities:
        if e.kind == "town_center":
            e.hp = 0
    Game.tick_game(g, [])
    assert_eq(g.over, true)
    assert_eq(g.winner, 0)


# -----------------------------------------------------------------------
# scripted_player_commands default
# -----------------------------------------------------------------------

func test_train_villager_command_spawns_unit():
    if not (ResourceLoader.exists("res://sim/commands.gd")
            and ResourceLoader.exists("res://sim/building.gd")):
        pending("train test requires commands.gd + building.gd siblings")
        return
    var g = Game.new_game(42)
    var tc_id := -1
    for e in g.entities:
        if e.kind == "town_center" and e.owner == 0:
            tc_id = e.entity_id
            break
    var cmd: Contract.Command = Contract.Command.new()
    cmd.kind = "train"
    cmd.issuing_player = 0
    cmd.building_id = tc_id
    cmd.unit_kind = "villager"
    var v_before := 0
    for e in g.entities:
        if e.kind == "villager" and e.owner == 0:
            v_before += 1
    Game.tick_game(g, [cmd])
    # Train takes ~12s = TICK_HZ*12 ticks; run that many empty ticks
    for _i in range(Contract.TICK_HZ * 12):
        Game.tick_game(g, [])
    var v_after := 0
    for e in g.entities:
        if e.kind == "villager" and e.owner == 0:
            v_after += 1
    assert_gt(v_after, v_before, "train cmd should spawn a new villager")


func test_scripted_player_commands_empty_default():
    var g = Game.new_game(42)
    assert_eq(Game.scripted_player_commands(g, 0, 0).size(), 0)


# -----------------------------------------------------------------------
# AC-72 parity vs Python fixture (gated on full cascade)
# -----------------------------------------------------------------------

func test_ac72_parity_seed42_first600():
    if not _siblings_ready():
        pending("AC-72 parity requires all sibling sim modules merged")
        return
    var fixture_path := "res://tests/fixtures/parity_seed42_first600.csv"
    var f := FileAccess.open(fixture_path, FileAccess.READ)
    assert_not_null(f, "parity fixture missing")
    if f == null:
        return

    # Build expected: tick -> {entity_id -> hp}
    var expected: Dictionary = {}
    var header_skipped := false
    while not f.eof_reached():
        var line := f.get_line().strip_edges()
        if line == "":
            continue
        if not header_skipped:
            header_skipped = true
            continue
        var parts := line.split(",")
        # Columns: tick,entity_id,kind,owner,pos_x,pos_y,hp
        var t := int(parts[0])
        var eid := int(parts[1])
        var hp := int(parts[6])
        if not expected.has(t):
            expected[t] = {}
        expected[t][eid] = hp
    f.close()

    var g = Game.new_game(42)
    var max_diffs := 5
    var diffs := 0
    for t in range(600):
        Game.tick_game(g, [])
        var exp_row: Dictionary = expected.get(t, {})
        var actual: Dictionary = {}
        for e in g.entities:
            actual[e.entity_id] = e.hp
        for eid in exp_row.keys():
            if not actual.has(eid):
                diffs += 1
                if diffs <= max_diffs:
                    gut.p("missing entity %d at tick %d" % [eid, t])
                continue
            if actual[eid] != exp_row[eid]:
                diffs += 1
                if diffs <= max_diffs:
                    gut.p("hp mismatch tick=%d eid=%d expected=%d actual=%d"
                        % [t, eid, exp_row[eid], actual[eid]])
    assert_eq(diffs, 0, "AC-72: parity drift vs Python fixture")
