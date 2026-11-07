"""College Football Playoff (CFP) committee ranking strategy."""

from typing import TYPE_CHECKING

from ncaa_dynasty_rerank.models import PollRanking, TeamRecord
from ncaa_dynasty_rerank.strategies.base import PollStrategy

if TYPE_CHECKING:
    from ncaa_dynasty_rerank.engine import RankingEngine


class CFPPollStrategy(PollStrategy):
    """CFP committee model: Pure resume, SOS, ranked wins, and head-to-head."""

    name = "College Football Playoff (CFP) Rankings"
    poll_type = "cfp"

    def rank(
        self,
        teams: list[TeamRecord],
        engine: "RankingEngine",
    ) -> list[PollRanking]:
        fbs_teams = [t for t in teams if t.conf_id not in (17, 24)]
        sorted_teams = sorted(fbs_teams, key=lambda t: t.resume_score, reverse=True)
        adjusted_teams = engine.apply_head_to_head_adjustments(sorted_teams)

        results: list[PollRanking] = []
        for idx, t in enumerate(adjusted_teams):
            rank = idx + 1
            results.append(
                PollRanking(
                    rank=rank,
                    team=t,
                    previous_rank=t.cfp_rank or t.cfp_prev_rank or rank,
                    score=t.resume_score,
                )
            )
        return results
