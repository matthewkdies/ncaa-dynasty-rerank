# 🏈 ncaa-dynasty-rerank

[![CI Test Suite](https://github.com/your-username/ncaa-dynasty-rerank/actions/workflows/publish.yml/badge.svg)](https://github.com/your-username/ncaa-dynasty-rerank/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> *"Let's be honest: NCAA Football 14 is still better than the modern, Madden-copied games."*

An automated, 100% pure-Python re-ranking engine for NCAA Football 14 (and College Football Revamped) dynasty saves. It analyzes real game schedules, opponent win rates, strength of record (SOR), margin of victory, and head-to-head match-ups to produce authentic CFP, AP, and Coaches Poll rankings. The tool modifies your RPCS3 save file in directly, quickly, and cleanly.

---

## Why?

I love college football, and I love programming. But most of all, I love NCAA Football 14 (and my fiancé, and cats, and friends, and y'know, other things too). Even with modern consoles and new college football releases, nothing quite matches the magic, dynasty depth, and soul of NCAA 14.

Unfortunately, the in-game ranking algorithm has a bad habit of keeping 2-3 bluebloods in the Top 10 while undefeated mid-majors and 7-1 powerhouses languish at #22. 

The [NCAA 14 Dynasty Tool](https://github.com/Bowersrd/NCAA14DynastyToolRelease) solved the problem of manual poll editing, but manually re-ranking 25 teams every single week takes time. After all, I'm a programmer. I want to run a script that automates this, darnit! This tool automates that process using a deterministic, resume-first analytics engine. It reads and writes your RPCS3 save directly, without needing a GUI or uploading files anywhere.

### Acknowledgments & Shoutouts
Huge love and respect to the giants whose shoulders this stands on:

- **The [College Football Revamped](https://github.com/cfbrevamped) (CFBR) Team**: For breathing brand new life into NCAA 14 with modern uniforms, stadiums, fields, and logos. This is what inspired me to get back into the game, setting up Sunshine, and more.
- **The [NCAA 14 Dynasty Tool](https://github.com/Bowersrd/NCAA14DynastyToolRelease) Team**: For their reverse-engineering of EA DB formats, the 12-team playoff mods, and inspiring this automation. Even though I'll be using this tool to rank, I'll definitely be using the Dynasty Tool for the incredible other features like the CFP, historical views, etc.

---

## Features

- **Pure Python**: Zero external dependencies (e.g., no Node.js, no Proton, no C compilers, and no LLMs burning API tokens). Bit-level reading and writing of EA Sports TDB saves.
- **Re-Ranking the Three Polls, with Distinct "Personalities"**:
  - **College Football Playoff (CFP)**: 100% resume-driven. Weighted on Top 25 wins, Strength of Schedule (SOS), quality road wins, and head-to-head. No inertia from preseason polls.
  - **AP Top 25 Poll**: Media perspective factoring in margin of victory, momentum, and Cinderella respect for surging Group of 5 teams. Generates authentic voter points (~1575 max) and 1st-place votes.
  - **USA Today Coaches Poll**: Traditional poll inertia (`TCPR`), making it harder to fall without losing and harder to jump rapidly, with blueblood pedigree consideration.
- **Baked-in Resume Rules**:
  - **Soft Tiers & Leapfrogging**: A 7-1 team with multiple top-10 wins can rightfully jump an untested 8-0 team playing an FCS/easy schedule.
  - **Bye-Week Invariance**: Evaluates quality density and average game performance so a 7-0 team with a late bye is never punished against an 8-0 team.
  - **Head-to-Head Enforcement**: Strict priority for teams with equal records; weighted tiebreaker bonus for 1-loss differences.
  - **Margin Diminishing Returns**: Blowout wins are rewarded up to a $\pm 24$ cap with diminishing returns, preventing you (and others) from "FCS farming" (or running up the score... have some sportsmanship, please!).
- **Safety**:
  - Automatic timestamped backups (`USR-DATA.bak.YYYYMMDD_HHMMSS`) before modifying a single byte.
  - `--dry-run` mode to preview proposed rankings in beautiful terminal tables.
  - Early-season CFP protection: detects when the in-game BCS/CFP poll is dormant (pre-Week 8) to prevent game UI glitches.
- **Dynasty Aliases for Ease of Use**:
  - Profile manager (`alias add`, `alias list`, `alias scan`) to switch between multiple dynasty careers with short names (e.g. `wvu`, `osu`, etc.).

---

## Installation

Install via `pip`:
```bash
pip install ncaa-dynasty-rerank
```

Or using `uv`:
```bash
uv tool install ncaa-dynasty-rerank
```

---

## Usage Guide

### Scan & Map Your Dynasty Save

Scan your system to auto-detect any dynasty saves in RPCS3 or Steam Proton:

```bash
ncaa-dynasty-rerank alias scan
```

Or manually map an alias:

```bash
ncaa-dynasty-rerank alias add wvu ~/.config/rpcs3/dev_hdd0/home/00000001/savedata/BLUS31159-DYNASTY-DEFAULT/USR-DATA --default
```

### Preview the Re-Rank (`--dry-run`)

Inspect the proposed Top 25 for all three polls with colorized (shoutout to [`rich`](https://github.com/textualize/rich)) movement indicators:

```bash
ncaa-dynasty-rerank --dry-run
```

### Apply to Your Save

When you're ready, run without flags. It will display the comparison, prompt for confirmation, create an automatic backup, and update the save file:

```bash
$ ncaa-dynasty-rerank

╭──────────────────────────────────────────────────────────────────────────────╮
│ Loading save: ~/.config/rpcs3/dev_hdd0/.../BLUS31159-DYNASTY-DEFAULT/USR-DATA│
╰──────────────────────────────────────────────────────────────────────────────╯
Loaded 142 teams and 528 completed games.

PROPOSED RANKINGS

                    College Football Playoff (CFP) Rankings                     
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃  Rank  ┃   Move   ┃ Team                         ┃  Record  ┃   Resume Score ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│   1    │    =     │ Florida Gators               │   7-0    │         187.25 │
│   2    │   ▲ +2   │ Alabama Crimson Tide         │   8-0    │         173.73 │
│   3    │   ▲ +2   │ West Virginia Mountaineers   │   8-0    │         159.29 │
│   4    │   ▼ -1   │ Ohio State Buckeyes          │   8-0    │         158.55 │
│   5    │   ▼ -3   │ Clemson Tigers               │   8-0    │         157.06 │
│   6    │   ▲ +5   │ UCLA Bruins                  │   6-1    │         133.45 │
...
Apply these rankings to your save file? [y/N]: y
✓ Created backup: USR-DATA.bak.20261107_113000
✓ Successfully applied new rankings to save file!
```

---

## Configuration & Extensibility

If you want to tweak conference weights, adjust margin caps, or add custom polls, you can! The library uses the [Strategy Pattern](https://en.wikipedia.org/wiki/Strategy_pattern):

```python
from ncaa_dynasty_rerank.config_rules import EngineConfig
from ncaa_dynasty_rerank.engine import RankingEngine
from ncaa_dynasty_rerank.strategies.base import PollStrategy
from ncaa_dynasty_rerank.strategies.registry import PollRegistry

# Custom conference weights or margin caps
config = EngineConfig(
    conference_weights={11: 1.20, 1: 1.20, 0: 1.05},  # Boost SEC & Big Ten
    margin_cap=21,
)


# Custom poll rating model (e.g. SP+ or /r/CFB poll)
class RedditCFBPoll(PollStrategy):
    name = "/r/CFB User Poll"
    poll_type = "rcfb"

    def rank(self, teams, engine):
        # Your custom ranking logic here
        return ...


registry = PollRegistry()
registry.register(RedditCFBPoll())
```

> [!note]
> I have future plans to make this all more configurable, both at the CLI level and at the user-level. Eventually, I want to support preferences being saved to a config file, which is loaded at runtime. But... later.

---

## Testing

The test suite runs against self-contained synthetic binary fixtures:

```bash
uv run --extra dev pytest -v
```
