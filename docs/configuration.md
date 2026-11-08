# Rule Configuration

All parameters controlling how resume scores and poll rankings are computed can be customized through a JSON configuration file.

## Configuration File Locations

The re-ranking engine looks for configuration rules in the following order:

1. **CLI Flag (`--rules <path>`)**: A custom file passed directly on the command line.
2. **User Default File**: `~/.config/ncaa-dynasty-rerank/rules.json`.
3. **Built-in Defaults**: Used when neither of the above files exists.

You can inspect the path to the default user rules file with:

```bash
ncaa-dynasty-rerank rules path
```

---

## Partial Overrides

You do not need to specify every parameter in your custom JSON file. The configuration loader recursively merges user-supplied values on top of the built-in defaults:

- **Scalars (numbers, booleans)**: Replace default values.
- **Dictionaries (such as `conference_weights`)**: Merge key-by-key. Specifying a single conference updates that conference while preserving default multipliers for all others.
- **Lists and sets (such as `blueblood_tgids`)**: Replaced by the user-provided array.

### Example Configuration

Create a file named `rules.json`:

```json
{
  "resume": {
    "margin_cap": 30,
    "conference_weights": {
      "sec": 1.25,
      "big10": 1.20
    },
    "blueblood_tgids": [
      "bama",
      "osu",
      "michigan",
      "texas",
      "notre_dame",
      "georgia",
      "clemson",
      "usc"
    ]
  },
  "ap": {
    "undefeated_non_power_boost": 5.0
  },
  "coaches": {
    "prior_rank_anchor_weight": 0.80,
    "blueblood_bonus": 3.0
  }
}
```

Apply this file on a re-ranking run:

```bash
ncaa-dynasty-rerank --rules rules.json
```

---

## Friendly Aliases for Conferences and Teams

You can use text names and abbreviations instead of numeric IDs in `conference_weights`, `power_conference_ids`, `fcs_conference_ids`, and `blueblood_tgids`.

### Supported Conference Aliases

| Conference | Numeric ID | Accepted Aliases |
| :--- | :---: | :--- |
| ACC | `0` | `acc`, `atlantic_coast` |
| Big Ten | `1` | `big10`, `big_10`, `bigten`, `big_ten`, `b1g`, `b10` |
| Big 12 | `2` | `big12`, `big_12`, `b12`, `bigxii` |
| American (AAC) | `3` | `aac`, `american`, `american_athletic` |
| Conference USA | `4` | `cusa`, `c_usa`, `conference_usa` |
| Independents | `5` | `independents`, `independent`, `ind`, `indy` |
| MAC | `7` | `mac`, `mid_american` |
| Mountain West | `9` | `mwc`, `mountain_west` |
| Pac-12 | `10` | `pac12`, `pac_12`, `pac`, `pac10` |
| SEC | `11` | `sec`, `southeastern` |
| Sun Belt | `13` | `sun_belt`, `sunbelt`, `sbc` |
| FCS | `17` | `fcs`, `fcs_east`, `fcs_west` |
| Generic / High School | `24` | `generic`, `high_school`, `hs` |

### Supported Team Aliases

All FBS teams in NCAA Football 14 are supported by canonical name or standard abbreviations, including:

- `"bama"`, `"alabama"` (TGID 3)
- `"osu"`, `"ohio_state"` (TGID 70)
- `"uf"`, `"florida"` (TGID 27)
- `"um"`, `"michigan"` (TGID 51)
- `"ou"`, `"oklahoma"` (TGID 71)
- `"okstate"`, `"oklahoma_state"` (TGID 72)
- `"ut"`, `"texas"` (TGID 97)
- `"nd"`, `"notre_dame"` (TGID 68)
- `"lsu"` (TGID 45)
- `"uga"`, `"georgia"` (TGID 30)
- `"clemson"` (TGID 21)
- `"usc"`, `"southern_cal"` (TGID 84)
- `"psu"`, `"penn_state"` (TGID 76)
- `"fsu"`, `"florida_state"` (TGID 31)
- `"wvu"`, `"west_virginia"` (TGID 126)
- `"boise"`, `"boise_state"` (TGID 12)

Numeric TGIDs are also accepted.

---

## CLI Rules Management

### Describing Rules

To view descriptions, sections, and default values for all rules:

```bash
ncaa-dynasty-rerank rules describe
```

To filter descriptions by rule name or section:

```bash
ncaa-dynasty-rerank rules describe margin
ncaa-dynasty-rerank rules describe coaches
```

### Viewing Active Rules

To display currently active rules as formatted JSON:

```bash
ncaa-dynasty-rerank rules show
```

To display currently active rules in a table alongside their descriptions:

```bash
ncaa-dynasty-rerank rules show -d
```

To display built-in default values regardless of any local `rules.json`:

```bash
ncaa-dynasty-rerank rules show --defaults
```

### Exporting Defaults

To export a complete default configuration file to `~/.config/ncaa-dynasty-rerank/rules.json`:

```bash
ncaa-dynasty-rerank rules export
```

To export to a custom file path:

```bash
ncaa-dynasty-rerank rules export custom_rules.json
```

### Validating a Rules File

To check a rules file for syntax errors or invalid fields before using it:

```bash
ncaa-dynasty-rerank rules validate custom_rules.json
```

---

## Rule Reference Summary

### Resume Engine Parameters (`resume`)

- `margin_cap` (int, default `24`): Maximum point differential counted towards game quality.
- `margin_power` (float, default `0.65`): Exponent applied to effective margin of victory.
- `margin_multiplier` (float, default `0.90`): Multiplier applied to margin factor for victories.
- `margin_penalty_multiplier` (float, default `0.70`): Multiplier applied to margin penalty for losses.
- `win_base` (float, default `12.0`): Flat base points for a win.
- `loss_base` (float, default `-14.0`): Flat base penalty for a loss.
- `road_win_bonus` (float, default `2.0`): Bonus points for winning an away game.
- `home_loss_penalty` (float, default `2.5`): Additional penalty for losing at home.
- `win_opp_win_pct_factor` (float, default `14.0`): Multiplier for opponent win percentage on a win.
- `win_opp_sos_factor` (float, default `10.0`): Multiplier for opponent SOS on a win.
- `fcs_or_bad_team_win_pct_threshold` (float, default `0.35`): Win percentage cutoff below which opponent quality points are capped.
- `fcs_or_bad_team_quality_cap` (float, default `4.0`): Maximum quality points awarded vs sub-threshold opponents.
- `loss_opp_win_pct_factor` (float, default `8.0`): Loss mitigation credit for opponent win percentage.
- `loss_opp_sos_factor` (float, default `6.0`): Loss mitigation credit for opponent SOS.
- `sos_default_opp_win_pct` (float, default `0.30`): Fallback opponent win percentage for 0-game opponents.
- `sos_default_owp` (float, default `0.50`): Fallback OWP when a team has no opponents.
- `sos_owp_weight` (float, default `2.0`): Weight of Opponents' Win Percentage in composite SOS.
- `sos_oowp_weight` (float, default `1.0`): Weight of Opponents' Opponents' Win Percentage in composite SOS.
- `unplayed_base` (float, default `50.0`): Base score for teams with zero games played.
- `unplayed_win_bonus` (float, default `10.0`): Score bonus per recorded win when evaluating unplayed teams.
- `unplayed_loss_penalty` (float, default `15.0`): Score penalty per recorded loss when evaluating unplayed teams.
- `quality_win_min_win_pct` (float, default `0.50`): Opponent win rate required to count as a quality win.
- `loss_penalty_multiplier` (float, default `8.5`): Score penalty multiplier per loss in final resume calculation.
- `win_pct_base` (float, default `35.0`): Baseline constant in the win percentage component.
- `win_pct_multiplier` (float, default `30.0`): Multiplier for team win percentage.
- `performance_multiplier` (float, default `2.2`): Multiplier for average game performance.
- `sos_multiplier` (float, default `32.0`): Multiplier for composite SOS.
- `quality_win_rate_multiplier` (float, default `22.0`): Multiplier for quality wins per game.
- `h2h_loss_threshold` (float, default `4.0`): Resume deficit threshold for head-to-head adjustments.
- `h2h_max_iterations` (int, default `3`): Maximum bubble-sort iterations for head-to-head adjustments.

### AP Poll Parameters (`ap`)

- `total_voters` (int, default `63`): Number of voters in the AP poll panel.
- `max_points` (int, default `1575`): Maximum poll points curve ceiling (`total_voters * 25`).
- `undefeated_non_power_boost` (float, default `2.5`): Score boost for undefeated non-Power teams.
- `win_bonus` (float, default `0.4`): Win volume bonus added per win.
- `enable_h2h_adjustments` (bool, default `true`): Whether head-to-head adjustments apply.

### Coaches Poll Parameters (`coaches`)

- `total_voters` (int, default `62`): Number of voters in the Coaches poll panel.
- `max_points` (int, default `1550`): Maximum poll points curve ceiling (`total_voters * 25`).
- `resume_weight` (float, default `0.70`): Relative weight placed on resume score.
- `prior_rank_anchor_weight` (float, default `0.55`): Poll inertia weight based on prior rank.
- `loss_anchor_damping` (float, default `0.65`): Multiplier applied to anchor when a team has losses.
- `hot_start_wins` (int, default `6`): Minimum wins to trigger hot-start boost for unranked teams.
- `hot_start_losses` (int, default `1`): Maximum losses allowed to trigger hot-start boost.
- `hot_start_bonus` (float, default `4.0`): Boost points added for hot-start teams.
- `blueblood_bonus` (float, default `2.0`): Brand pedigree bonus added to traditional blueblood programs.
- `enable_h2h_adjustments` (bool, default `true`): Whether head-to-head adjustments apply.

### CFP Parameters (`cfp`)

- `enable_h2h_adjustments` (bool, default `true`): Whether head-to-head adjustments apply to CFP rankings.
