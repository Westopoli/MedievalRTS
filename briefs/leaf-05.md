---
leaf_id: leaf-05
spec_file: SPEC.md
spec_lines: 106-117
test_file: tests/test_visibility.py
impl_file: sim/visibility.py
contract_imports:
  - sim.contract.Game
  - sim.contract.Entity
  - sim.contract.Player
  - sim.contract.BuildingSnapshot
  - sim.contract.MAP_W
  - sim.contract.MAP_H
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
  - sim/gather.py
  - tests/test_gather.py
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
impl_line_budget: 180
test_assertion_budget: 20
wave: 1
---

## Task

Implement per-player fog-of-war computation per SPEC.md lines 106-117 (AC-15..AC-22).

May import `sim.entities.get_stats` for the `sight` field per entity kind.

Provide in `sim/visibility.py`:

1. `init_visibility(game: Game) -> None` — populate `game.visibility` as a length-`len(game.players)` list of `MAP_W x MAP_H` grids filled with `"unseen"`. Populate `game.explored_snapshots` as a length-`len(game.players)` list of empty dicts. Idempotent: if already initialized to correct shape, do nothing.

2. `recompute_visibility(game: Game) -> None` — for each player P:
   - For each tile, demote any tile currently `"visible"` to `"explored"` first (snapshot pass), then mark `"visible"` any tile within Chebyshev `sight` of a P-owned unit or P-owned building (`hp > 0`). Tiles that were `"unseen"` and are now seen become `"visible"` directly (not via `"explored"`).
   - Update `game.explored_snapshots[P]` for each enemy building (kind in `town_center, house, barracks, wall, gate`) currently in a `"visible"` tile: record/refresh a `BuildingSnapshot` with current `pos, kind, owner, hp_last_seen=entity.hp` (AC-19).
   - When an enemy building is destroyed (`hp <= 0`) AND it was in P's snapshots, leave the snapshot in place (it ghosts as a remembered-but-destroyed building); the snapshot's `hp_last_seen` may freeze at the last observed value.

3. `is_command_visible(game: Game, issuing_player: int, target_tile: tuple[int, int]) -> bool` — returns `True` if the target tile is `"visible"` OR `"explored"` for `issuing_player`, or if `game.players[issuing_player].fog_cheat is True`. Returns `False` for `"unseen"`. Used by the commands leaf to gate command application per AC-21/AC-22.

4. `visible_entities_for(game: Game, viewer_player: int) -> list[Entity]` — returns the subset of `game.entities` the viewer can currently see. Always includes the viewer's own entities. Enemy units are included only if their `pos` is `"visible"` to viewer (AC-18). Enemy buildings: include the live entity if `pos` is `"visible"`; otherwise include nothing for that building (the snapshot is in `explored_snapshots` and rendered by the frontend separately).

## Acceptance

Run `python -m pytest tests/test_visibility.py -x -q`. Confirm RED. Implement in `sim/visibility.py` only. Confirm GREEN. Write to `.swarm/pending/leaf-05/`.

Tests:
- `init_visibility` produces correct shape grids of all `"unseen"`
- A single villager (owner=0) at (10, 10) — after `recompute_visibility`, tiles within Chebyshev 5 are `"visible"` for player 0, others `"unseen"`
- Symmetry: tiles owned by player 1's villager at (70, 30) are `"visible"` for player 1, `"unseen"` for player 0
- A unit moves out of sight: a previously-visible tile becomes `"explored"` (not `"unseen"`) on next recompute
- `is_command_visible` returns False for unseen tile, True for explored, True for visible
- `is_command_visible` returns True for ANY tile when `fog_cheat` is set on the issuing player (AC-22)
- `visible_entities_for(g, 0)` excludes a player-1 villager standing in a tile that is `"unseen"` to player 0
- `recompute_visibility` updates `explored_snapshots[0]` with a `BuildingSnapshot` of a player-1 building once the player-1 building is in a `"visible"` tile for player 0

## Escalation triggers

Stop and report to the parent if:
- A type the test imports is not in contract_imports (`sim.entities.get_stats` cross-leaf import is permitted).
- The impl would need to create a new file.
- The impl would need to edit a file in do_not_edit.
- Two sibling assertions seem to require contradictory behavior.
- Impl approaches impl_line_budget with assertions still failing.

## Assumption log

Write inferences to `briefs/leaf-05.ASSUMPTIONS.md`.
