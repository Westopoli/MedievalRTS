---
leaf_id: leaf-07
spec_file: SPEC_GODOT.md
spec_lines: 96-125
test_file: godot/tests/test_gather.gd
impl_file: godot/sim/gather.gd
contract_imports:
  - sim.contract.Entity
  - sim.contract.Game
  - sim.contract.Player
  - sim.contract.CARRY_CAP
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
test_assertion_budget: 18
wave: 1
---

## Task

Port `sim/gather.py` (209 lines) to GDScript at `godot/sim/gather.gd` per SPEC_GODOT.md lines 96-125 (AC-46, AC-47, AC-49, AC-50) and SPEC.md AC-5..AC-9 (gather + deposit). Pay close attention: this file already has THREE landed bug fixes in the Python source (adjacent-tile pathing, idempotent re-issue) — the port must preserve all three.

File-level state per SPEC_GODOT.md AC-47:
- `var _gather_state: Dictionary = {}` — keys are `entity_id`, values are dictionaries with fields `node_id: int`, `resource_kind: String`, `gather_progress: int` (mirror of Python `_GatherState` dataclass).

Provide these public functions matching the Python signatures:

1. `start_gather(game: Game, entity_id: int, resource_node_id: int) -> bool` — installs gather state and issues a move command to an adjacent tile of the resource node (NOT the node's own tile — pathfinder treats trees/mines as blocking). Idempotent: if the same villager is already gathering the same node, preserve `gather_progress` and return true. Returns false for invalid villager / node / kind. Per the Python sim's `_start_move_adjacent_to` helper, try the 8 surrounding tiles and use the first reachable. Late-bind `sim.pathfinding` via `load("res://sim/pathfinding.gd")` per AC-49.

2. `cancel_gather(entity_id: int) -> void` — removes the entry from `_gather_state`. Idempotent.

3. `is_gathering(entity_id: int) -> bool` — returns `entity_id in _gather_state`.

4. `tick_gather(game: Game) -> void` — advances every villager in `_gather_state`. Behavior per `sim/gather.py::tick_gather` (lines 146-209). Summary:
   - If villager is moving (per pathfinding.is_moving), skip.
   - If villager is carrying CARRY_CAP, walk to nearest owned TC; on arrival, deposit (increment player's `wood` or `gold`), zero `carry_amount` + `carrying`, re-issue move back to resource node.
   - If villager is at a node-adjacent tile, increment `gather_progress` by 1 each tick. When `gather_progress >= TICK_HZ` (1 sim second), grant +1 carry, decrement node hp by 1. If node dies, clear state. If carry hits cap, move to nearest TC.
   - If villager is not adjacent and not moving, re-issue move toward an adjacent tile.

5. `reset_module_state() -> void` — clears `_gather_state`.

Read `sim/gather.py` lines 60-209 in detail; the gather logic is subtle and the port must match tick-for-tick.

## Acceptance

Run `"C:/Users/Westley Yarlott/Downloads/Godot_v4.6.3-stable_win64.exe" --headless --path godot/ -s addons/gut/gut_cmdln.gd -gtest=res://tests/test_gather.gd -gexit` for this test file. Confirm RED. Implement in `godot/sim/gather.gd` only. Confirm GREEN. Write your final files to `.swarm/pending/leaf-07/`. Stop.

Tests must mirror `tests/test_gather.py` (6 tests). At minimum:
- `start_gather` returns false for invalid villager/node ids and for wrong-kind entities.
- A villager near a tree gathers +1 wood within CARRY_CAP + buffer ticks (test stubs `sim/pathfinding.gd::start_move` to teleport entity to the requested tile, mirror the Python test's pattern via GUT stubs / partial doubles).
- A villager gathers wood when working a tree (`carrying == "wood"` after TICK_HZ + 2 ticks).
- A villager gathers gold when working a gold mine.
- A second `start_gather` call for the same villager retargets to the new node (`_gather_state[v.entity_id].node_id == new_target_id`).
- Tree hp decrements; when tree hp hits 0, gather state clears.

## Escalation triggers

Stop and report to the parent if:
- A type the test imports is not in `contract_imports`.
- The 3 fixed bugs in `sim/gather.py` (adjacent-tile pathing, idempotent re-issue on same node, walk-back-to-TC after carry full) are not all clearly identified in the source. Re-read commit `6deed4b` log message.
- Impl approaches `impl_line_budget` (220) with assertions still failing.

## Assumption log

If at any point you inferred something not specified, write it to `briefs_godot/leaf-07.ASSUMPTIONS.md`. Likely inferences: GDScript syntax for "if X in dict" (use `dict.has(X)`), how to express `Optional[str]` for `carrying` field (`Variant` defaulting to `null` per AC-43).
