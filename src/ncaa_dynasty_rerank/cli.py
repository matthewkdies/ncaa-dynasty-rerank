"""Command-line interface for ncaa-dynasty-rerank."""

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ncaa_dynasty_rerank.config import ConfigManager
from ncaa_dynasty_rerank.discover import find_dynasty_saves
from ncaa_dynasty_rerank.engine import RankingEngine
from ncaa_dynasty_rerank.models import GameRecord, PollRanking, TeamRecord
from ncaa_dynasty_rerank.polls import PollGenerator
from ncaa_dynasty_rerank.postseason import PostseasonSyncer
from ncaa_dynasty_rerank.tdb import TDBFile

console = Console()


def render_movement(current: int, proposed: int) -> str:
    """Formats movement string with colors."""
    if current == 0 or current > 25:
        return "[bold cyan]NEW[/bold cyan]"
    diff = current - proposed
    if diff > 0:
        return f"[bold green]▲ +{diff}[/bold green]"
    elif diff < 0:
        return f"[bold red]▼ {diff}[/bold red]"
    else:
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

    if poll_type == "ap" or poll_type == "coaches":
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


def handle_alias_commands(args: argparse.Namespace, cfg: ConfigManager) -> int:
    """Dispatches alias management subcommands."""
    sub = args.alias_action

    if sub == "list":
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

    elif sub == "add":
        try:
            resolved = cfg.add_alias(args.name, args.path, set_default=args.default)
            console.print(f"[green]✓ Registered alias[/green] '[bold cyan]{args.name}[/bold cyan]' -> {resolved}")
            return 0
        except (FileNotFoundError, ValueError, OSError) as e:
            console.print(f"[red]Error:[/red] {e}")
            return 1

    elif sub == "remove":
        if cfg.remove_alias(args.name):
            console.print(f"[green]✓ Removed alias[/green] '{args.name}'")
            return 0
        console.print(f"[red]Error:[/red] Alias '{args.name}' not found.")
        return 1

    elif sub == "set-default":
        try:
            cfg.set_default(args.name)
            console.print(f"[green]✓ Set default dynasty to[/green] '{args.name}'")
            return 0
        except (KeyError, OSError) as e:
            console.print(f"[red]Error:[/red] {e}")
            return 1

    elif sub in ("scan", "discover"):
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

    return 0


def create_backup(save_path: Path) -> Path:
    """Creates a timestamped backup before modifying the save file."""
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
    backup_name = f"USR-DATA.bak.{timestamp}"
    backup_path = save_path.parent / backup_name
    shutil.copyfile(save_path, backup_path)
    return backup_path


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="ncaa-dynasty-rerank",
        description="Automated CFP, AP, and Coaches poll re-ranking engine for NCAA Football 14 saves.",
    )
    parser.add_argument("-d", "--dynasty", help="Dynasty alias name to use (configured via 'alias' command)")
    parser.add_argument("-s", "--save-path", help="Direct path to save directory or USR-DATA file")
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

    args = parser.parse_args()
    cfg = ConfigManager()

    if args.subcommand == "alias":
        return handle_alias_commands(args, cfg)

    # Re-ranking flow
    try:
        if args.save_path:
            save_path = Path(args.save_path).expanduser().resolve()
            if save_path.is_dir():
                save_path = save_path / "USR-DATA"
        else:
            save_path = cfg.resolve_save_path(args.dynasty)
    except (KeyError, FileNotFoundError, ValueError) as e:
        console.print(f"[red]Error finding save file:[/red] {e}")
        console.print("Run [bold cyan]ncaa-dynasty-rerank alias scan[/bold cyan] to discover and configure your save.")
        return 1

    if not save_path.exists():
        console.print(f"[red]Error:[/red] Save file does not exist at: {save_path}")
        return 1

    console.print(Panel(f"[bold green]Loading save:[/bold green] {save_path}", border_style="cyan"))

    # Load TDB
    try:
        tdb = TDBFile(save_path)
        raw_teams = tdb.get_teams()
        raw_games = tdb.get_schedule()
    except (ValueError, OSError) as e:
        console.print(f"[red]Failed to parse save file:[/red] {e}")
        return 1

    # Convert to models
    teams = [TeamRecord(**t) for t in raw_teams]
    games = [GameRecord(**g) for g in raw_games]

    console.print(
        f"Loaded [bold cyan]{len(teams)}[/bold cyan] teams and [bold cyan]{len(games)}[/bold cyan] completed games."
    )

    # Run engine & generate polls
    engine = RankingEngine(teams, games)
    poll_gen = PollGenerator(engine)
    cfp_poll, ap_poll, coaches_poll = poll_gen.generate_all()

    cfp_active = any(t.cfp_rank > 0 for t in teams)
    if not cfp_active:
        console.print(
            "[dim yellow]ℹ Note: CFP/BCS poll is not yet active in this dynasty week (TBRK=0). "
            "Preserving inactive state to prevent premature poll activation.[/dim yellow]\n"
        )

    # Postseason bowl synchronization
    all_schd_records = tdb.get_all_schedule_records()
    postseason_syncer = PostseasonSyncer()
    bowl_sync_result = None

    if cfp_active and postseason_syncer.is_bowl_season(all_schd_records):
        teams_by_tgid = {t.tgid: t for t in teams}
        bowl_sync_result = postseason_syncer.sync_major_bowls(all_schd_records, cfp_poll, teams_by_tgid)

    # Display Top 25 tables
    console.print("\n[bold underline]PROPOSED RANKINGS[/bold underline]\n")
    display_poll_table("College Football Playoff (CFP) Rankings", cfp_poll, "cfp")
    display_poll_table("Associated Press (AP) Top 25 Poll", ap_poll, "ap")
    display_poll_table("USA Today Coaches Poll", coaches_poll, "coaches")

    if bowl_sync_result and bowl_sync_result.diffs:
        console.print("\n[bold underline]PROPOSED BOWL MATCHUP UPDATES[/bold underline]\n")
        bowl_table = Table(title="Postseason Bowl Adjustments", box=box.ROUNDED)
        bowl_table.add_column("Bowl Game", style="cyan", no_wrap=True)
        bowl_table.add_column("Previous Matchup", style="dim")
        bowl_table.add_column("New Matchup", style="bold green")
        bowl_table.add_column("Reason", style="yellow")
        for d in bowl_sync_result.diffs:
            bowl_table.add_row(d.bowl_name, d.old_matchup, d.new_matchup, d.reason)
        console.print(bowl_table)

    if args.dry_run:
        console.print("\n[bold yellow]Dry-run mode active. No changes written to save file.[/bold yellow]")
        return 0

    # Confirmation
    confirm_msg = (
        "Apply these rankings and bowl updates to your save file?"
        if (bowl_sync_result and bowl_sync_result.updates)
        else "Apply these rankings to your save file?"
    )
    if not args.yes and not Confirm.ask(confirm_msg):
        console.print("[dim]Aborted by user. Save file unchanged.[/dim]")
        return 0

    # Safety: Create backup
    backup_file = create_backup(save_path)
    console.print(f"[green]✓ Created backup:[/green] {backup_file}")

    # Prepare update payload
    updates_by_tgid = {}
    if cfp_active:
        for r in cfp_poll:
            u = updates_by_tgid.setdefault(r.team.tgid, {})
            u["cfp_rank"] = r.rank
            u["cfp_prev_rank"] = r.previous_rank

    for r in ap_poll:
        u = updates_by_tgid.setdefault(r.team.tgid, {})
        u["ap_rank"] = r.rank
        u["ap_prev_rank"] = r.previous_rank
        u["ap_points"] = r.points
        u["ap_first_votes"] = r.first_place_votes

    for r in coaches_poll:
        u = updates_by_tgid.setdefault(r.team.tgid, {})
        u["coaches_rank"] = r.rank
        u["coaches_prev_rank"] = r.previous_rank
        u["coaches_points"] = r.points
        u["coaches_first_votes"] = r.first_place_votes

    update_list = [{"tgid": tgid, **fields} for tgid, fields in updates_by_tgid.items()]

    tdb.update_team_polls(update_list)
    if bowl_sync_result and bowl_sync_result.updates:
        tdb.update_schedule_games(bowl_sync_result.updates)
    tdb.save()

    console.print("[bold green]✓ Successfully applied new rankings to save file![/bold green]")
    console.print("[dim]You can now launch NCAA Football 14 to see your updated rankings.[/dim]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
