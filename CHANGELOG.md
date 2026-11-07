# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-11-07

### Added
- Extracted all resume calculation variables, SOS coefficients, and game valuation weights into a configurable EngineConfig model.
- Parameterized AP and Coaches poll strategies with dedicated configuration models controlling points curves, voter counts, Cinderella boosts, win volume bonuses, poll inertia anchors, and blueblood pedigree bonuses.
- Implemented recursive deep-merge configuration loading that allows users to provide partial overrides while preserving default ranking dynamics.
- Added support for friendly team and conference aliases (such as "sec", "big10", "bama", and "osu") in rules configuration files instead of requiring raw numeric IDs.
- Added comprehensive parameter descriptions across all configuration models and exposed them through a new `rules describe` CLI subcommand.
- Added a `--descriptions` option to `rules show` to display active ranking rules alongside their functional descriptions in a formatted table.
- Added CLI `--rules` (`-r`) flag to allow running re-ranking passes with custom rules files.
- Added `rules export`, `rules validate`, and `rules path` subcommands for managing user configuration files.

## [0.1.1] - 2026-11-07

### Added
- Applied CFP committee rankings (`TBRK`) and previous rank tracking (`TBPR`) by default on every re-ranking run without requiring `--force-cfp`.
- Guarded dynasty saves in early season weeks (before the in-game BCS/CFP poll is officially unlocked) by preserving inactive ranking state and skipping premature `TBRK` writes.
- `postseason.py`: Automatically detects unplayed bowl season schedules and aligns the National Championship Game to feature CFP #1 vs CFP #2. Former finalists displaced from the National Championship are automatically relocated into the vacated Major BCS bowl slots (e.g. Sugar Bowl).
  - Added a Rich table preview displaying proposed postseason matchup adjustments and replacement reasons before user confirmation.
  - Added `update_schedule_games()` to `TDBFile` for modifying home/away team matchups in `SCHD` with automatic CRC-32 checksum updates to successor tables (`SCWE`).

### Fixed

- Fixed RPCS3 crash on dynasty load caused by missing TDB table checksum recalculation. In EA Sports TDB saves, each table's payload (`fieldDefinitionBuffer + dataBuffer`) is verified by the game engine against the `priorCrc` field stored in the subsequent table's header. Modifying `TEAM` previously left `TSSE` (Team Season Stats) with an invalid `priorCrc`, causing the game engine to reject `TSSE` and dereference a null pointer when querying team stats. `TDBFile.save()` now automatically recalculates and writes successor `prior_crc` (and EOF CRC) values for all modified tables using the EA Sports big-endian CRC-32 algorithm.
- Fixed point curve monotonicity inversion in AP and Coaches poll strategies where rank 26 previously received more poll points than rank 25.
- Fixed in-game ranking movement arrows by properly recording previous poll ranks in AP previous rank and Coaches Poll.
- Fixed game crash caused by duplicate TGID entries in NCAA 14 `TEAM` tables. `TDBFile` now strictly restricts poll loading and updates to active FBS records (`0..125`, excluding FCS conference 17 and High School conference 24), guaranteeing an exact bijection of ranks `1..126` with no missing or duplicate ranks.


## [0.1.0] - 2026-11-07

### Added
- **Pure-Python TDB Binary Parser & Writer**: Implementation of the EA Sports Database (`TDB`) format capable of reading and updating `TEAM` and `SCHD` tables.
- **Big-Endian Bit Manipulation Engine (`BitView`)**: Bit-level buffer manipulator supporting arbitrary bit offsets, unsigned/signed integer packed fields, and fixed-width strings with bounds validation.
- **College Football Ranking Analytics Engine (`RatingEngine`)**:
  - Opponent Strength of Schedule (SOS) and Strength of Record (SOR) calculation.
  - Quality win bonuses with diminishing returns.
  - Margin of victory scaling with a configurable 24-point cap to prevent running up the score.
  - Head-to-head tiebreaking resolution and cycle handling.
  - Bye-week neutrality to ensure teams on a bye week are not unfairly penalized compared to active teams.
- **Extensible Poll Strategy Architecture (`PollRegistry`)**:
  - `CFPStrategy` (`cfp`): Resume-first evaluation prioritizing SOS, top-25 wins, and power-conference schedule strength.
  - `APStrategy` (`ap`): Media-style ranking prioritizing win-loss record and high-profile victories.
  - `CoachesStrategy` (`coaches`): Traditional poll logic weighting raw win totals with mild resume adjustments.
- **Interactive Terminal Interface (`ncaa-dynasty-rerank` CLI)**:
  - `rich` formatted Top 25 movement and comparison tables.
  - Automatic detection and scanning of NCAA Football 14 dynasty saves across RPCS3 (`dev_hdd0`) and Steam Proton directories.
  - Alias management subcommands (`add`, `list`, `set-default`, `remove`, `scan`) stored in `~/.config/ncaa-dynasty-rerank/config.json`.
  - Simulation support with `--dry-run`.
  - Automated timestamped backup generation (`USR-DATA.bak.YYYYMMDD_HHMMSS`) before committing any changes.
  - Early-season override flag (`--force-cfp`) to populate CFP rankings before the in-game week threshold.
  - Non-interactive batch execution flag (`-y` / `--yes`) for automated scripting.
- **Test Suite**:
  - Synthetic TDB save file generator producing valid binary database structures in memory and temporary directories.
  - Test coverage across bitview operations, TDB table updates, ranking engine invariants, strategy registration, and CLI commands.
- **CI/CD Automation**:
  - GitHub Actions testing matrix across Python 3.10, 3.11, 3.12, and 3.13.
  - Automated PyPI Trusted Publishing triggered on tagged releases (`v*`).

[Unreleased]: https://github.com/matthewkdies/ncaa-dynasty-rerank/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/matthewkdies/ncaa-dynasty-rerank/releases/tag/v0.1.0
