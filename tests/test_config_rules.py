from pathlib import Path

import pytest

from ncaa_dynasty_rerank.config_rules import (
    APPollConfig,
    CFPPollConfig,
    CoachesPollConfig,
    EngineConfig,
    RankingConfig,
    deep_merge,
    export_default_ranking_config,
    load_ranking_config,
)


def test_ranking_config_defaults():
    cfg = RankingConfig()
    assert isinstance(cfg.resume, EngineConfig)
    assert isinstance(cfg.ap, APPollConfig)
    assert isinstance(cfg.coaches, CoachesPollConfig)
    assert isinstance(cfg.cfp, CFPPollConfig)

    # Check some defaults
    assert cfg.resume.margin_cap == 24
    assert cfg.resume.win_base == 12.0
    assert cfg.resume.conference_weights[11] == 1.15
    assert 3 in cfg.resume.blueblood_tgids
    assert cfg.ap.total_voters == 63
    assert cfg.ap.undefeated_non_power_boost == 2.5
    assert cfg.coaches.total_voters == 62
    assert cfg.coaches.resume_weight == 0.70
    assert cfg.cfp.enable_h2h_adjustments is True


def test_deep_merge_partial_overrides():
    base = {
        "scalar": 10,
        "dict_val": {"a": 1, "b": 2},
        "list_val": [1, 2, 3],
        "nested": {"deep": {"val": "original", "keep": True}},
    }
    overrides = {
        "scalar": 20,
        "dict_val": {"b": 99, "c": 3},
        "list_val": [4, 5],
        "nested": {"deep": {"val": "modified"}},
    }
    merged = deep_merge(base, overrides)

    assert merged["scalar"] == 20
    assert merged["dict_val"] == {"a": 1, "b": 99, "c": 3}
    assert merged["list_val"] == [4, 5]
    assert merged["nested"]["deep"]["val"] == "modified"
    assert merged["nested"]["deep"]["keep"] is True


def test_ranking_config_partial_load_from_json(tmp_path: Path):
    rules_file = tmp_path / "custom_rules.json"
    rules_file.write_text(
        """
        {
          "resume": {
            "margin_cap": 35,
            "conference_weights": {
              "11": 1.30
            }
          },
          "ap": {
            "undefeated_non_power_boost": 5.0
          },
          "coaches": {
            "blueblood_bonus": 3.5
          }
        }
        """
    )

    cfg = load_ranking_config(rules_file)

    # Overridden values
    assert cfg.resume.margin_cap == 35
    assert cfg.resume.conference_weights[11] == 1.30
    assert cfg.ap.undefeated_non_power_boost == 5.0
    assert cfg.coaches.blueblood_bonus == 3.5

    # Retained default values
    assert cfg.resume.win_base == 12.0
    assert cfg.resume.conference_weights[1] == 1.15  # Big Ten unchanged
    assert cfg.ap.total_voters == 63
    assert cfg.coaches.resume_weight == 0.70
    assert cfg.cfp.enable_h2h_adjustments is True


def test_ranking_config_flat_resume_compatibility(tmp_path: Path):
    """If user passes a legacy or flat config with resume keys directly at top level."""
    rules_file = tmp_path / "flat_rules.json"
    rules_file.write_text(
        """
        {
          "margin_cap": 28,
          "win_base": 15.0
        }
        """
    )
    cfg = load_ranking_config(rules_file)
    assert cfg.resume.margin_cap == 28
    assert cfg.resume.win_base == 15.0


def test_export_default_ranking_config(tmp_path: Path):
    dest = tmp_path / "exported_rules.json"
    export_default_ranking_config(dest)

    assert dest.exists()
    loaded = load_ranking_config(dest)
    assert loaded == RankingConfig()


def test_load_nonexistent_file_raises():
    with pytest.raises(FileNotFoundError):
        load_ranking_config("/non/existent/path/rules.json")


def test_invalid_json_raises(tmp_path: Path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{not valid json")
    with pytest.raises(ValueError):
        load_ranking_config(bad_file)
