"""Headless match driver for the Medieval RTS balance harness.

Wraps `sim.game.new_game` and runs a full match between two `Commander`
callables. Returns a `MatchResult` with winner, tick count, and end-state
snapshots (resources, military counts) for fitness scoring.

This module is NOT part of the shipping sim — lives under `_balance/`,
excluded from any future student ZIP via the project's build filter (and
ignored from version-control of the shipping sim's behavior).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from sim.contract import Command, Game, TICK_HZ
from sim.game import new_game

Commander = Callable[[Game, int, int], list[Command]]


@dataclass
class PlayerStats:
    wood: int
    gold: int
    villager_count: int
    soldier_count: int
    archer_count: int
    scout_count: int
    house_count: int
    barracks_count: int
    wall_count: int
    gate_count: int
    tc_alive: bool


@dataclass
class MatchResult:
    winner: int | None
    over: bool
    final_tick: int
    seed: int
    p0_label: str
    p1_label: str
    stats: list[PlayerStats] = field(default_factory=list)

    def __str__(self) -> str:
        outcome = (
            f"winner=P{self.winner}" if self.over else "TIMEOUT"
        )
        return (
            f"[seed={self.seed:<6} {self.p0_label:>14} vs {self.p1_label:<14}] "
            f"{outcome:>10}  ticks={self.final_tick:>5}  "
            f"sec={self.final_tick / TICK_HZ:6.1f}  "
            f"P0(w={self.stats[0].wood:>4} g={self.stats[0].gold:>4} "
            f"v={self.stats[0].villager_count} s={self.stats[0].soldier_count} "
            f"a={self.stats[0].archer_count})  "
            f"P1(w={self.stats[1].wood:>4} g={self.stats[1].gold:>4} "
            f"v={self.stats[1].villager_count} s={self.stats[1].soldier_count} "
            f"a={self.stats[1].archer_count})"
        )


def _snapshot_player(game: Game, pid: int) -> PlayerStats:
    p = game.players[pid]
    ents = [e for e in game.entities if e.owner == pid]
    by_kind = {}
    for e in ents:
        by_kind[e.kind] = by_kind.get(e.kind, 0) + 1
    return PlayerStats(
        wood=p.wood,
        gold=p.gold,
        villager_count=by_kind.get("villager", 0),
        soldier_count=by_kind.get("soldier", 0),
        archer_count=by_kind.get("archer", 0),
        scout_count=by_kind.get("scout", 0),
        house_count=by_kind.get("house", 0),
        barracks_count=by_kind.get("barracks", 0),
        wall_count=by_kind.get("wall", 0),
        gate_count=by_kind.get("gate", 0),
        tc_alive=by_kind.get("town_center", 0) > 0,
    )


def run_match(
    p0_commander: Commander,
    p1_commander: Commander,
    seed: int = 42,
    max_ticks: int = TICK_HZ * 300,  # default 5 sim minutes
    p0_label: str = "P0",
    p1_label: str = "P1",
) -> MatchResult:
    """Run a single match between two Commanders. Returns MatchResult."""
    game = new_game(seed=seed)
    for t in range(max_ticks):
        inputs: list[Command] = []
        inputs += p0_commander(game, 0, t)
        inputs += p1_commander(game, 1, t)
        game.tick(inputs)
        if game.over:
            break
    return MatchResult(
        winner=game.winner,
        over=game.over,
        final_tick=game.tick_count,
        seed=seed,
        p0_label=p0_label,
        p1_label=p1_label,
        stats=[_snapshot_player(game, 0), _snapshot_player(game, 1)],
    )
