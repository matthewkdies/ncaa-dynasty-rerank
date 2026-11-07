"""Configuration and dynasty save profile alias management."""

import json
from pathlib import Path
from typing import Any

from ncaa_dynasty_rerank.config_rules import RankingConfig, load_ranking_config


class ConfigManager:
    """Manages persistent dynasty save aliases in ~/.config/ncaa-dynasty-rerank/config.json."""

    def __init__(self, config_dir: Path | None = None):
        if config_dir is None:
            self.config_dir = Path.home() / ".config" / "ncaa-dynasty-rerank"
        else:
            self.config_dir = Path(config_dir)
        self.config_path = self.config_dir / "config.json"
        self.rules_path = self.config_dir / "rules.json"
        self._config: dict[str, Any] = self._load()

    def get_default_rules_path(self) -> Path:
        """Returns the default rules file path in the config directory."""
        return self.rules_path

    def load_rules(self, custom_path: Path | str | None = None) -> tuple[RankingConfig, Path | None]:
        """Loads RankingConfig from custom path, or default rules.json if present, or defaults."""
        if custom_path:
            p = Path(custom_path).expanduser().resolve()
            return load_ranking_config(p), p

        if self.rules_path.exists():
            return load_ranking_config(self.rules_path), self.rules_path

        return load_ranking_config(None), None

    def _load(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {"default_alias": None, "aliases": {}}
        try:
            with open(self.config_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {"default_alias": None, "aliases": {}}

    def save(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2)

    def add_alias(self, name: str, path: str | Path, set_default: bool = False) -> Path:
        """Registers a named alias for a dynasty save file (USR-DATA)."""
        save_path = Path(path).expanduser().resolve()
        if save_path.is_dir():
            save_path = save_path / "USR-DATA"

        if not save_path.exists():
            raise FileNotFoundError(f"Save file not found at: {save_path}")

        name = name.strip().lower()
        self._config["aliases"][name] = str(save_path)

        if set_default or not self._config.get("default_alias"):
            self._config["default_alias"] = name

        self.save()
        return save_path

    def remove_alias(self, name: str) -> bool:
        name = name.strip().lower()
        if name in self._config["aliases"]:
            del self._config["aliases"][name]
            if self._config.get("default_alias") == name:
                remaining = list(self._config["aliases"].keys())
                self._config["default_alias"] = remaining[0] if remaining else None
            self.save()
            return True
        return False

    def set_default(self, name: str) -> None:
        name = name.strip().lower()
        if name not in self._config["aliases"]:
            raise KeyError(f"Alias '{name}' does not exist.")
        self._config["default_alias"] = name
        self.save()

    def get_alias(self, name: str) -> Path | None:
        path_str = self._config["aliases"].get(name.strip().lower())
        return Path(path_str) if path_str else None

    def get_default_alias(self) -> str | None:
        return self._config.get("default_alias")

    def list_aliases(self) -> list[tuple[str, str, bool]]:
        """Returns a list of (alias_name, path, is_default) tuples."""
        default = self.get_default_alias()
        results = []
        for name, p_str in sorted(self._config.get("aliases", {}).items()):
            results.append((name, p_str, name == default))
        return results

    def resolve_save_path(self, dynasty_alias: str | None = None) -> Path:
        """Resolves the save path for the specified alias or default alias."""
        if dynasty_alias:
            p = self.get_alias(dynasty_alias)
            if not p:
                raise KeyError(
                    f"Dynasty alias '{dynasty_alias}' not found. "
                    f"Use 'ncaa-dynasty-rerank alias list' to view registered aliases."
                )
            if not p.exists():
                raise FileNotFoundError(f"Configured save file does not exist: {p}")
            return p

        default_name = self.get_default_alias()
        if default_name:
            p = self.get_alias(default_name)
            if p and p.exists():
                return p

        aliases = self._config.get("aliases", {})
        if len(aliases) == 1:
            p = Path(next(iter(aliases.values())))
            if p.exists():
                return p

        raise ValueError(
            "No default dynasty save configured. "
            "Specify --dynasty <name>, or run 'ncaa-dynasty-rerank alias scan' to discover saves."
        )
