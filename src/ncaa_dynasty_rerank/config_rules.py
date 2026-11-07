"""Configurable rules and weight parameters for the ranking engine and polls."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


def deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Recursively merges dictionary `overrides` into `base` without mutating either."""
    result = dict(base)
    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class EngineConfig(BaseModel):
    """Encapsulates all weights, caps, and parameters used in resume calculations."""

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

    # Conference dynamic modifier blending
    conf_base_weight: float = 0.70
    conf_non_con_weight: float = 0.30
    conf_non_con_baseline: float = 0.75
    conf_non_con_multiplier: float = 0.50

    # Margin of victory scaling
    margin_cap: int = 24
    margin_power: float = 0.65
    margin_multiplier: float = 0.90
    margin_penalty_multiplier: float = 0.70

    # Game valuation constants
    win_base: float = 12.0
    loss_base: float = -14.0
    road_win_bonus: float = 2.0
    home_loss_penalty: float = 2.5
    win_opp_win_pct_factor: float = 14.0
    win_opp_sos_factor: float = 10.0
    fcs_or_bad_team_win_pct_threshold: float = 0.35
    fcs_or_bad_team_quality_cap: float = 4.0
    loss_opp_win_pct_factor: float = 8.0
    loss_opp_sos_factor: float = 6.0

    # Strength of schedule (SOS)
    sos_default_opp_win_pct: float = 0.30
    sos_default_owp: float = 0.50
    sos_owp_weight: float = 2.0
    sos_oowp_weight: float = 1.0

    # Resume score weights
    unplayed_base: float = 50.0
    unplayed_win_bonus: float = 10.0
    unplayed_loss_penalty: float = 15.0
    quality_win_min_win_pct: float = 0.50
    loss_penalty_multiplier: float = 8.5
    win_pct_base: float = 35.0
    win_pct_multiplier: float = 30.0
    performance_multiplier: float = 2.2
    sos_multiplier: float = 32.0
    quality_win_rate_multiplier: float = 22.0

    # Bye-week neutral blend (proportions)
    avg_performance_weight: float = 0.75
    total_performance_weight: float = 0.25

    # Head-to-head adjustments
    h2h_loss_threshold: float = 4.0
    h2h_max_iterations: int = 3

    # Power conference IDs
    power_conference_ids: set[int] = Field(default_factory=lambda: {0, 1, 2, 10, 11})

    # FCS / generic conference IDs
    fcs_conference_ids: set[int] = Field(default_factory=lambda: {17, 24})

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


class APPollConfig(BaseModel):
    """Configuration parameters for the Associated Press (AP) Top 25 Poll."""

    total_voters: int = 63
    max_points: int = 1575
    undefeated_non_power_boost: float = 2.5
    win_bonus: float = 0.4
    points_decay_power: float = 1.4
    points_decay_factor: float = 0.18
    enable_h2h_adjustments: bool = True

    # 1st place vote distribution thresholds
    first_place_threshold_large: float = 8.0
    first_place_threshold_medium: float = 4.0
    first_place_share_large: float = 0.75
    first_place_share_medium: float = 0.58
    first_place_share_close_third: float = 0.70
    first_place_close_third_threshold: float = 5.0


class CoachesPollConfig(BaseModel):
    """Configuration parameters for the USA Today Coaches Poll."""

    total_voters: int = 62
    max_points: int = 1550
    resume_weight: float = 0.70
    prior_rank_anchor_weight: float = 0.55
    loss_anchor_damping: float = 0.65
    hot_start_wins: int = 6
    hot_start_losses: int = 1
    hot_start_bonus: float = 4.0
    blueblood_bonus: float = 2.0
    points_decay_power: float = 1.4
    points_decay_factor: float = 0.18
    enable_h2h_adjustments: bool = True

    # 1st place vote distribution thresholds
    first_place_threshold_large: float = 7.0
    first_place_threshold_medium: float = 3.5
    first_place_share_large: float = 0.72
    first_place_share_medium: float = 0.55


class CFPPollConfig(BaseModel):
    """Configuration parameters for the College Football Playoff (CFP) committee rankings."""

    enable_h2h_adjustments: bool = True


class RankingConfig(BaseModel):
    """Root configuration holding all resume and poll ranking parameters."""

    resume: EngineConfig = Field(default_factory=EngineConfig)
    ap: APPollConfig = Field(default_factory=APPollConfig)
    coaches: CoachesPollConfig = Field(default_factory=CoachesPollConfig)
    cfp: CFPPollConfig = Field(default_factory=CFPPollConfig)


def load_ranking_config(path: Path | str | None = None) -> RankingConfig:
    """Loads a RankingConfig from file, merging user overrides on top of defaults."""
    default_model = RankingConfig()
    default_dict = json.loads(default_model.model_dump_json())

    if path is None:
        return default_model

    file_path = Path(path).expanduser().resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"Ranking rules file not found at: {file_path}")

    try:
        with open(file_path, encoding="utf-8") as f:
            raw_overrides = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in ranking rules file {file_path}: {e}") from e
    except OSError as e:
        raise OSError(f"Could not read ranking rules file {file_path}: {e}") from e

    if not isinstance(raw_overrides, dict):
        raise ValueError(f"Expected JSON object in ranking rules file, got {type(raw_overrides).__name__}")

    # Check if this is a flat legacy resume config (keys like 'margin_cap' at top-level)
    top_keys = set(raw_overrides.keys())
    sub_sections = {"resume", "ap", "coaches", "cfp"}
    if not top_keys.intersection(sub_sections):
        # All keys belong to resume directly
        normalized_overrides = {"resume": raw_overrides}
    else:
        normalized_overrides = raw_overrides

    merged = deep_merge(default_dict, normalized_overrides)
    return RankingConfig.model_validate(merged)


def export_default_ranking_config(dest: Path | str) -> Path:
    """Exports full default configuration to the specified JSON destination."""
    dest_path = Path(dest).expanduser().resolve()
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    default_config = RankingConfig()
    data = json.loads(default_config.model_dump_json())
    with open(dest_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return dest_path
