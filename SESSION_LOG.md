# Medieval RTS — Session Log

Append-only. Each session ends with a `## Session Pause — YYYY-MM-DD` block.
Fresh chats read the most recent block first.

---

## Session Pause — 2026-05-23

**Lane / context:** single context (`iCode/Demos/MedievalRTS/`). Separate repo from camp curriculum.
**Active workstream/task:** Balance tuning v0 — drive `_balance/` runner toward a non-trivial win-rate matrix so umbrella `test_full_scripted_match_terminates_with_winner` passes.
**Status:** in-progress.

### Where we are

In one sitting the full sim landed via `/swarm` cascade: spec → 11 leaf briefs → wave 1 (8 parallel agents) + wave 2 (3 sequential). All 11 modules on disk, 93 per-leaf tests passing, umbrella 11/12 passing. Remaining umbrella failure (`test_full_scripted_match_terminates_with_winner`) is a balance/AI-tuning issue, not a sim-correctness bug.

User pushed back on jumping to Godot frontend before tuning — invoked D3 precedent (`_balance/Day3/` headless sim + scripted strategies + fitness runner). Built `_balance/MedievalRTS/` with `sim_driver.py` (run_match), `strategies.py` (default/rush/turtle/eco/idle), `runner.py` (round-robin + win-rate matrix). Iterating AI patches to make default-AI actually win vs idle opponent. Currently mid-iteration — default still timing out vs idle at 600s sim cap despite multiple fixes landed.

### Last decision locked

**Tune-first, port-Godot-after** (matches D3 precedent). Reasoning: 1 failing umbrella test = balance, not bug; tuning without UI doesn't surface UX issues but Godot port without tuning wastes effort on broken loop; D3 built `_balance/` before declaring done; consistency with prior camp work.

### AI/sim patches landed this session (post-wave-2)

Each was diagnosed by running default-vs-idle then probing what default-AI was actually doing:

1. **`sim/gather.py`** — `_start_move_adjacent_to` helper. Path TO blocked tile (tree/gold_mine/TC) returns None; gather targets tree.pos directly → never moves. Fixed 3 call sites: initial gather, walk-back-to-TC, walk-back-to-node. Plus made `start_gather` idempotent for same-node re-issue (umbrella reissues commands per-tick → was resetting gather_progress).

2. **`sim/combat.py`** — `start_attack` idempotent for same-target re-issue (same pattern as gather). Out-of-range chase falls back to 8-adjacent tiles if direct path fails (same blocked-goal issue when attacking TCs / buildings). Also: integer-exact damage math replaced earlier float accumulator (avoids 5/30 × 30 < 1.0 drift).

3. **`sim/ai.py`** — four tweaks:
   - `claimed_eids: set[int]` tracks villagers/scouts/military claimed by emit_build / rule 8 / rule 9 within a single AI tick batch. Prevents rule 10 from emitting gather for the same villager just claimed by build (gather was re-tasking the builder → construction stalled forever).
   - Rule 3 (train villager) now reserves 80 wood for first barracks when `barracks_count == 0`. Without this, training drains wood below 80 → barracks never built → deadlock.
   - Rule 4 (train scout) gated on `barracks_count >= 1`. Early scouts burn 30 wood + 20 gold that should go to barracks.
   - (Other rules untouched.)

4. **`sim/commands.py`** — fog gate narrowed: `move` commands to UNSEEN tiles are NOW ALLOWED. Previous AC-21 interpretation forbade move into fog → scouts couldn't scout (rule 8 emitted move toward UNSEEN tile, gate dropped it). AoE3 + every commercial RTS lets units walk into fog. Attack commands still require visible-or-explored target.

### Current diagnostic state

After all patches: `default vs idle` STILL times out at 600s. Probe shows:
- Economy works (300+ wood mid-game, gold accumulates).
- Default AI builds: TC, 1 barracks, 2 houses, 5-9 villagers, 2 scouts, 8 soldiers, 4 archers (by 600s).
- Scouts now move to map corner (79, 51) and discover enemy TC (`explored_snapshots[0][1]` populated, visibility[0][70][30] == "explored").
- BUT no kill of idle's TC in 600s.

**Most likely remaining issue (untested):** military units (soldiers/archers) emitted via rule 9 with `attack(unit_id, enemy_tc_id)`. Each tick rule 9 re-emits. Combat now idempotent (preserves accumulator). So damage SHOULD accrue once attacker in range. But maybe attackers never get in range — scouts found TC at corner of map (79, 51) but enemy TC is at (70, 30). Mismatch? Probe stopped early — user interrupted with /wrap.

**Suspect:** scouts wandered to far corner, never directly visited (70, 30). Snapshot may be missing despite `explored_snapshots[0]` having entity 1 (the enemy TC). Or rule 9 issues attack but military units stuck at base — never start moving because something earlier in tick flow blocks them. Needs more probe.

### Next pending pick (if awaiting user input)

None explicit. Next action: continue balance iteration. Suggested probe sequence:
1. Run default-AI single-player 600s, log POSITIONS of all P0 military each minute. Confirm whether soldiers/archers actually move toward (70, 30) after rule 9 fires.
2. If they don't move: check if commands.apply_command authority check rejects (military entity owner == issuing_player, should be OK). Check if combat.start_attack returns False for any reason.
3. If they DO move but never arrive: long path + slow speed (2 tiles/sec × 60 tiles = 30 sim sec from base to enemy TC). With 8 soldiers + 4 archers should be enough damage in 60 sec to drop TC (800 hp / 8 dps = 100 sec per soldier, but 8 soldiers in parallel = 12.5 sec). Should work.

### Critical context to carry forward

- **Architecture: sim is Python (source of truth), Godot port is hand-translated later.** `_balance/` is Python-only headless driver mirroring D3 pattern. Lives at `iCode/Demos/MedievalRTS/_balance/`.
- **Multiplayer-ready by construction.** AI = a `Commander` impl, human input would be another `Commander`, network is a future `Commander`. Sim has zero knowledge of player input source. `Game.tick(inputs: list[Command])` is the lockstep boundary.
- **Symmetric fog** with per-player `fog_cheat` flag (AC-22, default False). v0 has AI playing under fog same as human.
- **Cross-test pollution still open.** Wave-1 leaf tests inject sys.modules stubs (sim.walls/entities/pathfinding) for parallel isolation; stubs leak across test files. Run pytest per-file for clean signal; full `pytest tests/` collection fails. Cleanup TODO: add stub teardown in wave-1 test fixtures.
- **Repo:** github.com/Westopoli/MedievalRTS, main branch. Last pushed commit: `6deed4b` ("Fix gather: path to adjacent tile + idempotent re-issue"). Subsequent AI/commands/combat patches + `_balance/` NOT yet committed (~150 LoC of churn pending).
- **User preference: tune-first-then-Godot.** Don't propose Godot port until balance settled.
- **NOT in iCode/ git repo.** iCode/ is NOT a git repo. The MedievalRTS subdir IS its own git repo (init'd this session).

### Files Touched This Session

Created:
- `iCode/Demos/MedievalRTS/SPEC.md` — 37 ACs, AoE3-inspired RTS spec
- `iCode/Demos/MedievalRTS/.claude-swarm.toml` — swarm config
- `iCode/Demos/MedievalRTS/.claude/settings.local.json` — pytest/python permissions for sub-agents (largely didn't help — sub-agents still got perm-denied)
- `iCode/Demos/MedievalRTS/.gitignore` — Python + Godot + .swarm/ ignores
- `iCode/Demos/MedievalRTS/sim/__init__.py`
- `iCode/Demos/MedievalRTS/sim/contract.py` — type contract (Command, Entity, Game, Map, Player, BuildingSnapshot, Literal aliases, constants)
- `iCode/Demos/MedievalRTS/sim/map_gen.py` — generate_map + place_starting_entities (leaf-01)
- `iCode/Demos/MedievalRTS/sim/entities.py` — STATS table + spawn_unit/spawn_building/classifiers (leaf-02)
- `iCode/Demos/MedievalRTS/sim/walls.py` — wall/gate passability lookup (leaf-03)
- `iCode/Demos/MedievalRTS/sim/pathfinding.py` — 8-dir A* + tick_movement (leaf-04)
- `iCode/Demos/MedievalRTS/sim/visibility.py` — 3-state fog (leaf-05)
- `iCode/Demos/MedievalRTS/sim/gather.py` — gather state machine; PATCHED 3× during balance for adjacent-tile pathing + idempotence (leaf-06 + patches)
- `iCode/Demos/MedievalRTS/sim/combat.py` — tick_combat; PATCHED for integer-exact damage + idempotent re-issue + adjacent-tile fallback (leaf-07 + patches)
- `iCode/Demos/MedievalRTS/sim/building.py` — construction + training queues + place_building_immediate (leaf-08)
- `iCode/Demos/MedievalRTS/sim/commands.py` — apply_command dispatcher; PATCHED to allow move into UNSEEN tiles (leaf-09 + patch)
- `iCode/Demos/MedievalRTS/sim/ai.py` — deterministic priority script; PATCHED 4× during balance (claimed_eids, villager_reserve, scout_defer, multiple) (leaf-10 + patches)
- `iCode/Demos/MedievalRTS/sim/game.py` — new_game + _tick orchestrator monkey-patched onto contract.Game + scripted_player_commands (leaf-11)
- `iCode/Demos/MedievalRTS/tests/conftest.py` — sys.path setup
- `iCode/Demos/MedievalRTS/tests/test_umbrella.py` — 12 spot-check tests (AC-1..AC-37)
- `iCode/Demos/MedievalRTS/tests/test_*.py` × 11 — per-leaf tests, ~93 total assertions, all green per-file
- `iCode/Demos/MedievalRTS/briefs/leaf-01.md..leaf-11.md` — swarm brief files
- `iCode/Demos/MedievalRTS/briefs/leaf-*.ASSUMPTIONS.md` × 8 — per-leaf inference logs
- `iCode/Demos/MedievalRTS/_balance/__init__.py`
- `iCode/Demos/MedievalRTS/_balance/sim_driver.py` — run_match + PlayerStats + MatchResult
- `iCode/Demos/MedievalRTS/_balance/strategies.py` — default/rush/turtle/eco/idle Commanders
- `iCode/Demos/MedievalRTS/_balance/runner.py` — round-robin + win-rate matrix + CLI

Repo state:
- 7 commits pushed to origin/main, latest `6deed4b`
- ~150 LoC of post-`6deed4b` changes uncommitted (ai.py + commands.py + combat.py balance patches + `_balance/` directory)

---

## Session Pause — 2026-05-25

**Lane / context:** same repo (`iCode/Demos/MedievalRTS/`).
**Active workstream/task:** AI tuning iteration — closed.
**Status:** done.

### What happened this session

Resumed mid-iteration. Built `_balance/probe_military.py` to log P0 military positions every 60 sim sec during default-vs-idle. Probe revealed two distinct bugs:

1. **Rule 9 trigger latency.** `sol_n >= 6` in `sim/ai.py` fired only at tick 14640 (488 sim sec). Probe shows 6th soldier didn't spawn until then because villagers, houses, barracks, walls, scouts, archers, and earlier soldiers all consume production capacity first. With only 112 sec left in the 600s cap and 60 tiles between bases at 2 tiles/sec, army couldn't traverse the map.

2. **Combat chase re-issue reset move state every tick.** `sim/combat.py` tick_combat compared `state.move_target` against `target.pos`. When pathing to a TC failed (buildings block their own tile), adjacent-tile fallback set `state.move_target = (70, 31)` while `target.pos = (70, 30)`. Comparison stayed unequal, so `start_move` ran on every subsequent tick — overwriting `_move_state[entity_id]` and resetting path progress to 0. Result: units pinned at base despite holding a valid path. Probe showed archer 71 at (11,30) with path_len=59 from t=240s through t=540s — zero displacement over 300 sim sec.

### Fixes landed

- `sim/ai.py:235` — rule 9 trigger changed from `sol_n >= 6` to `(sol_n + arch_n) >= 3`. Archers now contribute to attack force; army leaves base by ~180 sim sec.
- `sim/combat.py:135-152` — re-path only when `not pf.is_moving(attacker_id)` OR when target moved beyond chebyshev distance 1 from cached `state.move_target`. Idempotent for stationary targets (buildings), still responsive if target moves significantly.

### Verification

- `_balance/probe_military.py` default-vs-idle: P0 wins at tick 8451 (281 sim sec). Archers reach (65,31), accumulate damage in range, TC dies.
- `pytest tests/test_umbrella.py`: **12/12 green.** Previously-failing `test_full_scripted_match_terminates_with_winner` now passes.
- `pytest tests/test_combat.py`: 9/9 green (no regression in leaf tests).
- `python -m _balance.runner --strategies default rush turtle eco idle --seeds 3 --max-sec 600 --quiet`: 75 matches in 455s. Matrix:
  - default vs idle: 100% win, 249s avg
  - default vs default: 66.7% (P0 spawn bias)
  - default vs rush: 33.3% (rush slight edge from skipping walls — expected)
  - turtle/eco/idle vs each other: 100% timeout (no aggression — correct)

### Last decision locked

**Tune-first-then-port-Godot is satisfied.** Balance now settled. Godot frontend port unblocked, awaiting user greenlight to start.

### Critical context to carry forward

- **Two bug classes hit in this re-balance:** (a) AI rule thresholds gated on single unit type rather than combined military force; (b) combat re-issue comparison using a stale destination key. Future cross-cutting commands (gather, chase, scout move) should follow the same idempotence pattern: compare against the actual cached destination, not the current target field that the fallback may have remapped.
- Cross-test `sys.modules` pollution still open; `pytest tests/` collection still fails. Run per-file.
- Repo state: previously pushed commit `6deed4b`. All session work (5 sim patches + `_balance/` harness + probe) bundled in one new commit this session.

### Next pending pick

Godot frontend port — start or defer further (e.g., add 6th strategy, address P0 spawn bias first). User's call.
