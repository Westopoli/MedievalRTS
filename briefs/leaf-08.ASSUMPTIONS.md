# leaf-08 assumptions

## Sibling API shape (sim.entities, sim.pathfinding)

The brief permits importing `spawn_unit`, `spawn_building`, `is_building`,
`is_unit`, `get_stats` from `sim.entities` and `start_move`, `is_moving` from
`sim.pathfinding`, but does not pin their exact signatures. Inferred from
`sim/contract.py` Entity shape and the umbrella test usage:

- `spawn_unit(game, kind=..., owner=..., pos=...) -> Entity` — appends and
  returns the new entity. Keyword-only call style used.
- `spawn_building(game, kind=..., owner=..., pos=...) -> Entity` — same.
- `get_stats(kind) -> {"hp": int, "max_hp": int, ...}` — dict lookup. We
  consume `stats["max_hp"]` to set hp / max_hp after spawn.
- `is_unit(e)` / `is_building(e)` — boolean predicates on Entity.
- `start_move(game, entity_id, target_tile) -> bool` — non-blocking issue of
  a move command.

If real sibling impls return objects already at full hp, the explicit
hp/max_hp reset in `tick_construction` and `place_building_immediate` is a
harmless no-op. If they spawn at hp=0 or some debug value, our reset still
guarantees a fully-built building per AC.

## Footprint anchor

Brief says "tile + footprint fits in map bounds" but doesn't specify whether
`tile` is the footprint's top-left or center. We chose **top-left**: the
footprint extends `[tile.x, tile.x + width)` x `[tile.y, tile.y + height)`.
This is the convention most commonly used in RTS tile placement and matches
the umbrella's `place_building_immediate(g, kind="wall", tile=(15, y), ...)`
calls which place a 1x1 wall directly at `(15, y)`.

## Footprint center

For odd-sized buildings (e.g. 3x3 barracks) center = top-left + (1, 1). For
even-sized (2x2 house) we used floor-div, so center = top-left + (1, 1) as
well. This biases toward the upper-left interior tile. Adjacency check uses
Chebyshev <= 1, so any builder within the 3x3 surround of the center counts
as adjacent — for a 2x2 house centered at top-left+(1,1), the builder may
stand at the top-left tile itself and still satisfy the adjacency check.

## "Building's queue is empty"

Interpreted as: at most one in-progress `_Training` entry per `building_id`.
The brief says one-at-a-time per AC-11; no FIFO queue of pending entries.

## Population count

Per the brief: "current population count of unit-kinds for this player <
pop_cap". We count live (hp > 0) entities for which `is_unit(e)` is true and
`e.owner == player_id`. Buildings do not contribute to population.

## Pathfinding deferral

The brief says `move_and_collide` is deferred to D3 in some sibling memory,
but here we just call `start_move(...)`. We do not poll `is_moving` because
the construction tick uses the builder's current `pos` directly — it ticks
the timer iff the builder happens to be adjacent. This allows the test to
spawn the villager at the footprint tile and avoid needing real pathfinding.

## `place_building_immediate` cost

UMBRELLA-ONLY: bypasses cost, timer, AND footprint validation. The umbrella
calls it for walls at (15, 28..32) with no resource setup — deduction would
fail. Test confirms `g.players[0].wood` is unchanged.

## tick_training timing

Loop runs `time_seconds * TICK_HZ` total ticks. We decrement until `timer
<= 1`, then on the final tick we attempt spawn (skipping decrement). This
means a 12-second train finishes on tick 360 (when called 360 times),
matching the test's `for _ in range(TICK_HZ * 12)` window.
