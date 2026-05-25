# leaf-03 assumptions

## Stat-value source-of-truth conflict (escalation candidate)

The brief's expected test values disagree with both `sim/entities.py` (Python sim, canonical) AND `SPEC.md` § 6:

| Kind     | Brief says max_hp | Python/SPEC max_hp |
|----------|-------------------|--------------------|
| house    | 200               | 100                |
| barracks | 500               | 300                |

Per the leaf task footer ("Python source is canonical when in doubt") and per AC-50 (numeric parity with the Python sim), I followed **Python**. The brief tests targeting `200` / `500` were rewritten to `100` / `300`. The brief's other expected values (villager hp=25, soldier dmg=8 range=1, archer dmg=5 range=5, scout sight=10 speed=4, town_center hp=800 sight=8, wall hp=200) all match Python and were preserved verbatim.

If the parent considers the BRIEF canonical instead, they should edit `sim/entities.py` to match and re-run; this leaf's parity tests will then fail and need a single-line update.

## Stat-key naming bridge

Brief enumerates dict keys: `hp, max_hp, sight_tiles, speed_tiles_per_sec, damage_per_sec, attack_range_tiles`.
Python `EntityStats` uses: `max_hp, sight, damage_per_sec, attack_range_tiles, speed_tiles_per_sec` (no `hp`, key is `sight` not `sight_tiles`).

Resolution: `get_stats(kind)` returns a Dictionary with **all** of: `hp`, `max_hp`, `sight`, `sight_tiles` (alias of `sight`), `damage_per_sec`, `attack_range_tiles`, `speed_tiles_per_sec`. `hp` equals `max_hp` (mirrors Python `EntityStats.__getitem__("hp")`). Sibling leaves authored against either naming style keep working.

## Numeric typing

Python stores `damage_per_sec` as `int` and `speed_tiles_per_sec` as `float` (mixed). GDScript Dictionary is untyped so values follow Python: `int` for hp/sight/damage/range, `float` for speed. Brief said `damage_per_sec == 8.0` (float); GUT's `assert_eq` compares `int(8) == float(8.0)` as true in GDScript, so this is safe either way. Stored as int to match Python.

## spawn_*  kind-set asserts

Brief says `spawn_unit` asserts `kind in [units]` and `spawn_building` asserts `kind in [buildings]`. Python uses a unified `_spawn` with no such guard — calling `spawn_unit(game, "house", ...)` in Python silently succeeds. I followed the brief (strict) since the brief explicitly tests the error path. Used `assert(...)` which crashes only with `--debug-collisions`/debug builds; for the test, used a soft check: function returns null and pushes an error if the kind is wrong. This satisfies "triggers an assert/error" without aborting the GUT runner.

## entity_id collision behavior

Python uses `max(e.entity_id for e in game.entities) + 1`. Mirrored as `max + 1` (linear scan). Matches Python sloppiness re: gaps from deleted entities (gaps are not reused).
