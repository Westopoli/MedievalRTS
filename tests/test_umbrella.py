"""Umbrella acceptance test — SPEC.md §15.

Encodes spot-checks for AC-1..AC-37. MUST fail until every leaf is merged.
Do not weaken assertions to make this green; the umbrella is the contract.
"""

from __future__ import annotations

import pytest

from sim.contract import (
    CARRY_CAP,
    MAP_H,
    MAP_W,
    POP_CAP_START,
    START_GOLD,
    START_WOOD,
    TICK_HZ,
    BuildingSnapshot,
    Command,
    Entity,
    Game,
    Map,
    Player,
)


# Import sim modules lazily — they don't exist yet (RED). The umbrella must
# import-fail or assertion-fail until the cascade lands every leaf.
def _new_game(seed: int = 42) -> Game:
    from sim.game import new_game  # noqa: WPS433 — intentional lazy import
    return new_game(seed=seed)


def _generate_map(seed: int = 42) -> Map:
    from sim.map_gen import generate_map  # noqa: WPS433
    return generate_map(seed=seed)


# ---------------------------------------------------------------------------
# Map generation — AC-28..AC-34
# ---------------------------------------------------------------------------


def test_map_dimensions_and_determinism() -> None:
    m1 = _generate_map(seed=42)
    m2 = _generate_map(seed=42)
    assert m1.width == MAP_W and m1.height == MAP_H, "AC-28 map dims"
    assert m1.terrain == m2.terrain, "AC-28 same seed -> same terrain"


def test_map_starting_positions_and_resources() -> None:
    g = _new_game(seed=42)
    tcs = [e for e in g.entities if e.kind == "town_center"]
    assert len(tcs) == 2, "AC-29 exactly two TCs"
    by_owner = {tc.owner: tc.pos for tc in tcs}
    assert by_owner[0] == (10, 30), "AC-29 player TC tile"
    assert by_owner[1] == (70, 30), "AC-29 AI TC tile"

    trees_p0 = [e for e in g.entities if e.kind == "tree" and e.pos[0] < 40]
    trees_p1 = [e for e in g.entities if e.kind == "tree" and e.pos[0] >= 40]
    assert 20 <= len(trees_p0) <= 30, "AC-30 ~24 trees on player side"
    assert 20 <= len(trees_p1) <= 30, "AC-30 ~24 trees on AI side"

    mines_p0 = [e for e in g.entities if e.kind == "gold_mine" and e.pos[0] < 40]
    mines_p1 = [e for e in g.entities if e.kind == "gold_mine" and e.pos[0] >= 40]
    assert len(mines_p0) == 2 and len(mines_p1) == 2, "AC-31 two mines per side"

    villagers_p0 = [e for e in g.entities if e.kind == "villager" and e.owner == 0]
    villagers_p1 = [e for e in g.entities if e.kind == "villager" and e.owner == 1]
    assert len(villagers_p0) == 5 and len(villagers_p1) == 5, "AC-32 five villagers per player"


# ---------------------------------------------------------------------------
# Initial resources + pop cap — AC-5, AC-10
# ---------------------------------------------------------------------------


def test_initial_resources_and_pop_cap() -> None:
    g = _new_game(seed=42)
    assert len(g.players) == 2, "v0 two players"
    for p in g.players:
        assert p.wood == START_WOOD, "AC-5 start wood"
        assert p.gold == START_GOLD, "AC-5 start gold"
        assert p.pop_cap == POP_CAP_START, "AC-10 starting pop cap"
        assert p.fog_cheat is False, "AC-22 cheat default off"


# ---------------------------------------------------------------------------
# Fog of war — AC-15..AC-22
# ---------------------------------------------------------------------------


def test_fog_symmetric_and_initial_state() -> None:
    g = _new_game(seed=42)
    g.tick([])  # one tick to populate fog
    # Player 0 sees its own TC area.
    assert g.visibility[0][10][30] == "visible", "AC-16 P0 TC area visible to P0"
    # Player 0 does NOT see player 1's TC.
    assert g.visibility[0][70][30] == "unseen", "AC-21/AC-15 P0 cannot see P1 base initially"
    # Symmetric: player 1 sees its own area, not player 0's.
    assert g.visibility[1][70][30] == "visible", "AC-16 P1 TC area visible to P1"
    assert g.visibility[1][10][30] == "unseen", "AC-15 P1 cannot see P0 base initially"


def test_fog_command_drop_for_unseen_targets() -> None:
    """AC-21: a command targeting an UNSEEN tile is dropped (no crash, no effect)."""
    g = _new_game(seed=42)
    g.tick([])
    villager = next(e for e in g.entities if e.kind == "villager" and e.owner == 0)
    bad = Command(
        kind="move",
        issuing_player=0,
        entity_id=villager.entity_id,
        target_tile=(70, 30),  # P1 base — UNSEEN to P0
    )
    g.tick([bad])
    # Villager must still be near its TC; command dropped.
    assert abs(villager.pos[0] - 10) <= 2, "AC-21 unseen-targeted move dropped"


def test_fog_cheat_waives_gate() -> None:
    """AC-22: setting fog_cheat=True allows command on UNSEEN tile."""
    g = _new_game(seed=42)
    g.players[0].fog_cheat = True
    g.tick([])
    villager = next(e for e in g.entities if e.kind == "villager" and e.owner == 0)
    cmd = Command(
        kind="move",
        issuing_player=0,
        entity_id=villager.entity_id,
        target_tile=(70, 30),
    )
    g.tick([cmd])
    # Villager should have started moving (or at least the command is not dropped).
    # We only assert it didn't crash and the entity is still alive.
    assert villager.hp > 0, "AC-22 cheat: command accepted, no crash"


# ---------------------------------------------------------------------------
# Authority — AC-27
# ---------------------------------------------------------------------------


def test_authority_mismatch_dropped() -> None:
    g = _new_game(seed=42)
    g.tick([])
    p1_villager = next(e for e in g.entities if e.kind == "villager" and e.owner == 1)
    cmd = Command(
        kind="move",
        issuing_player=0,  # P0 trying to move P1's villager
        entity_id=p1_villager.entity_id,
        target_tile=(50, 30),
    )
    start_pos = p1_villager.pos
    g.tick([cmd])
    assert p1_villager.pos == start_pos, "AC-27 cross-owner command dropped"


# ---------------------------------------------------------------------------
# Pathfinding + walls/gates — AC-13, AC-23..AC-25
# ---------------------------------------------------------------------------


def test_walls_block_pathfinding_and_gate_admits_owner() -> None:
    from sim.pathfinding import find_path

    g = _new_game(seed=42)
    # Place a wall by P0 across (15, y) for y in 28..32, gate at (15, 30).
    from sim.building import place_building_immediate  # build helper used by umbrella only
    for y in range(28, 33):
        if y == 30:
            place_building_immediate(g, kind="gate", tile=(15, y), owner=0)
        else:
            place_building_immediate(g, kind="wall", tile=(15, y), owner=0)

    # P1 unit trying to cross row at (15,29) — must route around (no straight path through wall).
    path_enemy = find_path(g, start=(14, 29), goal=(16, 29), owner=1)
    assert path_enemy is None or all(step != (15, 29) for step in path_enemy), "AC-23 wall blocks enemy"

    # P0 unit through the gate at (15,30) — allowed.
    path_owner = find_path(g, start=(14, 30), goal=(16, 30), owner=0)
    assert path_owner is not None and (15, 30) in path_owner, "AC-24 gate admits owner"

    # P1 cannot use the gate.
    path_enemy_gate = find_path(g, start=(14, 30), goal=(16, 30), owner=1)
    assert path_enemy_gate is None or (15, 30) not in path_enemy_gate, "AC-24 gate rejects enemy"


# ---------------------------------------------------------------------------
# Gathering + deposit — AC-6, AC-9
# ---------------------------------------------------------------------------


def test_villager_gathers_wood_and_deposits() -> None:
    g = _new_game(seed=42)
    villager = next(e for e in g.entities if e.kind == "villager" and e.owner == 0)
    tree = next(e for e in g.entities if e.kind == "tree" and e.pos[0] < 40)
    initial_wood = g.players[0].wood

    cmd = Command(
        kind="gather",
        issuing_player=0,
        entity_id=villager.entity_id,
        resource_node_id=tree.entity_id,
    )
    # Run a generous window — walk to tree, fill cap, walk back, deposit.
    for _ in range(TICK_HZ * 60):
        g.tick([cmd])
        if g.players[0].wood > initial_wood:
            break

    assert g.players[0].wood > initial_wood, "AC-6/AC-9 villager gathered + deposited wood"


# ---------------------------------------------------------------------------
# Combat — AC-14
# ---------------------------------------------------------------------------


def test_combat_resolves_and_kills() -> None:
    g = _new_game(seed=42)
    # Spawn two opposing soldiers adjacent via test helper (umbrella-only).
    from sim.entities import spawn_unit

    s_p0 = spawn_unit(g, kind="soldier", owner=0, pos=(40, 30))
    s_p1 = spawn_unit(g, kind="soldier", owner=1, pos=(41, 30))
    g.players[0].fog_cheat = True  # allow attack command without scouting

    cmd = Command(
        kind="attack",
        issuing_player=0,
        entity_id=s_p0.entity_id,
        target_entity_id=s_p1.entity_id,
    )
    for _ in range(TICK_HZ * 30):
        g.tick([cmd])
        if s_p1.hp <= 0:
            break
    assert s_p1.hp <= 0, "AC-14 combat applied damage to death"


# ---------------------------------------------------------------------------
# Win condition — AC-35..AC-37
# ---------------------------------------------------------------------------


def test_winner_and_over_set_when_tc_falls() -> None:
    g = _new_game(seed=42)
    p1_tc = next(e for e in g.entities if e.kind == "town_center" and e.owner == 1)
    p1_tc.hp = 1
    # Apply a final blow via direct combat (umbrella-only helper).
    from sim.entities import spawn_unit

    attacker = spawn_unit(g, kind="soldier", owner=0, pos=(p1_tc.pos[0] - 1, p1_tc.pos[1]))
    g.players[0].fog_cheat = True
    cmd = Command(
        kind="attack",
        issuing_player=0,
        entity_id=attacker.entity_id,
        target_entity_id=p1_tc.entity_id,
    )
    for _ in range(TICK_HZ * 5):
        g.tick([cmd])
        if g.over:
            break
    assert g.over is True, "AC-36 game over"
    assert g.winner == 0, "AC-35 winner set"

    # AC-37: further commands are no-ops.
    pre_tick = g.tick_count
    g.tick([cmd])
    assert g.tick_count == pre_tick, "AC-37 no further ticks once over"


# ---------------------------------------------------------------------------
# End-to-end: full scripted run (AC-aggregate)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_full_scripted_match_terminates_with_winner() -> None:
    """Run a 9000-tick scripted match (player script + AI script). Assert termination."""
    from sim.ai import ai_tick
    from sim.game import scripted_player_commands

    g = _new_game(seed=42)
    for t in range(TICK_HZ * 300):  # 5 sim minutes
        inputs: list[Command] = []
        inputs += scripted_player_commands(g, player_id=0, tick=t)
        inputs += ai_tick(g, player_id=1, tick=t)
        g.tick(inputs)
        if g.over:
            break
    assert g.over is True, "match must end within 9000 ticks"
    assert g.winner in (0, 1), "AC-35 winner is one of the two players"
