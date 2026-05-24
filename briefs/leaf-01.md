---
leaf_id: leaf-01
spec_file: SPEC.md
spec_lines: 192-202
test_file: tests/test_map_gen.py
impl_file: sim/map_gen.py
contract_imports:
  - sim.contract.Map
  - sim.contract.Game
  - sim.contract.Entity
  - sim.contract.TerrainKind
  - sim.contract.MAP_W
  - sim.contract.MAP_H
do_not_edit:
  - sim/contract.py
  - sim/__init__.py
  - sim/entities.py
  - sim/walls.py
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
impl_line_budget: 180
test_assertion_budget: 18
wave: 1
---

## Task

Implement deterministic map generation per SPEC.md lines 192-202 (AC-28 through AC-34).

Provide two public functions in `sim/map_gen.py`:

1. `generate_map(seed: int) -> Map` — returns a `Map` instance with `width=MAP_W`, `height=MAP_H`, and a `terrain` 2D list (`terrain[x][y]`) of `TerrainKind` literals. Same seed must produce byte-identical output (AC-28). All non-resource tiles are `"grass"`. Tree tiles are placed in 4 cluster forests per side (~6 per cluster), within 12 tile Chebyshev distance of each player's Town Center anchor (AC-30). Gold mine tiles: 2 per side, within 10 tile Chebyshev distance of each TC anchor (AC-31). Use Python's `random.Random(seed)` (no global state). TC anchor for player 0 is `(10, 30)`; for player 1 is `(70, 30)` (AC-29). Resource node tile positions must NOT collide with TC anchors or villager spawn ring.

2. `place_starting_entities(game: Game, seed: int) -> None` — mutates `game.entities` in place. Must:
   - Place exactly one `town_center` entity per player at the AC-29 anchor positions with `hp=max_hp=800`.
   - Place exactly 5 `villager` entities per player on the 8 tiles surrounding their TC (`hp=max_hp=25`).
   - For each `terrain[x][y] == "tree"`, add a `tree` entity at `(x, y)` with `hp=max_hp=40` and `owner=-1` (no owner).
   - For each `terrain[x][y] == "gold_mine"`, add a `gold_mine` entity at `(x, y)` with `hp=max_hp=200` and `owner=-1`.
   - Each entity gets a unique sequential `entity_id` starting at 0.
   - Must be deterministic given the same seed and the same starting `game.entities` (no duplicates if called once).

Fog of war state initialization is NOT done here — `game.visibility` and `game.explored_snapshots` stay untouched by this module (AC-33).

## Acceptance

Run `python -m pytest tests/test_map_gen.py -x -q` for this test file. Confirm RED. Implement in `sim/map_gen.py` only. Confirm GREEN. Write your final `test_file` and `impl_file` to `.swarm/pending/leaf-01/` mirroring their paths from the project root (e.g. `sim/map_gen.py` → `.swarm/pending/leaf-01/sim/map_gen.py`). Stop. Do not copy files to their real destinations — `/swarm-merge` does that after gating.

Tests you must include (each is one or two assertions):
- AC-28: `generate_map(42).terrain == generate_map(42).terrain`
- AC-28: `generate_map(42).width == MAP_W and generate_map(42).height == MAP_H`
- AC-29: after `place_starting_entities`, exactly two town_centers exist at (10,30) and (70,30) with correct owners
- AC-30: tree count per side is in `range(20, 31)` and every tree is within Chebyshev 12 of its side's TC
- AC-31: exactly 2 gold mines per side, each within Chebyshev 10 of its side's TC
- AC-32: exactly 5 villagers per player, each adjacent (Chebyshev <= 1) to its TC, not overlapping any building/resource tile
- AC-34: non-tree, non-gold_mine tiles are `"grass"`
- Two calls to `place_starting_entities` on fresh games with seed 42 produce equal `[(e.kind, e.owner, e.pos) for e in g.entities]` lists

## Escalation triggers

Stop and report to the parent if:
- A type the test imports is not in contract_imports.
- The impl would need to create a new file.
- The impl would need to edit a file in do_not_edit.
- Two sibling assertions seem to require contradictory behavior.
- Impl approaches impl_line_budget with assertions still failing.

## Assumption log

If at any point you inferred something not specified, write it to `briefs/leaf-01.ASSUMPTIONS.md` before committing. One bullet per inference with source citation.
