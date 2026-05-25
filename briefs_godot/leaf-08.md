---
leaf_id: leaf-08
spec_file: SPEC_GODOT.md
spec_lines: 96-125
test_file: godot/tests/test_combat.gd
impl_file: godot/sim/combat.gd
contract_imports:
  - sim.contract.Entity
  - sim.contract.Game
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
test_assertion_budget: 18
wave: 1
---

## Task

Port `sim/combat.py` (154 lines) to GDScript at `godot/sim/combat.gd` per SPEC_GODOT.md lines 96-125 (AC-46, AC-47, AC-49, AC-50) and SPEC.md AC-14, AC-25 (damage application + death cleanup). The Python source has THREE landed fixes:

1. Integer-exact damage math (no float drift).
2. Idempotent re-issue (re-calling `start_attack` for the same target preserves accumulator).
3. Out-of-range chase: re-path only when not moving OR when target moved beyond chebyshev distance 1 of the cached destination — NOT every tick (otherwise path resets, unit pinned in place).

All three must be preserved in the port.

File-level state per SPEC_GODOT.md AC-47:
- `var _attack_state: Dictionary = {}` — keys are `attacker_id`, values are dictionaries with fields `target_id: int`, `in_range_ticks: int = 0`, `applied_damage: int = 0`, `move_target: Variant = null` (mirror of Python `_AttackState` dataclass).

Provide these public functions:

1. `start_attack(game: Game, attacker_id: int, target_id: int) -> bool` — installs attack state. Returns false for same-owner, dead attacker, dead target, or attacker with `damage_per_sec == 0` (villager). Idempotent for same-target re-issue (preserves accumulator). Late-bind `sim.entities.get_stats` via `load("res://sim/entities.gd")` per AC-49.

2. `cancel_attack(entity_id: int) -> void` — removes the entry. Idempotent.

3. `is_attacking(entity_id: int) -> bool` — returns `entity_id in _attack_state`.

4. `tick_combat(game: Game) -> void` — per tick, for each attacker in `_attack_state`:
   - If attacker or target died, remove from state.
   - Compute chebyshev distance. If `<= attack_range_tiles`, cancel any in-flight move, increment `in_range_ticks`, compute integer damage owed `(in_range_ticks * damage_per_sec) / TICK_HZ`, apply delta vs `applied_damage`. If target dies, remove and call internal `_clear_all_targeting(target_id)` which sweeps all attackers targeting it.
   - If `> attack_range_tiles`, chase. Re-path only when `not pathfinding.is_moving(attacker_id)` OR when `chebyshev(state.move_target, target.pos) > 1`. Path attempt: first try direct `pathfinding.start_move(game, attacker_id, target.pos)`; if false, try each of the 8 adjacent tiles; record the chosen tile in `state.move_target`.

5. `reset_module_state() -> void` — clears `_attack_state`.

Read `sim/combat.py` lines 1-154 in full. The chase logic (lines 128-152 in Python) is the third bug fix — replicate the comparison exactly.

## Acceptance

Run `"C:/Users/Westley Yarlott/Downloads/Godot_v4.6.3-stable_win64.exe" --headless --path godot/ -s addons/gut/gut_cmdln.gd -gtest=res://tests/test_combat.gd -gexit` for this test file. Confirm RED. Implement in `godot/sim/combat.gd` only. Confirm GREEN. Write your final files to `.swarm/pending/leaf-08/`. Stop.

Tests must mirror `tests/test_combat.py` (9 tests). At minimum:
- `start_attack` same-owner returns false.
- `start_attack` from villager (damage_per_sec == 0) returns false.
- `start_attack` valid installs state.
- Adjacent soldiers: after TICK_HZ ticks (1 sim sec), target hp == max_hp - damage_per_sec (integer exact, e.g. soldier vs soldier: 60 - 8).
- Target killed: target removed from `game.entities`.
- All attackers targeting the dead unit have their state cleared.
- Out-of-range attacker issues a move command (stub `pathfinding.start_move` via GUT to capture the call).
- `cancel_attack(eid)` clears state; `cancel_attack(999)` is no-op.
- Archer in range (Chebyshev 4, range 5) does damage.

## Escalation triggers

Stop and report to the parent if:
- A type the test imports is not in `contract_imports`.
- The integer damage math in `sim/combat.py` (lines 115-119: `owed = (in_range_ticks * damage_per_sec) // TICK_HZ`) cannot be expressed in GDScript without precision loss — escalate before substituting float math.
- The third bug fix (re-path comparison) is unclear from the Python source. Re-read `sim/combat.py` lines 128-152.
- Impl approaches `impl_line_budget` (200) with assertions still failing.

## Assumption log

If at any point you inferred something not specified, write it to `briefs_godot/leaf-08.ASSUMPTIONS.md`. Likely inferences: how to stub `sim/pathfinding.gd::start_move` for the out-of-range test (GUT partial doubles vs monkeypatch.setattr-style).
