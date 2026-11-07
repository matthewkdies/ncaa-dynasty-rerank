"""Auto-discovery of RPCS3 NCAA 14 dynasty save files."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ncaa_dynasty_rerank.config import ConfigManager


@dataclass
class DiscoveredSave:
    folder_name: str
    usr_data_path: Path
    last_modified: datetime
    is_aliased: bool
    alias_name: str | None = None


def find_dynasty_saves(
    search_dirs: list[Path] | None = None, config: ConfigManager | None = None
) -> list[DiscoveredSave]:
    """Scans system for BLUS31159 dynasty save folders containing USR-DATA."""
    if search_dirs is None:
        home = Path.home()
        search_dirs = [
            # Standard RPCS3
            home / ".config" / "rpcs3" / "dev_hdd0" / "home",
            # Flatpak Steam Proton (where Dynasty Tool often saves)
            home
            / ".var"
            / "app"
            / "com.valvesoftware.Steam"
            / ".local"
            / "share"
            / "Steam"
            / "steamapps"
            / "compatdata",
            # Native Steam Proton
            home / ".local" / "share" / "Steam" / "steamapps" / "compatdata",
        ]

    cfg = config or ConfigManager()
    aliased_paths: dict[str, str] = {str(Path(p).resolve()): alias for alias, p, _ in cfg.list_aliases()}

    found: list[DiscoveredSave] = []
    seen_paths: set[str] = set()

    for base_dir in search_dirs:
        if not base_dir.exists():
            continue

        try:
            for p in base_dir.rglob("*DYNASTY*"):
                if not p.is_dir():
                    continue

                usr_data = p / "USR-DATA"
                if usr_data.is_file():
                    canonical = str(usr_data.resolve())
                    if canonical in seen_paths:
                        continue
                    seen_paths.add(canonical)

                    mtime = datetime.fromtimestamp(usr_data.stat().st_mtime, tz=timezone.utc)
                    alias_name = aliased_paths.get(canonical)

                    found.append(
                        DiscoveredSave(
                            folder_name=p.name,
                            usr_data_path=usr_data.resolve(),
                            last_modified=mtime,
                            is_aliased=alias_name is not None,
                            alias_name=alias_name,
                        )
                    )
        except OSError:
            continue

    found.sort(key=lambda s: s.last_modified, reverse=True)
    return found
