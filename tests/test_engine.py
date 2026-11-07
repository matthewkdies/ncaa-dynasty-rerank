from ncaa_dynasty_rerank.config_rules import EngineConfig
from ncaa_dynasty_rerank.engine import RankingEngine
from ncaa_dynasty_rerank.models import GameRecord, TeamRecord


def make_team(
    tgid: int,
    name: str,
    conf_id: int,
    wins: int,
    losses: int,
    prev_rank: int = 0,
) -> TeamRecord:
    return TeamRecord(
        record_index=tgid,
        tgid=tgid,
        name=name,
        mascot="Mascot",
        full_name=f"{name} Mascot",
        conf_id=conf_id,
        div_id=0,
        wins=wins,
        losses=losses,
        coaches_rank=prev_rank,
        coaches_prev_rank=prev_rank,
        ap_rank=prev_rank,
        ap_prev_rank=prev_rank,
        cfp_rank=prev_rank,
        cfp_prev_rank=prev_rank,
    )


def test_engine_idempotence():
    """Verify evaluating resumes multiple times does not mutate/duplicate opponent lists."""
    t1 = make_team(1, "Alpha", 11, 2, 0)
    t2 = make_team(2, "Beta", 11, 0, 2)
    games = [
        GameRecord(
            record_index=1,
            week=1,
            away_tgid=2,
            home_tgid=1,
            away_score=10,
            home_score=35,
            winner_tgid=1,
            loser_tgid=2,
            margin=25,
        ),
        GameRecord(
            record_index=2,
            week=2,
            away_tgid=2,
            home_tgid=1,
            away_score=7,
            home_score=28,
            winner_tgid=1,
            loser_tgid=2,
            margin=21,
        ),
    ]

    engine = RankingEngine([t1, t2], games)
    engine.evaluate_resumes()
    initial_opponents_len = len(t1.opponents)
    initial_score = t1.resume_score

    # Re-evaluate
    engine.evaluate_resumes()
    assert len(t1.opponents) == initial_opponents_len
    assert t1.resume_score == initial_score


def test_engine_preseason_zero_games():
    """Verify engine handles teams with 0 games played safely without ZeroDivisionError."""
    t1 = make_team(1, "PreseasonA", 11, 0, 0)
    t2 = make_team(2, "PreseasonB", 1, 0, 0)

    engine = RankingEngine([t1, t2], [])
    resumes = engine.evaluate_resumes()
    assert len(resumes) == 2
    assert resumes[0].resume_score > 0


def test_engine_late_bye_week_invariance():
    """Verify a 7-0 team is not heavily penalized compared to an 8-0 team with identical opponent quality."""
    team_7_0 = make_team(1, "Team70", 11, 7, 0)
    team_8_0 = make_team(2, "Team80", 11, 8, 0)
    opp = make_team(100, "Opponent", 11, 4, 4)

    games = []
    # 7 games for Team 1
    for w in range(1, 8):
        games.append(
            GameRecord(
                record_index=w,
                week=w,
                away_tgid=100,
                home_tgid=1,
                away_score=14,
                home_score=28,
                winner_tgid=1,
                loser_tgid=100,
                margin=14,
            )
        )
    # 8 games for Team 2 (same margin against same opponent strength)
    for w in range(1, 9):
        games.append(
            GameRecord(
                record_index=10 + w,
                week=w,
                away_tgid=100,
                home_tgid=2,
                away_score=14,
                home_score=28,
                winner_tgid=2,
                loser_tgid=100,
                margin=14,
            )
        )

    engine = RankingEngine([team_7_0, team_8_0, opp], games)
    engine.evaluate_resumes()

    # Scores should be extremely close (difference < 1.5 points) despite the missing 8th game
    score_diff = abs(team_8_0.resume_score - team_7_0.resume_score)
    assert score_diff < 1.5, f"Expected bye-week neutrality, got difference {score_diff}"


def test_engine_leapfrog_elite_1loss_over_weak_undefeated():
    """Verify an elite 7-1 Power team with top wins can leapfrog an 8-0 weak G5 team with sub-.300 schedule."""
    elite_p5 = make_team(1, "Alabama", 11, 7, 1)  # SEC
    weak_g5 = make_team(2, "WeakG5", 13, 8, 0)  # Sun Belt

    top_opp = make_team(10, "Georgia", 11, 7, 1)
    fcs_opp = make_team(20, "FCS_East", 17, 1, 7)

    games = [
        # Alabama beat Georgia by 10, lost close road game to Georgia
        GameRecord(
            record_index=1,
            week=1,
            away_tgid=10,
            home_tgid=1,
            away_score=24,
            home_score=34,
            winner_tgid=1,
            loser_tgid=10,
            margin=10,
        ),
        GameRecord(
            record_index=2,
            week=2,
            away_tgid=1,
            home_tgid=10,
            away_score=28,
            home_score=31,
            winner_tgid=10,
            loser_tgid=1,
            margin=3,
        ),
    ]
    # Alabama won 6 other games against 5-3 teams
    mid_opps = []
    for w in range(3, 9):
        mid = make_team(30 + w, f"Mid_{w}", 11, 5, 3)
        mid_opps.append(mid)
        games.append(
            GameRecord(
                record_index=w,
                week=w,
                away_tgid=30 + w,
                home_tgid=1,
                away_score=14,
                home_score=35,
                winner_tgid=1,
                loser_tgid=30 + w,
                margin=21,
            )
        )

    # Weak G5 played 8 FCS/sub-.250 teams
    for w in range(1, 9):
        games.append(
            GameRecord(
                record_index=100 + w,
                week=w,
                away_tgid=20,
                home_tgid=2,
                away_score=7,
                home_score=17,
                winner_tgid=2,
                loser_tgid=20,
                margin=10,
            )
        )

    all_teams = [elite_p5, weak_g5, top_opp, fcs_opp] + mid_opps
    engine = RankingEngine(all_teams, games)
    engine.evaluate_resumes()

    # The 7-1 Power team with a top-10 win must leapfrog the 8-0 team playing an FCS schedule
    assert elite_p5.resume_score > weak_g5.resume_score


def test_margin_of_victory_cap():
    """Verify blowout games capped at margin_cap (e.g. 50 margin = 24 margin credit)."""
    cfg = EngineConfig(margin_cap=24)
    t = make_team(1, "BlowoutTeam", 11, 1, 0)
    opp = make_team(2, "Opp", 11, 0, 1)

    g_24 = GameRecord(
        record_index=1,
        week=1,
        away_tgid=2,
        home_tgid=1,
        away_score=0,
        home_score=24,
        winner_tgid=1,
        loser_tgid=2,
        margin=24,
    )
    g_60 = GameRecord(
        record_index=2,
        week=2,
        away_tgid=2,
        home_tgid=1,
        away_score=0,
        home_score=60,
        winner_tgid=1,
        loser_tgid=2,
        margin=60,
    )

    engine = RankingEngine([t, opp], [g_24, g_60], config=cfg)
    sos = {2: 0.50}
    confs = {11: 1.15}

    val_24 = engine.calculate_game_value(1, g_24, sos, confs)
    val_60 = engine.calculate_game_value(1, g_60, sos, confs)

    assert val_24 == val_60, f"Expected margin cap to equalize value, got {val_24} vs {val_60}"


def test_head_to_head_cycle_safety():
    """Verify 3-way H2H cycle (A beats B, B beats C, C beats A) terminates deterministically."""
    a = make_team(1, "TeamA", 11, 6, 1)
    b = make_team(2, "TeamB", 11, 6, 1)
    c = make_team(3, "TeamC", 11, 6, 1)

    a.resume_score = 100.0
    b.resume_score = 99.0
    c.resume_score = 98.0

    games = [
        GameRecord(
            record_index=1,
            week=1,
            away_tgid=2,
            home_tgid=1,
            away_score=14,
            home_score=21,
            winner_tgid=1,
            loser_tgid=2,
            margin=7,
        ),  # A beat B
        GameRecord(
            record_index=2,
            week=2,
            away_tgid=3,
            home_tgid=2,
            away_score=14,
            home_score=21,
            winner_tgid=2,
            loser_tgid=3,
            margin=7,
        ),  # B beat C
        GameRecord(
            record_index=3,
            week=3,
            away_tgid=1,
            home_tgid=3,
            away_score=14,
            home_score=21,
            winner_tgid=3,
            loser_tgid=1,
            margin=7,
        ),  # C beat A
    ]

    engine = RankingEngine([a, b, c], games)
    # Must terminate without infinite loop and return all 3 teams
    adjusted = engine.apply_head_to_head_adjustments([a, b, c])
    assert len(adjusted) == 3
    assert {t.tgid for t in adjusted} == {1, 2, 3}
