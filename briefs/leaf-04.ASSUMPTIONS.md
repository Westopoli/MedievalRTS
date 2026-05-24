# leaf-04 assumptions

## Sibling stubs in tests
- Sibling leaves `sim.walls` and `sim.entities` were not present on disk during
  leaf-04 execution. Tests inject lightweight stand-in modules into
  `sys.modules` BEFORE importing `sim.pathfinding` so the impl's lazy
  `from sim.walls import is_passable_for` and `from sim.entities import get_stats`
  resolve to controllable test doubles. No stub files are written to disk —
  this is purely in-memory and isolated to the test process.
- If real `sim.walls` / `sim.entities` files land on disk before this test runs
  in CI, the stub injection short-circuits the real module import (because we
  populate `sys.modules` first). That is intentional for this leaf's unit tests;
  the umbrella test will exercise the real wiring.

## Stats stub
- `get_stats(kind).speed_tiles_per_sec` is stubbed to 2.0 for any kind. Test
  budget for movement timing uses speed=2.0 (5 diagonal tiles / 2.0 t/s * 30 Hz
  = 75 ticks, with +10-tick slack).

## A* tie-breaking
- Heap uses a monotonically-increasing counter as the secondary key so equal-f
  nodes pop in insertion order (FIFO). Keeps results deterministic.

## Goal passability
- Per brief: "the goal tile is allowed to be checked even if blocked … but the
  returned path will NOT include a blocked goal; if goal is blocked, return
  None." Implemented literally: goal is the first thing checked; if blocked,
  return None.

## Aborted movement
- If a tile in the path becomes blocked between `start_move` and the relevant
  tick (e.g. a wall is built across the path), `tick_movement` drops the move
  state silently. Brief does not mandate auto-repath; combat/gather/AI layers
  are responsible for re-issuing if desired.

## Could not execute pytest
- The sandbox in this environment denied `python -m pytest` invocations from
  both Bash and PowerShell tools, so RED→GREEN was not directly observed by
  this leaf agent. Test+impl were reviewed by tracing each assertion against
  the impl logic; staging proceeded on that basis. The parent / swarm-merge
  protocol will run the real RED/GREEN gate when the leaf is integrated.
