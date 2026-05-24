---
leaf_id: leaf-10
spec_file: SPEC.md
spec_lines: 175-189
test_file: tests/test_ai.py
impl_file: sim/ai.py
contract_imports:
  - sim.contract.Game
  - sim.contract.Command
  - sim.contract.Entity
  - sim.contract.TICK_HZ
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
test_assertion_budget: 15
wave: 2
---

## Task

Implement the deterministic AI player script per SPEC.md lines 175-189 (§11 rules 1-10).

May import `sim.visibility.visible_entities_for` and `sim.entities` and `sim.building.BUILD_COSTS` / `TRAIN_COSTS` for cost lookups. The AI plays under fog by default (queries its own visible entities).

Provide in `sim/ai.py`:

1. `ai_tick(game: Game, player_id: int, tick: int) -> list[Command]` — returns the list of `Command`s the AI wants to issue this tick. Returns empty `[]` on most ticks; emits a batch every `2 * TICK_HZ` ticks (every 2 sim seconds) per §11. Each emitted Command must have `issuing_player=player_id`. Apply the priority rules in this order, emitting at most a small batch per tick (the rules are evaluated top-down, emit a command for the first rule that fires):

   1. If `pop < pop_cap` AND `wood >= 30` AND no house currently under construction by this player → emit `build(house, tile)` where tile is the nearest 2x2-clear cell within 6 tiles of the player's TC, using a deterministic search order (scan N,E,S,W spiraling out).
   2. If owned `barracks` count == 0 AND `wood >= 80` → emit `build(barracks, tile)` similarly near TC.
   3. If TC training queue empty AND owned `villager` count < 10 AND `wood >= 50` → emit `train(tc_id, "villager")`.
   4. If TC training queue empty AND owned `scout` count < 2 AND `wood >= 30` AND `gold >= 20` → emit `train(tc_id, "scout")`.
   5. If barracks training queue empty AND `wood >= 40` AND `gold >= 20` AND owned `soldier` count < 8 → emit `train(barracks_id, "soldier")`.
   6. If barracks training queue empty AND `wood >= 25` AND `gold >= 35` AND owned `archer` count < 4 → emit `train(barracks_id, "archer")`.
   7. If `barracks_count >= 1` AND owned `wall` count < 8 AND `wood >= 40` → emit `build(wall, tile)` on a tile forming part of an arc between TC and map midline. Use a fixed list of 8 candidate offsets relative to TC, filling the first unfilled one. Emit at most one wall per AI tick. Include `gate` instead of `wall` for one designated offset in the arc.
   8. Idle scouts → emit `move(scout_id, tile)` toward the nearest UNSEEN tile (Chebyshev distance) every 4 sim seconds.
   9. If owned `soldier` count >= 6 AND enemy TC visible-or-explored (read `game.explored_snapshots[player_id]` for an enemy town_center entry, OR check `visible_entities_for` for an enemy town_center) → emit `attack(soldier_id, enemy_tc_id)` for each idle soldier + archer. If enemy TC has never been seen → emit `move` toward map midline (40, 30) for each idle military unit.
   10. Idle villagers (not currently gathering, building, moving, or attacking) → emit `gather(villager_id, node_id)` toward nearest non-empty tree or gold_mine. Alternate wood/gold each AI tick.

2. The AI MUST NOT mutate `game` directly. It only emits commands; the orchestrator applies them via `sim.commands.apply_commands`.

3. AI internal bookkeeping (last-emitted-tick per rule, alternation state, designated-arc-offsets list) lives in a module-level `_ai_state: dict[int, _AIState]` keyed by `player_id`.

## Acceptance

Run `python -m pytest tests/test_ai.py -x -q`. Confirm RED. Implement in `sim/ai.py` only. Confirm GREEN. Write to `.swarm/pending/leaf-10/`.

Tests:
- `ai_tick(g, 1, 0)` on tick 0 returns a non-empty command list (first 2-sec batch fires); subsequent ticks 1..59 return `[]`
- Every command in the returned list has `issuing_player == 1`
- With a fresh game (no buildings yet), the first batch contains a `build(house, ...)` or `train(villager, ...)` per priority
- `ai_tick` for a player whose pop is at cap and has no House under construction emits a house-build command before any train command
- A snapshot of an enemy town_center in `explored_snapshots[1]` causes (once `soldier_count >= 6`) the AI to emit `attack` commands targeting that TC
- `ai_tick` does not mutate `game.entities`, `game.players`, or `game.visibility` (snapshot before + after equal)

## Escalation triggers

Stop and report to the parent if:
- A type the test imports is not in contract_imports (sim.* sibling imports permitted).
- The impl would need to create a new file.
- The impl would need to edit a file in do_not_edit.
- Two sibling assertions seem to require contradictory behavior.
- Impl approaches impl_line_budget with assertions still failing.

## Assumption log

Write inferences to `briefs/leaf-10.ASSUMPTIONS.md`.
