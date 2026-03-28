from __future__ import annotations
import os
import json
from datetime import datetime
from dataclasses import dataclass, field
from collections import Counter
from typing import Optional

from .cards import Card
from .engine import run_game
from .player import Player

LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")


@dataclass
class SimulationResult:
    deck1_name: str = ""
    deck2_name: str = ""
    total_games: int = 0
    wins: list[int] = field(default_factory=lambda: [0, 0])
    draws: int = 0
    total_turns: int = 0
    game_logs: list[list[str]] = field(default_factory=list)

    @property
    def win_rate_1(self) -> float:
        if self.total_games == 0:
            return 0
        return self.wins[0] / self.total_games * 100

    @property
    def win_rate_2(self) -> float:
        if self.total_games == 0:
            return 0
        return self.wins[1] / self.total_games * 100

    @property
    def avg_turns(self) -> float:
        if self.total_games == 0:
            return 0
        return self.total_turns / self.total_games

    def summary(self) -> str:
        lines = [
            f"\n{'='*60}",
            f"  {self.deck1_name} vs {self.deck2_name}",
            f"  {self.total_games} games played",
            f"{'='*60}",
            f"  {self.deck1_name}: {self.wins[0]} wins ({self.win_rate_1:.1f}%)",
            f"  {self.deck2_name}: {self.wins[1]} wins ({self.win_rate_2:.1f}%)",
            f"  Draws: {self.draws}",
            f"  Average turns: {self.avg_turns:.1f}",
            f"{'='*60}",
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "deck1": self.deck1_name,
            "deck2": self.deck2_name,
            "total_games": self.total_games,
            "deck1_wins": self.wins[0],
            "deck2_wins": self.wins[1],
            "draws": self.draws,
            "deck1_win_rate": round(self.win_rate_1, 1),
            "deck2_win_rate": round(self.win_rate_2, 1),
            "avg_turns": round(self.avg_turns, 1),
        }


def simulate(
    deck1: list[Card],
    deck2: list[Card],
    agent1: Player,
    agent2: Player,
    n_games: int = 100,
    deck1_name: str = "Deck 1",
    deck2_name: str = "Deck 2",
    verbose_game: Optional[int] = None,
    save_all_logs: bool = False,
) -> SimulationResult:
    result = SimulationResult(
        deck1_name=deck1_name,
        deck2_name=deck2_name,
        total_games=n_games,
    )

    for i in range(n_games):
        verbose = (verbose_game is not None and i == verbose_game)

        # Alternate who goes first
        if i % 2 == 0:
            state = run_game(deck1, deck2, agent1, agent2, verbose=verbose)
            if state.winner == 0:
                result.wins[0] += 1
            elif state.winner == 1:
                result.wins[1] += 1
            else:
                result.draws += 1
        else:
            state = run_game(deck2, deck1, agent2, agent1, verbose=verbose)
            if state.winner == 0:
                result.wins[1] += 1
            elif state.winner == 1:
                result.wins[0] += 1
            else:
                result.draws += 1

        result.total_turns += state.turn_number

        if save_all_logs:
            result.game_logs.append(list(state.turn_log))

    return result


def run_matchup_table(
    decks: dict[str, list[Card]],
    agent_factory,
    n_games: int = 50,
    save_logs: bool = False,
) -> dict[tuple[str, str], SimulationResult]:
    results = {}
    deck_names = list(decks.keys())

    for i, name1 in enumerate(deck_names):
        for j, name2 in enumerate(deck_names):
            if i >= j:
                continue
            print(f"  Simulating: {name1} vs {name2}...", end=" ", flush=True)
            result = simulate(
                decks[name1], decks[name2],
                agent_factory(), agent_factory(),
                n_games=n_games,
                deck1_name=name1,
                deck2_name=name2,
                save_all_logs=save_logs,
            )
            results[(name1, name2)] = result
            print(f"{result.win_rate_1:.0f}% - {result.win_rate_2:.0f}%")

    return results


def print_matchup_table(decks: dict, results: dict) -> str:
    """Print and return a formatted matchup table."""
    names = list(decks.keys())
    col_width = max(len(n) for n in names) + 2
    output_lines = []

    def out(line=""):
        print(line)
        output_lines.append(line)

    # Header
    header = " " * col_width
    for name in names:
        header += f"{name:>{col_width}}"
    out(f"\n{'='*len(header)}")
    out("  MATCHUP TABLE (Win % for row deck)")
    out(f"{'='*len(header)}")
    out(header)
    out("-" * len(header))

    # Win rates
    total_wins = {name: 0 for name in names}
    total_games = {name: 0 for name in names}

    for name1 in names:
        row = f"{name1:<{col_width}}"
        for name2 in names:
            if name1 == name2:
                row += f"{'---':>{col_width}}"
            elif (name1, name2) in results:
                r = results[(name1, name2)]
                row += f"{r.win_rate_1:>{col_width-1}.0f}%"
                total_wins[name1] += r.wins[0]
                total_wins[name2] += r.wins[1]
                total_games[name1] += r.total_games
                total_games[name2] += r.total_games
            elif (name2, name1) in results:
                r = results[(name2, name1)]
                row += f"{r.win_rate_2:>{col_width-1}.0f}%"
                total_wins[name1] += r.wins[1]
                total_wins[name2] += r.wins[0]
                total_games[name1] += r.total_games
                total_games[name2] += r.total_games
            else:
                row += f"{'N/A':>{col_width}}"
        out(row)

    out("-" * len(header))

    # Overall rankings
    out(f"\n{'='*40}")
    out("  OVERALL RANKINGS")
    out(f"{'='*40}")
    rankings = []
    for name in names:
        if total_games[name] > 0:
            wr = total_wins[name] / total_games[name] * 100
            rankings.append((name, wr, total_wins[name], total_games[name]))

    rankings.sort(key=lambda x: x[1], reverse=True)
    for rank, (name, wr, wins, games) in enumerate(rankings, 1):
        out(f"  #{rank} {name}: {wr:.1f}% ({wins}/{games})")
    out(f"{'='*40}")

    return "\n".join(output_lines)


def save_session_log(
    session_type: str,
    results: dict | SimulationResult,
    matchup_text: str = "",
    game_logs: list[list[str]] | None = None,
) -> str:
    """Save a complete session log to logs/ directory. Returns the log file path."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(LOGS_DIR, f"{session_type}_{timestamp}.log")
    json_path = os.path.join(LOGS_DIR, f"{session_type}_{timestamp}.json")

    # Build JSON data
    json_data = {
        "timestamp": datetime.now().isoformat(),
        "session_type": session_type,
    }

    if isinstance(results, dict):
        # Matchup table results
        json_data["matchups"] = {
            f"{k[0]}_vs_{k[1]}": v.to_dict() for k, v in results.items()
        }
    elif isinstance(results, SimulationResult):
        json_data["result"] = results.to_dict()

    # Save JSON
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    # Save readable log
    with open(log_path, "w") as f:
        f.write(f"Pokemon TCG Pocket Simulator - Session Log\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Type: {session_type}\n")
        f.write(f"{'='*60}\n\n")

        if matchup_text:
            f.write(matchup_text)
            f.write("\n\n")

        if isinstance(results, SimulationResult):
            f.write(results.summary())
            f.write("\n\n")

        # Write individual game logs
        if game_logs:
            for gi, log in enumerate(game_logs):
                f.write(f"\n{'#'*60}\n")
                f.write(f"  GAME {gi + 1}\n")
                f.write(f"{'#'*60}\n")
                for line in log:
                    f.write(line + "\n")
        elif isinstance(results, SimulationResult) and results.game_logs:
            for gi, log in enumerate(results.game_logs):
                f.write(f"\n{'#'*60}\n")
                f.write(f"  GAME {gi + 1}\n")
                f.write(f"{'#'*60}\n")
                for line in log:
                    f.write(line + "\n")
        elif isinstance(results, dict):
            for key, res in results.items():
                if res.game_logs:
                    f.write(f"\n{'#'*60}\n")
                    f.write(f"  {key[0]} vs {key[1]}\n")
                    f.write(f"{'#'*60}\n")
                    for gi, log in enumerate(res.game_logs):
                        f.write(f"\n--- Game {gi + 1} ---\n")
                        for line in log:
                            f.write(line + "\n")

    return log_path, json_path
