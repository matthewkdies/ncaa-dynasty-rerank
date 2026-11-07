from ncaa_dynasty_rerank.engine import RankingEngine
from ncaa_dynasty_rerank.models import PollRanking, TeamRecord
from ncaa_dynasty_rerank.strategies.base import PollStrategy
from ncaa_dynasty_rerank.strategies.registry import PollRegistry
from tests.test_engine import make_team


class CustomSPPlusStrategy(PollStrategy):
    """Custom user-defined rating model for testing registry extensibility."""

    name = "Custom SP+ Rating"
    poll_type = "spplus"

    def rank(self, teams: list[TeamRecord], engine: RankingEngine) -> list[PollRanking]:
        # Simple custom sorting: score by win percentage then raw wins
        sorted_teams = sorted(teams, key=lambda t: (t.win_pct, t.wins), reverse=True)
        return [PollRanking(rank=i + 1, team=t, score=t.win_pct * 100.0) for i, t in enumerate(sorted_teams)]


def test_custom_poll_strategy_registration():
    registry = PollRegistry()
    assert len(registry.all()) == 3  # CFP, AP, Coaches

    # Register custom strategy
    custom_strategy = CustomSPPlusStrategy()
    registry.register(custom_strategy)

    assert len(registry.all()) == 4
    retrieved = registry.get("spplus")
    assert retrieved.name == "Custom SP+ Rating"

    t1 = make_team(1, "TopTeam", 11, 8, 0)
    t2 = make_team(2, "SecondTeam", 11, 7, 1)

    engine = RankingEngine([t1, t2], [])
    ranked = retrieved.rank([t1, t2], engine)

    assert ranked[0].team.tgid == 1
    assert ranked[0].rank == 1
    assert ranked[0].score == 100.0
    assert ranked[1].rank == 2
