"""High-level poll generator interface using the pluggable PollRegistry."""

from ncaa_dynasty_rerank.engine import RankingEngine
from ncaa_dynasty_rerank.models import PollRanking
from ncaa_dynasty_rerank.strategies.registry import PollRegistry


class PollGenerator:
    """Produces the CFP, AP Top 25, and Coaches Polls using registered strategies."""

    def __init__(self, engine: RankingEngine, registry: PollRegistry | None = None):
        self.engine = engine
        self.registry = registry or PollRegistry()

    def generate_all(self) -> tuple[list[PollRanking], list[PollRanking], list[PollRanking]]:
        """Generates (cfp_poll, ap_poll, coaches_poll)."""
        teams = self.engine.evaluate_resumes()

        cfp = self.registry.get("cfp").rank(teams, self.engine)
        ap = self.registry.get("ap").rank(teams, self.engine)
        coaches = self.registry.get("coaches").rank(teams, self.engine)

        return cfp, ap, coaches
