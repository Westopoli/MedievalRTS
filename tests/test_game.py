"""Leaf-11 tests: tick orchestrator + new_game factory + scripted commands."""

from __future__ import annotations

from sim.contract import (
    Command,
    NUM_PLAYERS,
    POP_CAP_START,
    START_GOLD,
    START_WOOD,
)


def test_new_game_basic_shape() -> None:
    from sim.game import new_game

    g = new_game(seed=42)
    assert len(g.players) == NUM_PLAYERS
    assert g.players[0].wood == START_WOOD
    assert g.players[0].gold == START_GOLD
    assert g.players[0].pop_cap == POP_CAP_START
    # Starting entities placed by map_gen
    tcs = [e for e in g.entities if e.kind == "town_center"]
    assert len(tcs) == 2
    villagers = [e for e in g.entities if e.kind == "villager"]
    assert len(villagers) == 10
    assert g.tick_count == 0
    assert g.over is False


def test_initial_visibility_seeded() -> None:
    from sim.game import new_game

    g = new_game(seed=42)
    # init_visibility + initial recompute_visibility called in new_game
    assert g.visibility[0][10][30] == "visible"


def test_tick_advances_and_visibility_present() -> None:
    from sim.game import new_game

    g = new_game(seed=42)
    g.tick([])
    assert g.tick_count == 1
    assert g.visibility[0][10][30] == "visible"


def test_many_ticks_no_exception() -> None:
    from sim.game import new_game

    g = new_game(seed=42)
    for _ in range(50):
        g.tick([])
    assert g.tick_count == 50


def test_scripted_command_reaches_apply() -> None:
    """A stop command via inputs should clear movement state."""
    from sim.game import new_game
    from sim import pathfinding

    g = new_game(seed=42)
    g.tick([])
    villager = next(e for e in g.entities if e.kind == "villager" and e.owner == 0)
    # Move toward a visible tile near TC
    move_cmd = Command(
        kind="move", issuing_player=0, entity_id=villager.entity_id,
        target_tile=(10, 31),
    )
    g.tick([move_cmd])
    # Now stop — even if not currently moving, must not raise.
    stop_cmd = Command(kind="stop", issuing_player=0, entity_id=villager.entity_id)
    g.tick([stop_cmd])
    assert not pathfinding.is_moving(villager.entity_id)


def test_over_short_circuits_tick() -> None:
    """AC-37: g.over = True -> tick_count must not advance."""
    from sim.game import new_game

    g = new_game(seed=42)
    g.over = True
    pre = g.tick_count
    g.tick([Command(kind="stop", issuing_player=0, entity_id=0)])
    assert g.tick_count == pre


def test_win_when_tc_destroyed() -> None:
    """Kill p1 TC by setting hp=0 + removing it; one tick later p0 wins."""
    from sim.game import new_game

    g = new_game(seed=42)
    p1_tc = next(e for e in g.entities if e.kind == "town_center" and e.owner == 1)
    p1_tc.hp = 0
    # Remove dead TC manually (combat tick handles its own removals but a directly
    # zeroed entity needs explicit removal — orchestrator also sweeps hp<=0).
    g.tick([])
    assert g.over is True
    assert g.winner == 0


def test_scripted_player_commands_tick_60_house() -> None:
    from sim.game import new_game, scripted_player_commands

    g = new_game(seed=42)
    cmds = scripted_player_commands(g, player_id=0, tick=60)
    assert len(cmds) >= 1
    builds = [c for c in cmds if c.kind == "build" and c.building_kind == "house"]
    assert len(builds) == 1


def test_scripted_player_commands_empty_off_milestone() -> None:
    from sim.game import new_game, scripted_player_commands

    g = new_game(seed=42)
    assert scripted_player_commands(g, player_id=0, tick=61) == []
    assert scripted_player_commands(g, player_id=0, tick=0) == []
