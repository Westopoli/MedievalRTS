"""Shared type contract for the Medieval RTS sim.

This file is the ONLY module from which sibling sim leaves may import shared
types and constants. See SPEC.md §14. Editing this file is a parent-only
action — leaves that need a new shared symbol must escalate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


# ---------------------------------------------------------------------------
# Literal kinds
# ---------------------------------------------------------------------------

EntityKind = Literal[
    "villager", "soldier", "archer", "scout",
    "town_center", "house", "barracks", "wall", "gate",
    "tree", "gold_mine",
]
ResourceKind = Literal["wood", "gold"]
CommandKind = Literal["move", "attack", "gather", "build", "train", "stop"]
TerrainKind = Literal["grass", "tree", "gold_mine"]
VisibilityState = Literal["unseen", "explored", "visible"]


# ---------------------------------------------------------------------------
# Tunables / sizing constants
# ---------------------------------------------------------------------------

TILE_SIZE = 64
MAP_W = 80
MAP_H = 60
TICK_HZ = 30
POP_CAP_START = 5
POP_CAP_MAX = 50
CARRY_CAP = 10
START_WOOD = 300
START_GOLD = 150
CAMERA_SCROLL_SPEED = 800  # px/s; frontend-only constant

NUM_PLAYERS = 2  # v0; sim is N-player capable, this is just the v0 default


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Command:
    """A single per-tick player intent. `issuing_player` keys authority + fog."""

    kind: CommandKind
    issuing_player: int = 0
    entity_id: int = -1
    target_tile: tuple[int, int] | None = None
    target_entity_id: int | None = None
    resource_node_id: int | None = None
    building_kind: EntityKind | None = None
    unit_kind: EntityKind | None = None
    building_id: int | None = None


@dataclass
class Entity:
    entity_id: int
    kind: EntityKind
    owner: int
    pos: tuple[int, int]
    hp: int
    max_hp: int
    carrying: ResourceKind | None = None
    carry_amount: int = 0


@dataclass
class Player:
    player_id: int
    wood: int
    gold: int
    pop_cap: int
    fog_cheat: bool = False  # AC-22: opt-in waiver of fog gate for this player


@dataclass
class BuildingSnapshot:
    """Last-seen state of an enemy building visible while a tile was VISIBLE.

    Persists in EXPLORED tiles for the observing player (AC-19).
    """

    entity_id: int
    kind: EntityKind
    owner: int
    pos: tuple[int, int]
    hp_last_seen: int


@dataclass
class Map:
    width: int
    height: int
    terrain: list[list[TerrainKind]]


@dataclass
class Game:
    players: list[Player]
    entities: list[Entity]
    map: Map
    tick_count: int = 0
    over: bool = False
    winner: int | None = None
    # visibility[player_id][x][y] -> VisibilityState
    visibility: list[list[list[VisibilityState]]] = field(default_factory=list)
    # per-player last-seen building snapshots, keyed by entity_id
    explored_snapshots: list[dict[int, BuildingSnapshot]] = field(default_factory=list)

    def tick(self, inputs: list[Command]) -> None:
        """Advance the world by 1/TICK_HZ s. Implemented in sim/game.py."""
        raise NotImplementedError
