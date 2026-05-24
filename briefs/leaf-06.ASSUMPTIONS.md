# leaf-06 assumptions

1. **Pathfinding sibling not yet present.** `sim.pathfinding` and `sim.entities` modules don't exist on disk at this leaf's run time. Tests monkeypatch `sim.pathfinding` into `sys.modules` with a stub whose `start_move` immediately teleports the entity to the target tile and whose `is_moving` always returns `False`. This focuses the gather tests on gather state, deposit, and HP decrement — not on path traversal. Per brief guidance.

2. **Late-bound imports in `sim/gather.py`.** Helpers `_start_move` / `_is_moving` / `_cancel_move` import `sim.pathfinding` inside the function body rather than at module top. This lets the test fixture inject a stub via `sys.modules` before `sim.gather` is reloaded, without ever needing the real module on disk. Once leaf-04 (pathfinding) lands, behavior is unchanged.

3. **Pathfinding signatures inferred.** Brief lists only function names. Assumed:
   - `start_move(game, entity_id, target_tile)` — start movement, returns bool / None (return value ignored by gather logic).
   - `cancel_move(entity_id)` — stop movement.
   - `is_moving(entity_id) -> bool`.

4. **Test fails RED could not be confirmed in this run.** Test runner execution (pytest) was blocked by the sandbox in this leaf session. The test was authored expecting `sim/gather.py` not to exist (ImportError on `from sim.gather import ...`) as the RED state, then verified GREEN once the impl was in place by static review of the gather state machine vs. each assertion. Implementation is straightforward and self-contained; no behavior depends on side effects from un-runnable code.

5. **`get_stats` from `sim.entities` not used by `sim/gather.py`.** Brief permits the import but gather logic only needs `kind`, `hp`, `pos`, `owner` from the Entity dataclass — all already on the contract object. Stub is still injected in the test in case future expansion needs it.

6. **Deposit timing.** When a villager arrives adjacent to a TC carrying CARRY_CAP, the deposit happens on the *next* `tick_gather` call (not inside `start_move`). This matches the brief's "Else if villager has full carry... If adjacent... deposit" flow.

7. **Cap-hit re-routing happens in the same tick the cap is reached.** When `carry_amount` becomes `CARRY_CAP` inside the gather branch, `start_move` toward the nearest TC is issued immediately so the next tick begins travel. If no owned TC exists, the villager will continue gathering until something else resolves the state (the spec doesn't define this — assumed acceptable v0 behavior).
