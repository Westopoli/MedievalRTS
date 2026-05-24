---
leaf_id: leaf-11
spec_file: SPEC.md
spec_lines: 126-138
test_file: tests/test_game.py
impl_file: sim/game.py
contract_imports:
  - sim.contract.Game
  - sim.contract.Command
  - sim.contract.Player
  - sim.contract.Map
  - sim.contract.POP_CAP_START
  - sim.contract.START_WOOD
  - sim.contract.START_GOLD
  - sim.contract.NUM_PLAYERS
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
  - sim/commands.py
  - sim/ai.py
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
test_assertion_budget: 18
wave: 2
---

## Task

Implement the `Game.tick` orchestrator + `new_game` factory + a scripted-player command source for the umbrella, per SPEC.md lines 126-138 (§9 tick loop) and §13 win condition.

May import every wave-1 + wave-2 sibling module: `sim.map_gen`, `sim.visibility`, `sim.commands`, `sim.pathfinding`, `sim.gather`, `sim.combat`, `sim.building`, `sim.ai`. Plus `sim.contract`.

Provide in `sim/game.py`:

1. `new_game(seed: int = 42, num_players: int = NUM_PLAYERS) -> Game` — constructs a `Game` instance:
   - `map = generate_map(seed)`
   - `players = [Player(player_id=i, wood=START_WOOD, gold=START_GOLD, pop_cap=POP_CAP_START) for i in range(num_players)]`
   - `entities = []`, then call `sim.map_gen.place_starting_entities(g, seed)`
   - `tick_count = 0, over = False, winner = None`
   - Initialize visibility via `sim.visibility.init_visibility(g)` and one initial `recompute_visibility(g)` so fog reflects starting positions.
   - Return the Game.

2. Override `Game.tick`: monkey-patch `sim.contract.Game.tick` to call a module-level `_tick(game, inputs)` function. Order per AC §9:
   1. If `game.over` is True, return immediately (AC-37). Do NOT increment `tick_count`.
   2. `sim.commands.apply_commands(game, inputs)`
   3. `sim.pathfinding.tick_movement(game)`
   4. `sim.gather.tick_gather(game)`
   5. `sim.building.tick_construction(game)` then `sim.building.tick_training(game)`
   6. `sim.combat.tick_combat(game)`
   7. `sim.visibility.recompute_visibility(game)`
   8. Check win condition: for each player p, if NO `town_center` entity exists owned by p, the OTHER player wins. If exactly one player has a TC, set `game.winner` to that player's id and `game.over = True`. (Tie / both TCs destroyed in the same tick: lower-id player wins as deterministic tiebreaker.)
   9. Increment `game.tick_count`.

3. `scripted_player_commands(game: Game, player_id: int, tick: int) -> list[Command]` — used by the umbrella's `test_full_scripted_match_terminates_with_winner`. Returns deterministic commands for player 0 based on tick:
   - tick == 60 (2 sec): emit a `build(house, ...)` near player TC.
   - tick == 300 (10 sec): emit a `build(barracks, ...)` near player TC.
   - tick == 600 (20 sec): emit two `build(wall, ...)` and one `build(gate, ...)` along an arc between player TC and the map midline.
   - tick == 900 (30 sec): emit `train(tc_id, "scout")`.
   - tick == 1200, 1400, 1600 (40s, ~46s, ~53s): emit `train(barracks_id, "soldier")` (one each).
   - tick == 1800, 2000 (60s, ~66s): emit `train(barracks_id, "archer")`.
   - tick == 3000 (100 sec): for each owned soldier and archer, emit `move` toward (45, 30) (midline poke).
   - tick == 4500 (150 sec): for each owned military unit, if enemy TC is visible-or-explored, emit `attack(unit_id, enemy_tc_id)`; else continue moving toward (70, 30).
   - All other ticks: return `[]`.

   This script may issue commands referencing tiles that are UNSEEN to player 0; that's fine — the commands leaf's fog gate may drop them, and the script's role is only to provide a deterministic minimum. (We are NOT enabling fog_cheat for player 0 in this script.)

   Use `sim.visibility.visible_entities_for(game, 0)` to find the enemy TC id if visible/explored.

## Acceptance

Run `python -m pytest tests/test_game.py -x -q`. Confirm RED. Implement in `sim/game.py` only. Confirm GREEN. Write to `.swarm/pending/leaf-11/`.

Tests:
- `new_game(seed=42)` returns a Game with 2 players, the right starting wood/gold/pop_cap, and entities placed by map_gen
- `g.tick([])` once: `tick_count == 1`, visibility computed (player 0 has VISIBLE tiles near (10,30))
- After many `g.tick([])` calls, no exception is raised; `tick_count` matches the number of ticks
- A scripted command in `inputs` reaches the apply layer (e.g. a stop command actually clears state)
- Setting `g.over = True` then calling `g.tick([cmd])`: `tick_count` does NOT advance (AC-37)
- Manually setting hp=0 on player 1's town_center then calling `g.tick([])`: `g.over` becomes True and `g.winner == 0`
- `scripted_player_commands(g, 0, 60)` returns a non-empty list containing exactly one `build` command with `building_kind == "house"`
- `scripted_player_commands(g, 0, 61)` returns `[]`

## Escalation triggers

Stop and report to the parent if:
- A type the test imports is not in contract_imports (sim.* sibling imports permitted).
- The impl would need to create a new file.
- The impl would need to edit a file in do_not_edit.
- Two sibling assertions seem to require contradictory behavior.
- Impl approaches impl_line_budget with assertions still failing.

## Assumption log

Write inferences to `briefs/leaf-11.ASSUMPTIONS.md`.
