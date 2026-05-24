"""Entity stats catalog and factory helpers (leaf-02).

Public surface consumed by sibling leaves:
- ``STATS`` — dict[EntityKind, EntityStats]
- ``EntityStats`` — frozen dataclass, supports attribute access AND
  ``stats["max_hp"]``-style subscript (sibling `sim/building.py` uses both).
- ``spawn_unit(game, kind, owner, pos) -> Entity``
- ``spawn_building(game, kind, owner, pos) -> Entity``
- ``get_stats(kind) -> EntityStats``
- ``is_unit(kind_or_entity) -> bool`` — accepts either a kind string or an
  ``Entity`` (sibling `sim/building.py:_player_unit_count` calls with Entity).
- ``is_building(kind_or_entity) -> bool`` — same.

See SPEC.md §6 (lines 62-105).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from sim.contract import Entity, EntityKind, Game


# ---------------------------------------------------------------------------
# EntityStats record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EntityStats:
    """Immutable per-kind stats record.

    Supports both attribute access (``stats.max_hp``) and subscript access
    (``stats["max_hp"]``) so sibling leaves authored against either style
    keep working.
    """

    max_hp: int
    sight: int
    damage_per_sec: int
    attack_range_tiles: int
    speed_tiles_per_sec: float

    def __getitem__(self, key: str):
        # Map a couple of legacy short keys ("hp") used by stub fixtures.
        if key == "hp":
            return self.max_hp
        return getattr(self, key)

    def __contains__(self, key: str) -> bool:
        return key in {"max_hp", "hp", "sight", "damage_per_sec",
                       "attack_range_tiles", "speed_tiles_per_sec"}


# ---------------------------------------------------------------------------
# STATS table — values come from SPEC.md §6.
# ---------------------------------------------------------------------------

STATS: dict[str, EntityStats] = {
    # Units
    "villager": EntityStats(max_hp=25, sight=5, damage_per_sec=0,
                            attack_range_tiles=0, speed_tiles_per_sec=2.0),
    "soldier":  EntityStats(max_hp=60, sight=4, damage_per_sec=8,
                            attack_range_tiles=1, speed_tiles_per_sec=2.0),
    "archer":   EntityStats(max_hp=35, sight=7, damage_per_sec=5,
                            attack_range_tiles=5, speed_tiles_per_sec=2.0),
    "scout":    EntityStats(max_hp=30, sight=10, damage_per_sec=0,
                            attack_range_tiles=0, speed_tiles_per_sec=4.0),
    # Buildings
    "town_center": EntityStats(max_hp=800, sight=8, damage_per_sec=0,
                               attack_range_tiles=0, speed_tiles_per_sec=0),
    "house":       EntityStats(max_hp=100, sight=3, damage_per_sec=0,
                               attack_range_tiles=0, speed_tiles_per_sec=0),
    "barracks":    EntityStats(max_hp=300, sight=4, damage_per_sec=0,
                               attack_range_tiles=0, speed_tiles_per_sec=0),
    "wall":        EntityStats(max_hp=200, sight=0, damage_per_sec=0,
                               attack_range_tiles=0, speed_tiles_per_sec=0),
    "gate":        EntityStats(max_hp=200, sight=0, damage_per_sec=0,
                               attack_range_tiles=0, speed_tiles_per_sec=0),
    # Resources
    "tree":        EntityStats(max_hp=40, sight=0, damage_per_sec=0,
                               attack_range_tiles=0, speed_tiles_per_sec=0),
    "gold_mine":   EntityStats(max_hp=200, sight=0, damage_per_sec=0,
                               attack_range_tiles=0, speed_tiles_per_sec=0),
}


_UNIT_KINDS = frozenset({"villager", "soldier", "archer", "scout"})
_BUILDING_KINDS = frozenset({"town_center", "house", "barracks", "wall", "gate"})


# ---------------------------------------------------------------------------
# Lookups / classification
# ---------------------------------------------------------------------------


def get_stats(kind: EntityKind) -> EntityStats:
    """Return the stats record for ``kind``. Raises KeyError if unknown."""
    return STATS[kind]


def _coerce_kind(x: Union[str, Entity]) -> str:
    if isinstance(x, str):
        return x
    return x.kind


def is_unit(kind_or_entity: Union[EntityKind, Entity]) -> bool:
    """True iff the kind (or entity's kind) is a unit kind."""
    return _coerce_kind(kind_or_entity) in _UNIT_KINDS


def is_building(kind_or_entity: Union[EntityKind, Entity]) -> bool:
    """True iff the kind (or entity's kind) is a building kind."""
    return _coerce_kind(kind_or_entity) in _BUILDING_KINDS


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _next_entity_id(game: Game) -> int:
    if not game.entities:
        return 0
    return max(e.entity_id for e in game.entities) + 1


def _spawn(game: Game, kind: EntityKind, owner: int,
           pos: tuple[int, int]) -> Entity:
    stats = STATS[kind]
    e = Entity(
        entity_id=_next_entity_id(game),
        kind=kind,
        owner=owner,
        pos=pos,
        hp=stats.max_hp,
        max_hp=stats.max_hp,
    )
    game.entities.append(e)
    return e


def spawn_unit(game: Game, kind: EntityKind, owner: int,
               pos: tuple[int, int]) -> Entity:
    """Create a unit entity of ``kind`` and append it to ``game.entities``."""
    return _spawn(game, kind, owner, pos)


def spawn_building(game: Game, kind: EntityKind, owner: int,
                   pos: tuple[int, int]) -> Entity:
    """Create a building entity of ``kind`` and append it to ``game.entities``."""
    return _spawn(game, kind, owner, pos)
