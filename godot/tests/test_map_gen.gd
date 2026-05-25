## GUT tests for godot/sim/map_gen.gd per SPEC.md AC-28..AC-34 and
## SPEC_GODOT.md AC-51, AC-52.

extends GutTest

const Contract = preload("res://sim/contract.gd")
const MapGen = preload("res://sim/map_gen.gd")


func _cheb(a: Vector2i, b: Vector2i) -> int:
    return max(abs(a.x - b.x), abs(a.y - b.y))


func _new_game_with_map(seed_v: int) -> Contract.Game:
    var g: Contract.Game = Contract.Game.new()
    g.map_ = MapGen.generate_map(seed_v)
    g.entities = []
    return g


# AC-28 / AC-51: determinism — same seed yields same terrain.
func test_ac28_determinism():
    var a := MapGen.generate_map(42)
    var b := MapGen.generate_map(42)
    assert_eq(a.terrain, b.terrain)


# AC-28: map dimensions match contract constants.
func test_ac28_dimensions():
    var m := MapGen.generate_map(42)
    assert_eq(m.width, Contract.MAP_W)
    assert_eq(m.height, Contract.MAP_H)


# AC-29: exactly two town_center entities at the TC anchors, owners 0/1.
func test_ac29_town_centers():
    var g := _new_game_with_map(42)
    MapGen.place_starting_entities(g, 42)
    var tcs: Array = []
    for e in g.entities:
        if e.kind == "town_center":
            tcs.append(e)
    assert_eq(tcs.size(), 2)
    var by_owner := {}
    for e in tcs:
        by_owner[e.owner] = e.pos
    assert_eq(by_owner.get(0), Vector2i(10, 30))
    assert_eq(by_owner.get(1), Vector2i(70, 30))


# AC-30: tree count per side in [20, 30]; every tree within Chebyshev 12 of its TC.
func test_ac30_trees_per_side():
    var m := MapGen.generate_map(42)
    var p0_trees := 0
    var p1_trees := 0
    var all_within := true
    for x in range(m.width):
        for y in range(m.height):
            if m.terrain[x][y] == "tree":
                var pos := Vector2i(x, y)
                var d0 := _cheb(pos, Vector2i(10, 30))
                var d1 := _cheb(pos, Vector2i(70, 30))
                if d0 <= 12:
                    p0_trees += 1
                    if d0 > 12:
                        all_within = false
                elif d1 <= 12:
                    p1_trees += 1
                else:
                    all_within = false
    assert_true(p0_trees >= 20 and p0_trees <= 30, "p0 trees=%d" % p0_trees)
    assert_true(p1_trees >= 20 and p1_trees <= 30, "p1 trees=%d" % p1_trees)
    assert_true(all_within)


# AC-31: exactly 2 gold mines per side; each within Chebyshev 10 of its TC.
func test_ac31_gold_mines_per_side():
    var m := MapGen.generate_map(42)
    var p0_mines := 0
    var p1_mines := 0
    for x in range(m.width):
        for y in range(m.height):
            if m.terrain[x][y] == "gold_mine":
                var pos := Vector2i(x, y)
                if _cheb(pos, Vector2i(10, 30)) <= 10:
                    p0_mines += 1
                elif _cheb(pos, Vector2i(70, 30)) <= 10:
                    p1_mines += 1
    assert_eq(p0_mines, 2)
    assert_eq(p1_mines, 2)


# AC-32: 5 villagers per player, each Chebyshev 1 of its TC, no overlap.
func test_ac32_villagers():
    var g := _new_game_with_map(42)
    MapGen.place_starting_entities(g, 42)
    var p0_v: Array = []
    var p1_v: Array = []
    for e in g.entities:
        if e.kind == "villager":
            if e.owner == 0:
                p0_v.append(e.pos)
            elif e.owner == 1:
                p1_v.append(e.pos)
    assert_eq(p0_v.size(), 5)
    assert_eq(p1_v.size(), 5)
    var all_adjacent := true
    for p in p0_v:
        if _cheb(p, Vector2i(10, 30)) != 1: all_adjacent = false
    for p in p1_v:
        if _cheb(p, Vector2i(70, 30)) != 1: all_adjacent = false
    assert_true(all_adjacent)
    # No villager overlaps a tree or gold_mine tile.
    var all_grass := true
    for e in g.entities:
        if e.kind == "villager":
            if g.map_.terrain[e.pos.x][e.pos.y] != "grass": all_grass = false
    assert_true(all_grass)


# AC-34: every non-tree, non-gold_mine tile is "grass".
func test_ac34_default_grass():
    var m := MapGen.generate_map(42)
    var bad := 0
    for x in range(m.width):
        for y in range(m.height):
            var t = m.terrain[x][y]
            if t != "grass" and t != "tree" and t != "gold_mine":
                bad += 1
    assert_eq(bad, 0)


# Idempotence: calling place_starting_entities twice does not duplicate.
func test_idempotence():
    var g := _new_game_with_map(42)
    MapGen.place_starting_entities(g, 42)
    var snapshot: Array = []
    for e in g.entities:
        snapshot.append([e.kind, e.owner, e.pos])
    MapGen.place_starting_entities(g, 42)
    var after: Array = []
    for e in g.entities:
        after.append([e.kind, e.owner, e.pos])
    assert_eq(snapshot.size(), after.size())
    assert_eq(snapshot, after)
