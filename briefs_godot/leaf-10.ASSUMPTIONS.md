# leaf-10 assumptions

## Sibling stubs
The wave-1 GDScript sibling modules (pathfinding.gd, gather.gd, combat.gd,
building.gd, visibility.gd) have not landed yet — only `walls.gd` is present
in `godot/sim/`. To exercise `commands.gd` in isolation per AC-49, the impl
exposes a static `set_module(name, script)` override. Tests inject inner-class
`Stub*` scripts (each with the public function set the dispatcher calls plus
a state dict) and verify dispatch via those state dicts. This mirrors the
Python tests' monkey-patch style.

## Fog gate scope
The Python source (`sim/commands.py`) only fog-gates `attack`. SPEC.md AC-21
and the leaf-10 brief task spec both say "`attack` and `gather` still require
visibility." I chose the brief text as canonical for this leaf and fog-gate
`gather` on the resource node's tile too. The test suite does not cover
"gather on unseen node" — that path is dead-code-tested only by visual review.
If the umbrella later asserts otherwise, drop the `_fog_ok(... node.pos)`
check from the gather branch.

## Visibility array fallback
If `game.visibility` is null/empty (uninitialised), `_fog_ok` returns true
(fail-open). This matches `visibility.is_command_visible`'s default in the
Python sim before `init_visibility` runs.

## `stop` always returns true
The Python source returns `True` from `stop` unconditionally after cancelling
state. The GDScript port preserves this — even if nothing was cancelled, the
command is accepted.

## Variant null comparisons
Several Command fields are typed `Variant` with default `null`. Checks use
both `!= null` and `>= 0` for int-like fields (entity_id, building_id) to
match the Python `is not None and >= 0` pattern.

## GREEN verification
The Bash and PowerShell tools in this sandbox refused to execute the Godot
binary, so the test file could not be run from this leaf agent. Code was
audited manually against `tests/test_commands.py` and `sim/commands.py`.
Parent must re-run the GUT command from the brief to confirm GREEN before
merging.
