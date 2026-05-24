---
leaf_id: leaf-08
spec_file: SPEC.md
spec_lines: 80-104
test_file: tests/test_building.py
impl_file: sim/building.py
contract_imports:
  - sim.contract.Game
  - sim.contract.Entity
  - sim.contract.Player
  - sim.contract.EntityKind
  - sim.contract.TICK_HZ
  - sim.contract.POP_CAP_START
  - sim.contract.POP_CAP_MAX
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
test_assertion_budget: 25
wave: 1
---

## Task

Implement construction + unit training queues per SPEC.md lines 80-104 (AC-10, AC-11) plus the construction/training cost tables shown there.

May import `sim.entities.spawn_unit`, `sim.entities.spawn_building`, `sim.entities.is_building`, `sim.entities.is_unit`, `sim.entities.get_stats`, and `sim.pathfinding.start_move` / `is_moving`.

Provide in `sim/building.py`:

1. `BUILD_COSTS: dict[EntityKind, tuple[int, int, int]]` — `(wood, gold, time_seconds)` per building kind, per SPEC.md build table: house=(30,0,10), barracks=(80,0,15), wall=(5,0,3), gate=(25,5,5). town_center not present (not player-buildable in v0).

2. `TRAIN_COSTS: dict[EntityKind, tuple[int, int, int, EntityKind]]` — `(wood, gold, time_seconds, trained_at_building_kind)` per unit kind: villager=(50,0,12,"town_center"), scout=(30,20,10,"town_center"), soldier=(40,20,15,"barracks"), archer=(25,35,18,"barracks").

3. `BUILDING_FOOTPRINT: dict[EntityKind, tuple[int, int]]` — `(width, height)` per building kind: house=(2,2), barracks=(3,3), wall=(1,1), gate=(1,1), town_center=(2,2) (informational for collision; town_center not player-buildable).

4. `start_build(game: Game, builder_id: int, kind: EntityKind, tile: tuple[int, int]) -> bool` — for a villager builder, validate: kind is a player-buildable building (`kind in BUILD_COSTS`), tile + footprint fits in map bounds, no overlapping live entity occupies any footprint tile (excluding the builder villager itself), and `game.players[builder.owner]` has at least the wood + gold cost. On failure return False (no state change). On success: deduct cost from player, install construction state with timer = `time_seconds * TICK_HZ`, issue `start_move` for the villager toward the footprint center. Return True.

5. `tick_construction(game: Game) -> None` — for each in-progress construction, if the assigned villager is adjacent (Chebyshev <= 1) to the footprint center and alive, decrement timer by 1. When timer reaches 0, call `spawn_building` to create the new building entity at the footprint tile with full hp (from `get_stats`), then clear construction state for that builder. House completion adds `+5` to `game.players[builder.owner].pop_cap`, clamped at `POP_CAP_MAX` (AC-10).

6. `start_train(game: Game, building_id: int, unit_kind: EntityKind) -> bool` — validate: building exists, alive, owned by some player, `unit_kind in TRAIN_COSTS`, building.kind matches `TRAIN_COSTS[unit_kind][3]`, building's queue is empty (one-at-a-time, AC-11), player has cost, and current population count of unit-kinds for this player < `pop_cap`. On success deduct cost, install training queue entry with timer = `time_seconds * TICK_HZ`. Return True.

7. `tick_training(game: Game) -> None` — for each in-progress training, decrement timer by 1. When timer reaches 0, call `spawn_unit` at a tile adjacent to the building (first free Chebyshev=1 tile, in N,E,S,W,NE,SE,SW,NW order); if no free adjacent tile, defer (do not decrement further this tick); clear queue entry on spawn.

8. `place_building_immediate(game: Game, kind: EntityKind, tile: tuple[int, int], owner: int) -> Entity` — UMBRELLA-ONLY helper that bypasses construction (no cost, no timer). Calls `spawn_building` and returns it. Used by `tests/test_umbrella.py`.

Construction state and training queue state live in module-level `_construction: dict[int, _Construction]` (key = builder_id) and `_training: dict[int, _Training]` (key = building_id).

## Acceptance

Run `python -m pytest tests/test_building.py -x -q`. Confirm RED. Implement in `sim/building.py` only. Confirm GREEN. Write to `.swarm/pending/leaf-08/`.

Tests:
- `start_build` with insufficient wood returns False, no deduction
- Successful `start_build` for a House deducts 30 wood, installs construction
- After enough ticks (10 sec) of `tick_construction`, a `house` building entity exists at the tile with full hp
- House completion bumps `pop_cap` by 5
- `pop_cap` never exceeds `POP_CAP_MAX`
- `start_train` for "villager" at a TC with no queue and enough wood: returns True, deducts 50 wood
- Second `start_train` at the same building while queue full: returns False (AC-11)
- After `tick_training` for 12 sec, a new villager entity exists with owner matching the TC owner, at a tile adjacent to TC
- Training is blocked when current unit count >= pop_cap
- `place_building_immediate` creates a building with full hp and no cost deduction

## Escalation triggers

Stop and report to the parent if:
- A type the test imports is not in contract_imports (sibling-API imports permitted: sim.entities, sim.pathfinding).
- The impl would need to create a new file.
- The impl would need to edit a file in do_not_edit.
- Two sibling assertions seem to require contradictory behavior.
- Impl approaches impl_line_budget with assertions still failing.

## Assumption log

Write inferences to `briefs/leaf-08.ASSUMPTIONS.md`.
