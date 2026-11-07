# Python API

`ncaa_dynasty_rerank` can be used as a Python library to evaluate schedules, compute custom rankings, and read or modify NCAA Football 14 save files.

## Reading and Writing Saves with TDBFile

The `TDBFile` class parses uncompressed EA Sports DB files (`USR-DATA`):

```python
from pathlib import Path
from ncaa_dynasty_rerank.tdb import TDBFile
from ncaa_dynasty_rerank.models import TeamRecord, GameRecord

save_path = Path("~/.config/rpcs3/dev_hdd0/home/00000001/savedata/BLUS31159-DYNASTY-DEFAULT/USR-DATA").expanduser()
tdb = TDBFile(save_path)

# Retrieve raw records from TEAM and SCHD tables
raw_teams = tdb.get_teams()
raw_games = tdb.get_schedule()

# Convert dictionaries into typed Pydantic dataclasses
teams = [TeamRecord(**t) for t in raw_teams]
games = [GameRecord(**g) for g in raw_games]

print(f"Loaded {len(teams)} teams and {len(games)} completed games.")
```

---

## Evaluating Resumes with RankingEngine

The `RankingEngine` calculates team metrics, strength of schedule, and resume scores:

```python
from ncaa_dynasty_rerank.engine import RankingEngine
from ncaa_dynasty_rerank.config_rules import EngineConfig

# Instantiate engine with default or custom configuration
config = EngineConfig(margin_cap=28)
engine = RankingEngine(teams, games, config=config)

# Evaluate resumes
evaluated_teams = engine.evaluate_resumes()

# Inspect top resume score
evaluated_teams.sort(key=lambda t: t.resume_score, reverse=True)
top_team = evaluated_teams[0]
print(f"Top Resume: {top_team.full_name} ({top_team.record_str}) - Score: {top_team.resume_score}")
```

---

## Generating Polls

Use `PollGenerator` to run all three poll strategies (`cfp`, `ap`, and `coaches`):

```python
from ncaa_dynasty_rerank.polls import PollGenerator
from ncaa_dynasty_rerank.config_rules import RankingConfig

ranking_config = RankingConfig()
ranking_config.resume.margin_cap = 28
ranking_config.ap.undefeated_non_power_boost = 5.0

engine = RankingEngine(teams, games, config=ranking_config)
generator = PollGenerator(engine, config=ranking_config)

cfp_poll, ap_poll, coaches_poll = generator.generate_all()

# Print Top 5 in AP Poll
print("AP Top 5:")
for r in ap_poll[:5]:
    print(f"#{r.rank}: {r.team.full_name} ({r.points} pts, {r.first_place_votes} 1st votes)")
```

---

## Creating a Custom Poll Strategy

You can define custom ranking models by subclassing `PollStrategy` and registering your class in `PollRegistry`:

```python
from ncaa_dynasty_rerank.strategies.base import PollStrategy
from ncaa_dynasty_rerank.strategies.registry import PollRegistry
from ncaa_dynasty_rerank.models import PollRanking, TeamRecord
from ncaa_dynasty_rerank.engine import RankingEngine

class SimpleWinPctStrategy(PollStrategy):
    name = "Raw Win Percentage Ranking"
    poll_type = "win_pct"

    def rank(self, teams: list[TeamRecord], engine: RankingEngine) -> list[PollRanking]:
        # Filter FBS teams
        fbs = [t for t in teams if t.conf_id not in (17, 24)]
        sorted_teams = sorted(fbs, key=lambda t: (t.win_pct, t.wins), reverse=True)
        return [
            PollRanking(
                rank=i + 1,
                team=t,
                score=round(t.win_pct * 100.0, 2),
            )
            for i, t in enumerate(sorted_teams)
        ]

# Register custom model
registry = PollRegistry()
registry.register(SimpleWinPctStrategy())

custom_poll = registry.get("win_pct").rank(teams, engine)
```

---

## Writing Updates to the Save Binary

To persist new rankings to the save file, map updates by team `tgid` and call `tdb.update_team_polls()`. Saving automatically recalculates CRC-32 table checksums:

```python
# Build update dictionaries
update_payload = []
for r in ap_poll:
    update_payload.append({
        "tgid": r.team.tgid,
        "ap_rank": r.rank,
        "ap_prev_rank": r.previous_rank,
        "ap_points": r.points,
        "ap_first_votes": r.first_place_votes,
    })

# Write to database and save
tdb.update_team_polls(update_payload)
tdb.save()
```
