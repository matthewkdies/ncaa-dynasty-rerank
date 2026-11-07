# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-11-07

### Fixed

- Fixed game crash caused by duplicate TGID entries in NCAA 14 `TEAM` tables (specifically South Alabama's transition slot at record index 131 overwriting index 88). `TDBFile` now strictly restricts poll loading and updates to active FBS records (`0..125`, excluding FCS conference 17 and High School conference 24), guaranteeing an exact bijection of ranks `1..126` with no missing or duplicate ranks.


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
