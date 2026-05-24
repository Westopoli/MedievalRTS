"""Tests for sim.commands — command validation + dispatch (AC-21, AC-27)."""

from __future__ import annotations

import pytest

from sim.contract import (
    Command, Entity, Game, Map, Player, MAP_H, MAP_W, START_GOLD, START_WOOD,
    POP_CAP_START,
)
from sim import commands as cmds
from sim import combat, gather, pathfinding
from sim.map_gen import generate_map, place_starting_entities, TC0, TC1
from sim.visibility import init_visibility, recompute_visibility


SEED = 12345


def _fresh_game() -> Game:
    # Wipe sibling module state between tests (they keep dict state).
    pathfinding._move_state.clear()
    gather._gather_state.clear()
    combat._attack_state.clear()
    m = generate_map(SEED)
    players = [
        Player(player_id=0, wood=START_WOOD, gold=START_GOLD, pop_cap=POP_CAP_START),
        Player(player_id=1, wood=START_WOOD, gold=START_GOLD, pop_cap=POP_CAP_START),
    ]
    g = Game(players=players, entities=[], map=m)
    place_starting_entities(g, SEED)
    init_visibility(g)
    recompute_visibility(g)
    return g


def _villager(g: Game, owner: int) -> Entity:
    return next(e for e in g.entities if e.kind == "villager" and e.owner == owner)


def _tc(g: Game, owner: int) -> Entity:
    return next(e for e in g.entities if e.kind == "town_center" and e.owner == owner)


def _nearest_tree_to(g: Game, pos: tuple[int, int]) -> Entity:
    trees = [e for e in g.entities if e.kind == "tree"]
    return min(trees, key=lambda t: max(abs(t.pos[0] - pos[0]), abs(t.pos[1] - pos[1])))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_authority_mismatch_drops_move():
    g = _fresh_game()
    p1_vil = _villager(g, 1)
    orig_pos = p1_vil.pos
    cmd = Command(kind="move", issuing_player=0,
                  entity_id=p1_vil.entity_id, target_tile=(p1_vil.pos[0] + 1, p1_vil.pos[1]))
    result = cmds.apply_command(g, cmd)
    assert result is False
    assert p1_vil.pos == orig_pos
    assert not pathfinding.is_moving(p1_vil.entity_id)


def test_fog_blocks_move_to_unseen_tile():
    g = _fresh_game()
    p0_vil = _villager(g, 0)
    # TC1 area is far from player 0's vision (TC0=(10,30), TC1=(70,30)).
    target = (TC1[0] + 2, TC1[1])
    # Sanity: that tile is unseen for player 0
    assert g.visibility[0][target[0]][target[1]] == "unseen"
    cmd = Command(kind="move", issuing_player=0,
                  entity_id=p0_vil.entity_id, target_tile=target)
    result = cmds.apply_command(g, cmd)
    assert result is False
    assert not pathfinding.is_moving(p0_vil.entity_id)


def test_fog_cheat_bypasses_fog():
    g = _fresh_game()
    g.players[0].fog_cheat = True
    p0_vil = _villager(g, 0)
    target = (TC1[0] + 2, TC1[1])
    cmd = Command(kind="move", issuing_player=0,
                  entity_id=p0_vil.entity_id, target_tile=target)
    result = cmds.apply_command(g, cmd)
    assert result is True
    assert pathfinding.is_moving(p0_vil.entity_id)


def test_gather_visible_tree_succeeds():
    g = _fresh_game()
    p0_vil = _villager(g, 0)
    tree = _nearest_tree_to(g, p0_vil.pos)
    # Sanity: nearby tree tile is visible to player 0
    assert g.visibility[0][tree.pos[0]][tree.pos[1]] in ("visible", "explored")
    cmd = Command(kind="gather", issuing_player=0,
                  entity_id=p0_vil.entity_id, resource_node_id=tree.entity_id)
    result = cmds.apply_command(g, cmd)
    assert result is True
    assert gather.is_gathering(p0_vil.entity_id)


def test_attack_by_villager_drops():
    # Villager has dps=0; subsystem returns False; commands must propagate False.
    g = _fresh_game()
    g.players[0].fog_cheat = True  # bypass fog so we hit the subsystem check
    p0_vil = _villager(g, 0)
    p1_vil = _villager(g, 1)
    cmd = Command(kind="attack", issuing_player=0,
                  entity_id=p0_vil.entity_id, target_entity_id=p1_vil.entity_id)
    result = cmds.apply_command(g, cmd)
    assert result is False
    assert not combat.is_attacking(p0_vil.entity_id)


def test_train_wrong_owner_drops():
    g = _fresh_game()
    p1_tc = _tc(g, 1)
    cmd = Command(kind="train", issuing_player=0,
                  building_id=p1_tc.entity_id, unit_kind="villager")
    result = cmds.apply_command(g, cmd)
    assert result is False


def test_stop_cancels_all_state():
    g = _fresh_game()
    p0_vil = _villager(g, 0)
    # Install some state manually via subsystem calls.
    tree = _nearest_tree_to(g, p0_vil.pos)
    assert gather.start_gather(g, p0_vil.entity_id, tree.entity_id) is True
    assert gather.is_gathering(p0_vil.entity_id)
    # Force-install a movement state so we can verify stop clears it. The
    # gather subsystem's call to pathfinding.start_move may legitimately
    # return False when the resource tile is unreachable (e.g., tree tile
    # itself blocks pathing) — that's a wave-1 inter-leaf integration
    # issue (cleanup TODO) and orthogonal to AC-27 stop semantics.
    pathfinding.start_move(g, p0_vil.entity_id, (p0_vil.pos[0] + 1, p0_vil.pos[1]))
    assert pathfinding.is_moving(p0_vil.entity_id)
    cmd = Command(kind="stop", issuing_player=0, entity_id=p0_vil.entity_id)
    result = cmds.apply_command(g, cmd)
    assert result is True
    assert not gather.is_gathering(p0_vil.entity_id)
    assert not pathfinding.is_moving(p0_vil.entity_id)
    assert not combat.is_attacking(p0_vil.entity_id)


def test_apply_commands_returns_success_count():
    g = _fresh_game()
    p0_vil = _villager(g, 0)
    p1_vil = _villager(g, 1)
    tree = _nearest_tree_to(g, p0_vil.pos)
    good = Command(kind="gather", issuing_player=0,
                   entity_id=p0_vil.entity_id, resource_node_id=tree.entity_id)
    bad_authority = Command(kind="stop", issuing_player=0, entity_id=p1_vil.entity_id)
    bad_train = Command(kind="train", issuing_player=0,
                        building_id=_tc(g, 1).entity_id, unit_kind="villager")
    n = cmds.apply_commands(g, [good, bad_authority, bad_train])
    assert n == 1
