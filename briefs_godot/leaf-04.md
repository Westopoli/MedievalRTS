---
leaf_id: leaf-04
spec_file: SPEC_GODOT.md
spec_lines: 96-125
test_file: godot/tests/test_walls.gd
impl_file: godot/sim/walls.gd
contract_imports:
  - sim.contract.Entity
  - sim.contract.Game
do_not_edit:
  - godot/sim/contract.gd
  - godot/tests/test_contract.gd
  - godot/sim/map_gen.gd
  - godot/tests/test_map_gen.gd
  - godot/sim/entities.gd
  - godot/tests/test_entities.gd
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
impl_line_budget: 100
test_assertion_budget: 12
wave: 1
---

## Task

Port `sim/walls.py` (40 lines) to GDScript at `godot/sim/walls.gd` per SPEC_GODOT.md lines 96-125 (AC-46, AC-50) and SPEC.md AC-23, AC-24, AC-25.

Provide two public functions matching the Python signatures:

1. `is_passable_for(game: Game, tile: Vector2i, owner: int) -> bool` — returns `true` if no wall or gate occupies `tile`, OR a gate at that tile is owned by `owner`. Returns `false` for solid walls (blocks all per AC-23) and enemy-owned gates (AC-24). Logic must mirror `sim/walls.py::is_passable_for` exactly.

2. `wall_or_gate_at(game: Game, tile: Vector2i) -> Entity` — returns the wall/gate Entity at `tile` if one exists with `hp > 0`, else returns `null`. Used by the pathfinder leaf-05.

This is a small module. Total impl should fit comfortably in 60 lines. Reference: read `sim/walls.py` lines 1-40 in full.

## Acceptance

Run `"C:/Users/Westley Yarlott/Downloads/Godot_v4.6.3-stable_win64.exe" --headless --path godot/ -s addons/gut/gut_cmdln.gd -gtest=res://tests/test_walls.gd -gexit` for this test file. Confirm RED. Implement in `godot/sim/walls.gd` only. Confirm GREEN. Write your final files to `.swarm/pending/leaf-04/`. Stop.

Tests you must include:
- An empty game (no walls) returns `is_passable_for(g, Vector2i(5, 5), 0) == true` (AC-23 negative).
- A wall Entity with `owner=0` at `(5, 5)` returns `is_passable_for(g, Vector2i(5, 5), 0) == false` (AC-23 — walls block all, even owner's).
- A wall Entity with `owner=0` at `(5, 5)` returns `is_passable_for(g, Vector2i(5, 5), 1) == false`.
- A gate Entity with `owner=0` at `(5, 5)` returns `is_passable_for(g, Vector2i(5, 5), 0) == true` (AC-24 — owner passes).
- A gate Entity with `owner=0` at `(5, 5)` returns `is_passable_for(g, Vector2i(5, 5), 1) == false` (AC-24 — enemy blocked).
- A dead wall (hp == 0) does NOT block: `is_passable_for(g, Vector2i(5, 5), 0) == true` (AC-25 — destroyed tile passable).
- `wall_or_gate_at` returns the wall Entity if present.
- `wall_or_gate_at` returns `null` if no wall/gate at that tile.
- `wall_or_gate_at` returns `null` if the wall at that tile has `hp == 0`.

## Escalation triggers

Stop and report to the parent if:
- A type the test imports is not in `contract_imports`.
- The Python source uses a helper function not present in the GDScript standard library — escalate, do not silently inline a workaround.
- The impl would need to edit a file in `do_not_edit`.
- Impl approaches `impl_line_budget` (100) with assertions still failing.

## Assumption log

If at any point you inferred something not specified, write it to `briefs_godot/leaf-04.ASSUMPTIONS.md` before committing.
