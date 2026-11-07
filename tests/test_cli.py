from unittest.mock import patch

from ncaa_dynasty_rerank.cli import main, render_movement
from tests.synthetic_tdb import create_synthetic_save


def test_render_movement():
    assert "NEW" in render_movement(0, 15)
    assert "+3" in render_movement(18, 15)
    assert "-2" in render_movement(10, 12)
    assert "=" in render_movement(5, 5)


def test_cli_alias_crud_lifecycle(tmp_path):
    save_file = tmp_path / "USR-DATA"
    save_file.write_bytes(b"dummy")

    with patch("ncaa_dynasty_rerank.cli.ConfigManager") as mock_cfg_class:
        from ncaa_dynasty_rerank.config import ConfigManager

        real_cfg = ConfigManager(tmp_path / "cfg")
        mock_cfg_class.return_value = real_cfg

        # 1. Add alias
        with patch("sys.argv", ["ncaa-dynasty-rerank", "alias", "add", "myteam", str(save_file)]):
            assert main() == 0
            assert real_cfg.get_alias("myteam") == save_file.resolve()

        # 2. Add non-existent path -> must return 1
        with patch("sys.argv", ["ncaa-dynasty-rerank", "alias", "add", "bad", "/path/does/not/exist"]):
            assert main() == 1

        # 3. List
        with patch("sys.argv", ["ncaa-dynasty-rerank", "alias", "list"]):
            assert main() == 0

        # 4. Remove alias
        with patch("sys.argv", ["ncaa-dynasty-rerank", "alias", "remove", "myteam"]):
            assert main() == 0
            assert real_cfg.get_alias("myteam") is None

        # 5. Remove unknown alias -> must return 1
        with patch("sys.argv", ["ncaa-dynasty-rerank", "alias", "remove", "nonexistent"]):
            assert main() == 1


def test_cli_rerank_dry_run_with_synthetic_save(tmp_path):
    save_path = tmp_path / "USR-DATA"
    teams = [
        {"tgid": 1, "name": "TeamA", "mascot": "MascotA", "conf_id": 11, "wins": 8, "losses": 0, "cfp_rank": 1},
        {"tgid": 2, "name": "TeamB", "mascot": "MascotB", "conf_id": 1, "wins": 7, "losses": 1, "cfp_rank": 2},
    ]
    games = [{"away_tgid": 2, "home_tgid": 1, "away_score": 14, "home_score": 28, "week": 1, "status": 2}]
    create_synthetic_save(save_path, teams, games)

    # Test running CLI with --save-path and --dry-run
    with patch("sys.argv", ["ncaa-dynasty-rerank", "--save-path", str(save_path), "--dry-run"]):
        assert main() == 0


def test_cli_missing_save_path_error():
    with patch("sys.argv", ["ncaa-dynasty-rerank", "--save-path", "/non/existent/save/USR-DATA"]):
        assert main() == 1
