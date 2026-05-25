---
leaf_id: leaf-10
spec_file: SPEC_GODOT.md
spec_lines: 96-125
test_file: godot/tests/test_commands.gd
impl_file: godot/sim/commands.gd
contract_imports:
  - sim.contract.Command
  - sim.contract.Entity
  - sim.contract.Game
  - sim.contract.Player
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
  - godot/sim/visibility.gd
  - godot/tests/test_visibility.gd
  - godot/sim/gather.gd
  - godot/tests/test_gather.gd
  - godot/sim/combat.gd
  - godot/tests/test_combat.gd
  - godot/sim/building.gd
  - godot/tests/test_building.gd
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
test_assertion_budget: 22
wave: 1
---

## Task

Port `sim/commands.py` (136 lines) to GDScript at `godot/sim/commands.gd` per SPEC_GODOT.md lines 96-125 (AC-46, AC-49, AC-50) and SPEC.md AC-21, AC-22, AC-27 (fog gate, cheat flag, silent-drop validation).

This module is the dispatcher between a `Command` and the appropriate sim subsystem (gather/combat/pathfinding/building). It performs validation, fog gating, and authority checks. Invalid commands are SILENTLY DROPPED (AC-27).

Provide one public function:

`apply_command(game: Game, cmd: Command) -> bool` — returns `true` if the command was accepted and dispatched, `false` if dropped. Logic:

1. If `game.over == true`, drop (AC-37).
2. If `cmd.kind not in COMMAND_KINDS`, drop.
3. Look up entity by `cmd.entity_id` (or `cmd.building_id` for `train` kind). If not found / dead, drop.
4. Authority check: entity's `owner` must equal `cmd.issuing_player` (for `train`, the building's owner). Else drop.
5. Fog gate (AC-21, AC-22): for `attack` and `gather` kinds, the target tile must be `"visible"` or `"explored"` for `cmd.issuing_player` UNLESS `game.players[cmd.issuing_player].fog_cheat == true`. For `move`, ALL tiles allowed (including `unseen`) — this matches the post-1cc5e95 fog-gate rule documented in commit `183316c`.
6. Dispatch by kind:
   - `move` → `pathfinding.start_move(game, eid, target_tile)`.
   - `attack` → `combat.start_attack(game, eid, target_entity_id)`.
   - `gather` → `gather.start_gather(game, eid, resource_node_id)`.
   - `build` → `building.start_build(game, eid, building_kind, target_tile)`.
   - `train` → `building.start_train(game, building_id, unit_kind)`.
   - `stop` → cancel any of the above for `eid`. Call `gather.cancel_gather`, `combat.cancel_attack`, `pathfinding.cancel_move`.

Late-bind every sibling via `load("res://sim/<module>.gd")` inside the function body per SPEC_GODOT.md AC-49.

## Acceptance

Run `"C:/Users/Westley Yarlott/Downloads/Godot_v4.6.3-stable_win64.exe" --headless --path godot/ -s addons/gut/gut_cmdln.gd -gtest=res://tests/test_commands.gd -gexit` for this test file. Confirm RED. Implement in `godot/sim/commands.gd` only. Confirm GREEN. Write your final files to `.swarm/pending/leaf-10/`. Stop.

Tests must mirror `tests/test_commands.py` (13+ tests). At minimum:
- A command for a non-existent entity returns false.
- A command issued by player 0 targeting a player-1-owned entity returns false (authority).
- `move` into an `unseen` tile is ALLOWED (returns true) — this matches the post-`1cc5e95` fog-gate rule.
- `attack` targeting an `unseen` enemy is dropped (returns false).
- `fog_cheat = true` for the issuer waives the fog gate for `attack`.
- `gather` on a visible tree succeeds.
- `gather` on a non-resource entity returns false (delegates to gather.start_gather which validates kind).
- `build` with insufficient wood returns false.
- `train` on a TC with valid villager request returns true.
- `stop` cancels in-flight gather/attack/move for the entity.
- A command issued when `game.over == true` returns false (AC-37).
- An unknown `kind` returns false.
- All return-true paths actually invoke the right downstream (verified by inspecting the late-bound module's state after the call, e.g., `assert_true(gather._gather_state.has(eid))` after a successful gather).

## Escalation triggers

Stop and report to the parent if:
- A type the test imports is not in `contract_imports`.
- The fog gate's exact semantics differ between SPEC.md AC-21 and SPEC_GODOT.md leaf-10 task above — re-read commit `183316c` log message before resolving.
- The Python source uses `Command` as a dataclass with default-None fields and the GDScript `Variant`-default approach causes test-stub mismatches.
- Impl approaches `impl_line_budget` (200) with assertions still failing.

## Assumption log

If at any point you inferred something not specified, write it to `briefs_godot/leaf-10.ASSUMPTIONS.md`. Likely inferences: stub strategy for sibling modules in tests (GUT partial doubles vs file-level test variables), exact set of cancel calls under `stop`.
