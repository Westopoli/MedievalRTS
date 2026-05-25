# Leaf-06 Assumptions

## Inferences made

1. **Visibility grid representation**: Used nested `Array[Array[Array[String]]]`
   exactly mirroring the Python `list[list[list[str]]]` shape. Brief listed this
   vs `PackedByteArray` as a likely inference. Chose the nested-Array form so
   the Python `init_visibility`/`recompute_visibility` logic ports
   line-for-line, and so the contract.gd comment `# visibility[player_id][x][y]
   -> String` reads literally. Memory cost: 80*60*2 = 9,600 Strings (~150 KB
   when explored). Acceptable for v0.

2. **Iteration order in `recompute_visibility`**: x-outer, y-inner (same as
   Python). Demote pass and visibility-mark pass each iterate all cells per
   player. The Python implementation iterates entities sequentially in
   `game.entities` order; the port preserves that.

3. **`get_stats` return shape**: The brief said `sight_tiles`, and leaf-03's
   brief confirms `get_stats(kind) -> Dictionary` with `sight_tiles` key. The
   Python source uses `.sight` on a dataclass — the GDScript port uses
   `["sight_tiles"]` on a Dictionary. `_get_sight()` defensively handles both:
   Dictionary via `.get("sight_tiles", 0)`, otherwise `stats.sight_tiles`
   property access.

4. **Test stubbing pattern**: Added a module-level `static var
   _get_stats_override: Callable` to `visibility.gd`. When valid, the impl
   uses it instead of `load("res://sim/entities.gd").get_stats`. Tests set it
   in `before_each` and clear it in `after_each` via `reset_module_state()`
   (mirrors SPEC_GODOT.md AC-47 pattern). This isolates leaf-06 from
   sibling-leaf-03 producing `entities.gd` in parallel; once leaf-03 lands
   the override is unused and the production `load()` path activates.

5. **`Vector2i` for tile params**: Used `Vector2i` for `target_tile` in
   `is_command_visible` (Python uses `tuple[int, int]`). This matches the
   contract.gd Command.target_tile field type `Vector2i | null`.

6. **`reset_module_state()`**: Added per AC-47 even though the module's only
   state is the test-override Callable. Keeps the pattern uniform with other
   sim modules.

## Blocker

GUT verification could not be executed by leaf-06 — the harness denies invoking
the Godot binary (both Bash and PowerShell calls to
`Godot_v4.6.3-stable_win64.exe` are blocked at the permission layer). Static
review only: impl is 142 lines (under 200 budget), tests are 24 assertions
(under 25 budget), all leaf-owned paths only. Parent should run:

    & "C:\Users\Westley Yarlott\Downloads\Godot_v4.6.3-stable_win64.exe\Godot_v4.6.3-stable_win64.exe" --headless --path godot/ -s addons/gut/gut_cmdln.gd -gtest=res://tests/test_visibility.gd -gexit

to confirm GREEN before merging.
