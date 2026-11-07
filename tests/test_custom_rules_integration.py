from ncaa_dynasty_rerank.config_rules import (
    APPollConfig,
    CFPPollConfig,
    CoachesPollConfig,
    RankingConfig,
)
from ncaa_dynasty_rerank.engine import RankingEngine
from ncaa_dynasty_rerank.models import GameRecord
from ncaa_dynasty_rerank.polls import PollGenerator
from ncaa_dynasty_rerank.strategies.ap import APPollStrategy
from ncaa_dynasty_rerank.strategies.cfp import CFPPollStrategy
from ncaa_dynasty_rerank.strategies.coaches import CoachesPollStrategy
from ncaa_dynasty_rerank.strategies.registry import PollRegistry
from tests.test_engine import make_team


def test_ap_poll_custom_config():
    # Team 1: G5 undefeated 8-0 (conf 9 MWC)
    # Team 2: P5 7-1 (conf 11 SEC)
    t1 = make_team(1, "BoiseState", conf_id=9, wins=8, losses=0)
    t1.resume_score = 80.0
    t2 = make_team(2, "Georgia", conf_id=11, wins=7, losses=1)
    t2.resume_score = 85.0

    engine = RankingEngine([t1, t2], [])

    # Default AP: Boise has score 80.0 + 2.5 + 8*0.4 = 85.7. Georgia has 85.0 + 7*0.4 = 87.8 -> Georgia #1
    default_strat = APPollStrategy()
    ranked_default = default_strat.rank([t1, t2], engine)
    assert ranked_default[0].team.tgid == 2

    # Custom AP: Massive Cinderella boost
    custom_strat = APPollStrategy(config=APPollConfig(undefeated_non_power_boost=15.0))
    ranked_custom = custom_strat.rank([t1, t2], engine)
    # Boise gets +15 boost -> Boise #1
    assert ranked_custom[0].team.tgid == 1


def test_coaches_poll_custom_blueblood_and_inertia():
    # Team 1: Non-blueblood 8-0
    t1 = make_team(100, "WakeForest", conf_id=0, wins=8, losses=0, prev_rank=10)
    t1.resume_score = 90.0

    # Team 2: Blueblood 6-2 (e.g. Alabama tgid 3), prev_rank 1
    t2 = make_team(3, "Alabama", conf_id=11, wins=6, losses=2, prev_rank=1)
    t2.resume_score = 80.0

    engine = RankingEngine([t1, t2], [])

    # Default Coaches poll: Wake Forest wins on resume
    default_strat = CoachesPollStrategy()
    ranked_default = default_strat.rank([t1, t2], engine)
    assert ranked_default[0].team.tgid == 100

    # Custom Coaches poll: Extreme blueblood bonus
    custom_strat = CoachesPollStrategy(config=CoachesPollConfig(blueblood_bonus=25.0))
    ranked_custom = custom_strat.rank([t1, t2], engine)
    assert ranked_custom[0].team.tgid == 3


def test_poll_h2h_toggle():
    t1 = make_team(1, "Winner", conf_id=11, wins=7, losses=1)
    t1.resume_score = 84.0
    t2 = make_team(2, "Loser", conf_id=11, wins=7, losses=1)
    t2.resume_score = 85.0

    # T1 beat T2 head-to-head
    g = GameRecord(
        record_index=1,
        week=1,
        away_tgid=2,
        home_tgid=1,
        away_score=10,
        home_score=17,
        winner_tgid=1,
        loser_tgid=2,
        margin=7,
    )
    engine = RankingEngine([t1, t2], [g])

    # With H2H enabled (default), T1 flips ahead of T2
    cfp_default = CFPPollStrategy()
    ranked_default = cfp_default.rank([t1, t2], engine)
    assert ranked_default[0].team.tgid == 1

    # With H2H disabled in config, pure resume order holds (T2 has 85.0 > 84.0)
    cfp_disabled = CFPPollStrategy(config=CFPPollConfig(enable_h2h_adjustments=False))
    ranked_disabled = cfp_disabled.rank([t1, t2], engine)
    assert ranked_disabled[0].team.tgid == 2


def test_poll_generator_with_ranking_config():
    # Boise State: 8-0 G5
    t1 = make_team(1, "BoiseState", conf_id=9, wins=8, losses=0)
    # Georgia: 9-0 P5 (higher resume when evaluated without games: 140 vs 130)
    t2 = make_team(2, "Georgia", conf_id=11, wins=9, losses=0)

    ranking_cfg = RankingConfig()
    ranking_cfg.ap.undefeated_non_power_boost = 15.0

    engine = RankingEngine([t1, t2], [], config=ranking_cfg)
    registry = PollRegistry(config=ranking_cfg)
    generator = PollGenerator(engine, registry=registry)

    cfp, ap, coaches = generator.generate_all()

    # In AP, Boise State gets +15 Cinderella boost: 130 + 15 + 8*0.4 = 148.2 vs Georgia 140 + 9*0.4 = 143.6
    assert ap[0].team.tgid == 1
    # In CFP, pure resume Georgia is #1: 140 > 130
    assert cfp[0].team.tgid == 2
