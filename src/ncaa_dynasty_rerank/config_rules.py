"""Configurable rules and weight parameters for the ranking engine."""

from pydantic import BaseModel, Field


class EngineConfig(BaseModel):
    """Encapsulates all weights, caps, and parameters used in ranking calculations."""

    # Base conference prestige multipliers
    conference_weights: dict[int, float] = Field(
        default_factory=lambda: {
            11: 1.15,  # SEC
            1: 1.15,  # Big Ten
            0: 1.05,  # ACC
            2: 1.05,  # Big 12
            10: 1.05,  # Pac-12
            5: 1.00,  # Independents (Notre Dame, BYU, Army)
            3: 0.92,  # American (AAC)
            9: 0.92,  # Mountain West (MWC)
            13: 0.88,  # Sun Belt
            7: 0.88,  # MAC
            4: 0.88,  # C-USA
            17: 0.50,  # FCS East / West
            24: 0.40,  # Generic / High School
        }
    )
    default_conf_weight: float = 0.85

    # Margin of victory scaling
    margin_cap: int = 24
    margin_power: float = 0.65
    margin_multiplier: float = 0.90

    # Game valuation constants
    win_base: float = 12.0
    loss_base: float = -14.0
    road_win_bonus: float = 2.0
    home_loss_penalty: float = 2.5
    h2h_loss_threshold: float = 4.0

    # Bye-week neutral blend: proportion between average performance and cumulative total
    avg_performance_weight: float = 0.75
    total_performance_weight: float = 0.25

    # Power conference IDs
    power_conference_ids: set[int] = Field(default_factory=lambda: {0, 1, 2, 10, 11})

    # Traditional blueblood programs receiving pedigree consideration in Coaches poll
    blueblood_tgids: set[int] = Field(
        default_factory=lambda: {
            3,  # Alabama
            70,  # Ohio State
            27,  # Florida
            51,  # Michigan
            71,  # Oklahoma
            72,  # Oklahoma State / Texas
            97,  # Texas
            68,  # Notre Dame
            45,  # LSU
            30,  # Georgia
            21,  # Clemson
            84,  # USC
        }
    )
