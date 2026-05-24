---
leaf_id: leaf-02
spec_file: SPEC.md
spec_lines: 62-105
test_file: tests/test_entities.py
impl_file: sim/entities.py
contract_imports:
  - sim.contract.Entity
  - sim.contract.Game
do_not_edit:
  - sim/contract.py
  - sim/__init__.py
  - sim/map_gen.py
  - tests/test_map_gen.py
  - sim/walls.py
  - tests/test_walls.py
  - sim/pathfinding.py
  - tests/test_pathfinding.py
  - sim/visibility.py
  - tests/test_visibility.py
  - sim/gather.py
  - tests/test_gather.py
  - sim/combat.py
  - tests/test_combat.py
  - sim/building.py
  - tests/test_building.py
  - sim/commands.py
  - tests/test_commands.py
  - sim/ai.py
  - tests/test_ai.py
  - sim/game.py
  - tests/test_game.py
  - tests/test_umbrella.py
  - tests/conftest.py
  - SPEC.md
  - .claude-swarm.toml
  - briefs/**
  - app/**
  - assets/**
  - "*.tscn"
  - "*.gd"
  - project.godot
impl_line_budget: 180
test_assertion_budget: 20
wave: 1
---

## Task

Implement the entity stats catalog + factory helpers per SPEC.md lines 62-105.

Provide in `sim/entities.py`:

1. A `STATS` constant: a dict keyed by `EntityKind` with values being immutable records (use a frozen dataclass `EntityStats`) carrying the fields: `max_hp: int`, `sight: int` (0 for non-sighted entities), `damage_per_sec: int` (0 for non-combatants), `attack_range_tiles: int` (1 for melee, larger for ranged, 0 for non-combatants), `speed_tiles_per_sec: float` (0 for buildings). Populate exact values from the SPEC table:
   - villager: hp=25, sight=5, dps=0, range=0, speed=2.0
   - soldier: hp=60, sight=4, dps=8, range=1, speed=2.0
   - archer: hp=35, sight=7, dps=5, range=5, speed=2.0
   - scout: hp=30, sight=10, dps=0, range=0, speed=4.0
   - town_center: hp=800, sight=8, dps=0, range=0, speed=0
   - house: hp=100, sight=3, dps=0, range=0, speed=0
   - barracks: hp=300, sight=4, dps=0, range=0, speed=0
   - wall: hp=200, sight=0, dps=0, range=0, speed=0
   - gate: hp=200, sight=0, dps=0, range=0, speed=0
   - tree: hp=40, sight=0, dps=0, range=0, speed=0
   - gold_mine: hp=200, sight=0, dps=0, range=0, speed=0

2. `spawn_unit(game: Game, kind: EntityKind, owner: int, pos: tuple[int, int]) -> Entity` — creates a unit `Entity` with stats from `STATS`, assigns next free `entity_id` (max existing id + 1, or 0 if empty), appends to `game.entities`, returns the entity.

3. `spawn_building(game: Game, kind: EntityKind, owner: int, pos: tuple[int, int]) -> Entity` — same as `spawn_unit` but for building kinds.

4. `get_stats(kind: EntityKind) -> EntityStats` — returns stats record for the kind. Used by sibling leaves.

5. `is_unit(kind: EntityKind) -> bool` and `is_building(kind: EntityKind) -> bool` — classification helpers. Units: villager, soldier, archer, scout. Buildings: town_center, house, barracks, wall, gate. Resources (tree, gold_mine) are neither.

`STATS` and `EntityStats` may be imported by other leaves via `sim.entities` — this leaf's public surface beyond the contract is intentional.

## Acceptance

Run `python -m pytest tests/test_entities.py -x -q`. Confirm RED. Implement in `sim/entities.py` only. Confirm GREEN. Write your final `test_file` and `impl_file` to `.swarm/pending/leaf-02/` mirroring paths.

Tests:
- STATS contains all 11 EntityKind values
- `get_stats("soldier").damage_per_sec == 8` and other spot-checks per the table
- `spawn_unit(g, "villager", 0, (5, 5))` returns an Entity with hp=max_hp=25, owner=0, pos=(5,5)
- Two consecutive `spawn_unit` calls produce distinct, sequential entity_ids
- `is_unit("villager") is True`, `is_unit("house") is False`, `is_building("gate") is True`, `is_unit("tree") is False`

## Escalation triggers

Stop and report to the parent if:
- A type the test imports is not in contract_imports.
- The impl would need to create a new file.
- The impl would need to edit a file in do_not_edit.
- Two sibling assertions seem to require contradictory behavior.
- Impl approaches impl_line_budget with assertions still failing.

## Assumption log

If you inferred any value not specified above, write it to `briefs/leaf-02.ASSUMPTIONS.md`.
