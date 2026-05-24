# Medieval RTS — Spec (v0)

AoE3-inspired sandbox demo. Top-down 2D, scrolling map, edge-pan camera. Single player vs deterministic AI. Godot 4 + GDScript at runtime; headless Python sim used as source of truth for TDD via the swarm cascade. Lives at `iCode/Demos/MedievalRTS/`.

Acceptance criteria numbered AC-N. Umbrella test must encode all of them.

---

## 1. Vision

Real-time strategy game. N players (v0: 1 human + 1 AI). Every player follows identical rules — symmetric by construction so adding multiplayer later is a Commander swap, not a sim refactor. Each player controls a town, gathers resources, builds structures (incl. walls + gates), trains military units, scouts under fog of war, and tries to destroy enemies' Town Centers. Inspired by AoE3's full loop, scoped to one age, no civs, no tech tree, no naval.

Done = each player can: scroll map by mouse-edge pan (human only), scout under 3-state fog of war, gather wood + gold, build houses/barracks/walls/gates, train soldiers + archers + scouts, walk army to enemy base, destroy enemy TC. AI follows a deterministic priority script that obeys the same fog rules as a human (cheat flag exists but defaults off).

---

## 2. Stack

| | |
|---|---|
| Engine | Godot 4.6.x |
| Languages | GDScript (frontend), Python 3.11+ (sim + tests) |
| Test runner | pytest (sim only) |
| Asset pack | Kenney *Medieval RTS* CC0 — `~/Downloads/kenney_medieval-rts.zip` extracted to `assets/kenney_medieval/` |
| Viewport | 1280×720 |
| Tile size | 64×64 px |
| Map size | **80×60 tiles** (5120×3840 px world, ~16 screens) |
| Persistence | None |

---

## 3. Architecture

**Two layers, strictly separated:**

1. **Headless sim** (`sim/`, Python) — all game logic. No Godot import. Deterministic by seed. This is what swarm leaves implement + test.
2. **Godot frontend** (`*.gd`, `*.tscn`) — renders sim state, accepts input, drives sim. Thin. Hand-ported from sim after sim is green.

Sim ships permanently (not build-time only). Godot side calls a hand-translated GDScript port of the sim. Python sim is the spec; Python tests are authoritative. Any divergence Python↔GDScript is a bug.

Tick rate: 30 Hz fixed. `Game.tick(inputs: list[Command]) -> None`.

---

## 4. Camera + view (frontend, not sim)

- **AC-1:** World is 80×60 tiles at 64 px/tile = 5120×3840 px. Viewport is 1280×720. Camera shows a rectangular subset.
- **AC-2:** **Edge-pan only.** Cursor within 16 px of viewport edge → camera scrolls in that direction at `CAMERA_SCROLL_SPEED = 800 px/s` (sim-time-independent). No WASD camera, no middle-click drag, no arrow keys.
- **AC-3:** Camera clamped to world bounds — cannot scroll past edges.
- **AC-4:** Sim is unaware of camera position; all sim coords are world-tile coords. UI translates mouse position → world tile via camera offset.

## 5. Resources

Two resources: **wood** and **gold**. Both integer.

- **AC-5:** `Game` starts each player with `wood=300, gold=150` (bumped from v0-draft due to larger map / more building options).
- **AC-6:** Villager standing on a Tree tile gathers `+1 wood` per sim second.
- **AC-7:** Villager standing on a GoldMine tile gathers `+1 gold` per sim second.
- **AC-8:** Villager can only gather one resource at a time; new gather target cancels prior.
- **AC-9:** Carry cap = 10. Villager walks back to nearest owned Town Center (within 1 tile) to deposit.

## 6. Entities

All in `sim/entities.py`. Each has `entity_id: int`, `kind: EntityKind`, `owner: int` (0=player, 1=AI), `pos: tuple[int,int]`, `hp`, `max_hp`.

| Entity | Kind | hp | Sight | Notes |
|---|---|---|---|---|
| Villager | Unit | 25 | 5 | Gathers, builds, no combat |
| Soldier | Unit | 60 | 4 | Melee, dmg 8/sec adjacent |
| Archer | Unit | 35 | 7 | Ranged, dmg 5/sec at range ≤ 5 tiles |
| Scout | Unit | 30 | 10 | Fast (4 tiles/s), no combat, big sight |
| Town Center | Building | 800 | 8 | Trains villagers + scouts. One per player (game-ender). |
| House | Building | 100 | 3 | +5 pop cap. Cost 30 wood. |
| Barracks | Building | 300 | 4 | Trains soldiers + archers. Cost 80 wood. |
| Wall | Building | 200 | 0 | Blocks movement. Cost 5 wood per tile. 1×1 footprint. |
| Gate | Building | 200 | 0 | Like wall but owner units + allied may path through; enemy may not. Cost 25 wood. 1×1 footprint. |
| Tree | Resource | 40 wood | — | Depletes. Map-generated. |
| GoldMine | Resource | 200 gold | — | Depletes. Map-generated. |

- **AC-10:** Pop cap starts at 5, +5 per House, hard ceiling 50.
- **AC-11:** Buildings have one-at-a-time training queue.
- **AC-12:** Units obey explicit commands only; no auto-attack.
- **AC-13:** Move command finds path via 8-direction A* on tile grid. Buildings (incl. walls), trees, gold mines block.
- **AC-14:** Combat tick-resolved: each tick, units with attack command in range deal `dmg/30` damage. Death = entity removed.

**Train costs / times:**

| Unit | Wood | Gold | Time (s) | Built at |
|---|---|---|---|---|
| Villager | 50 | 0 | 12 | Town Center |
| Scout | 30 | 20 | 10 | Town Center |
| Soldier | 40 | 20 | 15 | Barracks |
| Archer | 25 | 35 | 18 | Barracks |

**Build costs / times:**

| Building | Wood | Gold | Build time (s) | Footprint |
|---|---|---|---|---|
| House | 30 | 0 | 10 | 2×2 |
| Barracks | 80 | 0 | 15 | 3×3 |
| Wall (per tile) | 5 | 0 | 3 | 1×1 |
| Gate | 25 | 5 | 5 | 1×1 |

Town Center is NOT player-buildable in v0 (each player gets exactly one at map gen).

## 7. Fog of war (3-state, symmetric)

Design principle: **all players are symmetric.** Human, AI, and future network players all play under the same fog rules. Asymmetry is achieved only via opt-in per-player flags (cheats, debug). This keeps the sim multiplayer-ready by construction.

- **AC-15:** Each tile has a per-player visibility state: `UNSEEN` (never seen), `EXPLORED` (seen before, not currently visible), `VISIBLE` (currently in sight of an owned unit/building).
- **AC-16:** Visibility recomputed every sim tick **for every player**. Tile is `VISIBLE` for player P if within `sight` tiles of any P-owned unit or P-owned building (Chebyshev distance).
- **AC-17:** When a tile transitions from `VISIBLE` to no-longer-in-sight, state becomes `EXPLORED` (not back to `UNSEEN`).
- **AC-18:** Enemy units inside non-`VISIBLE` tiles are NOT included in the player's visible-entity list (frontend hides them).
- **AC-19:** Enemy buildings: last-seen position + hp snapshot persists in `EXPLORED` tiles (ghost of building); current hp updates only while `VISIBLE`.
- **AC-20:** Resource nodes (trees, gold mines): persist in `EXPLORED` (terrain doesn't move).
- **AC-21:** Commands targeting entities/tiles in the issuing player's `UNSEEN` tiles are dropped. Applies to **all players, including AI** (AC-22 cheat may waive). Commands targeting `EXPLORED` tiles allowed (movement only).
- **AC-22:** **Per-player cheat flag** `Player.fog_cheat: bool` (default `False`). When `True`, AC-21 is waived for that player; commands accepted regardless of visibility. Designed for debug, scenario testing, easy-mode AI presets. **Default for AI in v0 = False** (AI plays under fog like human).

## 8. Walls + gates

- **AC-23:** Walls block all pathfinding (treated as impassable terrain).
- **AC-24:** Gates are pathfinder-passable for owner units and impassable for non-owner units. Pathfinder takes `owner: int` parameter when querying passability.
- **AC-25:** Walls + gates have HP; can be attacked + destroyed by enemy units. Destroyed wall/gate tile becomes passable.
- **AC-26:** Wall building: player issues `build(wall, tile)` per tile. Stretch-friendly UX (drag-paint multiple tiles) is Godot-side syntactic sugar — sim only handles one-tile-at-a-time builds.

## 9. Tick loop

`Game.tick(inputs: list[Command]) -> None` advances world by 1/30 s.

Order per tick:
1. Apply commands (each command filtered through AC-21 fog for its issuing player, AC-22 cheat waives).
2. Resolve movement (path step; recompute path if blocked).
3. Resolve gathering (carry cap, deposit on TC adjacency).
4. Resolve construction (timer; on complete, building HP set to full, footprint locked into pathing grid).
5. Resolve combat (damage application + death cleanup).
6. Resolve training (timer; on complete spawn unit on adjacent free tile).
7. Recompute fog of war **for every player** (AC-16, AC-17).
8. Update last-seen snapshots for `EXPLORED` enemy buildings, per player (AC-19).
9. Check win condition (AC-37).

## 10. Commands

`Command` is a dataclass with `kind: CommandKind` + `issuing_player: int`. Allowed kinds:

- `move(entity_id, target_tile)`
- `attack(entity_id, target_entity_id)`
- `gather(entity_id, resource_node_id)`
- `build(entity_id, building_kind, tile)` — villager places footprint, walks to it, constructs
- `train(building_id, unit_kind)` — adds to building's queue
- `stop(entity_id)`

Every command carries `issuing_player: int` — the player who issued it. The sim validates command authority: entity's `owner` must equal `issuing_player`, OR the command targets the issuing player's own building queue, etc. Fog gate uses `issuing_player` to look up `Player.fog_cheat` and the per-player visibility grid.

- **AC-27:** Invalid commands (insufficient resources, OOB tile, dead/missing entity, ownership mismatch, occupied tile, exceeding pop cap, footprint overlap with existing building/resource, fog-blocked per AC-21 absent AC-22 cheat) are silently dropped. Sim never crashes; sim never partially applies.

## 10b. Player input architecture (Commander pattern)

Sim does NOT know about humans, AI, or networks. `Game.tick(inputs)` takes a flat command list. Caller (test harness or Godot frontend) is responsible for collecting commands from each player's input source and passing them in.

Out-of-sim convention (NOT a sim leaf): each player has a `Commander` interface:

```python
class Commander(Protocol):
    def collect(self, game: Game, player_id: int) -> list[Command]: ...
```

Implementations:
- `HumanCommander` — reads UI input (Godot side, GDScript).
- `AICommander` — wraps `sim/ai.py` script.
- `NetworkCommander` — future wave, reads from network buffer.
- `ReplayCommander` — future wave, replays from log.

This pattern means **adding multiplayer is a Commander swap, not a sim refactor.** Sim leaves do not import `Commander` — it lives in `app/commanders.py` (outside `sim/`).

## 11. AI player

`sim/ai.py`. Deterministic priority script, no learning, no search. **Plays under fog like a human** (AC-22 cheat default False). Sees the world by querying its own visibility grid + entity list filtered through fog. Runs every 2 sim seconds:

1. If pop < pop_cap AND wood ≥ 30 AND houses_in_progress == 0 → build House near TC.
2. If barracks_count == 0 AND wood ≥ 80 → build Barracks.
3. If TC queue empty AND villager_count < 10 AND wood ≥ 50 → train Villager.
4. If TC queue empty AND scout_count < 2 AND wood ≥ 30 AND gold ≥ 20 → train Scout.
5. If barracks queue empty AND wood ≥ 40 AND gold ≥ 20 AND soldier_count < 8 → train Soldier.
6. If barracks queue empty AND wood ≥ 25 AND gold ≥ 35 AND archer_count < 4 → train Archer.
7. **Defensive layer:** if barracks_count ≥ 1 AND wall_count < 8 AND wood ≥ 40 → build wall arc covering N tiles between TC and map midline. 1 Gate per arc on the inward-facing side.
8. **Scouting:** idle Scouts → move-command to nearest `UNSEEN` tile every 4 sim seconds. Scout dies → train another (rule #4).
9. **Attack trigger:** if soldier_count ≥ 6 AND enemy TC `EXPLORED` or `VISIBLE` → group-move all soldiers + archers toward last-known enemy TC tile, attack-move on arrival. If enemy TC never seen → attack-move toward map midline first (poke for vision).
10. Idle villagers → assign to nearest non-empty Tree or GoldMine (alternating each call).

AI uses identical Command surface as human; no privileged operations.

## 12. Map generation

`sim/map_gen.py: generate_map(seed: int) -> Map` returns 80×60 tile grid.

- **AC-28:** Reproducible: same seed → same map.
- **AC-29:** Player TC at tile (10, 30), AI TC at tile (70, 30). Symmetric across vertical midline.
- **AC-30:** 4 Tree forests per side, ~6 trees per forest (~24 trees per side), clustered within 12 tiles of the TC.
- **AC-31:** 2 GoldMines per side, within 10 tiles of TC.
- **AC-32:** 5 villagers per player spawn adjacent to their TC.
- **AC-33:** No fog state in map gen — fog is `Game` state initialized per-player.
- **AC-34:** Remaining tiles = grass.

## 13. Win condition

- **AC-35:** When a Town Center hp drops to 0, opposing player wins.
- **AC-36:** `Game.winner` set to 0 or 1, `Game.over` becomes True.
- **AC-37:** No further commands processed after `Game.over` is True (early-return in step 1 of tick loop).

## 14. Type contract

`sim/contract.py`. Swarm leaves may only import names from this file (allowlist).

```python
# sim/contract.py
from dataclasses import dataclass, field
from typing import Literal

EntityKind = Literal[
    "villager", "soldier", "archer", "scout",
    "town_center", "house", "barracks", "wall", "gate",
    "tree", "gold_mine",
]
ResourceKind = Literal["wood", "gold"]
CommandKind = Literal["move", "attack", "gather", "build", "train", "stop"]
TerrainKind = Literal["grass", "tree", "gold_mine"]
VisibilityState = Literal["unseen", "explored", "visible"]

TILE_SIZE = 64
MAP_W = 80
MAP_H = 60
TICK_HZ = 30
POP_CAP_START = 5
POP_CAP_MAX = 50
CARRY_CAP = 10
START_WOOD = 300
START_GOLD = 150
CAMERA_SCROLL_SPEED = 800  # px/s

@dataclass(frozen=True)
class Command:
    kind: CommandKind
    issuing_player: int = 0  # which player issued this command (authority + fog gate key)
    entity_id: int = -1
    target_tile: tuple[int, int] | None = None
    target_entity_id: int | None = None
    resource_node_id: int | None = None
    building_kind: EntityKind | None = None
    unit_kind: EntityKind | None = None
    building_id: int | None = None

@dataclass
class Entity:
    entity_id: int
    kind: EntityKind
    owner: int
    pos: tuple[int, int]
    hp: int
    max_hp: int
    carrying: ResourceKind | None = None
    carry_amount: int = 0

@dataclass
class Player:
    player_id: int
    wood: int
    gold: int
    pop_cap: int
    fog_cheat: bool = False  # AC-22 opt-in; default symmetric fog

@dataclass
class BuildingSnapshot:
    """Last-seen snapshot for EXPLORED enemy buildings (AC-19)."""
    entity_id: int
    kind: EntityKind
    owner: int
    pos: tuple[int, int]
    hp_last_seen: int

@dataclass
class Map:
    width: int
    height: int
    terrain: list[list[TerrainKind]]

class Game:
    players: list[Player]
    entities: list[Entity]
    map: Map
    tick_count: int
    over: bool
    winner: int | None
    # per-player fog: visibility[player_id][x][y] -> VisibilityState
    visibility: list[list[list[VisibilityState]]]
    # per-player last-seen building snapshots, keyed by entity_id
    explored_snapshots: list[dict[int, BuildingSnapshot]]

    def tick(self, inputs: list[Command]) -> None: ...
```

Internal types (path state, AI bookkeeping, build queues) live in respective leaf modules — NOT importable across leaves.

## 15. Umbrella acceptance test

`tests/test_umbrella.py` — deterministic ~5-min (9000-tick) scripted scenario, both players symmetric.

1. `generate_map(seed=42)` → assert dims + TC positions + tree/gold counts (AC-28..AC-32).
2. Player 0 script: build 1 House @ tick 60, 1 Barracks @ tick 300, 2 Walls + 1 Gate @ tick 600 (defensive layer near TC), train 2 Scouts + 3 Soldiers + 2 Archers, scout toward midline, move-attack toward enemy TC after first sighting.
3. Player 1 = AI (§11 script, `fog_cheat=False`).
4. Spot-check fog (both players):
   - Tick 100: P0 sees (10,30) area, NOT (70,30); P1 sees (70,30) area, NOT (10,30).
   - When P0 Scout enters P1 base, P1 TC tile transitions UNSEEN→VISIBLE for P0, then later VISIBLE→EXPLORED with `BuildingSnapshot` persisting.
   - Symmetry: P1's visibility recomputed each tick same as P0's.
5. Spot-check walls/gates: enemy pathfinder routes around walls; gate rejects enemy and admits owner; destroyed wall becomes passable.
6. Spot-check authority: a `Command` with `issuing_player=0` targeting a P1-owned entity is dropped (ownership mismatch, AC-27).
7. Spot-check cheat flag: in a separate sub-scenario, set `players[1].fog_cheat = True`, issue AI command targeting an unseen-to-AI player entity, assert it is NOT dropped.
8. Assert by tick 9000: `game.over is True` and `game.winner in {0, 1}`.

## 16. Out of scope (v0)

- Multiple ages / tech tree
- Multiple civilizations
- Cavalry, siege weapons, monks, religion
- Towers (defensive structures beyond walls/gates)
- Water / boats / fishing
- Map editor
- Multiplayer / networking
- Save / load
- Sound / music
- Animations beyond static-sprite Modulate flash
- Formations (group-move = "issue same move to each unit")
- Mini-map
- Replays
- Difficulty levels (one AI script)
- Drag-paint wall building UX in sim (Godot-side sugar only)
- Multiplayer networking (Commander pattern wired but no NetworkCommander impl yet)
- Replay capture/playback (Commander pattern wired but no ReplayCommander impl yet)

## 17. Future waves

- Wave 2: mini-map (fog state already exists) + smarter AI (multiple personality presets, easy/hard difficulty via `fog_cheat` toggle + economy multipliers).
- Wave 3: cavalry + tech tree (1st upgrade tier).
- Wave 4: save/load + ReplayCommander.
- Wave 5: full Godot frontend polish + assets + sound.
- Wave 6: NetworkCommander → LAN/online multiplayer. Determinism audit needed; lockstep model already implied by `Game.tick(inputs)`.
- Wave 7: 3+ players + team alliances.

## 18. Repo layout

```
iCode/Demos/MedievalRTS/
  SPEC.md
  .claude-swarm.toml
  sim/
    __init__.py
    contract.py       # type contract
    game.py           # Game class + tick loop orchestrator
    entities.py       # entity dataclasses + factories + stats tables
    map_gen.py        # AC-28..AC-34
    pathfinding.py    # 8-dir A*, owner-aware (gates)
    visibility.py     # AC-15..AC-22 fog state
    combat.py         # damage resolution
    gather.py         # gather + deposit
    building.py       # construction + training queues + footprint validation
    walls.py          # wall/gate pathing rules (small, dedicated)
    ai.py             # AI script
    commands.py       # Command validation + dispatch + fog gate
  tests/
    test_umbrella.py
    test_<leaf>.py
  briefs/
  app/
    __init__.py
    commanders.py     # Commander protocol + HumanCommander stub + AICommander wrapper
  project.godot
  Main.tscn
  main.gd
  camera.gd
  assets/kenney_medieval/
```
