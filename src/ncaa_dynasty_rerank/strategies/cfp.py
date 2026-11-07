"""College Football Playoff (CFP) committee ranking strategy."""

from typing import TYPE_CHECKING

from ncaa_dynasty_rerank.config_rules import CFPPollConfig
from ncaa_dynasty_rerank.models import PollRanking, TeamRecord
from ncaa_dynasty_rerank.strategies.base import PollStrategy

if TYPE_CHECKING:
    from ncaa_dynasty_rerank.engine import RankingEngine


class CFPPollStrategy(PollStrategy):
    """CFP committee model: Pure resume, SOS, ranked wins, and head-to-head."""

    name = "College Football Playoff (CFP) Rankings"
    poll_type = "cfp"

    def __init__(self, config: CFPPollConfig | None = None):
        self.config = config or CFPPollConfig()

    def rank(
        self,
        teams: list[TeamRecord],
        engine: "RankingEngine",
    ) -> list[PollRanking]:
        fbs_teams = [t for t in teams if t.conf_id not in engine.config.fcs_conference_ids]
        sorted_teams = sorted(fbs_teams, key=lambda t: t.resume_score, reverse=True)
        if self.config.enable_h2h_adjustments:
            adjusted_teams = engine.apply_head_to_head_adjustments(sorted_teams)
        else:
            adjusted_teams = sorted_teams

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
