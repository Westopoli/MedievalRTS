---
leaf_id: leaf-05
spec_file: SPEC_GODOT.md
spec_lines: 96-125
test_file: godot/tests/test_pathfinding.gd
impl_file: godot/sim/pathfinding.gd
contract_imports:
  - sim.contract.Entity
  - sim.contract.Game
  - sim.contract.MAP_W
  - sim.contract.MAP_H
  - sim.contract.TICK_HZ
do_not_edit:
  - godot/sim/contract.gd
  - godot/tests/test_contract.gd
  - godot/sim/map_gen.gd
  - godot/tests/test_map_gen.gd
  - godot/sim/entities.gd
  - godot/tests/test_entities.gd
  - godot/sim/walls.gd
  - godot/tests/test_walls.gd
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
impl_line_budget: 220
test_assertion_budget: 22
wave: 1
---

## Task

Port `sim/pathfinding.py` (178 lines) to GDScript at `godot/sim/pathfinding.gd` per SPEC_GODOT.md lines 96-125 (AC-46, AC-47, AC-49, AC-50) and SPEC.md AC-13, AC-23, AC-24.

Implements 8-direction A* + per-tick movement execution.

Provide these public functions matching the Python signatures (per `sim/pathfinding.py`):

1. `find_path(game: Game, start: Vector2i, goal: Vector2i, owner: int) -> Array` — returns an `Array[Vector2i]` of tile waypoints from start to goal exclusive of start, inclusive of goal. Returns empty array if unreachable. Blocking tiles: any tile out of `[0, MAP_W)` × `[0, MAP_H)`, any tile containing a `tree`/`gold_mine`/`town_center`/`house`/`barracks` Entity, OR any tile failing `walls.is_passable_for(game, tile, owner)`. Costs: cardinal step 1.0, diagonal step 1.41. Late-bind `sim.walls.is_passable_for` via `load("res://sim/walls.gd")` inside the function body per SPEC_GODOT.md AC-49.

2. `start_move(game: Game, entity_id: int, target_tile: Vector2i) -> bool` — computes a path, installs movement state in the file-level `_move_state: Dictionary` (key = entity_id, value = `{path: Array[Vector2i], progress: float}` dictionary), returns `true` if a path was found, `false` otherwise. Per SPEC_GODOT.md AC-47 the dict is reset by `reset_module_state()`.

3. `cancel_move(entity_id: int) -> void` — removes the entry from `_move_state` if present. Idempotent.

4. `is_moving(entity_id: int) -> bool` — returns `entity_id in _move_state`.

5. `tick_movement(game: Game) -> void` — advances every entity in `_move_state` by its `speed_tiles_per_sec / TICK_HZ` per call. Late-bind `sim.entities.get_stats` via `load("res://sim/entities.gd")`. When `progress >= 1.0`, consume the next waypoint and snap the entity's `pos` to it; if the new tile is blocked (re-check via the same blocking rules as `find_path`), abort the move and remove from `_move_state`. Removes the entry when the path is empty.

6. `reset_module_state() -> void` — clears `_move_state`. For test isolation per SPEC_GODOT.md AC-47.

The blocking-tile rules MUST match `sim/pathfinding.py` exactly — specifically the `_BLOCKING_BUILDING_KINDS` frozenset (`{"tree", "gold_mine", "town_center", "house", "barracks"}`). Note that `wall` and `gate` are NOT in this set — they are routed through `walls.is_passable_for` instead, which handles the owner-aware gate rule.

## Acceptance

Run `"C:/Users/Westley Yarlott/Downloads/Godot_v4.6.3-stable_win64.exe" --headless --path godot/ -s addons/gut/gut_cmdln.gd -gtest=res://tests/test_pathfinding.gd -gexit` for this test file. Confirm RED. Implement in `godot/sim/pathfinding.gd` only. Confirm GREEN. Write your final files to `.swarm/pending/leaf-05/`. Stop.

Tests must mirror `tests/test_pathfinding.py` (10 tests). At minimum:
- Diagonal path on an empty map from `(0,0)` to `(5,5)` has length 5 and last waypoint == `(5,5)`.
- Path to an out-of-bounds tile returns empty.
- Path to a tile occupied by a tree returns empty.
- Walls (tiles where `is_passable_for` returns false for owner=0) force the path to deviate around them — `_wall_blocks` test fixture pattern can be replicated by monkeypatching `sim.walls.is_passable_for` via GUT's `partial_double` or by injecting a controllable test stub at `load`-time.
- A gate at `(3,3)` with `owner=0` admits player 0 but not player 1.
- `start_move(g, 42, Vector2i(5,5))` returns `true` for a reachable goal, installs state, and `is_moving(42) == true`.
- After enough `tick_movement` calls, the entity at `(0,0)` reaches `(5,5)`.
- `start_move` returns `false` for an unreachable goal.
- `cancel_move(42)` clears state; `is_moving(42) == false` after.
- `cancel_move(999)` (no state) is a no-op (no error).

## Escalation triggers

Stop and report to the parent if:
- The A* implementation in `sim/pathfinding.py` uses Python heapq idioms that have no clean GDScript equivalent — escalate before substituting an alternate algorithm (e.g., BFS) that may differ in tie-breaking.
- The test fixture for `is_passable_for` stubbing requires a GUT pattern that contradicts SPEC_GODOT.md AC-49 (late-bind via `load`). Escalate.
- Impl approaches `impl_line_budget` (220) with assertions still failing.

## Assumption log

If at any point you inferred something not specified, write it to `briefs_godot/leaf-05.ASSUMPTIONS.md`. Likely inferences: heap implementation choice (GDScript lacks heapq — likely use a sorted Array with `bsearch_custom` or roll your own), tie-breaking when two nodes have equal `f` score (Python heapq is stable by insertion order; document if you must diverge).
