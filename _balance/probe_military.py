"""Probe: log P0 military positions every 60 sim seconds during default vs idle.

Confirms whether soldiers/archers actually move toward enemy TC at (70, 30)
after rule 9 fires, or whether they stall at base.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sim.contract import TICK_HZ
from sim.game import new_game
from sim.ai import ai_tick
import sim.combat as combat
import sim.pathfinding as pf


def find_tc(game, pid):
    for e in game.entities:
        if e.owner == pid and e.kind == "town_center" and e.hp > 0:
            return e
    return None


def main(seed: int = 42, sim_seconds: int = 600):
    game = new_game(seed=seed)
    max_ticks = TICK_HZ * sim_seconds
    log_interval = TICK_HZ * 60  # every 60 sim sec

    enemy_tc = find_tc(game, 1)
    own_tc = find_tc(game, 0)
    print(f"Own   TC eid={own_tc.entity_id} pos={own_tc.pos}")
    print(f"Enemy TC eid={enemy_tc.entity_id} pos={enemy_tc.pos} hp={enemy_tc.hp}")
    print()

    last_attack_cmd_log = {}

    for t in range(max_ticks):
        cmds = ai_tick(game, 0, t)
        # log attack commands the moment they appear (first time per attacker)
        for c in cmds:
            if c.kind == "attack":
                key = c.entity_id
                if key not in last_attack_cmd_log:
                    last_attack_cmd_log[key] = (t, c.target_entity_id)
        game.tick(cmds)
        if game.over:
            print(f"OVER tick {t} winner=P{game.winner}")
            break
        if t > 0 and t % log_interval == 0:
            sim_t = t // TICK_HZ
            mil = [e for e in game.entities if e.owner == 0 and e.kind in ("soldier", "archer", "scout") and e.hp > 0]
            tc = find_tc(game, 1)
            tc_hp = tc.hp if tc else 0
            p0 = game.players[0]
            print(f"\n=== t={sim_t}s  P0(w={p0.wood} g={p0.gold})  enemy_TC_hp={tc_hp}  mil={len(mil)}  attack_cmds_emitted={len(last_attack_cmd_log)}")
            for e in mil:
                atk = combat._attack_state.get(e.entity_id)
                mv = pf._move_state.get(e.entity_id) if hasattr(pf, "_move_state") else None
                atk_str = f"atk(tgt={atk.target_id},in_range={atk.in_range_ticks},dmg={atk.applied_damage},mt={atk.move_target})" if atk else "atk=None"
                mv_str = f"path_len={len(mv.path)},next={mv.path[0] if mv.path else None}" if mv else "no_move"
                print(f"   {e.kind:7} eid={e.entity_id:3} pos={e.pos} hp={e.hp:3}  {atk_str}  {mv_str}")
    else:
        sim_t = max_ticks // TICK_HZ
        print(f"\nTIMEOUT {sim_t}s  attack_cmds_emitted={len(last_attack_cmd_log)}  first_attack_tick={min(last_attack_cmd_log.values())[0] if last_attack_cmd_log else 'never'}")


if __name__ == "__main__":
    main()
