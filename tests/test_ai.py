"""Tests for sim/ai.py — deterministic priority script. SPEC §11."""

from __future__ import annotations

import copy

import pytest

from sim.contract import (
    BuildingSnapshot,
    Command,
    Entity,
    Game,
    Map,
    Player,
    POP_CAP_START,
    START_GOLD,
    START_WOOD,
    TICK_HZ,
)
from sim.map_gen import TC0, TC1, generate_map, place_starting_entities
from sim.visibility import init_visibility, recompute_visibility


def _fresh_game(seed: int = 1) -> Game:
    """Build a fresh 2-player game with starting entities + initialised fog."""
    m = generate_map(seed)
    g = Game(
        players=[
            Player(player_id=0, wood=START_WOOD, gold=START_GOLD, pop_cap=POP_CAP_START),
            Player(player_id=1, wood=START_WOOD, gold=START_GOLD, pop_cap=POP_CAP_START),
        ],
        entities=[],
        map=m,
    )
    place_starting_entities(g, seed)
    init_visibility(g)
    recompute_visibility(g)
    return g


def _reset_ai_state() -> None:
    """Wipe module-level AI bookkeeping between tests."""
    import sim.ai as ai
    ai._ai_state.clear()


def test_tick_zero_emits_batch_and_intermediate_ticks_empty():
    _reset_ai_state()
    from sim.ai import ai_tick
    g = _fresh_game()
    batch = ai_tick(g, 1, 0)
    assert len(batch) > 0
    # Subsequent ticks 1..(2*TICK_HZ - 1) return [] (no new batch yet).
    intermediate_empty = all(ai_tick(g, 1, t) == [] for t in range(1, 2 * TICK_HZ))
    assert intermediate_empty


def test_issuing_player_set_on_all_commands():
    _reset_ai_state()
    from sim.ai import ai_tick
    g = _fresh_game()
    batch = ai_tick(g, 1, 0)
    assert all(isinstance(c, Command) for c in batch)
    assert all(c.issuing_player == 1 for c in batch)


def test_fresh_game_first_batch_is_house_build_or_villager_train():
    _reset_ai_state()
    from sim.ai import ai_tick
    g = _fresh_game()
    batch = ai_tick(g, 1, 0)
    # Pop is at cap (5 villagers vs pop_cap 5) AND wood >= 30, so rule 1 fires.
    kinds = [(c.kind, c.building_kind, c.unit_kind) for c in batch]
    assert ("build", "house", None) in kinds or any(
        c.kind == "train" and c.unit_kind == "villager" for c in batch
    )


def test_house_build_precedes_train_when_pop_at_cap():
    _reset_ai_state()
    from sim.ai import ai_tick
    g = _fresh_game()
    # Force pop at cap: starting 5 villagers, pop_cap 5. Wood >= 30. No house yet.
    assert g.players[1].pop_cap == POP_CAP_START
    batch = ai_tick(g, 1, 0)
    # Rule 1 must fire ahead of any train.
    house_idx = next((i for i, c in enumerate(batch)
                      if c.kind == "build" and c.building_kind == "house"), -1)
    train_idx = next((i for i, c in enumerate(batch) if c.kind == "train"), -1)
    assert house_idx != -1
    if train_idx != -1:
        assert house_idx < train_idx


def test_attack_emitted_when_soldiers_ready_and_enemy_tc_snapshot_known():
    _reset_ai_state()
    from sim.ai import ai_tick
    from sim.entities import spawn_unit
    g = _fresh_game()
    # Give player 1 six soldiers near its TC.
    for i in range(6):
        spawn_unit(g, "soldier", 1, (TC1[0] - 2, TC1[1] + i - 2))
    # Inject a snapshot of the enemy (player 0) town_center into player 1's
    # explored_snapshots, so the AI knows where to attack.
    enemy_tc = next(e for e in g.entities
                    if e.kind == "town_center" and e.owner == 0)
    g.explored_snapshots[1][enemy_tc.entity_id] = BuildingSnapshot(
        entity_id=enemy_tc.entity_id,
        kind="town_center",
        owner=0,
        pos=enemy_tc.pos,
        hp_last_seen=enemy_tc.hp,
    )
    batch = ai_tick(g, 1, 0)
    attack_cmds = [c for c in batch
                   if c.kind == "attack" and c.target_entity_id == enemy_tc.entity_id]
    assert len(attack_cmds) >= 1


def test_ai_tick_does_not_mutate_game():
    _reset_ai_state()
    from sim.ai import ai_tick
    g = _fresh_game()
    entities_before = copy.deepcopy(g.entities)
    players_before = copy.deepcopy(g.players)
    visibility_before = copy.deepcopy(g.visibility)
    snapshots_before = copy.deepcopy(g.explored_snapshots)
    _ = ai_tick(g, 1, 0)
    assert g.entities == entities_before
    assert g.players == players_before
    assert g.visibility == visibility_before
    assert g.explored_snapshots == snapshots_before
