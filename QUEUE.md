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
| Godot port wave 1 (sim parity) | substantially-done | 2026-05-25 | 11 sim leaves ported via parallel `/swarm` cascade + parent contract + GUT umbrella. 124/127 GREEN. Every test file passes in isolation. Pushed `b4f7533`. Six optional follow-ups parked in SESSION_LOG `## Session Pause — 2026-05-25 (Godot port wave 1)`. |
| Godot port wave 2 (render + input + camera) | not-started | — | Awaiting user greenlight. Per SPEC_GODOT.md §§ 6-10. Parent-owned scaffolding; no swarm cascade needed. |
| Cross-file GUT pollution cleanup | done | 2026-05-26 | Root cause: `test_commands.gd` injected stubs via `Commands.set_module()` with no `after_each` teardown → leaked into `test_game` + `test_umbrella`. Fix: source-fix `after_each` + defensive resets + `Building.reset_module_state` audit (option C). 127/127 GREEN. Details in SESSION_LOG `## Session Pause — 2026-05-26`. |
| SPEC_GODOT.md AC-72 wording update | open | 2026-05-25 | Wording still says byte-parity; landed code does structural parity. Reconcile before any wave-2 spec edit. |
| Parent assumption-sweep (briefs_godot/leaf-*.ASSUMPTIONS.md × 8) | open | 2026-05-25 | Per `/swarm` skill protocol. Hard-flagged items: RNG mismatch (leaf-02), hp value disagreement (leaf-03), heap tie-break (leaf-05), Callable injection seam (leaf-07), cost-tuple translation (leaf-09), tiebreaker for both-TCs-die (leaf-12). |
| Worktree branch cleanup (`worktree-agent-*` × 12) | open | 2026-05-25 | Locked by Agent runtime; gitignored, not blocking. Needs explicit `git worktree unlock` + `remove`. |
| Camp-day integration decision | not-applicable | — | Demo lives outside camp curriculum (`Demos/`). |
