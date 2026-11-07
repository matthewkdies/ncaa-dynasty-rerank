"""Unit tests for postseason bowl synchronization."""

from ncaa_dynasty_rerank.models import PollRanking, TeamRecord
from ncaa_dynasty_rerank.postseason import PostseasonSyncer


def make_team(tgid: int, name: str, cfp_rank: int = 0) -> TeamRecord:
    return TeamRecord(
        record_index=tgid,
        tgid=tgid,
        name=name,
        mascot="Mascot",
        full_name=name,
        conf_id=1,
        div_id=0,
        wins=10,
        losses=0,
        conf_wins=8,
        conf_losses=0,
        cfp_rank=cfp_rank,
        cfp_prev_rank=cfp_rank,
        ap_rank=cfp_rank,
        ap_prev_rank=cfp_rank,
        ap_points=1000,
        ap_first_votes=0,
        coaches_rank=cfp_rank,
        coaches_prev_rank=cfp_rank,
        coaches_points=1000,
        coaches_first_votes=0,
        resume_score=100.0,
    )


def test_is_bowl_season():
    syncer = PostseasonSyncer()

    # Regular season games (SEWT < 30)
    regular_games = [
        {"sewn": 10, "sewt": 10, "sgnm": 1, "gsta": 1, "away_score": 0, "home_score": 0},
    ]
    assert not syncer.is_bowl_season(regular_games)

    # Completed bowl games (scores > 0)
    completed_bowl_games = [
        {"sewn": 17, "sewt": 30, "sgnm": 7, "gsta": 2, "away_score": 24, "home_score": 21},
    ]
    assert not syncer.is_bowl_season(completed_bowl_games)

    # Unplayed bowl games (SEWT >= 30, scores == 0, GSTA == 1)
    unplayed_bowl_games = [
        {"sewn": 17, "sewt": 30, "sgnm": 7, "gsta": 1, "away_score": 0, "home_score": 0},
        {"sewn": 21, "sewt": 40, "sgnm": 40, "gsta": 1, "away_score": 0, "home_score": 0},
    ]
    assert syncer.is_bowl_season(unplayed_bowl_games)


def test_sync_national_championship_swap():
    syncer = PostseasonSyncer()

    # Teams: 1=Florida, 2=Clemson, 3=Alabama, 4=Oregon
    florida = make_team(1, "Florida", cfp_rank=1)
    clemson = make_team(2, "Clemson", cfp_rank=2)
    alabama = make_team(3, "Alabama", cfp_rank=4)
    oregon = make_team(4, "Oregon", cfp_rank=10)

    teams_by_tgid = {t.tgid: t for t in [florida, clemson, alabama, oregon]}

    # Initial bowl schedule:
    # Rec 10: Natty (SGNM 40): Clemson (2) @ Florida (1)
    # Rec 8:  Sugar (SGNM 35): Alabama (3) @ Oregon (4)
    schd_records = [
        {
            "record_index": 8,
            "sgnm": 35,
            "sewn": 20,
            "sewt": 32,
            "gsta": 1,
            "gatg": 3,
            "ghtg": 4,
            "away_score": 0,
            "home_score": 0,
        },
        {
            "record_index": 10,
            "sgnm": 40,
            "sewn": 21,
            "sewt": 40,
            "gsta": 1,
            "gatg": 2,
            "ghtg": 1,
            "away_score": 0,
            "home_score": 0,
        },
    ]

    # Proposed CFP Poll: #1 Florida, #2 Alabama, #3 West Virginia, #4 Ohio State, #5 Clemson
    cfp_poll = [
        PollRanking(rank=1, team=florida, previous_rank=1, score=180.0),
        PollRanking(rank=2, team=alabama, previous_rank=4, score=170.0),
        PollRanking(rank=5, team=clemson, previous_rank=2, score=150.0),
    ]

    result = syncer.sync_major_bowls(schd_records, cfp_poll, teams_by_tgid)

    # Expected:
    # Alabama (3) takes Clemson's (2) spot in Natty (Rec 10, away)
    # Clemson (2) takes Alabama's (3) spot in Sugar (Rec 8, away)
    assert len(result.updates) == 2
    natty_update = next(u for u in result.updates if u["record_index"] == 10)
    sugar_update = next(u for u in result.updates if u["record_index"] == 8)

    assert natty_update["away_tgid"] == 3  # Alabama
    assert natty_update["home_tgid"] == 1  # Florida
    assert sugar_update["away_tgid"] == 2  # Clemson
    assert sugar_update["home_tgid"] == 4  # Oregon

    assert len(result.diffs) == 2
    assert any("CFP National Championship" in d.bowl_name for d in result.diffs)
    assert any("Sugar Bowl" in d.bowl_name for d in result.diffs)


def test_sync_national_championship_idempotent():
    syncer = PostseasonSyncer()

    florida = make_team(1, "Florida", cfp_rank=1)
    alabama = make_team(3, "Alabama", cfp_rank=2)
    teams_by_tgid = {t.tgid: t for t in [florida, alabama]}

    # Already aligned: Alabama @ Florida in SGNM 40
    schd_records = [
        {
            "record_index": 10,
            "sgnm": 40,
            "sewn": 21,
            "sewt": 40,
            "gsta": 1,
            "gatg": 3,
            "ghtg": 1,
            "away_score": 0,
            "home_score": 0,
        },
    ]

    cfp_poll = [
        PollRanking(rank=1, team=florida, previous_rank=1, score=180.0),
        PollRanking(rank=2, team=alabama, previous_rank=2, score=170.0),
    ]

    result = syncer.sync_major_bowls(schd_records, cfp_poll, teams_by_tgid)
    assert len(result.updates) == 0
    assert len(result.diffs) == 0
