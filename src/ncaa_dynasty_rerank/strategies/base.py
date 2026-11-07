"""Base abstraction for pluggable poll ranking strategies."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ncaa_dynasty_rerank.models import PollRanking, TeamRecord

if TYPE_CHECKING:
    from ncaa_dynasty_rerank.engine import RankingEngine


class PollStrategy(ABC):
    """Abstract base class for a poll ranking model (e.g. CFP, AP, Coaches, BCS)."""

    name: str = ""
    poll_type: str = ""  # "cfp", "ap", "coaches", etc.

    @abstractmethod
    def rank(
        self,
        teams: list[TeamRecord],
        engine: "RankingEngine",
    ) -> list[PollRanking]:
        """Produces an ordered list of PollRanking objects for all eligible FBS teams."""
