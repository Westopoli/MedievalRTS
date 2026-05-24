---
leaf_id: leaf-03
spec_file: SPEC.md
spec_lines: 119-124
test_file: tests/test_walls.py
impl_file: sim/walls.py
contract_imports:
  - sim.contract.Game
  - sim.contract.Entity
do_not_edit:
  - sim/contract.py
  - sim/__init__.py
  - sim/map_gen.py
  - sim/entities.py
  - sim/pathfinding.py
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
impl_line_budget: 100
test_assertion_budget: 15
wave: 1
---

## Task

Implement wall/gate passability lookup per SPEC.md lines 119-124 (AC-23, AC-24, AC-25).

Provide in `sim/walls.py`:

1. `is_passable_for(game: Game, tile: tuple[int, int], owner: int) -> bool` — returns `True` if the tile can be entered by a unit owned by `owner`, considering only wall/gate entities at that tile. Rules:
   - If no wall or gate entity exists at `tile`, return `True` (this helper only knows walls/gates — trees/mines/other-buildings are handled by the pathfinding leaf).
   - If a `wall` entity exists at `tile` with `hp > 0`, return `False` regardless of owner (AC-23).
   - If a `gate` entity exists at `tile` with `hp > 0`: return `True` if `gate.owner == owner`, else `False` (AC-24).
   - If a wall or gate exists at `tile` with `hp <= 0`, treat it as not present (AC-25 — destroyed becomes passable). Caller is responsible for removing dead entities; this helper tolerates them present-but-dead.

2. `wall_or_gate_at(game: Game, tile: tuple[int, int]) -> Entity | None` — returns the first wall or gate entity at `tile` with `hp > 0`, else `None`. Convenience used by pathfinding + combat.

Do NOT implement pathfinding here. Do NOT mutate any state.

## Acceptance

Run `python -m pytest tests/test_walls.py -x -q`. Confirm RED. Implement in `sim/walls.py` only. Confirm GREEN. Write your final `test_file` and `impl_file` to `.swarm/pending/leaf-03/`.

Tests (build minimal Game instances inline; do not import other sim modules):
- Empty game, no walls: `is_passable_for(g, (5,5), 0) is True`
- Wall placed at (5,5) hp=200: `is_passable_for(g, (5,5), 0) is False` and same for owner=1 (AC-23)
- Gate placed at (5,5) owner=0 hp=200: `is_passable_for(g, (5,5), 0) is True`, `is_passable_for(g, (5,5), 1) is False` (AC-24)
- Wall at (5,5) hp=0: `is_passable_for(g, (5,5), 0) is True` (AC-25)
- `wall_or_gate_at(g, (5,5))` returns the entity when present and alive, None when absent or dead

## Escalation triggers

Stop and report to the parent if:
- A type the test imports is not in contract_imports.
- The impl would need to create a new file.
- The impl would need to edit a file in do_not_edit.
- Two sibling assertions seem to require contradictory behavior.
- Impl approaches impl_line_budget with assertions still failing.

## Assumption log

Write inferences to `briefs/leaf-03.ASSUMPTIONS.md`.
