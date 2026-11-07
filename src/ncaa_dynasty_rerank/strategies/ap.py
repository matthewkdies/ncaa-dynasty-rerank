"""Associated Press (AP) Top 25 media poll strategy."""

import math
from typing import TYPE_CHECKING

from ncaa_dynasty_rerank.models import PollRanking, TeamRecord
from ncaa_dynasty_rerank.strategies.base import PollStrategy

if TYPE_CHECKING:
    from ncaa_dynasty_rerank.engine import RankingEngine


def generate_ap_points(rank: int, max_points: int = 1575, total_voters: int = 63) -> int:
    """Generates authentic AP poll points curve from 63 voters."""
    if rank > 25:
        return max(5, int(80 - (rank - 25) * 15)) if rank <= 30 else 0
    base = (26 - rank) * total_voters
    decay = 1.0 - math.pow((rank - 1) / 25.0, 1.4) * 0.18
    return min(max_points, max(50, int(base * decay)))


def distribute_ap_first_votes(ranked_teams: list[TeamRecord], total_votes: int = 63) -> dict[int, int]:
    """Distributes AP 1st-place votes realistically among top candidates."""
    votes: dict[int, int] = {}
    if not ranked_teams:
        return votes

    top = ranked_teams[:3]
    top_scores = [max(0.0, t.resume_score) for t in top]
    if top_scores[0] <= 0:
        votes[top[0].tgid] = total_votes
        return votes

    gap = (top_scores[0] - top_scores[1]) if len(top_scores) > 1 else 999.0
    if gap > 8.0:
        votes[top[0].tgid] = total_votes - 2
        if len(top) > 1:
            votes[top[1].tgid] = 2
    elif gap > 4.0:
        votes[top[0].tgid] = int(total_votes * 0.75)
        votes[top[1].tgid] = total_votes - votes[top[0].tgid]
    else:
        votes[top[0].tgid] = int(total_votes * 0.58)
        rem = total_votes - votes[top[0].tgid]
        if len(top) > 2 and (top_scores[0] - top_scores[2]) < 5.0:
            votes[top[1].tgid] = int(rem * 0.70)
            votes[top[2].tgid] = rem - votes[top[1].tgid]
        else:
            votes[top[1].tgid] = rem

    return votes


class APPollStrategy(PollStrategy):
    """AP Media model: Resume + recency + margin + Group of 5 respect."""

    name = "Associated Press (AP) Top 25 Poll"
    poll_type = "ap"

    def rank(
        self,
        teams: list[TeamRecord],
        engine: "RankingEngine",
    ) -> list[PollRanking]:
        fbs_teams = [t for t in teams if t.conf_id not in (17, 24)]

        candidates = []
        for t in fbs_teams:
            score = t.resume_score
            # Boost for undefeated non-Power teams (Cinderella respect)
            if t.losses == 0 and t.conf_id not in engine.config.power_conference_ids:
                score += 2.5
            # Small bonus for win volume
            score += t.wins * 0.4
            candidates.append((t, score))

        sorted_teams = [item[0] for item in sorted(candidates, key=lambda x: x[1], reverse=True)]
        adjusted_teams = engine.apply_head_to_head_adjustments(sorted_teams)
        first_votes = distribute_ap_first_votes(adjusted_teams, total_votes=63)

        results: list[PollRanking] = []
        for idx, t in enumerate(adjusted_teams):
            rank = idx + 1
            pts = generate_ap_points(rank, max_points=1575, total_voters=63)
            fp = first_votes.get(t.tgid, 0)
            results.append(
                PollRanking(
                    rank=rank,
                    team=t,
                    previous_rank=t.ap_rank or t.ap_prev_rank or rank,
                    points=pts,
                    first_place_votes=fp,
                    score=round(t.resume_score, 2),
                )
            )
        return results
