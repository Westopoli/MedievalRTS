# leaf-05 assumptions

## Sight values (test fixture)

`sim/entities.py` (leaf-02) was not yet on disk at impl time, so the test fixture monkeypatches `sim.entities.get_stats` with a local table of `sight` values. Values used:

- villager 5, soldier 5, archer 6, scout 9
- town_center 8, house 4, barracks 5, wall 2, gate 3
- tree 0, gold_mine 0

These mirror the `sight` field referenced in leaf-02's spec checks (e.g. SPEC names `town_center.sight == 8`). If leaf-02 ships different numbers, the test still passes as long as `sight >= 1` for the kinds it actually exercises (villager, scout, town_center). The Chebyshev assertions are tight only for `villager.sight == 5` and `town_center.sight == 8`.

## Lazy import of sim.entities

`sim/visibility.py` imports `sim.entities` lazily inside `_get_sight` so that:
1. Tests can monkeypatch `sim.entities.get_stats` before the first call.
2. The module can be imported even when leaf-02 has not landed yet.

## Snapshots are never deleted

The brief says snapshots of destroyed enemy buildings persist (ghost). Implementation never removes entries from `explored_snapshots[p]`; it only adds/overwrites while visible. A destroyed building (hp<=0) is skipped during the vision-grant + snapshot-refresh loops, so its last known hp_last_seen freezes naturally.

## Zero-sight entities

Trees, gold_mines, and any building with sight==0 still mark their own tile as `visible` for the owner. (Resource nodes are unowned in practice so this is a no-op; included for safety.) Did not gate this on building-vs-unit because resource nodes have owner that may be set to a player in atypical scenarios — left permissive.

## Out-of-bounds entity positions

`recompute_visibility` and `visible_entities_for` defensively skip entities whose `pos` is outside `[0, MAP_W) x [0, MAP_H)`. No spec language on this; chosen to avoid IndexError if a sibling leaf produces an OOB position.

## RED/GREEN verification not run by leaf

The sandbox denied `python -m pytest` execution from this leaf. The test file was authored to fail RED (ImportError on `from sim import visibility`) prior to the impl being written, and the impl follows the brief's contract verbatim. Final pytest verification will be performed by `swarm-merge` running the umbrella against the staged files.
