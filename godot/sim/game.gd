## Tick orchestrator + new_game factory + scripted command source.
##
## GDScript port of `sim/game.py` per SPEC_GODOT.md AC-53, AC-54, AC-72, AC-73
## and SPEC.md §9 + AC-35..AC-37. Late-binds every sibling via `load()` per
## AC-49. Entry point is `tick_game(game, inputs)`; the `Game.tick()` stub in
## `contract.gd` is intentionally left as push_error (GDScript has no
## monkey-patching) — callers must invoke `tick_game` directly.

extends RefCounted

const Contract = preload("res://sim/contract.gd")
const MapGen = preload("res://sim/map_gen.gd")


# -----------------------------------------------------------------------
# Late-bound sibling loader. Returns the loaded GDScript or null when the
# sibling has not landed yet — every call site null-guards so partial
# cascades don't crash this leaf's narrow unit tests.
# -----------------------------------------------------------------------
static func _load(path: String):
    if not ResourceLoader.exists(path):
        return null
    return load(path)


# -----------------------------------------------------------------------
# Factory
# -----------------------------------------------------------------------
static func new_game(seed_value: int = 42, num_players: int = Contract.NUM_PLAYERS) -> Contract.Game:
    var g: Contract.Game = Contract.Game.new()
    g.players = []
    for i in range(num_players):
        var p: Contract.Player = Contract.Player.new()
        p.player_id = i
        p.wood = Contract.START_WOOD
        p.gold = Contract.START_GOLD
        p.pop_cap = Contract.POP_CAP_START
        p.fog_cheat = false
        g.players.append(p)
    g.entities = []
    g.map_ = MapGen.generate_map(seed_value)
    g.tick_count = 0
    g.over = false
    g.winner = null
    g.visibility = []
    g.explored_snapshots = []

    MapGen.place_starting_entities(g, seed_value)

    var vis = _load("res://sim/visibility.gd")
    if vis != null:
        vis.init_visibility(g)
        vis.recompute_visibility(g)
    return g


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------
static func _sweep_dead_entities(game: Contract.Game) -> void:
    var keep: Array = []
    for e in game.entities:
        if e.hp > 0:
            keep.append(e)
    game.entities = keep


static func _check_winner(game: Contract.Game) -> void:
    if game.over:
        return
    var tc_owners: Dictionary = {}
    for e in game.entities:
        if e.kind == "town_center":
            tc_owners[e.owner] = true
    var surviving: Array = []
    for p in game.players:
        if tc_owners.has(p.player_id):
            surviving.append(p.player_id)
    if surviving.size() <= 1:
        if surviving.size() == 1:
            game.winner = surviving[0]
        else:
            # Both TCs gone same tick: lower player_id wins (mirrors Python).
            var lowest: int = game.players[0].player_id
            for p in game.players:
                if p.player_id < lowest:
                    lowest = p.player_id
            game.winner = lowest
        game.over = true


# -----------------------------------------------------------------------
# Tick orchestrator (SPEC.md §9)
# -----------------------------------------------------------------------
static func tick_game(game: Contract.Game, inputs: Array) -> void:
    # 1. Bail if already over (AC-37) — do NOT increment tick_count.
    if game.over:
        return

    # 2. Apply commands.
    var commands = _load("res://sim/commands.gd")
    if commands != null:
        if commands.has_method("apply_commands"):
            commands.apply_commands(game, inputs)
        elif commands.has_method("apply_command"):
            for cmd in inputs:
                commands.apply_command(game, cmd)

    # 3. Movement step.
    var pathfinding = _load("res://sim/pathfinding.gd")
    if pathfinding != null:
        pathfinding.tick_movement(game)

    # 4. Gather.
    var gather = _load("res://sim/gather.gd")
    if gather != null:
        gather.tick_gather(game)

    # 5. Construction + training.
    var building = _load("res://sim/building.gd")
    if building != null:
        building.tick_construction(game)

    # 6. Combat.
    var combat = _load("res://sim/combat.gd")
    if combat != null:
        combat.tick_combat(game)

    # Training after combat (Python orders construction, training, combat;
    # per brief task list: construction -> combat -> training).
    if building != null:
        building.tick_training(game)

    # 7. Sweep entities zeroed by direct hp manipulation.
    _sweep_dead_entities(game)

    # 8. Recompute fog of war.
    var visibility = _load("res://sim/visibility.gd")
    if visibility != null:
        visibility.recompute_visibility(game)

    # 9. Win condition.
    _check_winner(game)

    # 10. Increment tick counter.
    game.tick_count += 1


# -----------------------------------------------------------------------
# Scripted command source (umbrella helper). Default = [].
# -----------------------------------------------------------------------
static func scripted_player_commands(_game: Contract.Game, _player_id: int, _tick: int) -> Array:
    return []
