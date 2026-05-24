# leaf-07 Assumptions

1. **Sibling stubs via sys.modules.** `sim.entities` and `sim.pathfinding` are parallel-wave leaves not yet on disk. The test file installs lightweight stubs into `sys.modules["sim.entities"]` and `sys.modules["sim.pathfinding"]` via an autouse fixture; `sim/combat.py` imports them lazily inside helper functions so the module itself loads without those siblings present. Once the real siblings ship, no production-code change is needed.

2. **`get_stats` shape.** Assumed stats object exposes `.damage_per_sec: float` and `.attack_range_tiles: int` (and `.max_hp` for test fixtures). Soldier dps=8 range=1, archer dps=5 range=5, villager dps=0 (per SPEC §6 table).

3. **Float accumulator semantics.** `damage_per_sec / TICK_HZ` accumulates per tick; whole units of accumulated damage are subtracted from integer hp each tick the accumulator crosses 1.0, leaving the fractional remainder. For soldier (8/30 = 0.2667) the accumulator reaches 8.0 after exactly 30 ticks, applying 8 damage in one tick on the 30th — matches AC-14 "after 1s, dmg/30 × 30 = dmg".

4. **Death threshold is hp <= 0.** When hp drops to 0 or below, hp is clamped to 0 and the entity is removed from `game.entities`. All attackers targeting that id are cleared from `_attack_state`.

5. **Chebyshev distance.** "In range" uses Chebyshev (king-move) distance since the grid is 8-direction (SPEC §6 AC-13). `attack_range_tiles <= dist`.

6. **Move target tracking.** `_AttackState` stores the last issued `move_target` so we only re-issue `start_move` when the target tile changes or movement has lapsed. Avoids per-tick pathing thrash.

7. **`is_attacking` definition.** Returns True iff entity has an installed attack state entry, regardless of whether it is actively damaging this tick (may be chasing).

8. **Wall/gate combat.** Same mechanism as units — a unit may target a wall/gate entity. Walls have dps=0 so cannot initiate attacks (start_attack returns False if attempted), but can be targeted. Removal from `game.entities` makes them passable via leaf-04's `wall_or_gate_at` lookup.

9. **No pytest run-confirmed.** RED/GREEN could not be executed inside the sandbox (pytest invocation denied). RED is structurally guaranteed (sim/combat.py did not exist when tests/test_combat.py was authored — ImportError). GREEN was verified by manual trace of each assertion against the implementation; see leaf-07 report for the per-test trace.
