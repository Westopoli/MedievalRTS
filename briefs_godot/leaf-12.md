---
leaf_id: leaf-12
spec_file: SPEC_GODOT.md
spec_lines: 127-160
test_file: godot/tests/test_game.gd
impl_file: godot/sim/game.gd
contract_imports:
  - sim.contract.Command
  - sim.contract.Entity
  - sim.contract.Game
  - sim.contract.Map
  - sim.contract.Player
  - sim.contract.MAP_W
  - sim.contract.MAP_H
  - sim.contract.TICK_HZ
  - sim.contract.START_WOOD
  - sim.contract.START_GOLD
  - sim.contract.POP_CAP_START
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
  - godot/sim/combat.gd
  - godot/tests/test_combat.gd
  - godot/sim/building.gd
  - godot/tests/test_building.gd
  - godot/sim/commands.gd
  - godot/tests/test_commands.gd
  - godot/sim/ai.gd
  - godot/tests/test_ai.gd
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
test_assertion_budget: 25
wave: 1
---

## Task

Port `sim/game.py` (265 lines) to GDScript at `godot/sim/game.gd` per SPEC_GODOT.md lines 127-160 (AC-53, AC-54, AC-72, AC-73) and SPEC.md § 9 (tick orchestration) + AC-35, AC-36, AC-37 (win condition).

Provide these public functions:

1. `new_game(seed: int) -> Game` — constructs a fresh `Game` Resource per `sim/contract.gd`. Initializes 2 `Player` instances with `START_WOOD` / `START_GOLD` / `POP_CAP_START`. Calls `map_gen.generate_map(seed)` and assigns to `game.map_`. Calls `map_gen.place_starting_entities(game, seed)`. Calls `visibility.init_visibility(game)` and `visibility.recompute_visibility(game)` once for tick 0. Returns the game.

2. `tick_game(game: Game, inputs: Array) -> void` — replaces the `Game.tick` body declared in `contract.gd`. The `contract.gd` `tick()` method delegates to this function via `var game_mod = load("res://sim/game.gd"); game_mod.tick_game(self, inputs)`. Per SPEC.md § 9, runs the per-tick order:

   1. If `game.over`, early-return (AC-37).
   2. Apply each command via `commands.apply_command(game, cmd)`. Commands with `issuing_player` mismatches are silently dropped.
   3. `pathfinding.tick_movement(game)`.
   4. `gather.tick_gather(game)`.
   5. `building.tick_construction(game)`.
   6. `combat.tick_combat(game)`.
   7. `building.tick_training(game)`.
   8. `visibility.recompute_visibility(game)`.
   9. Win check (AC-35, AC-36): for each player, count `town_center` entities with `owner == player_id` and `hp > 0`. If exactly one player has TCs alive, set `game.over = true`, `game.winner = that_player_id`.
   10. Increment `game.tick_count`.

   Late-bind every sibling via `load("res://sim/<module>.gd")` per AC-49.

3. `scripted_player_commands(game: Game, player_id: int, tick: int) -> Array` — placeholder helper used by the umbrella for spot-check tests. Returns `[]` by default; the umbrella may override per-tick command lists by passing them directly to `tick_game(game, inputs)`.

Per SPEC_GODOT.md AC-72, AC-73: this leaf is responsible for declaring (NOT generating) the parity-log fixture at `godot/tests/fixtures/parity_seed42_first600.csv`. The leaf brief includes instructions to regenerate the fixture from Python via:

```
cd iCode/Demos/MedievalRTS
python -c "
from sim.game import new_game
g = new_game(seed=42)
print('tick,eid,hp')
for t in range(600):
    g.tick([])
    for e in g.entities:
        print(f'{t},{e.entity_id},{e.hp}')
" > godot/tests/fixtures/parity_seed42_first600.csv
```

The leaf may NOT modify the fixture (it's parent-owned per `.claude-swarm.toml`). The leaf's test file READS the fixture and compares the GDScript run against it.

## Acceptance

Run `"C:/Users/Westley Yarlott/Downloads/Godot_v4.6.3-stable_win64.exe" --headless --path godot/ -s addons/gut/gut_cmdln.gd -gtest=res://tests/test_game.gd -gexit` for this test file. Confirm RED. Implement in `godot/sim/game.gd` only. Confirm GREEN. Write your final files to `.swarm/pending/leaf-12/`. Stop.

Tests must include:
- `new_game(42)` returns a Game with 2 Players, 80×60 map, 2 TCs at `Vector2i(10, 30)` and `Vector2i(70, 30)`, 5 villagers per player.
- `new_game(42).visibility` has shape `[2, 80, 60]`.
- `tick_game(g, [])` increments `g.tick_count`.
- After 1 tick, P0's tile `(10, 30)` is `"visible"` for player 0 (TC has sight 8).
- A `Command(kind="train", building_id=tc_id, unit_kind="villager", issuing_player=0)` issued to `tick_game` causes (after `TICK_HZ * 12` ticks) a new villager Entity to exist owned by player 0.
- After a P1 TC has its hp set to 0 manually, the next `tick_game` sets `game.over = true` and `game.winner = 0` (AC-35).
- After `game.over = true`, further `tick_game` calls do NOT increment `tick_count` (AC-37).
- Parity (AC-72): run 600 ticks of `new_game(42)` with no inputs. For each `(tick, entity_id)` row in `godot/tests/fixtures/parity_seed42_first600.csv`, the corresponding GDScript entity has the same hp.

## Escalation triggers

Stop and report to the parent if:
- A type the test imports is not in `contract_imports`.
- The Python `sim/game.py::_tick` orchestrator monkey-patches `Game.tick` (the file does this at module level). The GDScript equivalent should be the `tick_game(game, inputs)` static-ish function — escalate if the dispatch from `contract.gd::Game.tick` to `tick_game` cannot be wired per the task above.
- The parity fixture is missing (parent must regenerate via the Python command above before this leaf's tests can pass).
- Impl approaches `impl_line_budget` (220) with assertions still failing.
- The "exactly one player has TCs alive" win condition is ambiguous when both players' TCs die in the same tick — fall back to `winner = null` and `over = true`, document in the assumption log.

## Assumption log

If at any point you inferred something not specified, write it to `briefs_godot/leaf-12.ASSUMPTIONS.md`. Likely inferences: how to attach `tick_game` to the `Game.tick` method (GDScript has no monkey-patching — the `tick()` method on the Game Resource delegates via `load()` per the task above), parity tolerance on hp (currently 0 — exact match required by AC-72).
