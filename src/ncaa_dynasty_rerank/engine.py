"""Core resume evaluation, strength of schedule, and ranking engine."""

import math

from ncaa_dynasty_rerank.config_rules import EngineConfig
from ncaa_dynasty_rerank.models import GameRecord, TeamRecord


class RankingEngine:
    """Calculates team resume scores and authentic college football rankings."""

    def __init__(
        self,
        teams: list[TeamRecord],
        games: list[GameRecord],
        config: EngineConfig | None = None,
    ):
        self.config = config or EngineConfig()
        self.teams_by_tgid: dict[int, TeamRecord] = {t.tgid: t for t in teams}
        self.games = games
        self._populate_game_history()

    def _populate_game_history(self) -> None:
        """Links games to team records idempotently without accumulation leaks."""
        # Reset collections on teams to avoid mutation leaks if re-initialized
        for team in self.teams_by_tgid.values():
            team.opponents = []
            team.wins_against = []
            team.losses_to = []

        for g in self.games:
            w_tgid = g.winner_tgid
            l_tgid = g.loser_tgid

            if w_tgid in self.teams_by_tgid:
                winner = self.teams_by_tgid[w_tgid]
                winner.opponents.append(l_tgid)
                winner.wins_against.append(l_tgid)

            if l_tgid in self.teams_by_tgid:
                loser = self.teams_by_tgid[l_tgid]
                loser.opponents.append(w_tgid)
                loser.losses_to.append(w_tgid)

    def calculate_conference_modifiers(self) -> dict[int, float]:
        """Calculates dynamic conference strength from non-conference win rates."""
        conf_games: dict[int, list[bool]] = {}
        for g in self.games:
            w_team = self.teams_by_tgid.get(g.winner_tgid)
            l_team = self.teams_by_tgid.get(g.loser_tgid)
            if not w_team or not l_team:
                continue

            if w_team.conf_id != l_team.conf_id:
                conf_games.setdefault(w_team.conf_id, []).append(True)
                conf_games.setdefault(l_team.conf_id, []).append(False)

        modifiers: dict[int, float] = {}
        for cid, base in self.config.conference_weights.items():
            results = conf_games.get(cid, [])
            if results:
                non_con_pct = sum(results) / len(results)
                modifiers[cid] = base * 0.70 + (0.75 + non_con_pct * 0.5) * 0.30
            else:
                modifiers[cid] = base
        return modifiers

    def calculate_sos(self, conf_modifiers: dict[int, float]) -> dict[int, float]:
        """Calculates Strength of Schedule (OWP and OOWP)."""
        owp: dict[int, float] = {}
        for tgid, team in self.teams_by_tgid.items():
            if not team.opponents:
                owp[tgid] = 0.50
                continue

            opp_win_pcts = []
            for opp_id in team.opponents:
                opp = self.teams_by_tgid.get(opp_id)
                if opp and opp.games_played > 0:
                    conf_weight = conf_modifiers.get(opp.conf_id, self.config.default_conf_weight)
                    adjusted_wins = opp.wins - (1 if tgid in opp.wins_against else 0)
                    adjusted_games = max(1, opp.games_played - 1)
                    opp_win_pcts.append((adjusted_wins / adjusted_games) * conf_weight)
                else:
                    opp_win_pcts.append(0.30)

            owp[tgid] = sum(opp_win_pcts) / len(opp_win_pcts)

        sos: dict[int, float] = {}
        for tgid, team in self.teams_by_tgid.items():
            if not team.opponents:
                sos[tgid] = owp.get(tgid, 0.50)
                continue

            oowp_vals = [owp.get(opp_id, 0.50) for opp_id in team.opponents]
            oowp = sum(oowp_vals) / len(oowp_vals)
            composite_sos = (owp[tgid] * 2.0 + oowp) / 3.0
            sos[tgid] = composite_sos
            team.sos_score = composite_sos

        return sos

    def calculate_game_value(
        self,
        team_id: int,
        game: GameRecord,
        sos_scores: dict[int, float],
        conf_modifiers: dict[int, float],
    ) -> float:
        """Calculates the resume points awarded for an individual game."""
        is_winner = game.winner_tgid == team_id
        opp_id = game.loser_tgid if is_winner else game.winner_tgid
        opp = self.teams_by_tgid.get(opp_id)

        opp_conf = opp.conf_id if opp else 17
        conf_mod = conf_modifiers.get(opp_conf, self.config.default_conf_weight)
        opp_win_pct = opp.win_pct if opp else 0.25
        opp_sos = sos_scores.get(opp_id, 0.50)

        # Margin diminishing returns
        eff_margin = min(self.config.margin_cap, game.margin)
        margin_factor = math.pow(eff_margin, self.config.margin_power) * self.config.margin_multiplier

        # Location context
        is_road = game.away_tgid == team_id
        location_bonus = self.config.road_win_bonus if is_road else 0.0

        if is_winner:
            base = self.config.win_base
            quality = (opp_win_pct * 14.0 + opp_sos * 10.0) * conf_mod
            if opp_conf in (17, 24) or opp_win_pct < 0.35:
                quality = min(quality, 4.0)

            return base + quality + margin_factor + location_bonus
        else:
            base_loss = self.config.loss_base
            loss_mitigation = (opp_win_pct * 8.0 + opp_sos * 6.0) * conf_mod
            home_loss_penalty = -self.config.home_loss_penalty if not is_road else 0.0
            margin_penalty = -margin_factor * 0.70

            return base_loss + loss_mitigation + margin_penalty + home_loss_penalty

    def evaluate_resumes(self) -> list[TeamRecord]:
        """Calculates overall resume score for every team in the FBS."""
        conf_modifiers = self.calculate_conference_modifiers()
        sos_scores = self.calculate_sos(conf_modifiers)

        for tgid, team in self.teams_by_tgid.items():
            if team.conf_id in (17, 24):
                team.resume_score = -999.0
                continue

            team_games = [g for g in self.games if g.away_tgid == tgid or g.home_tgid == tgid]
            if not team_games:
                team.resume_score = 50.0 + (team.wins * 10.0) - (team.losses * 15.0)
                continue

            game_vals = [self.calculate_game_value(tgid, g, sos_scores, conf_modifiers) for g in team_games]

            avg_game_val = sum(game_vals) / len(game_vals)

            # Bye-week neutral performance is anchored directly to average game quality
            normalized_performance = avg_game_val

            # Quality wins normalized by games played for bye-week neutrality
            q_wins = sum(
                1
                for opp_id in team.wins_against
                if self.teams_by_tgid.get(opp_id) and self.teams_by_tgid[opp_id].win_pct >= 0.50
            )
            team.quality_wins = q_wins
            q_win_rate = q_wins / max(1, team.games_played)

            loss_penalty = team.losses * 8.5
            win_pct_component = (team.win_pct * 30.0) + 35.0 - loss_penalty

            resume_score = (
                win_pct_component + (normalized_performance * 2.2) + (team.sos_score * 32.0) + (q_win_rate * 22.0)
            )

            team.resume_score = round(resume_score, 2)

        return list(self.teams_by_tgid.values())

    def apply_head_to_head_adjustments(self, ranked_teams: list[TeamRecord]) -> list[TeamRecord]:
        """Enforces H2H winners ahead of losers for identical records and close resumes."""
        ranked = list(ranked_teams)
        n = len(ranked)

        # Bubble adjustments for adjacent teams
        for _ in range(3):
            changed = False
            for i in range(n - 1):
                t1 = ranked[i]
                t2 = ranked[i + 1]

                h2h_game = next(
                    (g for g in self.games if (g.winner_tgid == t2.tgid and g.loser_tgid == t1.tgid)),
                    None,
                )

                if h2h_game and (
                    t2.losses == t1.losses
                    or (
                        t2.losses == t1.losses + 1
                        and (t1.resume_score - t2.resume_score) < self.config.h2h_loss_threshold
                    )
                ):
                    ranked[i], ranked[i + 1] = t2, t1
                    changed = True

            if not changed:
                break

        return ranked
