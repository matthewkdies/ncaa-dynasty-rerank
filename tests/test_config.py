from ncaa_dynasty_rerank.config import ConfigManager
from ncaa_dynasty_rerank.discover import find_dynasty_saves


def test_config_manager_crud(tmp_path):
    cfg_dir = tmp_path / "config"
    cfg = ConfigManager(cfg_dir)

    # Create fake save file
    save_file = tmp_path / "BLUS31159-DYNASTY-WVU" / "USR-DATA"
    save_file.parent.mkdir(parents=True)
    save_file.write_bytes(b"dummy")

    # Add alias
    cfg.add_alias("wvu", save_file)
    assert cfg.get_default_alias() == "wvu"
    assert cfg.get_alias("wvu") == save_file.resolve()

    # Add second alias
    save2 = tmp_path / "BLUS31159-DYNASTY-TEST" / "USR-DATA"
    save2.parent.mkdir(parents=True)
    save2.write_bytes(b"dummy2")
    cfg.add_alias("test", save2)

    # Set default
    cfg.set_default("test")
    assert cfg.get_default_alias() == "test"

    # List
    aliases = cfg.list_aliases()
    assert len(aliases) == 2
    assert ("test", str(save2.resolve()), True) in aliases

    # Remove
    assert cfg.remove_alias("test") is True
    assert cfg.get_default_alias() == "wvu"


def test_discover_saves(tmp_path):
    rpcs3_dir = tmp_path / "rpcs3" / "dev_hdd0" / "home" / "00000001" / "savedata" / "BLUS31159-DYNASTY-DEFAULT"
    rpcs3_dir.mkdir(parents=True)
    (rpcs3_dir / "USR-DATA").write_bytes(b"data")

    found = find_dynasty_saves(search_dirs=[tmp_path])
    assert len(found) == 1
    assert found[0].folder_name == "BLUS31159-DYNASTY-DEFAULT"
    assert found[0].is_aliased is False
    assert found[0].last_modified.tzinfo is not None
