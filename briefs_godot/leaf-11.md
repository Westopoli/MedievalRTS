---
leaf_id: leaf-11
spec_file: SPEC_GODOT.md
spec_lines: 162-176
test_file: godot/tests/test_ai.gd
impl_file: godot/sim/ai.gd
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
  - godot/sim/commands.gd
  - godot/tests/test_commands.gd
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
test_assertion_budget: 18
wave: 1
---

## Task

Port `sim/ai.py` (274 lines) to GDScript at `godot/sim/ai.gd` per SPEC_GODOT.md lines 162-176 (AC-64, AC-65, AC-66) and SPEC.md § 11 (10-rule deterministic priority script). This is the locked AI script — the post-`1cc5e95` patches are part of the contract:

- Rule 9 trigger is `(sol_n + arch_n) >= 3` (NOT `sol_n >= 6` from earlier draft).
- `claimed_eids` tracking prevents one rule from re-tasking units claimed by another within the same AI tick.
- Rule 3 reserves 80 wood for the first barracks when `barracks_count == 0`.
- Rule 4 (train scout) gated on `barracks_count >= 1`.
- `_AIState` per-player struct mirrors `sim/ai.py::_AIState`.

File-level state per SPEC_GODOT.md AC-47:
- `var _ai_state: Dictionary = {}` — keys are `player_id`, values are dictionaries with fields matching the Python `_AIState` dataclass (`scout_last_dispatch_tick: int`, `gather_alt: int`, `walls_built_by_us: int`, `designated_gate_idx: int`).

Constants (mirror Python):
- `const _MILITARY: Array[String] = ["soldier", "archer"]`
- `const _SCOUT_PERIOD: int = TICK_HZ * 4` (4 sim sec between scout dispatches)
- `const _WALL_ARC_OFFSETS: Array[Vector2i] = [...]` — copy verbatim from `sim/ai.py`. Read the file.

Provide one public function:

`ai_tick(game: Game, player_id: int, tick: int) -> Array` — returns an `Array[Command]`. Implements the 10 rules per SPEC.md § 11, with the post-`1cc5e95` patches above. Late-bind every sibling via `load("res://sim/<module>.gd")` per AC-49. Per AC-64, threshold values and rule ordering must match `sim/ai.py` byte-for-byte.

The function is pure (no global state mutation outside `_ai_state[player_id]`). It does NOT call `apply_command`; it returns the command list for the caller (game.tick) to dispatch.

Also provide:
- `reset_module_state() -> void` — clears `_ai_state`.

## Acceptance

Run `"C:/Users/Westley Yarlott/Downloads/Godot_v4.6.3-stable_win64.exe" --headless --path godot/ -s addons/gut/gut_cmdln.gd -gtest=res://tests/test_ai.gd -gexit` for this test file. Confirm RED. Implement in `godot/sim/ai.gd` only. Confirm GREEN. Write your final files to `.swarm/pending/leaf-11/`. Stop.

Tests must include (mirror or extend `tests/test_ai.py` if it exists; the Python sim's ai tests are minimal so synthesize parity tests against the rule numbers):
- Fresh game, P0 has 5 villagers + 1 TC; `ai_tick(g, 0, 0)` returns a non-empty array containing a `train` command for a villager (rule 3).
- Rule 3 reserves 80 wood for first barracks: with `p.wood == 100, barracks_count == 0`, no villager train is issued (because 50 + 80 > 100).
- Rule 4 (scout) does not fire when `barracks_count == 0`.
- Rule 9 attack fires when `soldier_count + archer_count >= 3` and enemy TC is `explored`/`visible`.
- Rule 9 does NOT fire when `soldier_count + archer_count < 3`.
- Rule 10 (idle villager gather) returns a `gather` command for each idle villager pointing at a nearby tree or gold mine.
- Two consecutive `ai_tick` calls with the same game state produce identical command arrays (deterministic).
- `_ai_state` is per-player keyed: a `ai_tick(g, 0, ...)` does not perturb `_ai_state[1]`.

## Escalation triggers

Stop and report to the parent if:
- A type the test imports is not in `contract_imports`.
- The 10-rule script in `sim/ai.py` references a helper (`emit_train`, `emit_build`, `_is_busy`, `_nearest_unseen`, `_nearest_node`, `_footprint_clear`, `_nearest_owned_tc`) that is itself non-trivial — port them as file-level helper functions (NOT exposed as public API) inside the same `ai.gd` file.
- Threshold values or rule ordering in `sim/ai.py` disagree with the brief above — re-read commit `183316c` log message; the brief above is authoritative.
- Impl approaches `impl_line_budget` (220) with assertions still failing.

## Assumption log

If at any point you inferred something not specified, write it to `briefs_godot/leaf-11.ASSUMPTIONS.md`. Likely inferences: GDScript representation for `set[int]` (`Array[int]` vs `Dictionary` as set), exact `_WALL_ARC_OFFSETS` ordering (copy from Python verbatim — do not regenerate).
