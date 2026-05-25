# Medieval RTS — Godot Port Spec (Wave 1)

Companion to `SPEC.md`. The base spec defines the 37 acceptance criteria for the Python sim and the v0 game design. This document adds the acceptance criteria for the **Godot 4.6 hand-port** of that sim, plus the criteria for the render / input / camera / scene-tree layer that drives it.

ACs in this file continue the numbering from `SPEC.md` (which ends at AC-37). New ACs begin at **AC-38**. Where this document references an existing sim AC, it cites `SPEC.md` by number (e.g., "parity with AC-13").

This is the spec for **wave 1** of the Godot cascade: the GDScript port of the 11 sim modules + minimal render scaffold for a playable vertical slice. Wave 2 (full UI / HUD / Kenney sprite swap / sound / menus) is out of scope for this document.

---

## 1. Goal

Produce a playable Godot 4.6 build of the Medieval RTS that exactly mirrors the behavior of the Python sim, validated by GUT parity tests, with placeholder ColorRect rendering and a scrolling camera. The vertical slice is:

- Single-player session, P0 = human, P1 = `default_ai` from `sim/ai.py` ported to `godot/sim/ai.gd`.
- P0 starts with 1 villager (per the existing sim's AC-32 spawn ring, less the four villagers not under player control — those four are scripted to gather automatically so the human only directly controls one). Rest of P0's town behaves per sim defaults.
- P1 plays a full economy match per the AI script.
- Map is the full 80×60 generated per `SPEC.md` AC-28..AC-34.
- Symmetric fog visible to the player per `SPEC.md` AC-15..AC-22.
- Edge-pan scrolling camera per `SPEC.md` AC-2..AC-4.
- Placeholder ColorRect rendering for entities, TileMapLayer for terrain.
- Frame rate ≥ 30 fps on the development machine with the full map populated.
- The match terminates per `SPEC.md` AC-37 win condition or after 600 sim seconds (whichever comes first).

---

## 2. Repo layout

The Godot port lives in a `godot/` subdirectory of the existing repository at `iCode/Demos/MedievalRTS/`. The Python sim, the swarm config, and `SPEC.md` stay at the repo root. The Godot project root is `godot/project.godot`.

```
iCode/Demos/MedievalRTS/
  SPEC.md
  SPEC_GODOT.md
  .claude-swarm.toml
  sim/                      # Python sim (read-only for wave 1)
  tests/                    # Python tests (read-only for wave 1)
  _balance/                 # Python balance harness (read-only)
  briefs/                   # Existing Python-build briefs (read-only)
  briefs_godot/             # NEW: this wave's briefs
  godot/
    project.godot           # Godot project file (parent-owned)
    sim/
      contract.gd           # leaf-01 — type contract (parent-owned re-export only after leaf-01 lands)
      map_gen.gd            # leaf-02
      entities.gd           # leaf-03
      walls.gd              # leaf-04
      pathfinding.gd        # leaf-05
      visibility.gd         # leaf-06
      gather.gd             # leaf-07
      combat.gd             # leaf-08
      building.gd           # leaf-09
      commands.gd           # leaf-10
      ai.gd                 # leaf-11
      game.gd               # leaf-12
    scenes/
      Main.tscn             # parent-owned (wave 2 scaffolding)
    scripts/
      main.gd               # parent-owned (wave 2)
      camera.gd             # parent-owned (wave 2)
      render.gd             # parent-owned (wave 2)
    tests/
      test_<module>.gd      # one GUT test per leaf
      test_umbrella.gd      # parent-owned umbrella
    addons/
      gut/                  # GUT addon (parent-owned, vendored)
```

- **AC-38:** The Godot project at `godot/project.godot` targets Godot 4.6.x. `compatibility` rendering or `forward_plus` is permitted; `mobile` is not. Project name = `MedievalRTS`.
- **AC-39:** The Godot sim port lives at `godot/sim/`. One `.gd` file per Python sim module, same base name (`gather.py` → `gather.gd`, `map_gen.py` → `map_gen.gd`, etc.). No additional `.gd` files in `godot/sim/`.
- **AC-40:** No `.gd` file in `godot/sim/` may `extends Node` or `extends Resource` for the purpose of behaving as a scene-tree node. Sim files are pure logic — they expose constants, classes, and functions, and are loaded by `preload()` or `load()` from the render layer.

---

## 3. Type contract (GDScript)

The GDScript type contract is `godot/sim/contract.gd`. It mirrors `sim/contract.py` symbol-for-symbol:

- **AC-41:** Every constant defined in `sim/contract.py` (TILE_SIZE, MAP_W, MAP_H, TICK_HZ, POP_CAP_START, POP_CAP_MAX, CARRY_CAP, START_WOOD, START_GOLD, CAMERA_SCROLL_SPEED, NUM_PLAYERS) is defined as a top-level `const` in `godot/sim/contract.gd` with the same name and value.
- **AC-42:** Python `Literal` aliases (`EntityKind`, `ResourceKind`, `CommandKind`, `TerrainKind`, `VisibilityState`) have no compile-time analog in GDScript. The port uses bare `String` fields and relies on documentation in `SPEC.md` § 6 + `sim/contract.py` for the canonical member set. The port MAY include a top-level comment block in `godot/sim/contract.gd` listing the valid member strings for each former Literal — comment-only, not enforced at runtime. No leaf may add runtime validation that rejects a string outside the documented set (matches the Python sim's loose runtime behavior).
- **AC-43:** Every dataclass in `sim/contract.py` (`Command`, `Entity`, `Player`, `BuildingSnapshot`, `Map`, `Game`) is represented as a GDScript `class_name`'d Resource subclass declared in `godot/sim/contract.gd` (one file, multiple inner classes via `class ClassName extends Resource`). Field names match the Python dataclass field names exactly, with Python `int` → GDScript `int`, `str` → `String`, `tuple[int, int]` → `Vector2i`, `list[X]` → `Array[X]`, `dict[K, V]` → `Dictionary`, `Optional[X]` → typed property defaulting to `null`. The fields are:
  - `Command(kind: String, issuing_player: int = 0, entity_id: int = -1, target_tile: Variant = null, target_entity_id: Variant = null, resource_node_id: Variant = null, building_kind: Variant = null, unit_kind: Variant = null, building_id: Variant = null)`
  - `Entity(entity_id: int, kind: String, owner: int, pos: Vector2i, hp: int, max_hp: int, carrying: Variant = null, carry_amount: int = 0)`
  - `Player(player_id: int, wood: int, gold: int, pop_cap: int, fog_cheat: bool = false)`
  - `BuildingSnapshot(entity_id: int, kind: String, owner: int, pos: Vector2i, hp_last_seen: int)`
  - `Map(width: int, height: int, terrain: Array)` — `terrain` is `Array[Array]` of `String` per inner element (matches Python `list[list[TerrainKind]]`).
  - `Game(players: Array[Player], entities: Array[Entity], map_: Map, tick_count: int = 0, over: bool = false, winner: Variant = null, visibility: Array = [], explored_snapshots: Array = [])` — `map_` is named with a trailing underscore because `map` is a GDScript builtin.
- **AC-44:** `Game.tick(inputs: Array[Command]) -> void` is declared on the `Game` class but its body is `push_error("not implemented; see godot/sim/game.gd"); return` — the actual implementation lives in leaf-12 and is attached to the `Game` instance via a wrapper function in `godot/sim/game.gd`.
- **AC-45:** No leaf other than leaf-01 may add, remove, or rename a symbol in `godot/sim/contract.gd`. The file is parent-owned after leaf-01 lands.

---

## 4. Sim parity port (leaves 02-12)

Each Python sim module is hand-ported to GDScript. Parity is asserted via per-leaf GUT tests that mirror the existing per-leaf pytest tests at `tests/test_<module>.py`.

- **AC-46:** Each `godot/sim/<module>.gd` file (for module in `map_gen, entities, walls, pathfinding, visibility, gather, combat, building, commands, ai, game`) preserves the public function names from `sim/<module>.py`. Function arity may add a leading `game: Game` parameter where the Python equivalent relied on a closure (none currently do — Python sim already takes `game` as first arg). Return types match per-AC-43 mappings.
- **AC-47:** Module-level state in Python (`_gather_state`, `_attack_state`, `_construction`, `_training`, `_move_state`, `_ai_state`) becomes file-level `var` declarations in the corresponding `.gd` file with the same name. Tests reset these between scenarios by calling a per-module `reset_module_state()` exposed at the bottom of each `.gd` file. This is the GDScript analogue of the Python tests' per-module `dict.clear()` pattern.
- **AC-48:** Each leaf's GUT test file at `godot/tests/test_<module>.gd` asserts at least one parity expectation per AC from `SPEC.md` that the module implements. Acceptable assertion forms: `assert_eq`, `assert_true`, `assert_false`, `assert_almost_eq`, `assert_has`, `assert_does_not_have`. Each test file has at least 6 distinct `func test_*` methods; `test_assertion_budget` in the brief caps total assertions at 25.
- **AC-49:** No leaf may import from any sibling leaf's `.gd` file at module top-level. Sibling references go through `godot/sim/contract.gd` (constants, classes) only. Where a Python sim file uses `from sim import pathfinding` inside a function body to defer the import, the GDScript port uses `var pf = load("res://sim/pathfinding.gd")` inside the function body. This mirrors the late-bind pattern that the Python tests exploit for monkey-patching.
- **AC-50:** Numeric parity. For any AC in `SPEC.md` that specifies a numeric outcome (damage per second, gather rate, build time, sight radius, attack range, etc.), the GDScript port produces the same integer result as the Python sim for the same input. Verified by GUT tests that mirror the Python tests' arithmetic assertions.

---

## 5. Determinism and seeding

- **AC-51:** `godot/sim/map_gen.gd::generate_map(seed: int) -> Map` is deterministic given a seed. The port uses GDScript's `RandomNumberGenerator` with `seed = <input>`. Reseeding for sub-passes (forests, mines, villager spawn) uses the same sub-seed derivation as the Python sim (e.g., `rng.seed = seed; trees_rng = RandomNumberGenerator.new(); trees_rng.seed = rng.randi()`). The first 20 tile placements for `seed=42` must match `sim/map_gen.py::generate_map(42)` byte-for-byte (asserted by the umbrella).
- **AC-52:** No `randf()` / `randi()` calls without a per-RNG instance. No use of the GDScript global `randomize()` outside of the render layer.

---

## 6. Tick-loop integration (parent-owned, wave 1 scaffolding)

These ACs describe what the render layer must do to drive the ported sim. The render layer scaffolding itself is **parent-owned** (written outside the swarm cascade); the ACs are listed here so the umbrella can assert against them.

- **AC-53:** `godot/scripts/main.gd` instantiates a `Game` via `godot/sim/game.gd::new_game(seed)` in `_ready()`. It owns one persistent `Game` reference for the session.
- **AC-54:** `main.gd::_process(delta: float)` accumulates `delta` and calls `game.tick(inputs)` once per `1.0 / TICK_HZ` seconds of accumulated time. Multiple ticks may run in a single frame if the engine drops below 30 fps; no ticks run if delta is shorter than the threshold. The Godot frame rate is NOT capped to 30 fps.
- **AC-55:** Inputs to `game.tick(inputs)` are produced by `main.gd::collect_inputs()`, which calls `godot/sim/ai.gd::ai_tick(game, 1, game.tick_count)` for the AI player and returns an empty-or-1-element array of `Command` for the human player (input source is `scripts/input.gd`, parent-owned wave 2; for wave 1, no human-issued commands are required by the umbrella scenario).
- **AC-56:** Between sim ticks, the render layer interpolates entity world positions from `entity.pos` (a tile coordinate) to `tile_to_world(entity.pos)` using `tile_size = 64`. Interpolation is a linear lerp between the last-tick position and the current-tick position; movement looks continuous despite 30 Hz tick. Render frame rate target: 60 fps.

---

## 7. Render layer (parent-owned wave 1 scaffolding)

- **AC-57:** A `TileMapLayer` node named `TerrainLayer` renders `game.map.terrain` once at start. The three terrain kinds map to three `TileSetSource` placeholder colors: `grass=#3a7a3a`, `tree=#1f5f1f`, `gold_mine=#b89c33`. No per-tile re-draw after init; depleted resources are rendered by entity-layer removal (the tile stays the same color until end of match — this is acceptable for the placeholder pass).
- **AC-58:** Each `Entity` in `game.entities` is rendered as a `ColorRect` child of a `Node2D` named `EntityLayer`. Color by kind: `villager=#4a8a4a`, `soldier=#cc4444`, `archer=#cc8844`, `scout=#44aacc`, `town_center=#6666aa`, `house=#aa8866`, `barracks=#8855aa`, `wall=#888888`, `gate=#cccc88`, `tree=#1f5f1f`, `gold_mine=#b89c33`. Size: unit kinds = `32×32 px`, building kinds = footprint × `64 px` (e.g., house = `128×128`, barracks = `192×192`), resource kinds = `64×64`. Placement: `position = tile_to_world(entity.pos) + Vector2(tile_size / 2, tile_size / 2)`, with `pivot_offset` centered.
- **AC-59:** Per-player fog overlay: a second `Node2D` named `FogLayer[player_id]` (one per player) draws a semi-transparent rectangle over every tile whose `visibility[player_id][x][y]` is not `"visible"`. `unseen` tiles render at `alpha=0.85`, `explored` tiles render at `alpha=0.4`. Only the local player's fog overlay is visible (P0 for the human session). The fog overlay is recomputed every render frame from the latest sim state.
- **AC-60:** A debug HUD `Label` in the top-left renders `"Tick: <tick_count>  P0(w=<wood> g=<gold>)  P1(w=<wood> g=<gold>)  Pop: <p0_units>/<pop_cap>"` updated once per sim tick.

---

## 8. Camera (parent-owned wave 1 scaffolding)

- **AC-61:** Edge-pan camera per `SPEC.md` AC-2 / AC-3. Camera scrolls at `CAMERA_SCROLL_SPEED = 800 px/s` (from contract.gd, mirrors Python constant). Scroll is engine-time-driven (`_process(delta)`), NOT sim-time-driven. Camera position is clamped to world bounds.
- **AC-62:** Camera starts centered on the human player's TC tile (P0 = (10, 30)).
- **AC-63:** No WASD camera. No arrow keys. No middle-click drag. Edge-pan only, per `SPEC.md` AC-2.

---

## 9. AI integration

- **AC-64:** `godot/sim/ai.gd::ai_tick(game: Game, player_id: int, tick: int) -> Array[Command]` is the GDScript port of `sim/ai.py::ai_tick`. Same signature. Same 10-rule script. Same `claimed_eids` claim-tracking. Same rule-9 attack threshold `(sol_n + arch_n) >= 3` per the post-1cc5e95 tuning patches.
- **AC-65:** AI plays under symmetric fog (`Player.fog_cheat = false`) per `SPEC.md` AC-22 default.
- **AC-66:** No leaf may change rule ordering or threshold values from those locked at Python commit `1cc5e95`. Any tuning re-iteration is a separate wave that updates both the Python sim and the GDScript port together.

---

## 10. Input (parent-owned wave 1 scaffolding)

Wave 1 vertical slice does NOT require working human input. P0's town behaves per sim defaults — 5 villagers gather, 1 of them is designated "the player villager" (highlighted with a yellow outline) but operates under the same AI gather assignment as the others. Input scaffolding is wave 2.

- **AC-67:** A `Node2D` named `HumanVillagerHighlight` follows the entity_id-0 villager (the first P0 villager spawned) and draws a `2-px` yellow outline around its ColorRect. This is the only player-facing indication that "this is the human's villager."

---

## 11. Vertical slice acceptance

The umbrella scenario is the playable build of the slice. It must satisfy:

- **AC-68:** Launching `Godot --path godot/` shows the full 80×60 map rendered with terrain colors, both TCs visible, all 5 villagers per player rendered, fog overlay covering the unseen majority of the map for P0.
- **AC-69:** The match advances at 30 Hz sim tick. At engine frame 60 (~1 second of wall time), `game.tick_count` is in `[28, 32]` (allowing ±2 ticks for startup jitter).
- **AC-70:** Edge-panning the camera with the cursor at the right edge moves the camera right at `~800 px/s`. The camera does not scroll past world bounds.
- **AC-71:** Within 600 sim seconds, either `game.over == true` with `game.winner in [0, 1]`, OR the human can observe (via the debug HUD) that P1's economy has produced ≥ 1 barracks, ≥ 3 soldiers, and ≥ 2 archers — confirming the AI port is functioning. Both branches close the slice.

---

## 12. Out of scope (wave 1)

Deferred to later waves:

- Kenney sprite swap. All entity rendering is ColorRect placeholders.
- Working human input (click-to-select, right-click-to-command). The slice runs without it.
- HUD beyond the debug `Label`. No resource icons, no portraits, no minimap.
- Sound, music, audio.
- Menus, main menu, save/load.
- Win/lose screen. Match end is HUD-only.
- Networked multiplayer.
- Animations beyond static-color render.
- Steam packaging / export presets.

---

## 13. Determinism budget

- **AC-72:** A single-player single-AI session run with `seed = 42` against `godot/sim/game.gd::new_game(42)` produces the same sequence of `(tick_count, entity_id, hp)` tuples for every entity, every tick, as the equivalent Python sim run started from `sim/game.py::new_game(42)`. Verified by a GUT integration test that loads a Python-emitted ground-truth log of the first 600 ticks and compares.
- **AC-73:** The ground-truth log is a parent-owned artifact at `godot/tests/fixtures/parity_seed42_first600.csv`. The leaf-12 brief includes instructions to regenerate it from the Python sim if a parity mismatch surfaces.

---

## 14. Type contract

The shared type contract for the GDScript port is `godot/sim/contract.gd`. It mirrors `sim/contract.py` symbol-for-symbol per **AC-41 through AC-45** above. Leaves 02-12 may only `preload("res://sim/contract.gd")` and reference symbols from that file's allowlist:

- Constants: `TILE_SIZE`, `MAP_W`, `MAP_H`, `TICK_HZ`, `POP_CAP_START`, `POP_CAP_MAX`, `CARRY_CAP`, `START_WOOD`, `START_GOLD`, `CAMERA_SCROLL_SPEED`, `NUM_PLAYERS`.
- Kind arrays: `ENTITY_KINDS`, `RESOURCE_KINDS`, `COMMAND_KINDS`, `TERRAIN_KINDS`, `VISIBILITY_STATES`.
- Classes (declared inside `contract.gd`): `Command`, `Entity`, `Player`, `BuildingSnapshot`, `Map`, `Game`.

Internal types (path state, attack state, gather state, building queues, AI bookkeeping) live in the respective leaf modules — not importable across leaves.

`godot/sim/contract.gd` is parent-owned AFTER leaf-01 lands. Leaf-01 is the only leaf that writes `contract.gd`. Subsequent waves that need a new shared symbol must escalate to the parent — no leaf may add a class or constant to `contract.gd` after leaf-01.

---

## 15. Umbrella acceptance test

The Godot umbrella is `godot/tests/test_umbrella.gd`, run via GUT headless:

```
"C:/Users/Westley Yarlott/Downloads/Godot_v4.6.3-stable_win64.exe" \
  --headless --path godot/ \
  -s addons/gut/gut_cmdln.gd \
  -gtest=res://tests/test_umbrella.gd -gexit
```

The umbrella does not exercise the scene tree (TileMapLayer / ColorRect rendering / camera) — those are visually validated by the user launching the editor. The umbrella exercises the SIM PORT under the same conditions as the Python umbrella at `tests/test_umbrella.py`:

1. `var game = preload("res://sim/game.gd").new_game(42)` — assert map dims, TC positions, tree/gold counts per `SPEC.md` AC-28..AC-32.
2. Scripted P0 commands (mirroring the Python umbrella's spot-checks) at ticks 60 / 300 / 600.
3. P1 = `default_ai` from `godot/sim/ai.gd`, called per tick with `fog_cheat=false`.
4. Fog spot-checks at ticks 100, 500, 1500 — symmetric per `SPEC.md` AC-15..AC-22.
5. Authority spot-check: a `Command` with `issuing_player=0` targeting a P1-owned entity is dropped per `SPEC.md` AC-27.
6. Cheat-flag spot-check: in a separate sub-scenario, set `game.players[1].fog_cheat = true`, issue AI command targeting an unseen-to-AI tile, assert it is NOT dropped.
7. By tick 18000 (600 sim sec), assert `game.over == true` AND `game.winner in [0, 1]` — same termination guarantee the Python umbrella enforces.
8. Parity spot-check (AC-72): for the first 600 ticks of a `seed=42` default-vs-idle run, the GDScript-emitted `(tick, eid, hp)` log matches the Python-emitted ground-truth at `godot/tests/fixtures/parity_seed42_first600.csv` byte-for-byte.

The umbrella MUST be RED before any leaf is spawned. A passing umbrella on a fresh repo indicates the test is checking stubs, not behavior. Parent verifies RED before invoking `/swarm-review`.

---

## 16. Future waves

- **Wave 2:** Render polish, working human input (click-to-select, command palette, build palette, drag-paint walls), HUD beyond debug label, win/lose screen, minimap. Kenney sprite swap.
- **Wave 3:** Sound + music. Menus + save/load.
- **Wave 4:** Steam export presets + packaging.
- **Wave 5:** Networked multiplayer via `NetworkCommander` (see `SPEC.md` §10b).

---

## 17. Inferences logged at planning time

The following inferences were made by the parent (this chat) while drafting this spec. They are listed here so `/swarm-review` and downstream waves can audit them:

- **GDScript class shape for dataclasses:** chose `class ClassName extends Resource` inner classes within `contract.gd` over individual `class_name` files. Source: keeps the contract a single file (matches Python's single `contract.py`), and Resource subclasses serialize cleanly for the parity-log fixture.
- **Module-level state pattern:** chose file-level `var` declarations with a `reset_module_state()` function per file. Source: mirrors the Python `_gather_state = {}; _attack_state = {}` module-level dicts; alternatives (Autoload singleton, instance-on-Game) would diverge from the Python source in ways that complicate parity reasoning.
- **Late-bind via `load()`:** chose `var pf = load("res://sim/pathfinding.gd")` inside function bodies over module-level `preload()`. Source: mirrors the Python `from sim import pathfinding` inside function bodies (sim/gather.py:73, sim/combat.py:40-42).
- **Game.tick wrapper pattern:** chose to keep the `tick()` method on the `Game` class as a thin dispatcher and put the orchestration logic in `godot/sim/game.gd::_tick(game, inputs)`. Source: matches Python's `sim/game.py::_tick` orchestrator pattern.
- **Map field name:** chose `map_` (trailing underscore) for the field on `Game` because `map` is a GDScript builtin. Source: GDScript reserved-word conflict.

End of SPEC_GODOT.md.
