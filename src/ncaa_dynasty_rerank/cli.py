"""Command-line interface for ncaa-dynasty-rerank."""

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table

from ncaa_dynasty_rerank.config import ConfigManager
from ncaa_dynasty_rerank.config_rules import (
    export_default_ranking_config,
    get_all_rules_metadata,
    load_ranking_config,
)
from ncaa_dynasty_rerank.discover import find_dynasty_saves
from ncaa_dynasty_rerank.engine import RankingEngine
from ncaa_dynasty_rerank.models import GameRecord, PollRanking, TeamRecord
from ncaa_dynasty_rerank.polls import PollGenerator
from ncaa_dynasty_rerank.postseason import BowlDiff, PostseasonSyncer
from ncaa_dynasty_rerank.tdb import TDBFile

console = Console()
DOCS_URL = "https://matthewkdies.github.io/ncaa-dynasty-rerank/"


# -----------------------------------------------------------------------------
# Terminal Display Formatting
# -----------------------------------------------------------------------------


def render_movement(current: int, proposed: int) -> str:
    """Formats movement string with colors."""
    if current == 0 or current > 25:
        return "[bold cyan]NEW[/bold cyan]"
    diff = current - proposed
    if diff > 0:
        return f"[bold green]▲ +{diff}[/bold green]"
    if diff < 0:
        return f"[bold red]▼ {diff}[/bold red]"
    return "[dim]=[/dim]"


def display_poll_table(title: str, poll_results: list[PollRanking], poll_type: str) -> None:
    """Displays a rich terminal table for the top 25 of a poll."""
    table = Table(
        title=f"[bold gold1]{title}[/bold gold1]",
        show_header=True,
        header_style="bold magenta",
        border_style="dim",
    )
    table.add_column("Rank", justify="center", style="bold yellow", width=6)
    table.add_column("Move", justify="center", width=8)
    table.add_column("Team", style="bold white", width=28)
    table.add_column("Record", justify="center", style="cyan", width=8)

    if poll_type in ("ap", "coaches"):
        table.add_column("Points", justify="right", style="green", width=10)
        table.add_column("1st Votes", justify="center", style="bold yellow", width=10)
    elif poll_type == "cfp":
        table.add_column("Resume Score", justify="right", style="green", width=14)

    for r in poll_results[:25]:
        prev = r.previous_rank
        move_str = render_movement(prev, r.rank)
        team_name = r.team.full_name
        rec_str = r.team.record_str

        if poll_type in ("ap", "coaches"):
            pts_str = str(r.points)
            fp_str = str(r.first_place_votes) if r.first_place_votes > 0 else "-"
            table.add_row(str(r.rank), move_str, team_name, rec_str, pts_str, fp_str)
        else:
            score_str = f"{r.score:.2f}"
            table.add_row(str(r.rank), move_str, team_name, rec_str, score_str)

    console.print(table)
    console.print()


def display_bowl_diffs(diffs: list[BowlDiff]) -> None:
    """Displays proposed major bowl alignment changes in a Rich table."""
    console.print("\n[bold underline]PROPOSED BOWL MATCHUP UPDATES[/bold underline]\n")
    table = Table(title="Postseason Bowl Adjustments", box=box.ROUNDED)
    table.add_column("Bowl Game", style="cyan", no_wrap=True)
    table.add_column("Previous Matchup", style="dim")
    table.add_column("New Matchup", style="bold green")
    table.add_column("Reason", style="yellow")
    for d in diffs:
        table.add_row(d.bowl_name, d.old_matchup, d.new_matchup, d.reason)
    console.print(table)


def create_backup(save_path: Path) -> Path:
    """Creates a timestamped backup before modifying the save file."""
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
    backup_name = f"USR-DATA.bak.{timestamp}"
    backup_path = save_path.parent / backup_name
    shutil.copyfile(save_path, backup_path)
    return backup_path


# -----------------------------------------------------------------------------
# Alias Subcommands
# -----------------------------------------------------------------------------


def _handle_alias_list(cfg: ConfigManager) -> int:
    aliases = cfg.list_aliases()
    if not aliases:
        console.print("[yellow]No dynasty aliases configured yet.[/yellow]")
        console.print("Run [bold cyan]ncaa-dynasty-rerank alias scan[/bold cyan] to discover saves.")
        return 0

    table = Table(title="[bold]Registered Dynasty Aliases[/bold]")
    table.add_column("Alias", style="bold cyan")
    table.add_column("Default", justify="center", style="bold green")
    table.add_column("Save Path", style="dim")

    for name, path_str, is_def in aliases:
        def_mark = "★" if is_def else ""
        table.add_row(name, def_mark, path_str)
    console.print(table)
    return 0


def _handle_alias_add(args: argparse.Namespace, cfg: ConfigManager) -> int:
    try:
        resolved = cfg.add_alias(args.name, args.path, set_default=args.default)
        console.print(f"[green]✓ Registered alias[/green] '[bold cyan]{args.name}[/bold cyan]' -> {resolved}")
        return 0
    except (FileNotFoundError, ValueError, OSError) as e:
        console.print(f"[red]Error:[/red] {e}")
        return 1


def _handle_alias_remove(args: argparse.Namespace, cfg: ConfigManager) -> int:
    if cfg.remove_alias(args.name):
        console.print(f"[green]✓ Removed alias[/green] '{args.name}'")
        return 0
    console.print(f"[red]Error:[/red] Alias '{args.name}' not found.")
    return 1


def _handle_alias_set_default(args: argparse.Namespace, cfg: ConfigManager) -> int:
    try:
        cfg.set_default(args.name)
        console.print(f"[green]✓ Set default dynasty to[/green] '{args.name}'")
        return 0
    except (KeyError, OSError) as e:
        console.print(f"[red]Error:[/red] {e}")
        return 1


def _handle_alias_scan(cfg: ConfigManager) -> int:
    console.print("[bold]Scanning system for NCAA 14 dynasty saves...[/bold]")
    found = find_dynasty_saves(config=cfg)
    if not found:
        console.print("[yellow]No dynasty saves found in standard locations.[/yellow]")
        return 0

    table = Table(title=f"[bold]Discovered Dynasty Saves ({len(found)} found)[/bold]")
    table.add_column("#", justify="center", style="bold yellow", width=4)
    table.add_column("Folder Name", style="bold white", width=26)
    table.add_column("Location / Path", style="dim", width=45)
    table.add_column("Last Modified", style="cyan", width=20)
    table.add_column("Status", justify="center")

    for idx, s in enumerate(found, start=1):
        status = f"[green]Aliased as '{s.alias_name}'[/green]" if s.is_aliased else "[yellow]Unmapped[/yellow]"
        mtime_str = s.last_modified.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        short_path = str(s.usr_data_path).replace(str(Path.home()), "~")
        table.add_row(str(idx), s.folder_name, short_path, mtime_str, status)

    console.print(table)

    unmapped = [s for s in found if not s.is_aliased]
    if (
        unmapped
        and sys.stdin.isatty()
        and Confirm.ask("\nWould you like to register an alias for one of the unmapped saves?")
    ):
        choice_str = Prompt.ask("Enter number to alias", choices=[str(i) for i in range(1, len(found) + 1)])
        selected = found[int(choice_str) - 1]
        suggested_name = selected.folder_name.replace("BLUS31159-DYNASTY-", "").lower() or "dynasty"
        alias_name = Prompt.ask("Enter alias name", default=suggested_name)
        cfg.add_alias(alias_name, selected.usr_data_path, set_default=True)
        console.print(f"[green]✓ Successfully registered '{alias_name}' as default dynasty![/green]")

    return 0


def handle_alias_commands(args: argparse.Namespace, cfg: ConfigManager) -> int:
    """Dispatches alias management subcommands."""
    sub = args.alias_action
    if sub == "list":
        return _handle_alias_list(cfg)
    if sub == "add":
        return _handle_alias_add(args, cfg)
    if sub == "remove":
        return _handle_alias_remove(args, cfg)
    if sub == "set-default":
        return _handle_alias_set_default(args, cfg)
    if sub in ("scan", "discover"):
        return _handle_alias_scan(cfg)
    return 0


# -----------------------------------------------------------------------------
# Rules Subcommands
# -----------------------------------------------------------------------------


def _handle_rules_export(args: argparse.Namespace, cfg: ConfigManager) -> int:
    dest = args.destination or cfg.get_default_rules_path()
    try:
        exported_path = export_default_ranking_config(dest)
        console.print(f"[green]✓ Exported default ranking rules to:[/green] {exported_path}")
        return 0
    except OSError as e:
        console.print(f"[red]Error exporting ranking rules:[/red] {e}")
        return 1


def _handle_rules_validate(args: argparse.Namespace, cfg: ConfigManager) -> int:
    target = Path(args.path).expanduser().resolve() if args.path else cfg.get_default_rules_path()
    try:
        load_ranking_config(target)
        console.print(f"[green]✓ Ranking rules file is valid:[/green] {target}")
        return 0
    except (ValueError, FileNotFoundError, OSError) as e:
        console.print(f"[red]Error validating ranking rules:[/red] {e}")
        return 1


def _handle_rules_describe(args: argparse.Namespace) -> int:
    all_rules = get_all_rules_metadata()
    query = args.parameter.strip().lower() if args.parameter else ""
    if query:
        filtered = [
            r
            for r in all_rules
            if query in r["name"].lower() or query in r["section"].lower() or query in r["full_name"].lower()
        ]
        if not filtered:
            console.print(f"[yellow]No rules found matching query '[bold]{query}[/bold]'.[/yellow]")
            return 0
    else:
        filtered = all_rules

    table = Table(title="[bold gold1]Ranking Engine & Poll Rule Descriptions[/bold gold1]", box=box.ROUNDED)
    table.add_column("Rule Name", style="bold cyan", width=34)
    table.add_column("Section", style="magenta", width=10)
    table.add_column("Default", justify="right", style="green", width=12)
    table.add_column("Description", style="white")

    for r in filtered:
        val_str = str(r["default"])
        if isinstance(r["default"], (set, dict)):
            val_str = f"({len(r['default'])} items)"
        table.add_row(r["name"], r["section"], val_str, r["description"])

    console.print(table)
    return 0


def _handle_rules_show(args: argparse.Namespace, cfg: ConfigManager) -> int:
    try:
        if getattr(args, "defaults", False):
            config = load_ranking_config(None)
            console.print("[dim]Displaying built-in default ranking rules:[/dim]")
        else:
            config, active_path = cfg.load_rules()
            if active_path:
                console.print(f"[dim]Displaying active rules from: {active_path}[/dim]")
            else:
                console.print("[dim]Displaying active rules (using built-in defaults; no rules.json found):[/dim]")

        if getattr(args, "descriptions", False):
            all_rules = get_all_rules_metadata()
            table = Table(title="[bold gold1]Active Ranking Rules & Descriptions[/bold gold1]", box=box.ROUNDED)
            table.add_column("Rule Name", style="bold cyan", width=34)
            table.add_column("Section", style="magenta", width=10)
            table.add_column("Active Value", justify="right", style="green", width=12)
            table.add_column("Description", style="white")

            for r in all_rules:
                sec_obj = getattr(config, r["section"])
                active_val = getattr(sec_obj, r["name"])
                val_str = str(active_val)
                if isinstance(active_val, (set, dict)):
                    val_str = f"({len(active_val)} items)"
                table.add_row(r["name"], r["section"], val_str, r["description"])

            console.print(table)
            return 0

        json_str = config.model_dump_json(indent=2)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
        console.print(syntax)
        return 0
    except (ValueError, FileNotFoundError, OSError) as e:
        console.print(f"[red]Error reading rules:[/red] {e}")
        return 1


def handle_rules_commands(args: argparse.Namespace, cfg: ConfigManager) -> int:
    """Dispatches ranking rules management subcommands."""
    sub = args.rules_action
    if sub == "path":
        console.print(str(cfg.get_default_rules_path()))
        return 0
    if sub == "export":
        return _handle_rules_export(args, cfg)
    if sub == "validate":
        return _handle_rules_validate(args, cfg)
    if sub == "describe":
        return _handle_rules_describe(args)
    if sub == "show":
        return _handle_rules_show(args, cfg)
    return 0


def handle_docs_command(args: argparse.Namespace) -> int:
    """Displays or opens the official documentation website."""
    console.print(f"[bold cyan]Documentation:[/bold cyan] {DOCS_URL}")
    if getattr(args, "open", False):
        import webbrowser

        webbrowser.open(DOCS_URL)
        console.print("[dim]Opened documentation in web browser.[/dim]")
    return 0


# -----------------------------------------------------------------------------
# Re-ranking Pipeline Core
# -----------------------------------------------------------------------------


def resolve_target_save_path(args: argparse.Namespace, cfg: ConfigManager) -> Path:
    """Resolves save path from CLI argument or alias configuration."""
    if args.save_path:
        save_path = Path(args.save_path).expanduser().resolve()
        if save_path.is_dir():
            save_path = save_path / "USR-DATA"
        return save_path
    return cfg.resolve_save_path(args.dynasty)


def build_team_poll_updates(
    cfp_poll: list[PollRanking],
    ap_poll: list[PollRanking],
    coaches_poll: list[PollRanking],
    cfp_active: bool,
) -> list[dict[str, Any]]:
    """Constructs database update dictionaries for all three polls."""
    updates: dict[int, dict[str, Any]] = {}

    if cfp_active:
        for r in cfp_poll:
            u = updates.setdefault(r.team.tgid, {})
            u["cfp_rank"] = r.rank
            u["cfp_prev_rank"] = r.previous_rank

    for r in ap_poll:
        u = updates.setdefault(r.team.tgid, {})
        u["ap_rank"] = r.rank
        u["ap_prev_rank"] = r.previous_rank
        u["ap_points"] = r.points
        u["ap_first_votes"] = r.first_place_votes

    for r in coaches_poll:
        u = updates.setdefault(r.team.tgid, {})
        u["coaches_rank"] = r.rank
        u["coaches_prev_rank"] = r.previous_rank
        u["coaches_points"] = r.points
        u["coaches_first_votes"] = r.first_place_votes

    return [{"tgid": tgid, **fields} for tgid, fields in updates.items()]


def execute_rerank(args: argparse.Namespace, cfg: ConfigManager) -> int:
    """Executes the full re-ranking workflow on the target dynasty save."""
    # 1. Load ranking rules
    try:
        ranking_config, active_rules_path = cfg.load_rules(args.rules)
    except (ValueError, FileNotFoundError, OSError) as e:
        console.print(f"[red]Error loading ranking rules:[/red] {e}")
        return 1

    # 2. Locate save file
    try:
        save_path = resolve_target_save_path(args, cfg)
    except (KeyError, FileNotFoundError, ValueError) as e:
        console.print(f"[red]Error finding save file:[/red] {e}")
        console.print("Run [bold cyan]ncaa-dynasty-rerank alias scan[/bold cyan] to discover and configure your save.")
        return 1

    if not save_path.exists():
        console.print(f"[red]Error:[/red] Save file does not exist at: {save_path}")
        return 1

    console.print(Panel(f"[bold green]Loading save:[/bold green] {save_path}", border_style="cyan"))

    # 3. Parse TDB tables
    try:
        tdb = TDBFile(save_path)
        raw_teams = tdb.get_teams()
        raw_games = tdb.get_schedule()
    except (ValueError, OSError) as e:
        console.print(f"[red]Failed to parse save file:[/red] {e}")
        return 1

    teams = [TeamRecord(**t) for t in raw_teams]
    games = [GameRecord(**g) for g in raw_games]
    console.print(
        f"Loaded [bold cyan]{len(teams)}[/bold cyan] teams and [bold cyan]{len(games)}[/bold cyan] completed games."
    )
    if active_rules_path:
        console.print(f"[dim]Applying custom ranking rules from: {active_rules_path}[/dim]")

    # 4. Compute rankings
    engine = RankingEngine(teams, games, config=ranking_config)
    poll_gen = PollGenerator(engine, config=ranking_config)
    cfp_poll, ap_poll, coaches_poll = poll_gen.generate_all()

    cfp_active = any(t.cfp_rank > 0 for t in teams)
    if not cfp_active:
        console.print(
            "[dim yellow]ℹ Note: CFP/BCS poll is not yet active in this dynasty week (TBRK=0). "
            "Preserving inactive state to prevent premature poll activation.[/dim yellow]\n"
        )

    # 5. Postseason bowl synchronization
    all_schd_records = tdb.get_all_schedule_records()
    postseason_syncer = PostseasonSyncer()
    bowl_sync_result = None

    if cfp_active and postseason_syncer.is_bowl_season(all_schd_records):
        teams_by_tgid = {t.tgid: t for t in teams}
        bowl_sync_result = postseason_syncer.sync_major_bowls(all_schd_records, cfp_poll, teams_by_tgid)

    # 6. Preview proposed adjustments
    console.print("\n[bold underline]PROPOSED RANKINGS[/bold underline]\n")
    display_poll_table("College Football Playoff (CFP) Rankings", cfp_poll, "cfp")
    display_poll_table("Associated Press (AP) Top 25 Poll", ap_poll, "ap")
    display_poll_table("USA Today Coaches Poll", coaches_poll, "coaches")

    if bowl_sync_result and bowl_sync_result.diffs:
        display_bowl_diffs(bowl_sync_result.diffs)

    if args.dry_run:
        console.print("\n[bold yellow]Dry-run mode active. No changes written to save file.[/bold yellow]")
        return 0

    # 7. User confirmation
    confirm_msg = (
        "Apply these rankings and bowl updates to your save file?"
        if (bowl_sync_result and bowl_sync_result.updates)
        else "Apply these rankings to your save file?"
    )
    if not args.yes and not Confirm.ask(confirm_msg):
        console.print("[dim]Aborted by user. Save file unchanged.[/dim]")
        return 0

    # 8. Create safety backup & persist updates
    backup_file = create_backup(save_path)
    console.print(f"[green]✓ Created backup:[/green] {backup_file}")

    update_payload = build_team_poll_updates(cfp_poll, ap_poll, coaches_poll, cfp_active)
    tdb.update_team_polls(update_payload)
    if bowl_sync_result and bowl_sync_result.updates:
        tdb.update_schedule_games(bowl_sync_result.updates)
    tdb.save()

    console.print("[bold green]✓ Successfully applied new rankings to save file![/bold green]")
    console.print("[dim]You can now launch NCAA Football 14 to see your updated rankings.[/dim]")
    return 0


# -----------------------------------------------------------------------------
# Parser Construction and Entry Point
# -----------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Builds the top-level argument parser and subcommands."""
    parser = argparse.ArgumentParser(
        prog="ncaa-dynasty-rerank",
        description="Automated CFP, AP, and Coaches poll re-ranking engine for NCAA Football 14 saves.",
        epilog=f"Documentation: {DOCS_URL}",
    )
    parser.add_argument("-d", "--dynasty", help="Dynasty alias name to use (configured via 'alias' command)")
    parser.add_argument("-s", "--save-path", help="Direct path to save directory or USR-DATA file")
    parser.add_argument("-r", "--rules", help="Path to custom ranking rules JSON file")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview proposed rankings without modifying the save file"
    )
    parser.add_argument(
        "-y", "--yes", action="store_true", help="Automatically apply changes without confirmation prompt"
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommands")

    # alias subcommand
    alias_parser = subparsers.add_parser("alias", help="Manage dynasty save aliases")
    alias_sub = alias_parser.add_subparsers(dest="alias_action", required=True)
    alias_sub.add_parser("list", help="List registered dynasty aliases")

    add_parser = alias_sub.add_parser("add", help="Add a new dynasty alias")
    add_parser.add_argument("name", help="Friendly alias name (e.g. 'wvu')")
    add_parser.add_argument("path", help="Path to dynasty folder or USR-DATA")
    add_parser.add_argument("--default", action="store_true", help="Set as default dynasty")

    set_def_parser = alias_sub.add_parser("set-default", help="Set default dynasty alias")
    set_def_parser.add_argument("name", help="Alias name to set as default")

    rem_parser = alias_sub.add_parser("remove", help="Remove an alias")
    rem_parser.add_argument("name", help="Alias name to remove")

    alias_sub.add_parser("scan", help="Scan system for dynasty saves and prompt to map them")
    alias_sub.add_parser("discover", help="Alias for scan")

    # rules subcommand
    rules_parser = subparsers.add_parser("rules", help="Manage and inspect ranking calculation rules")
    rules_sub = rules_parser.add_subparsers(dest="rules_action", required=True)
    rules_sub.add_parser("path", help="Print default rules file path")

    export_parser = rules_sub.add_parser("export", help="Export default rules JSON")
    export_parser.add_argument(
        "destination", nargs="?", help="Output path (defaults to ~/.config/ncaa-dynasty-rerank/rules.json)"
    )

    show_parser = rules_sub.add_parser("show", help="Display current active rules")
    show_parser.add_argument(
        "--defaults", action="store_true", help="Show built-in default rules instead of active overrides"
    )
    show_parser.add_argument(
        "-d", "--descriptions", action="store_true", help="Display tabular view with parameter descriptions"
    )

    desc_parser = rules_sub.add_parser(
        "describe", help="Display descriptions and defaults for ranking calculation rules"
    )
    desc_parser.add_argument("parameter", nargs="?", help="Optional parameter or section name to filter by")

    validate_parser = rules_sub.add_parser("validate", help="Validate a rules JSON file")
    validate_parser.add_argument(
        "path", nargs="?", help="Path to rules file to validate (defaults to ~/.config/ncaa-dynasty-rerank/rules.json)"
    )

    # docs subcommand
    docs_parser = subparsers.add_parser("docs", help="Display or open official documentation website")
    docs_parser.add_argument("-o", "--open", action="store_true", help="Open documentation in the default web browser")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    cfg = ConfigManager()

    if args.subcommand == "alias":
        return handle_alias_commands(args, cfg)
    if args.subcommand == "rules":
        return handle_rules_commands(args, cfg)
    if args.subcommand == "docs":
        return handle_docs_command(args)

    return execute_rerank(args, cfg)


if __name__ == "__main__":
    sys.exit(main())
