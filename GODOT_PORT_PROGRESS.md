# Godot Port Planning — Progress Checkpoint

This file tracks the state of the Godot port planning workstream so a
compacted future chat can resume without losing position.

## Context
- Repo: `iCode/Demos/MedievalRTS/` (single repo for Python sim + Godot port).
- Python sim: locked at commit `1cc5e95`, 105/105 pytest green, balance settled.
- Godot port: subdir `godot/`, hand-port of all 11 sim modules to GDScript + GUT parity tests.
- Vertical slice: player has 1 villager, AI opponent (default-AI ported) plays full economy, scrolling camera, fog, placeholder ColorRect rendering.
- Sprite swap (Kenney) deferred. Sound/menus/save/networked deferred.
- Locks from user this session: subdir layout (not separate repo); ~12 leaves (1:1 sim mirror); placeholder colors first; TileMapLayer for tiles; full 80x60 + scrolling cam; /swarm-review only as reviewer; AI opponent in slice.

## Cascade phase
Running `/swarm` (planning skill). Parent (this chat) owns ALL planning. No subagent delegation. After briefs land, run `/swarm-review` next.

## Status checklist

- [x] Confirm Godot 4.6.3 binary present (`~/Downloads/Godot_v4.6.3-stable_win64.exe`)
- [x] Confirm `.claude-swarm.toml` exists at repo root (already configured for Python sim)
- [x] Draft `SPEC_GODOT.md` (254 lines, AC-38..AC-73, 36 new ACs continuing sim's 1-37)
- [x] Extend `.claude-swarm.toml` `parent_owned` for Godot wave
- [x] Draft `briefs_godot/leaf-01.md` (contract.gd)
- [x] Draft `briefs_godot/leaf-02.md` (map_gen.gd)
- [x] Draft `briefs_godot/leaf-03.md` (entities.gd)
- [x] Draft `briefs_godot/leaf-04.md` (walls.gd)
- [x] Draft `briefs_godot/leaf-05.md` (pathfinding.gd)
- [x] Draft `briefs_godot/leaf-06.md` (visibility.gd)
- [x] Draft `briefs_godot/leaf-07.md` (gather.gd)
- [x] Draft `briefs_godot/leaf-08.md` (combat.gd)
- [x] Draft `briefs_godot/leaf-09.md` (building.gd)
- [x] Draft `briefs_godot/leaf-10.md` (commands.gd)
- [x] Draft `briefs_godot/leaf-11.md` (ai.gd)
- [x] Draft `briefs_godot/leaf-12.md` (game.gd)
- [x] Draft `briefs_godot/README.md` (wave-1 summary)
- [x] Hand-off message to user: "run /swarm-review next"

## Decisions already locked (do NOT re-litigate)
- Layout: `godot/` subdir inside existing MedievalRTS repo.
- Sim port style: full hand-port + GUT parity tests, no IPC bridge to Python.
- Render: placeholder ColorRect per entity kind. TileMapLayer for terrain tiles. Sprite swap to Kenney pack happens AFTER vertical slice plays.
- Map: full 80x60 to match sim.
- Camera: edge-pan + clamp per existing SPEC.md AC-1..AC-4. Engine-time, not sim-time.
- Slice opponent: P1 runs `default_ai` ported to `godot/sim/ai.gd`. P0 is human, given 1 villager.
- Wave 1 scope = sim parity port only. Render/input/camera scene tree = parent-owned wave 2.
- Reviewer: `/swarm-review` only.

## Open inferences (to be logged in ASSUMPTIONS.md as drafted)
- TBD as drafting proceeds. Examples I expect to log:
  - GDScript class shape for Command/Entity/Player (Resource subclass vs dict vs Object)
  - GUT addon source (addons/gut/ vs project plugin manifest)
  - Coordinate convention: sim (x,y) tile -> Godot world pixels via tile_size constant
  - Whether `_construction` / `_attack_state` / `_gather_state` module-level dicts in Python become Autoload singletons or class-instance dicts in GDScript

## How to resume after compaction
1. Read this file first.
2. Check the boxes above — first unchecked item is your next action.
3. Re-read `SPEC.md`, `sim/contract.py`, and `briefs/leaf-01.md` (template anchor) before drafting any new artifact.
4. Do NOT spawn subagents for drafting. Parent owns all planning.
5. After all briefs land, hand off with: "Briefs written to briefs_godot/. Run /swarm-review next."

## Files touched by this planning phase
- `GODOT_PORT_PROGRESS.md` (this file — checkpoint only, no impl content)
- `SPEC_GODOT.md` (pending)
- `briefs_godot/leaf-01.md` ... `leaf-12.md` (pending)
- `briefs_godot/README.md` (pending)
- `.claude-swarm.toml` (parent_owned extension pending)
