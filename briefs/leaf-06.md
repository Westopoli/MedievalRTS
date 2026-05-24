---
leaf_id: leaf-06
spec_file: SPEC.md
spec_lines: 52-60
test_file: tests/test_gather.py
impl_file: sim/gather.py
contract_imports:
  - sim.contract.Game
  - sim.contract.Entity
  - sim.contract.Player
  - sim.contract.CARRY_CAP
  - sim.contract.TICK_HZ
do_not_edit:
  - sim/contract.py
  - sim/__init__.py
  - sim/map_gen.py
  - tests/test_map_gen.py
  - sim/entities.py
  - tests/test_entities.py
  - sim/walls.py
  - tests/test_walls.py
  - sim/pathfinding.py
  - tests/test_pathfinding.py
  - sim/visibility.py
  - tests/test_visibility.py
  - sim/combat.py
  - tests/test_combat.py
  - sim/building.py
  - tests/test_building.py
  - sim/commands.py
  - tests/test_commands.py
  - sim/ai.py
  - tests/test_ai.py
  - sim/game.py
  - tests/test_game.py
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
impl_line_budget: 200
test_assertion_budget: 20
wave: 1
---

## Task

Implement resource gathering, walking back to TC, and deposit per SPEC.md lines 52-60 (AC-5..AC-9).

May import `sim.pathfinding.start_move` / `cancel_move` / `is_moving` for villager movement, and `sim.entities` for kind checks.

Provide in `sim/gather.py`:

1. `start_gather(game: Game, entity_id: int, resource_node_id: int) -> bool` — if `entity_id` refers to a live `villager`-kind entity owned by some player, and `resource_node_id` refers to a live `tree` or `gold_mine` entity, install gather state for the villager (target node id, resource kind inferred from node kind) and issue `start_move` toward the node's tile. Cancel any prior gather state for this villager (AC-8). Return `True` on success, `False` if either entity is missing/dead/wrong kind.

2. `tick_gather(game: Game) -> None` — for each villager with gather state:
   - If villager is moving, do nothing this tick (movement leaf advances them).
   - Else if villager has full carry (`carry_amount >= CARRY_CAP`), find nearest live owned `town_center`. If adjacent (Chebyshev <= 1), deposit `carry_amount` into `game.players[villager.owner].wood` or `.gold` based on `villager.carrying`; reset `carrying=None, carry_amount=0`; re-issue `start_move` back to the resource node if it still exists, else clear gather state.
   - Else if villager is adjacent to (or standing on) the resource node and the node has `hp > 0`: gather `+1 carry_amount` per sim second (i.e. once every `TICK_HZ` ticks per villager). Set `villager.carrying = resource_kind`. Decrement node `hp` by 1 per gather tick; on node death, clear gather state for this villager.
   - Else (not at node, not moving): re-issue `start_move` toward node.
   - If `carry_amount` just reached `CARRY_CAP`, issue `start_move` toward nearest owned TC.

3. `cancel_gather(entity_id: int) -> None` — remove gather state; called by commands leaf when villager is re-tasked.

4. `is_gathering(entity_id: int) -> bool`.

Gather state lives in a module-level `_gather_state: dict[int, _GatherState]`.

## Acceptance

Run `python -m pytest tests/test_gather.py -x -q`. Confirm RED. Implement in `sim/gather.py` only. Confirm GREEN. Write to `.swarm/pending/leaf-06/`.

Tests:
- `start_gather` with bad entity ids returns False, installs no state
- After `start_gather` and enough ticks (movement + gather + walk back + deposit), `game.players[0].wood` increases by at least 1
- Villager gathering from a tree sets `villager.carrying == "wood"`; from gold_mine sets `"gold"`
- Villager `carry_amount` never exceeds CARRY_CAP
- A second `start_gather` call to a different node replaces the first (AC-8)
- Tree node `hp` decrements as villager gathers; when tree hp reaches 0, gather state for that villager is cleared

## Escalation triggers

Stop and report to the parent if:
- A type the test imports is not in contract_imports (`sim.pathfinding` and `sim.entities` cross-leaf imports permitted).
- The impl would need to create a new file.
- The impl would need to edit a file in do_not_edit.
- Two sibling assertions seem to require contradictory behavior.
- Impl approaches impl_line_budget with assertions still failing.

## Assumption log

Write inferences to `briefs/leaf-06.ASSUMPTIONS.md`.
