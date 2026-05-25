---
leaf_id: leaf-09
spec_file: SPEC_GODOT.md
spec_lines: 96-125
test_file: godot/tests/test_building.gd
impl_file: godot/sim/building.gd
contract_imports:
  - sim.contract.Entity
  - sim.contract.Game
  - sim.contract.Player
  - sim.contract.POP_CAP_MAX
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
  - godot/sim/pathfinding.gd
  - godot/tests/test_pathfinding.gd
  - godot/sim/visibility.gd
  - godot/tests/test_visibility.gd
  - godot/sim/gather.gd
  - godot/tests/test_gather.gd
  - godot/sim/combat.gd
  - godot/tests/test_combat.gd
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

Port `sim/building.py` (219 lines) to GDScript at `godot/sim/building.gd` per SPEC_GODOT.md lines 96-125 (AC-46, AC-47, AC-49, AC-50) and SPEC.md AC-10 (pop cap), AC-11 (training queue), AC-26 (wall building), and the cost/time tables in SPEC.md § 6.

File-level state per SPEC_GODOT.md AC-47:
- `var _construction: Dictionary = {}` — keys are villager_id, values are dictionaries with fields `kind: String`, `tile: Vector2i`, `progress: int`.
- `var _training: Dictionary = {}` — keys are building_id, values are dictionaries with `unit_kind: String`, `progress: int`.

Top-level constants (mirror Python):
- `const BUILD_COSTS: Dictionary = {"house": [30, 0, 10], "barracks": [80, 0, 15], "wall": [5, 0, 3], "gate": [25, 5, 5]}` — `[wood, gold, time_seconds]`.
- `const TRAIN_COSTS: Dictionary = {"villager": [50, 0, 12, "town_center"], "scout": [30, 20, 10, "town_center"], "soldier": [40, 20, 15, "barracks"], "archer": [25, 35, 18, "barracks"]}` — `[wood, gold, time_seconds, building_kind]`.
- `const BUILDING_FOOTPRINT: Dictionary = {"town_center": Vector2i(3, 3), "house": Vector2i(2, 2), "barracks": Vector2i(3, 3), "wall": Vector2i(1, 1), "gate": Vector2i(1, 1)}`.

Provide these public functions matching the Python signatures:

1. `start_build(game: Game, villager_id: int, kind: String, tile: Vector2i) -> bool` — validates: villager exists + is alive + is a villager + is the owner; kind is in BUILD_COSTS (i.e., not `town_center` per SPEC.md § 6); wood/gold sufficient; footprint clear (no entity/resource on those tiles); not already constructing. On success: deduct cost, store state in `_construction`, issue move to the build tile.

2. `tick_construction(game: Game) -> void` — increment progress; on completion (`progress >= time_seconds * TICK_HZ`), spawn the building Entity at the stored tile via `entities.gd::spawn_building` with full hp, remove from `_construction`. For house, bump owner's `pop_cap += 5`, clamped to `POP_CAP_MAX`.

3. `start_train(game: Game, building_id: int, unit_kind: String) -> bool` — validates: building exists; kind matches the building (TRAIN_COSTS lookup); resources sufficient; building queue empty (`AC-11` — one-at-a-time); pop room available. On success: deduct cost, store state in `_training`.

4. `tick_training(game: Game) -> void` — increment progress; on completion, spawn the unit Entity on an adjacent free tile via `entities.gd::spawn_unit`, remove from `_training`.

5. `place_building_immediate(game: Game, kind: String, tile: Vector2i, owner: int) -> Entity` — for tests + map_gen — spawns a fully-constructed building at full hp with no cost deduction. Returns the Entity.

6. `reset_module_state() -> void` — clears both `_construction` and `_training`.

Read `sim/building.py` in full for exact validation order and edge cases.

## Acceptance

Run `"C:/Users/Westley Yarlott/Downloads/Godot_v4.6.3-stable_win64.exe" --headless --path godot/ -s addons/gut/gut_cmdln.gd -gtest=res://tests/test_building.gd -gexit` for this test file. Confirm RED. Implement in `godot/sim/building.gd` only. Confirm GREEN. Write your final files to `.swarm/pending/leaf-09/`. Stop.

Tests must mirror `tests/test_building.py` (13 tests). At minimum:
- `BUILD_COSTS["house"] == [30, 0, 10]`; `TRAIN_COSTS["villager"] == [50, 0, 12, "town_center"]`; `BUILDING_FOOTPRINT["barracks"] == Vector2i(3, 3)`.
- `start_build(g, vid, "house", Vector2i(8, 8))` with insufficient wood returns false; player wood unchanged.
- `start_build(g, vid, "house", Vector2i(8, 8))` with enough wood deducts 30, stores state, returns true.
- After `TICK_HZ * 10` calls to `tick_construction`, the house Entity exists at full hp (200).
- House completion bumps `pop_cap` by 5.
- Pop cap clamped at `POP_CAP_MAX`.
- `start_train(g, tc_id, "villager")` with enough wood returns true, queue non-empty.
- Second `start_train` on a busy TC returns false; cost not deducted twice (AC-11).
- After `TICK_HZ * 12` calls to `tick_training`, villager Entity spawned within Chebyshev 1 of TC.
- `start_train` blocked when pop full.
- `place_building_immediate` returns full-hp building with no cost.
- `start_build(g, vid, "town_center", ...)` returns false (TC not player-buildable).
- `start_train(g, barracks_id, "villager")` returns false (wrong building).

## Escalation triggers

Stop and report to the parent if:
- A type the test imports is not in `contract_imports`.
- The Python source uses helper functions that fail in the GDScript stdlib (e.g., `dict.setdefault`).
- Footprint-clear validation in `sim/building.py` interacts with `walls.gd` or `pathfinding.gd` in a way that creates a cycle through unimplemented siblings — escalate (parent may need to adjust the order of leaves or the late-bind pattern).
- Impl approaches `impl_line_budget` (220) with assertions still failing.

## Assumption log

If at any point you inferred something not specified, write it to `briefs_godot/leaf-09.ASSUMPTIONS.md`. Likely inferences: how to express the Python tuple in `BUILD_COSTS[kind] = (wood, gold, time)` in GDScript (use `Array`, since GDScript has no tuple type), exact algorithm for finding adjacent-free-tile spawn slot.
