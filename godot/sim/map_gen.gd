## Deterministic map generation and starting-entity placement.
##
## GDScript port of `sim/map_gen.py` per SPEC_GODOT.md AC-46, AC-50, AC-51,
## AC-52 and SPEC.md AC-28..AC-34. Pure module-level functions; no global
## RNG state. The single `RandomNumberGenerator` instance is created per call.

extends RefCounted

const Contract = preload("res://sim/contract.gd")

const TC0 := Vector2i(10, 30)
const TC1 := Vector2i(70, 30)

const _FORESTS_PER_SIDE := 4
const _TREES_PER_FOREST := 6
const _GOLD_MINES_PER_SIDE := 2
const _TREE_RADIUS := 12
const _GOLD_RADIUS := 10


static func _villager_ring(tc: Vector2i) -> Array:
    var ring: Array = []
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx == 0 and dy == 0:
                continue
            ring.append(Vector2i(tc.x + dx, tc.y + dy))
    return ring


static func _in_bounds(x: int, y: int) -> bool:
    return x >= 0 and x < Contract.MAP_W and y >= 0 and y < Contract.MAP_H


static func _place_cluster_trees(rng: RandomNumberGenerator, terrain: Array,
                                  tc: Vector2i, blocked: Dictionary) -> void:
    var placed_total := 0
    var target := _FORESTS_PER_SIDE * _TREES_PER_FOREST
    var forest_centers: Array = []
    var attempts := 0
    while forest_centers.size() < _FORESTS_PER_SIDE and attempts < 500:
        attempts += 1
        var dx := rng.randi_range(-_TREE_RADIUS + 2, _TREE_RADIUS - 2)
        var dy := rng.randi_range(-_TREE_RADIUS + 2, _TREE_RADIUS - 2)
        var cx := tc.x + dx
        var cy := tc.y + dy
        if not _in_bounds(cx, cy):
            continue
        if max(abs(dx), abs(dy)) < 4:
            continue
        forest_centers.append(Vector2i(cx, cy))

    for fc in forest_centers:
        var placed_in_forest := 0
        var f_attempts := 0
        while placed_in_forest < _TREES_PER_FOREST and f_attempts < 200:
            f_attempts += 1
            var tx: int = fc.x + rng.randi_range(-2, 2)
            var ty: int = fc.y + rng.randi_range(-2, 2)
            if not _in_bounds(tx, ty):
                continue
            var key := Vector2i(tx, ty)
            if blocked.has(key):
                continue
            if terrain[tx][ty] != "grass":
                continue
            if max(abs(tx - tc.x), abs(ty - tc.y)) > _TREE_RADIUS:
                continue
            terrain[tx][ty] = "tree"
            blocked[key] = true
            placed_in_forest += 1
            placed_total += 1
            if placed_total >= target:
                return


static func _place_gold_mines(rng: RandomNumberGenerator, terrain: Array,
                               tc: Vector2i, blocked: Dictionary) -> void:
    var placed := 0
    var attempts := 0
    while placed < _GOLD_MINES_PER_SIDE and attempts < 500:
        attempts += 1
        var dx := rng.randi_range(-_GOLD_RADIUS, _GOLD_RADIUS)
        var dy := rng.randi_range(-_GOLD_RADIUS, _GOLD_RADIUS)
        var gx := tc.x + dx
        var gy := tc.y + dy
        if not _in_bounds(gx, gy):
            continue
        if max(abs(dx), abs(dy)) < 3:
            continue
        var key := Vector2i(gx, gy)
        if blocked.has(key):
            continue
        if terrain[gx][gy] != "grass":
            continue
        terrain[gx][gy] = "gold_mine"
        blocked[key] = true
        placed += 1


static func generate_map(seed_value: int) -> Contract.Map:
    var rng := RandomNumberGenerator.new()
    rng.seed = seed_value

    var terrain: Array = []
    for x in range(Contract.MAP_W):
        var col: Array = []
        for y in range(Contract.MAP_H):
            col.append("grass")
        terrain.append(col)

    var blocked: Dictionary = {}
    for tc in [TC0, TC1]:
        blocked[tc] = true
        for p in _villager_ring(tc):
            blocked[p] = true

    for tc in [TC0, TC1]:
        _place_cluster_trees(rng, terrain, tc, blocked)
        _place_gold_mines(rng, terrain, tc, blocked)

    var m: Contract.Map = Contract.Map.new()
    m.width = Contract.MAP_W
    m.height = Contract.MAP_H
    m.terrain = terrain
    return m


static func place_starting_entities(game: Contract.Game, _seed_value: int) -> void:
    # Idempotence guard (brief leaf-02): if a town_center already exists, no-op.
    for existing in game.entities:
        if existing.kind == "town_center":
            return
    var next_id: int = game.entities.size()

    # Town centers
    var tc0: Contract.Entity = Contract.Entity.new()
    tc0.entity_id = next_id; next_id += 1
    tc0.kind = "town_center"; tc0.owner = 0; tc0.pos = TC0
    tc0.hp = 800; tc0.max_hp = 800
    game.entities.append(tc0)

    var tc1: Contract.Entity = Contract.Entity.new()
    tc1.entity_id = next_id; next_id += 1
    tc1.kind = "town_center"; tc1.owner = 1; tc1.pos = TC1
    tc1.hp = 800; tc1.max_hp = 800
    game.entities.append(tc1)

    # Villagers — 5 per player on adjacent ring, deterministic order
    for pair in [[0, TC0], [1, TC1]]:
        var pid: int = pair[0]
        var tc: Vector2i = pair[1]
        var ring := _villager_ring(tc)
        for i in range(5):
            var v: Contract.Entity = Contract.Entity.new()
            v.entity_id = next_id; next_id += 1
            v.kind = "villager"; v.owner = pid; v.pos = ring[i]
            v.hp = 25; v.max_hp = 25
            game.entities.append(v)

    # Trees + gold mines from terrain
    var terrain: Array = game.map_.terrain
    for x in range(game.map_.width):
        for y in range(game.map_.height):
            var t: String = terrain[x][y]
            if t == "tree":
                var e: Contract.Entity = Contract.Entity.new()
                e.entity_id = next_id; next_id += 1
                e.kind = "tree"; e.owner = -1; e.pos = Vector2i(x, y)
                e.hp = 40; e.max_hp = 40
                game.entities.append(e)
            elif t == "gold_mine":
                var e2: Contract.Entity = Contract.Entity.new()
                e2.entity_id = next_id; next_id += 1
                e2.kind = "gold_mine"; e2.owner = -1; e2.pos = Vector2i(x, y)
                e2.hp = 200; e2.max_hp = 200
                game.entities.append(e2)
