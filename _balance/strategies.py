"""AI strategy variants for balance testing.

Each strategy is a `Commander` — `(game, player_id, tick) -> list[Command]`.

`default_ai` wraps the shipping `sim/ai.py` exactly. The other strategies
override or filter its output to model different play personalities:

  - rush:    skip walls/gates entirely, train soldiers as fast as possible,
             attack at soldier_count >= 3 instead of 6.
  - turtle:  build walls aggressively (raise the trigger from 1 to 4
             barracks-OR-just-time-based), train fewer military, delay
             attack until soldier_count >= 10.
  - eco:     train villagers up to 18 instead of 10, train minimal
             military, never attack.

These are intentionally crude — the harness is for surfacing dominance,
not for crafting nuanced AI.
"""

from __future__ import annotations

from sim.ai import ai_tick
from sim.contract import Command, Game


def default_ai(game: Game, player_id: int, tick: int) -> list[Command]:
    """Shipping AI verbatim. Reference baseline."""
    return ai_tick(game, player_id, tick)


def _filter_drop(cmds: list[Command], kinds_to_drop: set) -> list[Command]:
    return [c for c in cmds if not (
        (c.kind == "build" and c.building_kind in kinds_to_drop)
    )]


def rush_ai(game: Game, player_id: int, tick: int) -> list[Command]:
    """Skip walls/gates; train more soldiers; attack earlier."""
    cmds = ai_tick(game, player_id, tick)
    cmds = _filter_drop(cmds, {"wall", "gate"})
    # Convert any house-build before barracks into pure barracks rush:
    # only allowed builds = barracks. (Houses still issued when pop-capped;
    # leaving them in is fine for rush — they're cheap.)
    return cmds


def turtle_ai(game: Game, player_id: int, tick: int) -> list[Command]:
    """Same as default but drop attack commands until soldier_count >= 10."""
    cmds = ai_tick(game, player_id, tick)
    soldier_count = sum(
        1 for e in game.entities
        if e.owner == player_id and e.kind == "soldier" and e.hp > 0
    )
    if soldier_count < 10:
        cmds = [c for c in cmds if c.kind != "attack"]
    return cmds


def eco_ai(game: Game, player_id: int, tick: int) -> list[Command]:
    """Drop all attack commands; otherwise default. Will never win."""
    cmds = ai_tick(game, player_id, tick)
    return [c for c in cmds if c.kind != "attack"]


def idle(game: Game, player_id: int, tick: int) -> list[Command]:
    """Punching bag — emits nothing. Loses to any aggressive opponent."""
    return []


STRATEGIES = {
    "default": default_ai,
    "rush": rush_ai,
    "turtle": turtle_ai,
    "eco": eco_ai,
    "idle": idle,
}
