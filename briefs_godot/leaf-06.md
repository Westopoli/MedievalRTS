---
leaf_id: leaf-06
spec_file: SPEC_GODOT.md
spec_lines: 96-125
test_file: godot/tests/test_visibility.gd
impl_file: godot/sim/visibility.gd
contract_imports:
  - sim.contract.Entity
  - sim.contract.Game
  - sim.contract.Player
  - sim.contract.BuildingSnapshot
  - sim.contract.MAP_W
  - sim.contract.MAP_H
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
impl_line_budget: 200
test_assertion_budget: 25
wave: 1
---

## Task

Port `sim/visibility.py` (154 lines) to GDScript at `godot/sim/visibility.gd` per SPEC_GODOT.md lines 96-125 (AC-46, AC-50) and SPEC.md AC-15..AC-22 (3-state symmetric fog of war).

Provide these public functions matching the Python signatures:

1. `init_visibility(game: Game) -> void` — initializes `game.visibility` to a `NUM_PLAYERS`-sized array of `MAP_W × MAP_H` grids, each cell `"unseen"`. Initializes `game.explored_snapshots` to a list of `NUM_PLAYERS` empty Dictionaries (keyed by entity_id). Idempotent: if `game.visibility` already has the correct shape, do not reset cells that already have non-default state.

2. `recompute_visibility(game: Game) -> void` — for each player P, for each cell, computes new visibility state. A tile is `"visible"` for P if any P-owned alive Entity (unit or building) has Chebyshev distance ≤ `get_stats(kind).sight_tiles` from that tile. Late-bind `sim.entities.get_stats` via `load("res://sim/entities.gd")` per SPEC_GODOT.md AC-49. Transitions: `visible`-this-tick stays `visible`. Was-visible-now-not transitions to `explored` (AC-17). Tiles never visible stay `unseen`. Updates `game.explored_snapshots[P]`: for every enemy building Entity newly seen in `visible` tile, write a `BuildingSnapshot` (owner ≠ P). Snapshots persist after the building dies or the tile drops to `explored` (AC-19).

3. `is_command_visible(game: Game, player_id: int, tile: Vector2i) -> bool` — returns `true` if `game.visibility[player_id][tile.x][tile.y]` is `"visible"` or `"explored"`. Returns `true` regardless of state if `game.players[player_id].fog_cheat == true` (AC-22).

4. `visible_entities_for(game: Game, player_id: int) -> Array` — returns the subset of `game.entities` that this player sees: every P-owned entity unconditionally, plus every enemy entity at a `"visible"` tile (AC-18).

Sight values come from `entities.gd::get_stats(kind).sight_tiles`. Dead entities (hp <= 0) do NOT grant vision (AC: matches the Python test `test_dead_building_does_not_grant_vision`).

## Acceptance

Run `"C:/Users/Westley Yarlott/Downloads/Godot_v4.6.3-stable_win64.exe" --headless --path godot/ -s addons/gut/gut_cmdln.gd -gtest=res://tests/test_visibility.gd -gexit` for this test file. Confirm RED. Implement in `godot/sim/visibility.gd` only. Confirm GREEN. Write your final files to `.swarm/pending/leaf-06/`. Stop.

Tests must mirror `tests/test_visibility.py` (13 tests). At minimum:
- `init_visibility(g)` sets `g.visibility` to a `NUM_PLAYERS`-sized array of `MAP_W × MAP_H` grids of `"unseen"`.
- `init_visibility` is idempotent: a tile manually set to `"visible"` survives a second call.
- A single villager at `(10, 10)` reveals all tiles within Chebyshev 5 to its owner.
- A villager at `(70, 30)` reveals to player 1 but not player 0 (symmetric — AC-16).
- After a villager moves away from `(10, 10)`, the tile transitions to `"explored"` not back to `"unseen"` (AC-17).
- `is_command_visible(g, 0, unseen_tile) == false`.
- `is_command_visible(g, 0, explored_tile) == true`; `is_command_visible(g, 0, visible_tile) == true`.
- `is_command_visible(g, 0, unseen_tile)` returns `true` after setting `g.players[0].fog_cheat = true` (AC-22).
- `visible_entities_for` excludes enemies in unseen tiles (AC-18).
- `visible_entities_for` includes enemies in visible tiles.
- Enemy building snapshot is recorded the moment it becomes visible (AC-19).
- Building snapshot persists in `explored_snapshots` after the building's hp drops to 0 (AC-19 persistence).
- A standalone building (no unit) reveals tiles within its `sight_tiles` (test with `town_center` sight 8).
- A dead building (`hp == 0`) does not grant vision.

## Escalation triggers

Stop and report to the parent if:
- A type the test imports is not in `contract_imports`.
- The Python source mixes Chebyshev and Euclidean distance somewhere — escalate before silently picking.
- Impl approaches `impl_line_budget` (200) with assertions still failing.

## Assumption log

If at any point you inferred something not specified, write it to `briefs_godot/leaf-06.ASSUMPTIONS.md`. Likely inferences: how to represent the 3D visibility grid (`Array[Array[Array[String]]]` vs flat `PackedByteArray` with index math), iteration order for `recompute_visibility`.
