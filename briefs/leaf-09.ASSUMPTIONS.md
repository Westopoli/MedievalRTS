# leaf-09 assumptions

## Execution environment
- `python -m pytest` is allow-listed per brief, but every invocation in this
  session was denied by the sandbox harness ("Permission to use Bash has been
  denied"). Only `python --version` and the allow-listed mkdir/cp/ls passed.
- RED/GREEN cycle therefore could NOT be observed by the leaf agent. Impl was
  written by careful spec/API tracing; parent should run pytest before merge.

## Design inferences
1. **Authority short-circuit on missing entity.** Brief says: "if `cmd`
   references an `entity_id` that exists, that entity's `owner` must equal
   `cmd.issuing_player`. Mismatch → drop." For a missing entity_id the authority
   check is skipped; the downstream subsystem helper will then return False
   (since it cannot find the entity) and the command drops via that path.
2. **`gather` retains its subsystem-installed move.** `sim.gather.start_gather`
   internally calls `_start_move` to walk the villager to the node. Cancelling
   move after a successful gather would defeat the point, so we cancel attack
   only (not move) on a successful gather dispatch.
3. **`build` cancels move BEFORE dispatch** so that `start_build`'s own
   internal `start_move` to the footprint center is the move state that
   persists after the command.
4. **`stop` has no fog gate and no subsystem call.** It only cancels state;
   returns True if entity_id is well-formed and authority check passed (or the
   entity does not exist — same drop semantics as other kinds).
5. **`apply_command` never wraps helper calls in try/except.** Per brief,
   exceptions from subsystem helpers indicate true bugs and must propagate.
   Only validation failures return False.
6. **`Command` is frozen dataclass with default `entity_id=-1`.** Treated as
   "no entity referenced" for authority purposes (matches `_find_entity`
   returning None for negative ids).
