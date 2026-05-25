# leaf-07 assumptions

## Inferences not explicit in brief

1. **Pathfinding stub seam.** Brief says tests stub `sim.pathfinding`; AC-49 mandates `load("res://sim/pathfinding.gd")` inside function bodies. GDScript cannot monkeypatch `static func` on a loaded script the way pytest patches a module. To honor both: added `static var _pf_override = null` on `gather.gd`. The internal `_pf()` helper returns `_pf_override` if set, else `load("res://sim/pathfinding.gd")`. Tests set `_pf_override` to a stub RefCounted in `before_each` and `reset_module_state()` clears it. This preserves the late-bind pattern (real `load()` is the production path) while letting tests inject a teleporting `start_move` / `is_moving==false` stub mirroring `tests/test_gather.py`'s monkeypatch fixture.

2. **"if X in dict" -> `dict.has(X)`.** Per brief footer.

3. **`Optional[str]` for `carrying`.** Untyped `Variant` field on `Contract.Entity` (already in `contract.gd`); compared via `== "wood"` / `== "gold"`; cleared with `null`. Per AC-43.

4. **Tuple -> Vector2i.** Python `(x, y)` becomes `Vector2i(x, y)`. `_chebyshev` takes Vector2i. The pathfinding stub accepts the param untyped and coerces if a Vector2-ish object slips through.

5. **`_gather_state` dict value shape.** Python `_GatherState` dataclass mapped to a Dictionary with `node_id`, `resource_kind`, `gather_progress` keys per brief explicit guidance. Field access uses `.dot` syntax (legal on GDScript Dictionaries) so the call sites read closer to the Python original.

6. **Iteration safety.** Python uses `list(_gather_state.keys())` to allow mid-iteration mutation. Ported as `_gather_state.keys().duplicate()` (Godot 4 `keys()` already returns a fresh Array but `.duplicate()` is explicit/defensive).

7. **`static` vs instance.** Module-level functions and state in Python become `static func` / `static var` on a `RefCounted`-extending GDScript class. Callers do `Gather.start_gather(...)`, `Gather._gather_state[...]` — matches the test pattern in `tests/test_gather.py` (`gather._gather_state.clear()`).

8. **GUT test count.** Brief said "at minimum" 6 named cases; ported all 6 from `tests/test_gather.py` with the same assertions. Total 18 assertions == `test_assertion_budget`.
