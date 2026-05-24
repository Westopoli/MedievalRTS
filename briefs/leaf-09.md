---
leaf_id: leaf-09
spec_file: SPEC.md
spec_lines: 141-154
test_file: tests/test_commands.py
impl_file: sim/commands.py
contract_imports:
  - sim.contract.Game
  - sim.contract.Command
  - sim.contract.CommandKind
do_not_edit:
  - sim/contract.py
  - sim/__init__.py
  - sim/map_gen.py
  - sim/entities.py
  - sim/walls.py
  - sim/pathfinding.py
  - sim/visibility.py
  - sim/gather.py
  - sim/combat.py
  - sim/building.py
  - sim/ai.py
  - sim/game.py
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
test_assertion_budget: 22
wave: 2
---

## Task

Implement command validation + dispatch per SPEC.md lines 141-154 (AC-21, AC-27).

May import every wave-1 sibling module: `sim.pathfinding`, `sim.gather`, `sim.combat`, `sim.building`, `sim.visibility`. This leaf is the integration glue.

Provide in `sim/commands.py`:

1. `apply_command(game: Game, cmd: Command) -> bool` — single entry point. Returns `True` if the command was applied, `False` if silently dropped per AC-27. Steps:
   - **Authority check** — if `cmd` references an `entity_id` that exists, that entity's `owner` must equal `cmd.issuing_player`. Mismatch → drop.
   - For commands that reference a `building_id`, that building's `owner` must equal `cmd.issuing_player`. Mismatch → drop.
   - **Fog gate (AC-21)** — for `move` and `attack`, the relevant target tile must be visible-or-explored to `cmd.issuing_player`, OR `game.players[cmd.issuing_player].fog_cheat` must be True. For `attack` the target tile is the target entity's current pos (the issuing player must have seen the target's current tile at some point). Use `sim.visibility.is_command_visible`. Drop if blocked.
   - **Dispatch** — based on `cmd.kind`:
     - `move`: call `sim.pathfinding.start_move(game, cmd.entity_id, cmd.target_tile)`. Also `cancel_gather` and `cancel_attack` for that entity (re-tasking).
     - `attack`: call `sim.combat.start_attack(game, cmd.entity_id, cmd.target_entity_id)`. `cancel_gather` + `cancel_move` on attacker.
     - `gather`: call `sim.gather.start_gather(game, cmd.entity_id, cmd.resource_node_id)`. `cancel_attack` + `cancel_move`.
     - `build`: call `sim.building.start_build(game, cmd.entity_id, cmd.building_kind, cmd.target_tile)`. `cancel_attack` + `cancel_gather` + `cancel_move` on builder.
     - `train`: call `sim.building.start_train(game, cmd.building_id, cmd.unit_kind)`.
     - `stop`: `cancel_move`, `cancel_gather`, `cancel_attack` for `cmd.entity_id`.
   - Each dispatch helper already validates its own preconditions; if the helper returns False, propagate as drop (return False).
   - Never raise. Any unexpected exception in a helper means a bug — let it propagate (leaf must NOT wrap helpers in try/except; do not paper over bugs).

2. `apply_commands(game: Game, cmds: list[Command]) -> int` — calls `apply_command` for each cmd in order, returns the count of successfully-applied commands.

## Acceptance

Run `python -m pytest tests/test_commands.py -x -q`. Confirm RED. Implement in `sim/commands.py` only. Confirm GREEN. Write to `.swarm/pending/leaf-09/`.

Tests (build a small game with two players, one villager each, one tree, one TC each; call `init_visibility` + `recompute_visibility` first):
- `apply_command` with `issuing_player=0` trying to `move` player-1's villager returns False; villager pos unchanged (AC-27 authority)
- `apply_command` with `issuing_player=0` `move` to an UNSEEN tile on player-1's side returns False; no movement state installed (AC-21 fog)
- Same command with `players[0].fog_cheat = True` returns True (AC-22 cheat)
- `apply_command` with `gather` of a tree the villager has seen returns True; gather state installed
- `apply_command` with `attack` where attacker is a villager (dps=0) returns False (subsystem validation propagates)
- `apply_command` for `train` at a building owned by the wrong player returns False
- `apply_command` for `stop` cancels move + gather + attack state for the entity
- `apply_commands` returns count of successes; mixed valid/invalid list applies only the valid ones

## Escalation triggers

Stop and report to the parent if:
- A type the test imports is not in contract_imports (sim.* sibling imports permitted as listed above).
- The impl would need to create a new file.
- The impl would need to edit a file in do_not_edit.
- Two sibling assertions seem to require contradictory behavior.
- Impl approaches impl_line_budget with assertions still failing.

## Assumption log

Write inferences to `briefs/leaf-09.ASSUMPTIONS.md`.
