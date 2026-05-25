---
leaf_id: leaf-01
spec_file: SPEC_GODOT.md
spec_lines: 60-94
test_file: godot/tests/test_contract.gd
impl_file: godot/sim/contract.gd
contract_imports:
  - sim.contract.TILE_SIZE
  - sim.contract.MAP_W
  - sim.contract.MAP_H
  - sim.contract.TICK_HZ
  - sim.contract.POP_CAP_START
  - sim.contract.POP_CAP_MAX
  - sim.contract.CARRY_CAP
  - sim.contract.START_WOOD
  - sim.contract.START_GOLD
  - sim.contract.CAMERA_SCROLL_SPEED
  - sim.contract.NUM_PLAYERS
  - sim.contract.Command
  - sim.contract.Entity
  - sim.contract.Player
  - sim.contract.BuildingSnapshot
  - sim.contract.Map
  - sim.contract.Game
do_not_edit:
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
  - godot/icon.svg
  - godot/icon.png
  - godot/scenes/**
  - godot/scripts/**
  - godot/addons/**
  - godot/tests/test_umbrella.gd
  - godot/tests/fixtures/**
  - godot/export_presets.cfg
  - app/**
  - assets/**
impl_line_budget: 220
test_assertion_budget: 25
wave: 1
---

## Task

Port `sim/contract.py` to GDScript at `godot/sim/contract.gd` per SPEC_GODOT.md lines 60-94 (AC-41 through AC-45).

The file must contain, in this order:

1. A file-level docstring (`## ...` comment block) noting that this file mirrors `sim/contract.py` and is parent-owned after this leaf lands.
2. All eleven top-level `const` declarations from SPEC_GODOT.md AC-41 with the literal values copied from `sim/contract.py`: `TILE_SIZE = 64`, `MAP_W = 80`, `MAP_H = 60`, `TICK_HZ = 30`, `POP_CAP_START = 5`, `POP_CAP_MAX = 50`, `CARRY_CAP = 10`, `START_WOOD = 300`, `START_GOLD = 150`, `CAMERA_SCROLL_SPEED = 800`, `NUM_PLAYERS = 2`.
3. The five `const Array[String]` kind arrays from SPEC_GODOT.md AC-42 — `ENTITY_KINDS`, `RESOURCE_KINDS`, `COMMAND_KINDS`, `TERRAIN_KINDS`, `VISIBILITY_STATES` — with members in the order specified in AC-42.
4. Six inner classes per SPEC_GODOT.md AC-43, each declared as `class ClassName extends Resource` with all fields typed per the AC-43 mapping table. The classes, in this order: `Command`, `Entity`, `Player`, `BuildingSnapshot`, `Map`, `Game`.
5. The `Game` class includes a `func tick(inputs: Array) -> void:` whose body is `push_error("Game.tick not implemented; see godot/sim/game.gd"); return` per SPEC_GODOT.md AC-44.

Field types follow the AC-43 mapping exactly: `tuple[int, int]` → `Vector2i`, `Literal` → `String`, `Optional[X]` → `Variant` defaulting to `null`, `list[X]` → `Array[X]` (or untyped `Array` where the element is itself a nested array per AC-43's `Map.terrain` line), `dict[K, V]` → `Dictionary`.

The Game class field named `map` in the Python dataclass is renamed `map_` in GDScript per the AC-43 footnote (avoids the GDScript `map` builtin name collision). All other field names match Python exactly.

This file is the GDScript type contract for the entire Godot port. It is the ONLY file in `godot/sim/` that may declare classes; sibling leaves consume these classes via `preload("res://sim/contract.gd")`. No other leaf in this wave may add, remove, or rename a symbol declared here per SPEC_GODOT.md AC-45.

## Acceptance

Run `"C:/Users/Westley Yarlott/Downloads/Godot_v4.6.3-stable_win64.exe" --headless --path godot/ -s addons/gut/gut_cmdln.gd -gtest=res://tests/test_contract.gd -gexit` for this test file. Confirm RED (file does not exist yet). Implement in `godot/sim/contract.gd` only. Confirm GREEN. Write your final `test_file` and `impl_file` to `.swarm/pending/leaf-01/godot/sim/contract.gd` and `.swarm/pending/leaf-01/godot/tests/test_contract.gd`. Stop. Do not copy files to their real destinations — `/swarm-merge` does that after gating.

Tests you must include (each is one or two assertions):
- AC-41: every constant from `sim/contract.py` is present and equals the Python value (assert `Contract.TILE_SIZE == 64`, `Contract.MAP_W == 80`, etc., for all 11 constants — 11 assertions).
- AC-42: every kind array has the exact members in declaration order (e.g., `assert_eq(Contract.ENTITY_KINDS, ["villager", "soldier", "archer", "scout", "town_center", "house", "barracks", "wall", "gate", "tree", "gold_mine"])` — 5 assertions).
- AC-43: a `Contract.Command.new()` returns a Resource subclass instance with all default field values (kind=null/empty, issuing_player=0, entity_id=-1, etc.).
- AC-43: a `Contract.Entity.new(7, "villager", 0, Vector2i(3,4), 25, 25)` returns a Resource subclass instance with the assigned field values.
- AC-43: a `Contract.Player.new(0, 300, 150, 5)` returns a Resource subclass instance whose `fog_cheat` defaults to `false`.
- AC-43: a `Contract.Map.new(80, 60, [])` instance accepts the construction args and the `terrain` field is `Array`-typed.
- AC-43: a `Contract.Game.new([], [], Contract.Map.new(80, 60, []))` instance has `tick_count == 0`, `over == false`, `winner == null`, `visibility == []`, `explored_snapshots == []`.
- AC-44: calling `game.tick([])` on a fresh `Contract.Game` instance emits a `push_error` (test via `assert_eq(gut.get_logger().get_errors().size() >= 1, true)` after the call). The function must return without crashing.
- AC-45 (negative check, optional): assert that `contract.gd` does not define functions other than the `Game.tick` stub. Implementation: scan the script bytecode or simply assert the file-level method set matches an allowlist. If this check is too brittle in GUT, skip it; the parent enforces AC-45 via the `do_not_edit` check at `/swarm-review`.

## Escalation triggers

Stop and report to the parent if:
- A type the test imports is not in the contract_imports list above.
- The impl would need to create a new file other than `godot/sim/contract.gd` and `godot/tests/test_contract.gd`.
- The impl would need to edit a file in `do_not_edit`.
- Two sibling assertions seem to require contradictory behavior.
- Impl approaches `impl_line_budget` (220) with assertions still failing.
- GUT's Resource subclass introspection is insufficient to verify AC-43 field types — escalate so the parent can adjust the AC text rather than the leaf inferring a workaround.

## Assumption log

If at any point you inferred something not specified, write it to `briefs_godot/leaf-01.ASSUMPTIONS.md` before committing. One bullet per inference with source citation. Examples of likely inferences: default value for `Variant` fields, exact syntax for nested `class Foo extends Resource` declarations, whether to use `@export` decorators on Resource fields.
