---
leaf_id: leaf-03
spec_file: SPEC_GODOT.md
spec_lines: 96-125
test_file: godot/tests/test_entities.gd
impl_file: godot/sim/entities.gd
contract_imports:
  - sim.contract.Entity
  - sim.contract.Game
do_not_edit:
  - godot/sim/contract.gd
  - godot/tests/test_contract.gd
  - godot/sim/map_gen.gd
  - godot/tests/test_map_gen.gd
  - godot/sim/walls.gd
  - godot/tests/test_walls.gd
  - godot/sim/pathfinding.gd
  - godot/tests/test_pathfinding.gd
  - godot/sim/visibility.gd
  - godot/tests/test_visibility.gd
  - godot/sim/gather.gd
  - godot/tests/test_gather.gd
  - godot/sim/combat.gd
  - godot/tests/test_combat.gd
  - godot/sim/building.gd
  - godot/tests/test_building.gd
  - godot/sim/commands.gd
  - godot/tests/test_commands.gd
  - godot/sim/ai.gd
  - godot/tests/test_ai.gd
  - godot/sim/game.gd
  - godot/tests/test_game.gd
  - sim/**
  - tests/**
  - _balance/**
  - briefs/**
  - SPEC.md
  - SPEC_GODOT.md
  - .claude-swarm.toml
  - briefs_godot/**
  - GODOT_PORT_PROGRESS.md
  - godot/project.godot
  - godot/scenes/**
  - godot/scripts/**
  - godot/addons/**
  - godot/tests/test_umbrella.gd
  - godot/tests/fixtures/**
  - app/**
  - assets/**
impl_line_budget: 180
test_assertion_budget: 22
wave: 1
---

## Task

Port `sim/entities.py` (154 lines) to GDScript at `godot/sim/entities.gd` per SPEC_GODOT.md lines 96-125 (AC-46, AC-50).

Provide these public functions matching the Python signatures:

1. `get_stats(kind: String) -> Dictionary` — returns a Dictionary with keys `hp`, `max_hp`, `sight_tiles`, `speed_tiles_per_sec`, `damage_per_sec`, `attack_range_tiles`. Values mirror the `STATS` table in `sim/entities.py`. Default sentinel values for non-applicable fields (e.g., a tree has `speed_tiles_per_sec = 0.0`, `damage_per_sec = 0.0`). Read `sim/entities.py` for the exact numbers; do NOT alter any value.

2. `spawn_unit(game: Game, kind: String, owner: int, pos: Vector2i) -> Entity` — creates a new `Entity` with a fresh `entity_id` (one past max existing id, or 0 if empty), appends to `game.entities`, returns it. `hp = max_hp = get_stats(kind).max_hp`. Asserts `kind in ["villager", "soldier", "archer", "scout"]`.

3. `spawn_building(game: Game, kind: String, owner: int, pos: Vector2i) -> Entity` — same as `spawn_unit` but asserts `kind in ["town_center", "house", "barracks", "wall", "gate"]`.

4. `is_unit(entity: Entity) -> bool` — true iff `entity.kind` is a unit kind.

5. `is_building(entity: Entity) -> bool` — true iff `entity.kind` is a building kind.

6. `is_resource(entity: Entity) -> bool` — true iff `entity.kind in ["tree", "gold_mine"]`.

All stats values must match `sim/entities.py` exactly. Read the Python file. Any divergence is a parity bug.

## Acceptance

Run `"C:/Users/Westley Yarlott/Downloads/Godot_v4.6.3-stable_win64.exe" --headless --path godot/ -s addons/gut/gut_cmdln.gd -gtest=res://tests/test_entities.gd -gexit` for this test file. Confirm RED. Implement in `godot/sim/entities.gd` only. Confirm GREEN. Write your final files to `.swarm/pending/leaf-03/`. Stop.

Tests you must include:
- `get_stats("villager").hp == 25` and `max_hp == 25`.
- `get_stats("soldier").damage_per_sec == 8.0` and `attack_range_tiles == 1`.
- `get_stats("archer").damage_per_sec == 5.0` and `attack_range_tiles == 5`.
- `get_stats("scout").sight_tiles == 10` and `speed_tiles_per_sec == 4.0`.
- `get_stats("town_center").max_hp == 800` and `sight_tiles == 8`.
- `get_stats("house").max_hp == 200` and `sight_tiles == 3`.
- `get_stats("barracks").max_hp == 500` and `sight_tiles == 5`.
- `get_stats("wall").max_hp == 200` and `damage_per_sec == 0.0`.
- `spawn_unit(game, "villager", 0, Vector2i(5, 5))` returns an Entity whose `entity_id` is 0 in a fresh game, `kind == "villager"`, `hp == 25`, `max_hp == 25`. A second call gets `entity_id == 1`.
- `spawn_building(game, "barracks", 1, Vector2i(70, 28))` returns an Entity owned by player 1 with `kind == "barracks"`, `hp == 500`.
- `is_unit` / `is_building` / `is_resource` classify correctly for one entity of each kind (3 assertions).
- `spawn_unit(game, "house", ...)` triggers an assert/error (use GUT's `assert_eq(gut.get_logger().get_errors().size() >= 1, true)` or skip if assertion catching is brittle).

## Escalation triggers

Stop and report to the parent if:
- A type the test imports is not in `contract_imports`.
- The Python `sim/entities.py` references stats that disagree with `SPEC.md` § 6 — escalate; the parent reconciles which source is canonical.
- The impl would need to edit a file in `do_not_edit`.
- Impl approaches `impl_line_budget` (180) with assertions still failing.

## Assumption log

If at any point you inferred something not specified, write it to `briefs_godot/leaf-03.ASSUMPTIONS.md` before committing. Likely inferences: GDScript representation for "no stat" (0 vs null), exact behavior on duplicate `entity_id` (Python doesn't guard against this — match the Python sloppiness).
