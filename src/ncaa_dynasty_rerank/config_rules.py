"""Configurable rules and weight parameters for the ranking engine and polls."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from ncaa_dynasty_rerank.aliases import resolve_conference_id, resolve_team_id


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
        },
        description="Base conference strength multipliers. Accepts conference names/aliases (e.g. 'sec', 'big10').",
    )
    default_conf_weight: float = Field(
        default=0.85,
        description="Fallback conference multiplier for unknown or unmapped conferences.",
    )

    # Conference dynamic modifier blending
    conf_base_weight: float = Field(
        default=0.70,
        description="Proportion of final conference modifier derived from static base prestige.",
    )
    conf_non_con_weight: float = Field(
        default=0.30,
        description="Proportion of final conference modifier derived from in-season non-conference win rate.",
    )
    conf_non_con_baseline: float = Field(
        default=0.75,
        description="Baseline adjustment constant applied to non-conference performance calculation.",
    )
    conf_non_con_multiplier: float = Field(
        default=0.50,
        description="Scaling factor applied to a conference's non-conference winning percentage.",
    )

    # Margin of victory scaling
    margin_cap: int = Field(
        default=24,
        description="Maximum point differential counted towards game quality to prevent running up the score.",
    )
    margin_power: float = Field(
        default=0.65,
        description="Exponent applied to effective margin of victory to model diminishing returns.",
    )
    margin_multiplier: float = Field(
        default=0.90,
        description="Multiplier applied to diminishing-returns margin factor for victories.",
    )
    margin_penalty_multiplier: float = Field(
        default=0.70,
        description="Multiplier applied to blowout margin penalty when losing a game.",
    )

    # Game valuation constants
    win_base: float = Field(
        default=12.0,
        description="Flat base resume points awarded for any victory.",
    )
    loss_base: float = Field(
        default=-14.0,
        description="Flat base resume penalty deducted for any loss.",
    )
    road_win_bonus: float = Field(
        default=2.0,
        description="Bonus resume points awarded for winning an away game.",
    )
    home_loss_penalty: float = Field(
        default=2.5,
        description="Additional penalty deducted for losing a game at home.",
    )
    win_opp_win_pct_factor: float = Field(
        default=14.0,
        description="Scaling weight for opponent winning percentage when evaluating a victory.",
    )
    win_opp_sos_factor: float = Field(
        default=10.0,
        description="Scaling weight for opponent SOS when evaluating a victory.",
    )
    fcs_or_bad_team_win_pct_threshold: float = Field(
        default=0.35,
        description="Opponent winning percentage threshold below which quality win points are capped.",
    )
    fcs_or_bad_team_quality_cap: float = Field(
        default=4.0,
        description="Maximum quality points awarded for beating FCS or sub-threshold opponents.",
    )
    loss_opp_win_pct_factor: float = Field(
        default=8.0,
        description="Loss mitigation credit awarded based on opponent winning percentage.",
    )
    loss_opp_sos_factor: float = Field(
        default=6.0,
        description="Loss mitigation credit awarded based on opponent strength of schedule.",
    )

    # Strength of schedule (SOS)
    sos_default_opp_win_pct: float = Field(
        default=0.30,
        description="Fallback opponent win percentage used when an opponent has played zero games.",
    )
    sos_default_owp: float = Field(
        default=0.50,
        description="Fallback Opponents' Win Percentage (OWP) used when a team has no opponents.",
    )
    sos_owp_weight: float = Field(
        default=2.0,
        description="Relative weight of Opponents' Win Percentage in the composite SOS calculation.",
    )
    sos_oowp_weight: float = Field(
        default=1.0,
        description="Relative weight of Opponents' Opponents' Win Percentage (OOWP) in composite SOS.",
    )

    # Resume score weights
    unplayed_base: float = Field(
        default=50.0,
        description="Baseline resume score awarded to teams before any games have been played.",
    )
    unplayed_win_bonus: float = Field(
        default=10.0,
        description="Score multiplier per recorded win when evaluating unplayed game schedules.",
    )
    unplayed_loss_penalty: float = Field(
        default=15.0,
        description="Score multiplier per recorded loss when evaluating unplayed game schedules.",
    )
    quality_win_min_win_pct: float = Field(
        default=0.50,
        description="Minimum opponent winning percentage to qualify as a quality win.",
    )
    loss_penalty_multiplier: float = Field(
        default=8.5,
        description="Resume score penalty multiplier per loss in final resume calculation.",
    )
    win_pct_base: float = Field(
        default=35.0,
        description="Base constant in the winning percentage component of resume score.",
    )
    win_pct_multiplier: float = Field(
        default=30.0,
        description="Multiplier for team winning percentage in final resume score.",
    )
    performance_multiplier: float = Field(
        default=2.2,
        description="Multiplier for average game performance quality in final resume score.",
    )
    sos_multiplier: float = Field(
        default=32.0,
        description="Multiplier for composite Strength of Schedule in final resume score.",
    )
    quality_win_rate_multiplier: float = Field(
        default=22.0,
        description="Multiplier for quality wins per game in final resume score.",
    )

    # Bye-week neutral blend (proportions)
    avg_performance_weight: float = Field(
        default=0.75,
        description="Proportion of performance quality anchored to per-game average.",
    )
    total_performance_weight: float = Field(
        default=0.25,
        description="Proportion of performance quality anchored to cumulative totals.",
    )

    # Head-to-head adjustments
    h2h_loss_threshold: float = Field(
        default=4.0,
        description="Maximum resume score deficit across which a head-to-head winner leapfrogs a 1-loss worse opponent.",
    )
    h2h_max_iterations: int = Field(
        default=3,
        description="Maximum bubble-sort iterations for resolving head-to-head adjustments.",
    )

    # Power conference IDs
    power_conference_ids: set[int] = Field(
        default_factory=lambda: {0, 1, 2, 10, 11},
        description="Power conferences (ACC, Big Ten, Big 12, Pac-12, SEC). Accepts aliases (e.g. 'sec', 'big10').",
    )

    # FCS / generic conference IDs
    fcs_conference_ids: set[int] = Field(
        default_factory=lambda: {17, 24},
        description="Conferences excluded from FBS rankings. Accepts aliases (e.g. 'fcs', 'generic').",
    )

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
        },
        description="Programs receiving brand loyalty consideration in Coaches poll. Accepts aliases (e.g. 'bama', 'osu').",
    )

    @field_validator("conference_weights", mode="before")
    @classmethod
    def _validate_conf_weights(cls, v: Any) -> dict[int, float]:
        if not isinstance(v, dict):
            return v
        resolved: dict[int, float] = {}
        for key, weight in v.items():
            cid = resolve_conference_id(key)
            resolved[cid] = float(weight)
        return resolved

    @field_validator("power_conference_ids", "fcs_conference_ids", mode="before")
    @classmethod
    def _validate_conf_ids(cls, v: Any) -> set[int]:
        if isinstance(v, (list, set, tuple)):
            return {resolve_conference_id(item) for item in v}
        return v

    @field_validator("blueblood_tgids", mode="before")
    @classmethod
    def _validate_team_ids(cls, v: Any) -> set[int]:
        if isinstance(v, (list, set, tuple)):
            return {resolve_team_id(item) for item in v}
        return v


class APPollConfig(BaseModel):
    """Configuration parameters for the Associated Press (AP) Top 25 Poll."""

    total_voters: int = Field(
        default=63,
        description="Total number of media voters in the AP poll panel.",
    )
    max_points: int = Field(
        default=1575,
        description="Maximum possible points in the AP poll curve (voters * 25).",
    )
    undefeated_non_power_boost: float = Field(
        default=2.5,
        description="Resume boost awarded to undefeated Group of 5 teams (Cinderella respect).",
    )
    win_bonus: float = Field(
        default=0.4,
        description="Small score bonus per win representing media preference for raw win volume.",
    )
    points_decay_power: float = Field(
        default=1.4,
        description="Exponential curve factor shaping the non-linear decay of voter points.",
    )
    points_decay_factor: float = Field(
        default=0.18,
        description="Magnitude scaling coefficient for the voter point curve decay.",
    )
    enable_h2h_adjustments: bool = Field(
        default=True,
        description="Whether to apply head-to-head adjustments to the AP rankings.",
    )

    # 1st place vote distribution thresholds
    first_place_threshold_large: float = Field(
        default=8.0,
        description="Resume gap threshold where the #1 team claims almost all 1st-place votes.",
    )
    first_place_threshold_medium: float = Field(
        default=4.0,
        description="Resume gap threshold for a moderate split of 1st-place votes.",
    )
    first_place_share_large: float = Field(
        default=0.75,
        description="Proportion of 1st-place votes awarded when gap exceeds large threshold.",
    )
    first_place_share_medium: float = Field(
        default=0.58,
        description="Proportion of 1st-place votes awarded when gap is within medium threshold.",
    )
    first_place_share_close_third: float = Field(
        default=0.70,
        description="Proportion of remaining 1st-place votes given to #2 when #3 is close.",
    )
    first_place_close_third_threshold: float = Field(
        default=5.0,
        description="Resume gap between #1 and #3 triggering a three-way vote split.",
    )


class CoachesPollConfig(BaseModel):
    """Configuration parameters for the USA Today Coaches Poll."""

    total_voters: int = Field(
        default=62,
        description="Total number of FBS coaches in the Coaches poll panel.",
    )
    max_points: int = Field(
        default=1550,
        description="Maximum possible points in the Coaches poll curve (voters * 25).",
    )
    resume_weight: float = Field(
        default=0.70,
        description="Weight given to team resume score (coaches place less weight on pure resume).",
    )
    prior_rank_anchor_weight: float = Field(
        default=0.55,
        description="Poll inertia anchor weight awarded to previously ranked teams (26 - prev_rank).",
    )
    loss_anchor_damping: float = Field(
        default=0.65,
        description="Damping multiplier applied to prior rank anchor when a team has recorded a loss.",
    )
    hot_start_wins: int = Field(
        default=6,
        description="Minimum wins for an unranked team to trigger a hot-start ranking boost.",
    )
    hot_start_losses: int = Field(
        default=1,
        description="Maximum losses allowed for an unranked team to trigger hot-start boost.",
    )
    hot_start_bonus: float = Field(
        default=4.0,
        description="Boost added to unranked teams meeting hot-start criteria.",
    )
    blueblood_bonus: float = Field(
        default=2.0,
        description="Pedigree boost added to traditional blueblood programs.",
    )
    points_decay_power: float = Field(
        default=1.4,
        description="Exponential curve factor shaping the non-linear decay of voter points.",
    )
    points_decay_factor: float = Field(
        default=0.18,
        description="Magnitude scaling coefficient for the voter point curve decay.",
    )
    enable_h2h_adjustments: bool = Field(
        default=True,
        description="Whether to apply head-to-head adjustments to the Coaches rankings.",
    )

    # 1st place vote distribution thresholds
    first_place_threshold_large: float = Field(
        default=7.0,
        description="Resume gap threshold where the #1 team claims almost all 1st-place votes.",
    )
    first_place_threshold_medium: float = Field(
        default=3.5,
        description="Resume gap threshold for a moderate split of 1st-place votes.",
    )
    first_place_share_large: float = Field(
        default=0.72,
        description="Proportion of 1st-place votes awarded when gap exceeds large threshold.",
    )
    first_place_share_medium: float = Field(
        default=0.55,
        description="Proportion of 1st-place votes awarded when gap is within medium threshold.",
    )


class CFPPollConfig(BaseModel):
    """Configuration parameters for the College Football Playoff (CFP) committee rankings."""

    enable_h2h_adjustments: bool = Field(
        default=True,
        description="Whether to apply head-to-head adjustments to the CFP rankings.",
    )


class RankingConfig(BaseModel):
    """Root configuration holding all resume and poll ranking parameters."""

    resume: EngineConfig = Field(default_factory=EngineConfig, description="Resume engine calculation rules.")
    ap: APPollConfig = Field(default_factory=APPollConfig, description="AP Top 25 Media poll rules.")
    coaches: CoachesPollConfig = Field(default_factory=CoachesPollConfig, description="Coaches poll rules.")
    cfp: CFPPollConfig = Field(default_factory=CFPPollConfig, description="CFP committee ranking rules.")


def get_all_rules_metadata() -> list[dict[str, Any]]:
    """Returns a flat list of metadata describing all configuration parameters."""
    cfg = RankingConfig()
    schema = cfg.model_json_schema()
    defs = schema.get("$defs", {})

    sub_configs = [
        ("resume", "EngineConfig", cfg.resume),
        ("ap", "APPollConfig", cfg.ap),
        ("coaches", "CoachesPollConfig", cfg.coaches),
        ("cfp", "CFPPollConfig", cfg.cfp),
    ]

    rules = []
    for section_name, def_name, model_inst in sub_configs:
        model_props = defs.get(def_name, {}).get("properties", {})
        for prop_name, prop_data in model_props.items():
            current_val = getattr(model_inst, prop_name)
            desc = prop_data.get("description", "No description provided.")
            type_name = prop_data.get("type", "unknown")
            rules.append(
                {
                    "section": section_name,
                    "name": prop_name,
                    "full_name": f"{section_name}.{prop_name}",
                    "type": type_name,
                    "default": current_val,
                    "description": desc,
                }
            )
    return rules


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
    normalized_overrides = (
        {"resume": raw_overrides} if not top_keys.intersection(sub_sections) else raw_overrides
    )

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
