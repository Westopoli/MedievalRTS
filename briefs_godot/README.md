# briefs_godot — Wave 1 of the Godot port cascade

This directory holds the leaf briefs for **wave 1** of the Medieval RTS Godot port. Wave 1 = hand-port of all 11 Python sim modules to GDScript + per-leaf GUT parity tests.

## Wave 1 leaves

| Leaf | Module | Impl | Test | Python source |
|---|---|---|---|---|
| leaf-01 | type contract | `godot/sim/contract.gd` | `godot/tests/test_contract.gd` | `sim/contract.py` |
| leaf-02 | map gen | `godot/sim/map_gen.gd` | `godot/tests/test_map_gen.gd` | `sim/map_gen.py` |
| leaf-03 | entity stats + factories | `godot/sim/entities.gd` | `godot/tests/test_entities.gd` | `sim/entities.py` |
| leaf-04 | walls + gates | `godot/sim/walls.gd` | `godot/tests/test_walls.gd` | `sim/walls.py` |
| leaf-05 | pathfinding + movement | `godot/sim/pathfinding.gd` | `godot/tests/test_pathfinding.gd` | `sim/pathfinding.py` |
| leaf-06 | fog of war | `godot/sim/visibility.gd` | `godot/tests/test_visibility.gd` | `sim/visibility.py` |
| leaf-07 | gather + deposit | `godot/sim/gather.gd` | `godot/tests/test_gather.gd` | `sim/gather.py` |
| leaf-08 | combat + death cleanup | `godot/sim/combat.gd` | `godot/tests/test_combat.gd` | `sim/combat.py` |
| leaf-09 | construction + training | `godot/sim/building.gd` | `godot/tests/test_building.gd` | `sim/building.py` |
| leaf-10 | command dispatch + fog gate | `godot/sim/commands.gd` | `godot/tests/test_commands.gd` | `sim/commands.py` |
| leaf-11 | AI script | `godot/sim/ai.gd` | `godot/tests/test_ai.gd` | `sim/ai.py` |
| leaf-12 | game tick orchestrator + new_game | `godot/sim/game.gd` | `godot/tests/test_game.gd` | `sim/game.py` |

All 12 leaves run in **wave 1** (parallel). No sibling-edit overlap; each leaf owns exactly one impl + one test file. The shared type contract (`godot/sim/contract.gd`) is owned by leaf-01 in this wave and becomes parent-owned afterward per SPEC_GODOT.md AC-45.

## Not in this wave

The render layer (TileMapLayer terrain render, ColorRect entities, fog overlay, debug HUD), the input layer (mouse-click → Command pipeline), the camera (edge-pan + clamp), and the `project.godot` shell are **parent-owned scaffolding** that lives outside the swarm cascade. They are listed in SPEC_GODOT.md §§ 6-10 so the umbrella can assert against them, but the leaf briefs do NOT own those files.

Sprite art (Kenney pack swap), sound, menus, save/load, networked multiplayer, and the Steam export presets are deferred to later waves.

## Source-of-truth note

The 12 leaves port from the Python sim at commit `1cc5e95`. Three landed bug fixes in the Python source are part of the contract that the port must preserve:

1. `sim/gather.py` — adjacent-tile pathing + idempotent re-issue (commit `6deed4b`).
2. `sim/combat.py` — integer-exact damage math + idempotent attack re-issue + chase re-path only when destination drifted (commit `183316c`).
3. `sim/ai.py` — `(sol_n + arch_n) >= 3` attack trigger (NOT `sol_n >= 6`), `claimed_eids` per-tick claim tracking, villager_reserve for first barracks, scout gated on barracks (commit `183316c`).

If a leaf reads the Python source and sees behavior that doesn't match the brief, the brief is authoritative — escalate to the parent.

## How to proceed

1. **Parent (this chat) verifies the briefs.** Run `/swarm-review` from the repo root. Do not spawn any leaf agents until `/swarm-review` reports `all PASS`.
2. **Set up the Godot shell.** Parent (outside the cascade) creates `godot/project.godot`, vendors the GUT addon at `godot/addons/gut/`, regenerates the parity fixture at `godot/tests/fixtures/parity_seed42_first600.csv` from the Python sim, and writes the RED `godot/tests/test_umbrella.gd` per SPEC_GODOT.md § 15.
3. **Spawn the 12 leaves in parallel.** Each leaf works in its own task, writes only its owned impl + test, lands in `.swarm/pending/leaf-NN/`.
4. **Per-leaf merge.** Run `/swarm-merge leaf-NN` for each green leaf. Order does NOT matter within wave 1 — leaves are designed to be independent at merge time.
5. **Run the umbrella.** After all 12 leaves merge, the parent runs `test_umbrella.gd` end-to-end. If GREEN: wave 1 is done and wave 2 (render / input / camera scaffolding + Kenney sprite swap) can begin.
6. **Parent assumption-sweep.** Before wave 2, sweep `briefs_godot/leaf-NN.ASSUMPTIONS.md` files for cross-leaf inferences per the `/swarm` skill's sweep protocol.

## Files in this directory

- `README.md` — this file.
- `leaf-01.md` ... `leaf-12.md` — one brief per leaf.
- `leaf-NN.ASSUMPTIONS.md` — written by leaves at runtime (one per leaf that had to infer something).
- `ASSUMPTIONS.md` — parent's intake assumption log (none yet — intake was fully interactive).
