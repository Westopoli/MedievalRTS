---
leaf_id: leaf-07
spec_file: SPEC.md
spec_lines: 62-84
test_file: tests/test_combat.py
impl_file: sim/combat.py
contract_imports:
  - sim.contract.Game
  - sim.contract.Entity
  - sim.contract.TICK_HZ
do_not_edit:
  - sim/contract.py
  - sim/__init__.py
  - sim/map_gen.py
  - sim/entities.py
  - sim/walls.py
  - sim/pathfinding.py
  - sim/visibility.py
  - sim/gather.py
  - sim/building.py
  - sim/commands.py
  - sim/ai.py
  - sim/game.py
  - tests/test_umbrella.py
  - tests/conftest.py
  - SPEC.md
  - .claude-swarm.toml
  - briefs/**
  - app/**
  - assets/**
  - "*.tscn"
  - "*.gd"
  - project.godot
impl_line_budget: 180
test_assertion_budget: 18
wave: 1
---

## Task

Implement combat tick + death cleanup per SPEC.md lines 62-84 (AC-14, AC-25).

May import `sim.entities.get_stats` for `damage_per_sec` + `attack_range_tiles`, and `sim.pathfinding.start_move` / `cancel_move` / `is_moving` to drive in-range pursuit.

Provide in `sim/combat.py`:

1. `start_attack(game: Game, attacker_id: int, target_id: int) -> bool` — installs attack state for the attacker (target entity_id). Returns `False` if attacker is missing/dead, target missing/dead, attacker has `damage_per_sec == 0`, or attacker.owner == target.owner. Otherwise installs state, returns `True`.

2. `tick_combat(game: Game) -> None` — for each entity with attack state:
   - If target is missing or `hp <= 0`, clear this entity's attack state.
   - Else if Chebyshev distance between attacker.pos and target.pos `<= attack_range_tiles`: cancel any movement on attacker; deduct `damage_per_sec / TICK_HZ` from target.hp (use a float accumulator per-attacker stored alongside state, applied to integer hp on each whole-damage threshold).
   - Else attacker not yet in range: if attacker is not moving toward target's current tile, issue `start_move` toward target's tile.
   - After damage application, if target.hp <= 0, remove target from `game.entities` and clear attack state for ALL entities targeting that id.

3. `cancel_attack(entity_id: int) -> None` — remove attack state for entity (silent no-op if absent).

4. `is_attacking(entity_id: int) -> bool`.

Combat state lives in module-level `_attack_state: dict[int, _AttackState]`.

Damage to walls/gates is allowed via this same mechanism (target a wall/gate entity). Destroyed walls/gates become passable automatically once their entity is removed from `game.entities` — leaf-04 pathfinding consults `sim.walls.wall_or_gate_at` which already returns None for removed entities.

## Acceptance

Run `python -m pytest tests/test_combat.py -x -q`. Confirm RED. Implement in `sim/combat.py` only. Confirm GREEN. Write to `.swarm/pending/leaf-07/`.

Tests:
- `start_attack` with same-owner attacker+target returns False, no state installed
- Two adjacent opposing soldiers: after one second of `tick_combat`, target hp == max_hp - damage_per_sec (AC-14)
- A target reduced to hp <= 0 is removed from `game.entities`
- All attackers targeting a dead target have their attack state cleared
- An attacker out of range issues a movement command (verify movement state appears for attacker after one `tick_combat`)
- A villager (damage_per_sec=0) cannot start an attack: `start_attack` returns False (AC-12 villagers non-combat)

## Escalation triggers

Stop and report to the parent if:
- A type the test imports is not in contract_imports (`sim.entities` / `sim.pathfinding` / `sim.walls` cross-leaf imports permitted).
- The impl would need to create a new file.
- The impl would need to edit a file in do_not_edit.
- Two sibling assertions seem to require contradictory behavior.
- Impl approaches impl_line_budget with assertions still failing.

## Assumption log

Write inferences to `briefs/leaf-07.ASSUMPTIONS.md`.
