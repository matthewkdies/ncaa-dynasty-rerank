"""USA Today Coaches Poll strategy."""

import math
from typing import TYPE_CHECKING

from ncaa_dynasty_rerank.config_rules import CoachesPollConfig
from ncaa_dynasty_rerank.models import PollRanking, TeamRecord
from ncaa_dynasty_rerank.strategies.base import PollStrategy

if TYPE_CHECKING:
    from ncaa_dynasty_rerank.engine import RankingEngine


def generate_coaches_points(
    rank: int,
    max_points: int = 1550,
    total_voters: int = 62,
    decay_power: float = 1.4,
    decay_factor: float = 0.18,
) -> int:
    """Generates authentic Coaches poll points curve from voters."""
    if rank > 25:
        return max(0, int(42 - (rank - 26) * 8)) if rank <= 30 else 0
    base = (26 - rank) * total_voters
    decay = 1.0 - math.pow((rank - 1) / 25.0, decay_power) * decay_factor
    return min(max_points, max(50, int(base * decay)))


def distribute_coaches_first_votes(
    ranked_teams: list[TeamRecord],
    total_votes: int = 62,
    threshold_large: float = 7.0,
    threshold_medium: float = 3.5,
    share_large: float = 0.72,
    share_medium: float = 0.55,
) -> dict[int, int]:
    """Distributes Coaches 1st-place votes realistically."""
    votes: dict[int, int] = {}
    if not ranked_teams:
        return votes

    top = ranked_teams[:3]
    top_scores = [max(0.0, t.resume_score) for t in top]
    if top_scores[0] <= 0:
        votes[top[0].tgid] = total_votes
        return votes

    gap = (top_scores[0] - top_scores[1]) if len(top_scores) > 1 else 999.0
    if gap > threshold_large:
        votes[top[0].tgid] = total_votes - 2
        if len(top) > 1:
            votes[top[1].tgid] = 2
    elif gap > threshold_medium:
        votes[top[0].tgid] = int(total_votes * share_large)
        votes[top[1].tgid] = total_votes - votes[top[0].tgid]
    else:
        votes[top[0].tgid] = int(total_votes * share_medium)
        rem = total_votes - votes[top[0].tgid]
        votes[top[1].tgid] = rem

    return votes


class CoachesPollStrategy(PollStrategy):
    """Coaches model: Strong poll inertia (prior rank anchor) + brand loyalty."""

    name = "USA Today Coaches Poll"
    poll_type = "coaches"

    def __init__(self, config: CoachesPollConfig | None = None):
        self.config = config or CoachesPollConfig()

    def rank(
        self,
        teams: list[TeamRecord],
        engine: "RankingEngine",
    ) -> list[PollRanking]:
        fbs_teams = [t for t in teams if t.conf_id not in engine.config.fcs_conference_ids]

        candidates = []
        for t in fbs_teams:
            score = t.resume_score * self.config.resume_weight
            # Prior rank anchor (poll inertia)
            prev_rk = t.coaches_rank or t.coaches_prev_rank
            if prev_rk and 1 <= prev_rk <= 25:
                anchor = (26 - prev_rk) * self.config.prior_rank_anchor_weight
                if t.losses > 0:
                    anchor *= self.config.loss_anchor_damping
                score += anchor
            elif t.wins >= self.config.hot_start_wins and t.losses <= self.config.hot_start_losses:
                score += self.config.hot_start_bonus

            # Blueblood pedigree bonus
            if t.tgid in engine.config.blueblood_tgids:
                score += self.config.blueblood_bonus

            candidates.append((t, score))

        sorted_teams = [item[0] for item in sorted(candidates, key=lambda x: x[1], reverse=True)]
        if self.config.enable_h2h_adjustments:
            adjusted_teams = engine.apply_head_to_head_adjustments(sorted_teams)
        else:
            adjusted_teams = sorted_teams

        first_votes = distribute_coaches_first_votes(
            adjusted_teams,
            total_votes=self.config.total_voters,
            threshold_large=self.config.first_place_threshold_large,
            threshold_medium=self.config.first_place_threshold_medium,
            share_large=self.config.first_place_share_large,
            share_medium=self.config.first_place_share_medium,
        )

        results: list[PollRanking] = []
        for idx, t in enumerate(adjusted_teams):
            rank = idx + 1
            pts = generate_coaches_points(
                rank,
                max_points=self.config.max_points,
                total_voters=self.config.total_voters,
                decay_power=self.config.points_decay_power,
                decay_factor=self.config.points_decay_factor,
            )
            fp = first_votes.get(t.tgid, 0)
            results.append(
                PollRanking(
                    rank=rank,
                    team=t,
                    previous_rank=t.coaches_rank or t.coaches_prev_rank or rank,
                    points=pts,
                    first_place_votes=fp,
                    score=round(t.resume_score, 2),
                )
            )
        return results
