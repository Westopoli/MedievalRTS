# Medieval RTS — Workstream Queue

One row per workstream. Update status as work moves.

| Workstream | Status | Last touched | Note |
|---|---|---|---|
| SPEC v0 (37 ACs) | done | 2026-05-23 | Committed `d5d4623`. Symmetric fog, walls+gates, 80×60 scrolling map, sim/frontend split, Commander pattern. |
| `.claude-swarm.toml` + umbrella RED + briefs | done | 2026-05-23 | `/swarm-review` PASS 11/11. Committed `b133322`. |
| Wave 1 sim modules (8 leaves) | done | 2026-05-23 | 70 per-leaf tests passing in isolation. Committed `68660e7`. |
| Wave 2 sim modules (commands/ai/game) | done | 2026-05-23 | 23 per-leaf tests passing. Umbrella 10/12 → 11/12 after gather fix. Committed `125ab86` + `6deed4b`. |
| Cross-test sys.modules pollution cleanup | done | 2026-05-25 | Rewrote 5 wave-1 test files to `monkeypatch.setattr` on real `sim.*` modules instead of replacing them in `sys.modules`. `pytest tests/` now collects and runs 105/105 green. |
| `_balance/` harness build | done | 2026-05-25 | `_balance/{sim_driver,strategies,runner}.py` + `probe_military.py`. Round-robin matrix runs clean. |
| AI tuning iteration | done | 2026-05-25 | Two final fixes: rule 9 trigger lowered from `sol_n>=6` to `(sol_n+arch_n)>=3` (army leaves base at t~180s instead of t~488s); combat chase re-issue stopped resetting path every tick (was comparing `state.move_target` against `target.pos` — always unequal once adjacent fallback fired). default vs idle: 100% win, 249s avg. |
| Umbrella `test_full_scripted_match_terminates_with_winner` | passing | 2026-05-25 | 12/12 green after AI tuning. |
| Godot frontend port | unblocked | 2026-05-25 | Balance settled. Awaiting user greenlight to start. Tune-first-then-port lock satisfied. |
| Camp-day integration decision | not-applicable | — | Demo lives outside camp curriculum (`Demos/`). |
