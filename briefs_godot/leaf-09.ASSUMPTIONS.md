# leaf-09 assumptions

1. **Tuple representation.** Python `tuple[int, int, int]` and
   `tuple[int, int, int, EntityKind]` in BUILD_COSTS / TRAIN_COSTS are encoded
   as untyped `Array` literals (`[30, 0, 10]`, `[50, 0, 12, "town_center"]`)
   since GDScript has no tuple type. Tests compare with `assert_eq` against
   the same Array literal — equality holds positionally.

2. **BUILDING_FOOTPRINT values use Vector2i.** Python uses `tuple[int, int]`
   for `(width, height)`. The brief explicitly specified `Vector2i(w, h)` so
   we use Vector2i. Tests compare with `Vector2i(3, 3)`.

3. **Module-level `var` -> `static var`.** SPEC_GODOT.md AC-47 says
   file-level `var`. To get the Python module-singleton semantics (where
   `B._construction.clear()` in tests mutates the same dict that
   `start_build` writes to), we use `static var`. Tests reach the state via
   `Building._construction.has(...)` which works for static vars on a
   preloaded script.

4. **Late-bind via override slots.** AC-49 says late-bind via `load()`
   inside functions. Since `entities.gd` and `pathfinding.gd` are
   not-yet-implemented sibling leaves, the impl falls back to `load()` only
   if `entities_override` / `pathfinding_override` is null. Tests assign
   these slots in `before_each`, so the real sibling files are never
   touched during this leaf's GUT run. This is the GDScript equivalent of
   the Python tests' `monkeypatch.setattr(sim.entities, ...)`.

5. **Stub script as nested class.** The test file declares
   `class _EntitiesStub extends RefCounted` with `static func` methods
   matching the sibling API surface that `building.gd` calls
   (`spawn_unit`, `spawn_building`, `is_unit`, `get_stats` — `is_building`
   added for symmetry). The class object itself is passed in as the
   override; building.gd calls e.g. `_EntitiesStub.spawn_building(...)`,
   which is valid since GDScript class objects forward static calls.

6. **Adjacency spawn algorithm copied verbatim.** Order N, E, S, W, NE, SE,
   SW, NW; first iterates over offsets, then over footprint tiles. Returns
   the first candidate that is in-bounds, not part of the footprint, not
   already seen, and not occupied by a live entity. The Python source's
   exact iteration order is preserved so AC-50 numeric parity is
   maintainable when a unit-spawn-location parity test is later added.

7. **`game.map_` not `game.map`.** Contract.gd renames `map` to `map_`
   (Python builtin shadow). All references go through `game.map_`.

8. **Static-binary execution blocked.** The harness denied permission to
   run the Godot binary, so this leaf was verified by static review only.
   The umbrella run during /swarm-merge will catch any runtime defect.
