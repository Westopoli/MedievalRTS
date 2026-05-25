"""Fitness runner — runs round-robin matches, reports win-rate matrix.

Usage:
    python -m _balance.runner --trials 5 --seeds 5 --max-sec 300

Prints:
  - per-match line with seed, matchup, winner, ticks, end-state stats
  - aggregate win-rate matrix
  - timeout rate (matches that hit max_ticks without termination)
"""

from __future__ import annotations

import argparse
import time
from collections import defaultdict

from sim.contract import TICK_HZ

from _balance.sim_driver import run_match
from _balance.strategies import STRATEGIES


def _reset_module_state() -> None:
    """Clear cross-match module-level state in sim leaves.

    The sim was built with module-level dicts for movement, gather,
    combat, building, training, ai state. Across matches we must wipe
    them or earlier-match entity ids could collide with new ones.
    """
    from sim import ai, building, combat, gather, pathfinding
    pathfinding._move_state.clear()
    gather._gather_state.clear()
    combat._attack_state.clear()
    building._construction.clear()
    building._training.clear()
    if hasattr(ai, "_ai_state"):
        ai._ai_state.clear()


def run_round_robin(
    strategy_names: list[str],
    seeds: list[int],
    trials_per_seed: int,
    max_sec: int,
    verbose: bool = True,
) -> dict:
    """Run every strategy vs every strategy across seeds. Returns aggregate dict."""
    max_ticks = max_sec * TICK_HZ

    wins = defaultdict(int)           # (p0_strat, p1_strat) -> p0 wins count
    losses = defaultdict(int)         # (p0_strat, p1_strat) -> p1 wins count
    timeouts = defaultdict(int)       # (p0_strat, p1_strat) -> timeout count
    total = defaultdict(int)
    tick_totals = defaultdict(int)
    tick_max = defaultdict(int)

    for p0_name in strategy_names:
        for p1_name in strategy_names:
            for seed in seeds:
                for trial in range(trials_per_seed):
                    actual_seed = seed * 1000 + trial
                    _reset_module_state()
                    res = run_match(
                        STRATEGIES[p0_name],
                        STRATEGIES[p1_name],
                        seed=actual_seed,
                        max_ticks=max_ticks,
                        p0_label=p0_name,
                        p1_label=p1_name,
                    )
                    if verbose:
                        print(res)
                    key = (p0_name, p1_name)
                    total[key] += 1
                    tick_totals[key] += res.final_tick
                    tick_max[key] = max(tick_max[key], res.final_tick)
                    if not res.over:
                        timeouts[key] += 1
                    elif res.winner == 0:
                        wins[key] += 1
                    else:
                        losses[key] += 1

    return {
        "strategies": strategy_names,
        "wins": dict(wins),
        "losses": dict(losses),
        "timeouts": dict(timeouts),
        "total": dict(total),
        "tick_avg": {k: tick_totals[k] / total[k] for k in total},
        "tick_max": dict(tick_max),
    }


def print_summary(agg: dict) -> None:
    strats = agg["strategies"]
    n = len(strats)
    print()
    print("=" * 78)
    print("WIN-RATE MATRIX  (rows = P0, cols = P1)")
    print("  cell = P0 win-rate % / timeout-rate %")
    print("=" * 78)
    header = "             " + "  ".join(f"{s:>12}" for s in strats)
    print(header)
    for row in strats:
        cells = []
        for col in strats:
            key = (row, col)
            t = agg["total"].get(key, 0)
            if t == 0:
                cells.append(f"{'-':>12}")
                continue
            w = agg["wins"].get(key, 0)
            to = agg["timeouts"].get(key, 0)
            cells.append(f"{w/t*100:5.1f}% /{to/t*100:5.1f}%")
        print(f"{row:>12} " + "  ".join(f"{c:>12}" for c in cells))
    print()
    print("=" * 78)
    print("AVERAGE / MAX MATCH LENGTH  (sim seconds; max_sec = timeout cap)")
    print("=" * 78)
    print(header)
    for row in strats:
        cells = []
        for col in strats:
            key = (row, col)
            t = agg["total"].get(key, 0)
            if t == 0:
                cells.append(f"{'-':>12}")
                continue
            avg = agg["tick_avg"].get(key, 0) / TICK_HZ
            mx = agg["tick_max"].get(key, 0) / TICK_HZ
            cells.append(f"{avg:5.0f}/{mx:5.0f}s")
        print(f"{row:>12} " + "  ".join(f"{c:>12}" for c in cells))
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Medieval RTS balance runner")
    parser.add_argument("--strategies", nargs="+", default=["default", "rush", "turtle", "idle"],
                        help="Strategy names to round-robin (default: default rush turtle idle)")
    parser.add_argument("--seeds", type=int, default=3,
                        help="Number of distinct seeds (default: 3)")
    parser.add_argument("--trials", type=int, default=1,
                        help="Trials per (matchup, seed) (default: 1)")
    parser.add_argument("--max-sec", type=int, default=300,
                        help="Per-match timeout in sim-seconds (default: 300)")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress per-match lines; print only summary")
    args = parser.parse_args()

    seeds = list(range(42, 42 + args.seeds))
    start = time.time()
    agg = run_round_robin(
        strategy_names=args.strategies,
        seeds=seeds,
        trials_per_seed=args.trials,
        max_sec=args.max_sec,
        verbose=not args.quiet,
    )
    print_summary(agg)
    n_matches = sum(agg["total"].values())
    print(f"Ran {n_matches} matches in {time.time() - start:.1f}s")


if __name__ == "__main__":
    main()
