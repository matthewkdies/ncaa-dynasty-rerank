"""Postseason bowl synchronization engine for NCAA Football 14 dynasties."""

from dataclasses import dataclass
from typing import Any

from ncaa_dynasty_rerank.models import PollRanking, TeamRecord

BOWL_NAMES: dict[int, str] = {
    40: "CFP National Championship",
    37: "Capital One Orange Bowl",
    36: "Goodyear Cotton Bowl",
    35: "Allstate Sugar Bowl",
    34: "Vrbo Fiesta Bowl",
    32: "Rose Bowl",
    31: "Cheez-It Citrus Bowl",
    30: "ReliaQuest Bowl",
    29: "Servpro First Responder Bowl",
    28: "Chick-fil-A Peach Bowl",
    27: "AutoZone Liberty Bowl",
    26: "TransPerfect Music City Bowl",
    25: "Tony the Tiger Sun Bowl",
    24: "Guaranteed Rate Bowl",
    23: "Valero Alamo Bowl",
    22: "LA Bowl",
    21: "Lockheed Armed Forces Bowl",
    20: "TaxAct Texas Bowl",
    19: "Radiance Independence Bowl",
    18: "Pop-Tarts Bowl",
    17: "SDCCU Holiday Bowl",
    16: "Duke's Mayo Bowl",
    15: "Military Bowl",
    14: "Quick Lane Bowl",
    13: "EasyPost Hawai'i Bowl",
    12: "R+L Carriers New Orleans Bowl",
    11: "SRS Las Vegas Bowl",
    10: "Union Home Gasparilla Bowl",
    9: "Barstool Arizona Bowl",
    8: "Famous Idaho Potato Bowl",
    7: "New Mexico Bowl",
}


@dataclass
class BowlDiff:
    """Represents a human-readable change to a bowl game matchup."""

    bowl_name: str
    old_matchup: str
    new_matchup: str
    reason: str


@dataclass
class BowlSyncResult:
    """Result of postseason bowl synchronization containing updates and diffs."""

    updates: list[dict[str, Any]]
    diffs: list[BowlDiff]


class PostseasonSyncer:
    """Synchronizes postseason bowl games with CFP rankings."""

    def __init__(self, bowl_names: dict[int, str] | None = None):
        self.bowl_names = bowl_names or BOWL_NAMES

    def get_bowl_name(self, sgnm: int) -> str:
        """Returns the friendly name for a bowl game number."""
        return self.bowl_names.get(sgnm, f"Bowl (SGNM {sgnm})")

    def is_bowl_season(self, games_or_records: list[dict[str, Any]]) -> bool:
        """Determines if the save is currently in Bowl Season with unplayed bowl games."""
        for g in games_or_records:
            sewt = g.get("sewt", 0)
            sewn = g.get("sewn", 0)
            gsta = g.get("status") if "status" in g else g.get("gsta", 0)
            away_score = g.get("away_score", 0)
            home_score = g.get("home_score", 0)

            # In NCAA 14, bowl games occur in weeks with SEWT >= 30 and SEWN >= 17
            is_bowl_week = sewt >= 30 or sewn >= 17
            is_unplayed = gsta == 1 and away_score == 0 and home_score == 0

            if is_bowl_week and is_unplayed:
                return True
        return False

    def sync_major_bowls(
        self,
        schd_records: list[dict[str, Any]],
        cfp_rankings: list[PollRanking],
        teams_by_tgid: dict[int, TeamRecord],
    ) -> BowlSyncResult:
        """Synchronizes the National Championship and major bowls with the new CFP rankings."""
        if not cfp_rankings or len(cfp_rankings) < 2:
            return BowlSyncResult(updates=[], diffs=[])

        target_rank1_tgid = cfp_rankings[0].team.tgid
        target_rank2_tgid = cfp_rankings[1].team.tgid

        # Find all unplayed bowl games in SCHD
        bowl_games: list[dict[str, Any]] = []
        for g in schd_records:
            sewt = g.get("sewt", 0)
            sewn = g.get("sewn", 0)
            gsta = g.get("gsta", 0)
            away_score = g.get("away_score", 0)
            home_score = g.get("home_score", 0)

            if (sewt >= 30 or sewn >= 17) and gsta == 1 and away_score == 0 and home_score == 0:
                bowl_games.append(g)

        if not bowl_games:
            return BowlSyncResult(updates=[], diffs=[])

        # Locate the National Championship Game (SGNM 40)
        natty_game = next((g for g in bowl_games if g.get("sgnm") == 40), None)
        if not natty_game:
            return BowlSyncResult(updates=[], diffs=[])

        current_natty_home = natty_game.get("ghtg", 0)
        current_natty_away = natty_game.get("gatg", 0)

        # Check if already aligned: CFP #1 as Home, CFP #2 as Away
        if current_natty_home == target_rank1_tgid and current_natty_away == target_rank2_tgid:
            return BowlSyncResult(updates=[], diffs=[])

        # If aligned but reversed:
        if current_natty_home == target_rank2_tgid and current_natty_away == target_rank1_tgid:
            updates = [
                {
                    "record_index": natty_game["record_index"],
                    "away_tgid": target_rank2_tgid,
                    "home_tgid": target_rank1_tgid,
                }
            ]
            t1_name = teams_by_tgid.get(target_rank1_tgid)
            t2_name = teams_by_tgid.get(target_rank2_tgid)
            t1_str = t1_name.full_name if t1_name else f"TGID {target_rank1_tgid}"
            t2_str = t2_name.full_name if t2_name else f"TGID {target_rank2_tgid}"
            diffs = [
                BowlDiff(
                    bowl_name=self.get_bowl_name(40),
                    old_matchup=f"{t1_str} @ {t2_str}",
                    new_matchup=f"{t2_str} @ {t1_str}",
                    reason="Corrected home/away seeding (CFP #1 hosts)",
                )
            ]
            return BowlSyncResult(updates=updates, diffs=diffs)

        updates: list[dict[str, Any]] = []
        diffs: list[BowlDiff] = []

        # We need Home = target_rank1_tgid, Away = target_rank2_tgid in Natty
        # Track pending updates to games
        game_updates_by_idx: dict[int, dict[str, int]] = {}

        def get_team_str(tgid: int) -> str:
            t = teams_by_tgid.get(tgid)
            return t.full_name if t else f"TGID {tgid}"

        # 1. Align Home Team (CFP #1)
        displaced_home = None
        if current_natty_home != target_rank1_tgid:
            displaced_home = current_natty_home
            # Find where target_rank1_tgid is currently scheduled
            orig_game = next(
                (
                    g
                    for g in bowl_games
                    if g.get("record_index") != natty_game["record_index"]
                    and (g.get("gatg") == target_rank1_tgid or g.get("ghtg") == target_rank1_tgid)
                ),
                None,
            )
            game_updates_by_idx.setdefault(natty_game["record_index"], {})["home_tgid"] = target_rank1_tgid

            if orig_game:
                orig_idx = orig_game["record_index"]
                orig_sgnm = orig_game.get("sgnm", 0)
                is_away = orig_game.get("gatg") == target_rank1_tgid
                slot_key = "away_tgid" if is_away else "home_tgid"
                game_updates_by_idx.setdefault(orig_idx, {})[slot_key] = displaced_home

                old_orig_away = orig_game.get("gatg", 0)
                old_orig_home = orig_game.get("ghtg", 0)
                new_orig_away = displaced_home if is_away else old_orig_away
                new_orig_home = displaced_home if not is_away else old_orig_home

                diffs.append(
                    BowlDiff(
                        bowl_name=self.get_bowl_name(orig_sgnm),
                        old_matchup=f"{get_team_str(old_orig_away)} @ {get_team_str(old_orig_home)}",
                        new_matchup=f"{get_team_str(new_orig_away)} @ {get_team_str(new_orig_home)}",
                        reason=f"Displaced former Natty finalist {get_team_str(displaced_home)} takes vacated bowl slot",
                    )
                )

        # 2. Align Away Team (CFP #2)
        displaced_away = None
        if current_natty_away != target_rank2_tgid:
            displaced_away = current_natty_away
            orig_game = next(
                (
                    g
                    for g in bowl_games
                    if g.get("record_index") != natty_game["record_index"]
                    and (g.get("gatg") == target_rank2_tgid or g.get("ghtg") == target_rank2_tgid)
                ),
                None,
            )
            game_updates_by_idx.setdefault(natty_game["record_index"], {})["away_tgid"] = target_rank2_tgid

            if orig_game:
                orig_idx = orig_game["record_index"]
                orig_sgnm = orig_game.get("sgnm", 0)
                is_away = orig_game.get("gatg") == target_rank2_tgid
                slot_key = "away_tgid" if is_away else "home_tgid"
                game_updates_by_idx.setdefault(orig_idx, {})[slot_key] = displaced_away

                old_orig_away = orig_game.get("gatg", 0)
                old_orig_home = orig_game.get("ghtg", 0)
                new_orig_away = displaced_away if is_away else old_orig_away
                new_orig_home = displaced_away if not is_away else old_orig_home

                diffs.append(
                    BowlDiff(
                        bowl_name=self.get_bowl_name(orig_sgnm),
                        old_matchup=f"{get_team_str(old_orig_away)} @ {get_team_str(old_orig_home)}",
                        new_matchup=f"{get_team_str(new_orig_away)} @ {get_team_str(new_orig_home)}",
                        reason=f"Displaced former Natty finalist {get_team_str(displaced_away)} takes vacated bowl slot",
                    )
                )

        # Diff for the National Championship game itself
        old_natty_str = f"{get_team_str(current_natty_away)} @ {get_team_str(current_natty_home)}"
        new_natty_str = f"{get_team_str(target_rank2_tgid)} @ {get_team_str(target_rank1_tgid)}"
        diffs.insert(
            0,
            BowlDiff(
                bowl_name=self.get_bowl_name(40),
                old_matchup=old_natty_str,
                new_matchup=new_natty_str,
                reason="Aligned matchup to CFP #1 vs CFP #2",
            ),
        )

        for r_idx, fields in game_updates_by_idx.items():
            game_rec = next(g for g in bowl_games if g["record_index"] == r_idx)
            full_update = {
                "record_index": r_idx,
                "away_tgid": fields.get("away_tgid", game_rec.get("gatg")),
                "home_tgid": fields.get("home_tgid", game_rec.get("ghtg")),
            }
            updates.append(full_update)

        return BowlSyncResult(updates=updates, diffs=diffs)
