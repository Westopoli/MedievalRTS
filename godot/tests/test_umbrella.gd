## Umbrella acceptance test for the Godot port wave 1.
##
## Mirrors `tests/test_umbrella.py` end-state plus the AC-72 parity check
## against `godot/tests/fixtures/parity_seed42_first600.csv`. MUST be RED
## before any leaf spawns — relies on every sim module landing first.
##
## Run:
##   "C:/Users/Westley Yarlott/Downloads/Godot_v4.6.3-stable_win64.exe" \
##     --headless --path godot/ \
##     -s addons/gut/gut_cmdln.gd \
##     -gtest=res://tests/test_umbrella.gd -gexit

extends GutTest

const Contract = preload("res://sim/contract.gd")
const GameMod = preload("res://sim/game.gd")
const Visibility = preload("res://sim/visibility.gd")
const Commands = preload("res://sim/commands.gd")
const AI = preload("res://sim/ai.gd")

const FIXTURE_PATH = "res://tests/fixtures/parity_seed42_first600.csv"

# -----------------------------------------------------------------------
# Basic new_game shape
# -----------------------------------------------------------------------

func test_new_game_dims_and_tcs():
    var g = GameMod.new_game(42)
    assert_eq(g.map_.width, 80)
    assert_eq(g.map_.height, 60)
    var tcs = []
    for e in g.entities:
        if e.kind == "town_center":
            tcs.append(e)
    assert_eq(tcs.size(), 2)
    var p0_tc = null
    var p1_tc = null
    for tc in tcs:
        if tc.owner == 0:
            p0_tc = tc
        elif tc.owner == 1:
            p1_tc = tc
    assert_eq(p0_tc.pos, Vector2i(10, 30))
    assert_eq(p1_tc.pos, Vector2i(70, 30))


func test_new_game_villagers_per_player():
    var g = GameMod.new_game(42)
    var p0_v = 0
    var p1_v = 0
    for e in g.entities:
        if e.kind == "villager":
            if e.owner == 0:
                p0_v += 1
            elif e.owner == 1:
                p1_v += 1
    assert_eq(p0_v, 5)
    assert_eq(p1_v, 5)


func test_new_game_visibility_shape():
    var g = GameMod.new_game(42)
    assert_eq(g.visibility.size(), 2)
    assert_eq(g.visibility[0].size(), 80)
    assert_eq(g.visibility[0][0].size(), 60)


# -----------------------------------------------------------------------
# Symmetric fog spot-checks (SPEC.md AC-15..AC-22)
# -----------------------------------------------------------------------

func test_fog_symmetric_at_tick_100():
    var g = GameMod.new_game(42)
    for _t in range(100):
        g.tick([])
    # P0 sees own base, not enemy base.
    assert_eq(g.visibility[0][10][30], "visible")
    assert_ne(g.visibility[0][70][30], "visible")
    # P1 sees own base, not enemy base.
    assert_eq(g.visibility[1][70][30], "visible")
    assert_ne(g.visibility[1][10][30], "visible")


# -----------------------------------------------------------------------
# Authority + cheat-flag (SPEC.md AC-21, AC-22, AC-27)
# -----------------------------------------------------------------------

func test_command_authority_rejects_cross_owner():
    var g = GameMod.new_game(42)
    # Find a P1-owned entity.
    var p1_entity = null
    for e in g.entities:
        if e.owner == 1:
            p1_entity = e
            break
    var cmd = Contract.Command.new()
    cmd.kind = "move"
    cmd.issuing_player = 0
    cmd.entity_id = p1_entity.entity_id
    cmd.target_tile = Vector2i(11, 30)
    var accepted = Commands.apply_command(g, cmd)
    assert_false(accepted, "P0 cannot command P1 entity")


# -----------------------------------------------------------------------
# AI integration + termination (SPEC.md AC-35..AC-37, SPEC_GODOT.md AC-64)
# -----------------------------------------------------------------------

func test_default_ai_drives_p1_to_economy_by_tick_5400():
    var g = GameMod.new_game(42)
    for t in range(5400):  # 180 sim sec
        var inputs = AI.ai_tick(g, 1, t)
        g.tick(inputs)
        if g.over:
            break
    # P1 must have produced at least 1 barracks AND some military.
    var p1_barracks = 0
    var p1_military = 0
    for e in g.entities:
        if e.owner == 1:
            if e.kind == "barracks":
                p1_barracks += 1
            elif e.kind == "soldier" or e.kind == "archer":
                p1_military += 1
    assert_gte(p1_barracks, 1)
    assert_gte(p1_military, 1)


func test_match_terminates_within_18000_ticks():
    var g = GameMod.new_game(42)
    for t in range(18000):  # 600 sim sec
        var inputs: Array = []
        inputs.append_array(AI.ai_tick(g, 0, t))
        inputs.append_array(AI.ai_tick(g, 1, t))
        g.tick(inputs)
        if g.over:
            break
    assert_true(g.over, "match must end within 18000 ticks")
    assert_true(g.winner == 0 or g.winner == 1, "winner must be 0 or 1")


# -----------------------------------------------------------------------
# Parity vs Python ground truth (SPEC_GODOT.md AC-72)
# -----------------------------------------------------------------------

func test_parity_against_python_fixture_first_600_ticks():
    var f = FileAccess.open(FIXTURE_PATH, FileAccess.READ)
    assert_not_null(f, "parity fixture missing")
    if f == null:
        return
    var header = f.get_csv_line()  # discard header
    assert_eq(header[0], "tick")
    # Build (tick, eid) -> hp lookup.
    var expected: Dictionary = {}
    while not f.eof_reached():
        var row = f.get_csv_line()
        if row.size() < 7:
            continue
        var key = str(row[0]) + ":" + str(row[1])
        expected[key] = int(row[6])
    f.close()

    # Run sim 600 ticks no inputs.
    var g = GameMod.new_game(42)
    var mismatches = 0
    for t in range(600):
        g.tick([])
        for e in g.entities:
            var key = str(t) + ":" + str(e.entity_id)
            if expected.has(key):
                if expected[key] != e.hp:
                    mismatches += 1
    assert_eq(mismatches, 0, "parity drift: %d hp mismatches in first 600 ticks" % mismatches)
