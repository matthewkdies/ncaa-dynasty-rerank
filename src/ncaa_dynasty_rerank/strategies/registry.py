"""Registry for discovering and managing poll ranking strategies."""

from ncaa_dynasty_rerank.strategies.ap import APPollStrategy
from ncaa_dynasty_rerank.strategies.base import PollStrategy
from ncaa_dynasty_rerank.strategies.cfp import CFPPollStrategy
from ncaa_dynasty_rerank.strategies.coaches import CoachesPollStrategy


class PollRegistry:
    """Manages available poll strategies, allowing custom models to be registered."""

    def __init__(self):
        self._strategies: dict[str, PollStrategy] = {}
        self.register_default_strategies()

    def register_default_strategies(self) -> None:
        self.register(CFPPollStrategy())
        self.register(APPollStrategy())
        self.register(CoachesPollStrategy())

    def register(self, strategy: PollStrategy) -> None:
        self._strategies[strategy.poll_type] = strategy

    def get(self, poll_type: str) -> PollStrategy:
        if poll_type not in self._strategies:
            raise KeyError(f"Poll strategy '{poll_type}' not found in registry.")
        return self._strategies[poll_type]

    def all(self) -> list[PollStrategy]:
        return list(self._strategies.values())
