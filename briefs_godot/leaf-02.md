---
leaf_id: leaf-02
spec_file: SPEC_GODOT.md
spec_lines: 96-125
test_file: godot/tests/test_map_gen.gd
impl_file: godot/sim/map_gen.gd
contract_imports:
  - sim.contract.MAP_W
  - sim.contract.MAP_H
  - sim.contract.Map
  - sim.contract.Game
  - sim.contract.Entity
do_not_edit:
  - godot/sim/contract.gd
  - godot/tests/test_contract.gd
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
impl_line_budget: 180
test_assertion_budget: 20
wave: 1
---

## Task

Port `sim/map_gen.py` (153 lines) to GDScript at `godot/sim/map_gen.gd` per SPEC_GODOT.md lines 96-125 (AC-46, AC-50, AC-51, AC-52) and the existing sim spec `SPEC.md` AC-28..AC-34.

Provide two public functions in `godot/sim/map_gen.gd`:

1. `generate_map(seed: int) -> Map` — returns a `Map` Resource (from `godot/sim/contract.gd`) with `width = MAP_W`, `height = MAP_H`, and a `terrain` 2D `Array` where `terrain[x][y]` is one of `TERRAIN_KINDS` (`"grass"`, `"tree"`, `"gold_mine"`). Deterministic per seed (SPEC.md AC-28). Tree placements form 4 cluster forests per side (~6 per cluster), within Chebyshev 12 of each player's TC anchor (AC-30). Gold mine placements: 2 per side, within Chebyshev 10 of each TC anchor (AC-31). Use one `RandomNumberGenerator` instance with `seed = <input>` per SPEC_GODOT.md AC-51. TC anchor for P0 is `Vector2i(10, 30)`; P1 is `Vector2i(70, 30)` (AC-29). Resource tile positions must NOT collide with TC anchors or the surrounding villager spawn ring.

2. `place_starting_entities(game: Game, seed: int) -> void` — mutates `game.entities` in place per SPEC.md AC-29, AC-32. Place exactly one `town_center` entity per player at the AC-29 anchor positions with `hp=max_hp=800`. Place exactly 5 `villager` entities per player on tiles surrounding their TC (`hp=max_hp=25`). For each `terrain[x][y] == "tree"`, append a `tree` entity at `(x, y)` with `hp=max_hp=40`, `owner=-1`. For each `terrain[x][y] == "gold_mine"`, append a `gold_mine` entity at `(x, y)` with `hp=max_hp=200`, `owner=-1`. Assign sequential `entity_id` starting at 0. Idempotent: calling twice on the same game must not duplicate entities (assert the entity count after the second call equals the first).

`game.visibility` and `game.explored_snapshots` are NOT touched here (AC-33). Per SPEC_GODOT.md AC-52, no `randomize()` calls and no global RNG state — only the per-call RNG instance.

Reference: read `sim/map_gen.py` lines 1-153 for the exact Python algorithm. Mirror the cluster-placement loop and the resource-collision avoidance.

## Acceptance

Run `"C:/Users/Westley Yarlott/Downloads/Godot_v4.6.3-stable_win64.exe" --headless --path godot/ -s addons/gut/gut_cmdln.gd -gtest=res://tests/test_map_gen.gd -gexit` for this test file. Confirm RED. Implement in `godot/sim/map_gen.gd` only. Confirm GREEN. Write your final files to `.swarm/pending/leaf-02/godot/sim/map_gen.gd` and `.swarm/pending/leaf-02/godot/tests/test_map_gen.gd`. Stop.

Tests you must include (1-2 assertions each):
- AC-28 / AC-51: `generate_map(42).terrain == generate_map(42).terrain` deep-equal.
- AC-28: `generate_map(42).width == MAP_W and generate_map(42).height == MAP_H`.
- AC-29: after `place_starting_entities`, exactly two `town_center` entities exist at `Vector2i(10, 30)` and `Vector2i(70, 30)` with `owner` 0 and 1 respectively.
- AC-30: tree count per side is in `[20, 30]` (4 forests × ~6 trees, allow ±25% slack) and every tree is within Chebyshev 12 of its side's TC.
- AC-31: exactly 2 gold mines per side, each within Chebyshev 10 of its side's TC.
- AC-32: exactly 5 villagers per player, each within Chebyshev 1 of its TC, not overlapping any building/resource tile.
- AC-34: every non-tree, non-gold_mine tile is `"grass"`.
- Idempotence: `place_starting_entities(game, 42)` called twice produces equal `[(e.kind, e.owner, e.pos) for e in game.entities]` lists.
- AC-51: a `RandomNumberGenerator` is the only RNG source (test by asserting two separate `generate_map(42)` calls produce equal terrain — covered by AC-28 above).
- AC-52: `randomize()` is not called (covered by determinism test).

## Escalation triggers

Stop and report to the parent if:
- A type the test imports is not in `contract_imports`.
- The impl would need to create a new file other than the two listed.
- The impl would need to edit a file in `do_not_edit`.
- Cluster-placement algorithm in `sim/map_gen.py` produces results that cannot be replicated in GDScript with `RandomNumberGenerator` (escalate; do not silently substitute another RNG).
- Impl approaches `impl_line_budget` (180) with assertions still failing.

## Assumption log

If at any point you inferred something not specified, write it to `briefs_godot/leaf-02.ASSUMPTIONS.md` before committing. Likely inferences: exact `RandomNumberGenerator` seeding subroutine, handling of edge cases when cluster placement collides with map boundaries, choice between `Array[String]` and `PackedStringArray` for `terrain` rows.
