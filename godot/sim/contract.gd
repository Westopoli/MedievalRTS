## Shared type contract for the MedievalRTS Godot port.
##
## Mirrors `sim/contract.py` (Python sim, commit a6ef4f7+) symbol-for-symbol
## per SPEC_GODOT.md AC-41..AC-45. This file is PARENT-OWNED. Leaves may
## `preload("res://sim/contract.gd")` and reference these symbols; they may
## NOT add, remove, or rename any symbol declared here. Type contract
## changes go through SPEC_GODOT.md + parent edit + re-run swarm-review.
##
## Documented kind member sets (matches Python `Literal[...]` aliases — not
## enforced at runtime per SPEC_GODOT.md AC-42):
##
##   EntityKind:     "villager", "soldier", "archer", "scout",
##                   "town_center", "house", "barracks", "wall", "gate",
##                   "tree", "gold_mine"
##   ResourceKind:   "wood", "gold"
##   CommandKind:    "move", "attack", "gather", "build", "train", "stop"
##   TerrainKind:    "grass", "tree", "gold_mine"
##   VisibilityState: "unseen", "explored", "visible"

extends RefCounted


# -----------------------------------------------------------------------
# Tunable / sizing constants (per SPEC_GODOT.md AC-41)
# -----------------------------------------------------------------------

const TILE_SIZE = 64
const MAP_W = 80
const MAP_H = 60
const TICK_HZ = 30
const POP_CAP_START = 5
const POP_CAP_MAX = 50
const CARRY_CAP = 10
const START_WOOD = 300
const START_GOLD = 150
const CAMERA_SCROLL_SPEED = 800  # px/s; frontend-only constant
const NUM_PLAYERS = 2  # v0 default; sim is N-player capable


# -----------------------------------------------------------------------
# Public Resource subclasses (per SPEC_GODOT.md AC-43)
# -----------------------------------------------------------------------


class Command extends Resource:
    @export var kind: String = ""
    @export var issuing_player: int = 0
    @export var entity_id: int = -1
    # Optional fields default to null (Variant). Setters typed to allow either
    # a concrete value or null per AC-43 mapping.
    @export var target_tile = null  # Vector2i | null
    @export var target_entity_id = null  # int | null
    @export var resource_node_id = null  # int | null
    @export var building_kind = null  # String | null
    @export var unit_kind = null  # String | null
    @export var building_id = null  # int | null


class Entity extends Resource:
    @export var entity_id: int = -1
    @export var kind: String = ""
    @export var owner: int = 0
    @export var pos: Vector2i = Vector2i.ZERO
    @export var hp: int = 0
    @export var max_hp: int = 0
    @export var carrying = null  # String | null ("wood" | "gold")
    @export var carry_amount: int = 0


class Player extends Resource:
    @export var player_id: int = 0
    @export var wood: int = 0
    @export var gold: int = 0
    @export var pop_cap: int = 5
    @export var fog_cheat: bool = false  # AC-22


class BuildingSnapshot extends Resource:
    @export var entity_id: int = -1
    @export var kind: String = ""
    @export var owner: int = 0
    @export var pos: Vector2i = Vector2i.ZERO
    @export var hp_last_seen: int = 0


class Map extends Resource:
    @export var width: int = 0
    @export var height: int = 0
    @export var terrain: Array = []  # Array[Array[String]]


class Game extends Resource:
    @export var players: Array = []  # Array[Player]
    @export var entities: Array = []  # Array[Entity]
    @export var map_: Map = null  # `map` is a GDScript builtin; underscore suffix
    @export var tick_count: int = 0
    @export var over: bool = false
    @export var winner = null  # int | null
    @export var visibility: Array = []  # visibility[player_id][x][y] -> String
    @export var explored_snapshots: Array = []  # Array[Dictionary[int, BuildingSnapshot]]

    func tick(inputs: Array) -> void:
        # Delegate to godot/sim/game.gd::tick_game (parent-wired post-leaf-12).
        var game_mod = load("res://sim/game.gd")
        if game_mod != null and game_mod.has_method("tick_game"):
            game_mod.tick_game(self, inputs)
        else:
            push_error("Game.tick: game.gd not loaded or missing tick_game")
