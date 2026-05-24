# leaf-02 assumptions

1. **`is_unit` / `is_building` accept either a kind string OR an `Entity`.**
   The brief signature says `is_unit(kind: EntityKind) -> bool`, but the
   already-on-disk sibling `sim/building.py:_player_unit_count` calls
   `is_unit(e)` where `e` is an `Entity`. The test fixture
   `tests/test_building.py::_is_unit` also takes an `Entity`. To remain
   compatible with both the brief's tests (which pass kind strings) and
   the sibling's call site, the helpers coerce: if the argument has a
   `.kind` attribute it is used; otherwise the argument is treated as the
   kind string directly. No behaviour change for either caller style.

2. **`EntityStats` supports `__getitem__` in addition to attribute access.**
   The brief says "immutable record" and the test file uses only
   attribute access (`get_stats("soldier").damage_per_sec`). However,
   sibling `sim/building.py:tick_construction` does `stats["max_hp"]`
   (subscript). To avoid forcing a merge-time edit in `sim/building.py`
   (which is on `do_not_edit`), `EntityStats.__getitem__` is implemented:
   `stats["max_hp"]` → `stats.max_hp`, plus a legacy alias
   `stats["hp"]` → `stats.max_hp` matching the stub tables used by the
   sibling test fixtures.

3. **`entity_id` allocation uses `max(existing_ids) + 1`** (or 0 for an
   empty `game.entities`). The brief specifies this; just noting that
   it is robust to non-contiguous ids (e.g. after entity deaths).

4. **`pytest` was not run.** Despite the brief stating `python -m pytest`
   is allow-listed via `.claude/settings.local.json`, every Bash /
   PowerShell invocation including `python -m pytest`, `python -c`, and
   even `pytest --version` was rejected at runtime by the sandbox.
   Only argument-less `python --version` succeeded. The implementation
   was hand-traced against each assertion in `tests/test_entities.py`
   (5 tests, ~20 assertions, all confirmed to pass by inspection). The
   parent agent should run pytest after merge to verify GREEN.
