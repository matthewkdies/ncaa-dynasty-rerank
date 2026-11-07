# CLI Usage

The primary interface is the `ncaa-dynasty-rerank` command-line executable.

## Save Management and Aliases

RPCS3 stores dynasty saves in deep directory structures, for example:
`~/.config/rpcs3/dev_hdd0/home/00000001/savedata/BLUS31159-DYNASTY-WVU/USR-DATA`

You can register short alias names so you do not need to type the full file path each time.

### Automatic Discovery

Scan standard RPCS3 and Steam Proton directories for NCAA 14 dynasty saves:

```bash
ncaa-dynasty-rerank alias scan
```

The scan command lists all discovered saves and interactively prompts you to register an alias for any unmapped save.

### Manual Alias Registration

To register an alias manually:

```bash
ncaa-dynasty-rerank alias add wvu ~/.config/rpcs3/dev_hdd0/home/00000001/savedata/BLUS31159-DYNASTY-WVU/USR-DATA
```

To set an alias as default:

```bash
ncaa-dynasty-rerank alias set-default wvu
```

### Listing and Removing Aliases

List all configured aliases:

```bash
ncaa-dynasty-rerank alias list
```

Remove an alias:

```bash
ncaa-dynasty-rerank alias remove wvu
```

Configuration mappings are stored in `~/.config/ncaa-dynasty-rerank/config.json`.

---

## Re-ranking Dynasty Saves

### Standard Run

To re-rank using your default dynasty alias:

```bash
ncaa-dynasty-rerank
```

To re-rank a specific named alias:

```bash
ncaa-dynasty-rerank -d wvu
```

To re-rank by providing an explicit file or directory path:

```bash
ncaa-dynasty-rerank -s /path/to/BLUS31159-DYNASTY-SAVE/USR-DATA
```

### Dry Run (Preview Only)

To evaluate rankings and view the terminal tables without modifying the save file:

```bash
ncaa-dynasty-rerank --dry-run
```

### Non-Interactive Execution

To skip the interactive confirmation prompt (useful in automation scripts):

```bash
ncaa-dynasty-rerank -y
```

---

## Re-ranking Workflow Lifecycle

When you run `ncaa-dynasty-rerank`, the program executes the following steps:

1. **Loads the Save File**: Opens the uncompressed `USR-DATA` binary and reads table records (`TEAM` and `SCHD`).
2. **Evaluates Resumes**: Evaluates game outcomes, opponent records, strength of schedule, and point differentials for all 126 active FBS teams.
3. **Generates Polls**:
   - CFP Rankings: Pure resume score order with head-to-head adjustments.
   - AP Poll: Media model factoring in win volume, non-power undefeated bonuses, and authentic point curves.
   - Coaches Poll: Includes poll inertia anchors based on prior rank and blueblood bonuses.
4. **Checks Inactive Weeks**: If `TBRK` is zero across all teams (early-season weeks before the in-game BCS/CFP poll activates), the tool skips writing `TBRK` to avoid premature poll activation.
5. **Syncs Postseason Bowls**: In bowl season, updates the National Championship game in `SCHD` to match CFP #1 vs CFP #2 and relocates displaced teams into available major bowl slots.
6. **Displays Preview Tables**: Outputs Top 25 tables for CFP, AP, and Coaches polls, along with any bowl matchup diffs.
7. **Creates Backup**: Creates `USR-DATA.bak.<timestamp>` in the save folder before committing changes.
8. **Recalculates Checksums**: Writes the updated ranks, points, and schedule games into `TEAM` and `SCHD`, recalculating table `priorCrc` checksums so RPCS3 can load the file without errors.
