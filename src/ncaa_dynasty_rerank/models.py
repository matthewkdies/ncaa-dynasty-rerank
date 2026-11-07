"""Data models for teams, games, and poll rankings using Pydantic."""

from pydantic import BaseModel, Field


class GameRecord(BaseModel):
    """Represents a completed football game."""

    record_index: int
    week: int
    status: int = 2
    away_tgid: int
    home_tgid: int
    away_score: int
    home_score: int
    winner_tgid: int
    loser_tgid: int
    margin: int

    @property
    def is_home_win(self) -> bool:
        return self.winner_tgid == self.home_tgid


class TeamRecord(BaseModel):
    """Represents an NCAA team and its dynasty save state."""

    record_index: int
    tgid: int
    name: str
    mascot: str
    full_name: str
    conf_id: int
    div_id: int
    wins: int
    losses: int
    conf_wins: int = 0
    conf_losses: int = 0

    # Current Poll Rankings in save
    cfp_rank: int = 0
    cfp_prev_rank: int = 0
    ap_rank: int = 0
    ap_points: int = 0
    ap_first_votes: int = 0
    ap_prev_rank: int = 0
    coaches_rank: int = 0
    coaches_points: int = 0
    coaches_first_votes: int = 0
    coaches_prev_rank: int = 0

    # Calculated metrics
    resume_score: float = 0.0
    sos_score: float = 0.0
    quality_wins: int = 0
    opponents: list[int] = Field(default_factory=list)
    wins_against: list[int] = Field(default_factory=list)
    losses_to: list[int] = Field(default_factory=list)

    @property
    def games_played(self) -> int:
        return self.wins + self.losses

    @property
    def win_pct(self) -> float:
        if self.games_played == 0:
            return 0.0
        return self.wins / self.games_played

    @property
    def record_str(self) -> str:
        return f"{self.wins}-{self.losses}"


class PollRanking(BaseModel):
    """Ranked team result for a specific poll."""

    rank: int
    team: TeamRecord
    previous_rank: int = 0
    points: int = 0
    first_place_votes: int = 0
    score: float = 0.0
