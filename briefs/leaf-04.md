---
leaf_id: leaf-04
spec_file: SPEC.md
spec_lines: 83-83
test_file: tests/test_pathfinding.py
impl_file: sim/pathfinding.py
contract_imports:
  - sim.contract.Game
  - sim.contract.Entity
  - sim.contract.MAP_W
  - sim.contract.MAP_H
do_not_edit:
  - sim/contract.py
  - sim/__init__.py
  - sim/map_gen.py
  - sim/entities.py
  - sim/visibility.py
  - sim/gather.py
  - sim/combat.py
  - sim/building.py
  - sim/commands.py
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
impl_line_budget: 220
test_assertion_budget: 20
wave: 1
---

## Task

Implement 8-direction A* pathfinding plus per-tick movement execution per SPEC.md line 83 (AC-13) and line 124 + 122 (AC-23/AC-24 routing around walls/gates).

This leaf may `import sim.walls` to consult wall/gate passability — that import is permitted because leaf-03 (`sim/walls.py`) is a sibling that publishes a passability lookup API for this leaf to consume. It is NOT a contract import.

Provide in `sim/pathfinding.py`:

1. `find_path(game: Game, start: tuple[int, int], goal: tuple[int, int], owner: int) -> list[tuple[int, int]] | None` — returns a list of tile coords from `start` (exclusive) to `goal` (inclusive), or `None` if unreachable. 8-direction movement (N, NE, E, SE, S, SW, W, NW). Diagonal cost = 1.41, cardinal cost = 1.0. Heuristic = Chebyshev distance. Blocked tiles per AC-13/AC-23/AC-24:
   - Outside `[0, MAP_W) x [0, MAP_H)` is blocked.
   - Tile occupied by `tree`, `gold_mine`, `town_center`, `house`, or `barracks` entity (any `hp > 0`) is blocked.
   - Walls/gates: use `sim.walls.is_passable_for(game, tile, owner)`.
   - The `goal` tile is allowed to be checked even if blocked (caller may want adjacency-to-goal) — but the returned path will NOT include a blocked goal; if goal is blocked, return `None`.

2. `tick_movement(game: Game) -> None` — advance any entity currently with a movement-state set by one tick. Movement state is stored in a module-level `_move_state: dict[int, _MoveState]` keyed by `entity_id`. `_MoveState` holds the current path remainder and a sub-tile progress accumulator (so a unit with `speed_tiles_per_sec=2.0` advances 2/30 of a tile per tick — when the accumulator >= 1.0, snap `entity.pos` to next tile in path, decrement accumulator). When path is exhausted, remove state entry.

3. `start_move(game: Game, entity_id: int, target_tile: tuple[int, int]) -> bool` — compute a path from the entity's current position to `target_tile` with owner = the entity's owner. If path found and non-empty, install movement state, return `True`. If unreachable, do nothing, return `False`.

4. `cancel_move(entity_id: int) -> None` — remove movement state if present (silent no-op if absent). Used by combat / gather when re-tasking a unit.

5. `is_moving(entity_id: int) -> bool` — `entity_id in _move_state`.

Unit speed lookup: import `sim.entities.get_stats(kind).speed_tiles_per_sec`. This cross-leaf import is permitted (entities is a sibling publishing a stats lookup API).

## Acceptance

Run `python -m pytest tests/test_pathfinding.py -x -q`. Confirm RED. Implement in `sim/pathfinding.py` only. Confirm GREEN. Write to `.swarm/pending/leaf-04/`.

Tests:
- Empty 20x20 game, find_path((0,0), (5,5), 0) returns a path of length 5 (diagonal)
- Path is None when goal is OOB
- Path is None when goal tile is a tree
- A wall at (3,3) forces the path from (0,3) to (6,3) to deviate (path doesn't include (3,3))
- A gate at (3,3) owner=0 admits owner=0 (path may include (3,3))
- A gate at (3,3) owner=0 rejects owner=1 (path doesn't include (3,3) or returns None)
- `start_move` + repeated `tick_movement` advances the entity's pos along the path; entity reaches goal within (path_length / speed) * TICK_HZ + a small slack of ticks
- `cancel_move` clears state; subsequent `tick_movement` is a no-op for that entity

## Escalation triggers

Stop and report to the parent if:
- A type the test imports is not in contract_imports (other than `sim.walls` and `sim.entities` which are sibling-API imports permitted by this brief).
- The impl would need to create a new file.
- The impl would need to edit a file in do_not_edit.
- Two sibling assertions seem to require contradictory behavior.
- Impl approaches impl_line_budget with assertions still failing.

## Assumption log

Write inferences to `briefs/leaf-04.ASSUMPTIONS.md`.
