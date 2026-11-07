from pathlib import Path

import pytest

from ncaa_dynasty_rerank.tdb import TDBFile
from tests.synthetic_tdb import create_synthetic_save


@pytest.fixture
def synthetic_save(tmp_path) -> Path:
    save_path = tmp_path / "USR-DATA"
    teams = [
        {
            "tgid": 1,
            "name": "Clemson",
            "mascot": "Tigers",
            "conf_id": 0,
            "wins": 8,
            "losses": 0,
            "cfp_rank": 1,
            "ap_rank": 1,
            "coaches_rank": 1,
            "ap_points": 1550,
            "coaches_points": 1500,
        },
        {
            "tgid": 2,
            "name": "Alabama",
            "mascot": "Crimson Tide",
            "conf_id": 11,
            "wins": 7,
            "losses": 1,
            "cfp_rank": 2,
            "ap_rank": 2,
            "coaches_rank": 2,
            "ap_points": 1480,
            "coaches_points": 1440,
        },
    ]
    games = [{"away_tgid": 2, "home_tgid": 1, "away_score": 21, "home_score": 28, "week": 1, "status": 2}]
    return create_synthetic_save(save_path, teams, games)


def test_synthetic_tdb_load(synthetic_save):
    tdb = TDBFile(synthetic_save)
    teams = tdb.get_teams()
    assert len(teams) == 2

    clemson = next(t for t in teams if t["tgid"] == 1)
    assert clemson["name"] == "Clemson"
    assert clemson["mascot"] == "Tigers"
    assert clemson["wins"] == 8
    assert clemson["losses"] == 0
    assert clemson["cfp_rank"] == 1

    games = tdb.get_schedule()
    assert len(games) == 1
    assert games[0]["winner_tgid"] == 1
    assert games[0]["loser_tgid"] == 2
    assert games[0]["margin"] == 7


def test_synthetic_tdb_update_and_save(synthetic_save):
    tdb = TDBFile(synthetic_save)
    # Update Alabama's AP rank to 5 and points to 1100
    tdb.update_team_polls([{"tgid": 2, "ap_rank": 5, "ap_points": 1100}])
    tdb.save()

    # Reload from disk and verify byte-level modification
    tdb_reloaded = TDBFile(synthetic_save)
    teams = tdb_reloaded.get_teams()
    bama = next(t for t in teams if t["tgid"] == 2)
    assert bama["ap_rank"] == 5
    assert bama["ap_points"] == 1100

    # Verify Clemson was untouched
    clemson = next(t for t in teams if t["tgid"] == 1)
    assert clemson["ap_rank"] == 1
    assert clemson["ap_points"] == 1550


def test_tdb_duplicate_tgid_and_non_fbs_filtering(tmp_path):
    save_path = tmp_path / "USR-DATA"
    teams = [
        {"tgid": 1, "name": "TeamA", "conf_id": 0, "wins": 8, "losses": 0, "cfp_rank": 1},
        {"tgid": 235, "name": "South Alabama", "conf_id": 13, "wins": 2, "losses": 4, "cfp_rank": 107},
        {"tgid": 160, "name": "FCS East", "conf_id": 17, "wins": 0, "losses": 0, "cfp_rank": 0},
        {"tgid": 235, "name": "South Alabama", "conf_id": 13, "wins": 0, "losses": 0, "cfp_rank": 0},
        {"tgid": 610, "name": "User HS team", "conf_id": 24, "wins": 0, "losses": 0, "cfp_rank": 0},
    ]
    create_synthetic_save(save_path, teams, [])

    tdb = TDBFile(save_path)
    loaded_teams = tdb.get_teams()

    # Must only load FBS teams, skipping FCS, HS, and duplicate TGIDs
    assert len(loaded_teams) == 2
    assert [t["tgid"] for t in loaded_teams] == [1, 235]
    assert loaded_teams[1]["record_index"] == 1

    # Updating polls must update record 1 (real FBS team), NOT record 3 (duplicate non-FBS)
    tdb.update_team_polls([{"tgid": 235, "cfp_rank": 77}])
    tdb.save()

    reloaded = TDBFile(save_path)
    rec1_bv = reloaded.tables["TEAM"].get_record_bitview(1)
    rec3_bv = reloaded.tables["TEAM"].get_record_bitview(3)

    tbrk_def = reloaded.tables["TEAM"].fields["TBRK"]
    rec1_rank = rec1_bv.get_bits(tbrk_def.offset, tbrk_def.bits)
    rec3_rank = rec3_bv.get_bits(tbrk_def.offset, tbrk_def.bits)

    assert rec1_rank == 77
    assert rec3_rank == 0


def test_tdb_crc_update_on_save(synthetic_save):
    from ncaa_dynasty_rerank.tdb import TdbCrc

    tdb = TDBFile(synthetic_save)
    team_table = tdb.tables["TEAM"]
    schd_table = tdb.tables["SCHD"]
    initial_schd_prior_crc = schd_table.header.prior_crc

    # Modify TEAM table
    tdb.update_team_polls([{"tgid": 1, "ap_rank": 3, "ap_points": 1400}])
    tdb.save()

    # Reload file directly from disk and check SCHD's prior_crc header field
    crc_calc = TdbCrc()
    team_payload = bytes(team_table.field_defs_raw) + bytes(team_table.records_data)
    expected_crc = crc_calc.checksum(team_payload)

    reloaded = TDBFile(synthetic_save)
    reloaded_schd = reloaded.tables["SCHD"]
    assert reloaded_schd.header.prior_crc == expected_crc
    assert reloaded_schd.header.prior_crc != initial_schd_prior_crc


def test_update_schedule_games(synthetic_save):
    tdb = TDBFile(synthetic_save)
    schd = tdb.tables["SCHD"]
    assert not schd.is_changed

    # Update record 0 in SCHD
    tdb.update_schedule_games([{"record_index": 0, "away_tgid": 99, "home_tgid": 88}])
    assert schd.is_changed

    bv = schd.get_record_bitview(0)
    gatg = bv.get_bits(schd.fields["GATG"].offset, schd.fields["GATG"].bits)
    ghtg = bv.get_bits(schd.fields["GHTG"].offset, schd.fields["GHTG"].bits)
    assert gatg == 99
    assert ghtg == 88

    tdb.save()
    reloaded = TDBFile(synthetic_save)
    reloaded_schd = reloaded.tables["SCHD"]
    reloaded_bv = reloaded_schd.get_record_bitview(0)
    assert reloaded_bv.get_bits(schd.fields["GATG"].offset, schd.fields["GATG"].bits) == 99
    assert reloaded_bv.get_bits(schd.fields["GHTG"].offset, schd.fields["GHTG"].bits) == 88
