#!/usr/bin/env python3
"""
Pokemon TCG Pocket Simulator - Web Interface
Run with: python app.py
Then open http://localhost:5000
"""
import json
import os
import glob
import threading
from datetime import datetime
from flask import Flask, render_template, jsonify, request

from data.decks import META_DECKS, validate_deck
from ptcgp.ai import AIPlayer
from ptcgp.player import RandomPlayer
from ptcgp.engine import run_game
from ptcgp.cards import PokemonCard, ItemCard, SupporterCard
from ptcgp.enums import PokemonStage
from ptcgp.simulator import simulate, save_session_log

app = Flask(__name__)

LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Track running simulations
running_sims = {}


# ── Pages ──────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── API Endpoints ──────────────────────────────────────────────────

@app.get("/api/decks")
def api_decks():
    """Return info about all available decks."""
    result = {}
    for name, factory in META_DECKS.items():
        deck = factory()
        pokemon = [c for c in deck if isinstance(c, PokemonCard)]
        items = [c for c in deck if isinstance(c, ItemCard)]
        supporters = [c for c in deck if isinstance(c, SupporterCard)]
        ex_pokemon = [c for c in pokemon if c.is_ex]

        result[name] = {
            "name": name,
            "total_cards": len(deck),
            "pokemon_count": len(pokemon),
            "item_count": len(items),
            "supporter_count": len(supporters),
            "energy_types": list(set(
                c.energy_type.value for c in pokemon
                if c.energy_type.value != "Colorless"
            )),
            "ex_pokemon": [c.name for c in ex_pokemon],
            "cards": [],
        }
        seen = set()
        for c in deck:
            if c.id not in seen:
                seen.add(c.id)
                count = sum(1 for x in deck if x.id == c.id)
                card_info = {"id": c.id, "name": c.name, "count": count}
                if isinstance(c, PokemonCard):
                    card_info.update({
                        "type": "Pokemon",
                        "hp": c.hp,
                        "energy_type": c.energy_type.value,
                        "stage": c.stage.name.title(),
                        "is_ex": c.is_ex,
                        "attacks": [
                            {
                                "name": a.name,
                                "damage": a.base_damage,
                                "energy_cost": [e.value for e in a.energy_cost],
                                "description": a.description,
                            }
                            for a in c.attacks
                        ],
                        "weakness": c.weakness.value if c.weakness else None,
                        "retreat_cost": c.retreat_cost,
                    })
                elif isinstance(c, ItemCard):
                    card_info.update({"type": "Item", "description": c.description})
                elif isinstance(c, SupporterCard):
                    card_info.update({"type": "Supporter", "description": c.description})
                result[name]["cards"].append(card_info)

    return jsonify(result)


@app.post("/api/simulate")
def api_simulate():
    """Run a simulation between two decks."""
    data = request.get_json()
    deck1_name = data.get("deck1")
    deck2_name = data.get("deck2")
    n_games = min(data.get("games", 50), 500)
    mode = data.get("mode", "ai_vs_ai")  # ai_vs_ai or ai_vs_random

    if deck1_name not in META_DECKS:
        return jsonify({"error": f"Unknown deck: {deck1_name}"}), 400
    if deck2_name not in META_DECKS:
        return jsonify({"error": f"Unknown deck: {deck2_name}"}), 400

    deck1 = META_DECKS[deck1_name]()
    deck2 = META_DECKS[deck2_name]()

    agent1 = AIPlayer("AI-1")
    agent2 = RandomPlayer("Random") if mode == "ai_vs_random" else AIPlayer("AI-2")

    result = simulate(
        deck1, deck2, agent1, agent2,
        n_games=n_games,
        deck1_name=deck1_name,
        deck2_name=deck2_name,
        save_all_logs=True,
    )

    # Save logs
    safe = f"{deck1_name.replace(' ', '_')}_vs_{deck2_name.replace(' ', '_')}"
    log_path, json_path = save_session_log(safe, result)

    return jsonify({
        "deck1": deck1_name,
        "deck2": deck2_name,
        "games": n_games,
        "deck1_wins": result.wins[0],
        "deck2_wins": result.wins[1],
        "draws": result.draws,
        "deck1_win_rate": round(result.win_rate_1, 1),
        "deck2_win_rate": round(result.win_rate_2, 1),
        "avg_turns": round(result.avg_turns, 1),
        "log_file": os.path.basename(log_path),
        "json_file": os.path.basename(json_path),
    })


@app.post("/api/play-game")
def api_play_game():
    """Run a single game and return the full turn log."""
    data = request.get_json()
    deck1_name = data.get("deck1")
    deck2_name = data.get("deck2")

    if deck1_name not in META_DECKS or deck2_name not in META_DECKS:
        return jsonify({"error": "Unknown deck"}), 400

    deck1 = META_DECKS[deck1_name]()
    deck2 = META_DECKS[deck2_name]()

    agent1 = AIPlayer("AI-1")
    agent2 = AIPlayer("AI-2")

    state = run_game(deck1, deck2, agent1, agent2, verbose=False)

    # Parse log into structured turns
    turns = []
    current_turn = {"turn": 0, "player": -1, "events": []}
    for line in state.turn_log:
        if line.startswith("\n=== Turn"):
            if current_turn["events"]:
                turns.append(current_turn)
            parts = line.strip().split(" ")
            turn_num = int(parts[2])
            player_num = int(parts[5])
            current_turn = {"turn": turn_num, "player": player_num, "events": []}
        elif line.strip():
            current_turn["events"].append(line.strip())
    if current_turn["events"]:
        turns.append(current_turn)

    return jsonify({
        "deck1": deck1_name,
        "deck2": deck2_name,
        "winner": state.winner,
        "total_turns": state.turn_number,
        "turns": turns,
        "full_log": state.turn_log,
    })


@app.post("/api/matchup-table")
def api_matchup_table():
    """Run all matchups and return the table."""
    data = request.get_json() or {}
    n_games = min(data.get("games", 30), 200)

    deck_names = list(META_DECKS.keys())
    decks = {name: META_DECKS[name]() for name in deck_names}

    results = {}
    for i, name1 in enumerate(deck_names):
        for j, name2 in enumerate(deck_names):
            if i >= j:
                continue
            result = simulate(
                decks[name1], decks[name2],
                AIPlayer("AI-1"), AIPlayer("AI-2"),
                n_games=n_games,
                deck1_name=name1,
                deck2_name=name2,
            )
            results[f"{name1} vs {name2}"] = {
                "deck1": name1,
                "deck2": name2,
                "deck1_wins": result.wins[0],
                "deck2_wins": result.wins[1],
                "deck1_win_rate": round(result.win_rate_1, 1),
                "deck2_win_rate": round(result.win_rate_2, 1),
            }

    # Build matrix
    matrix = {}
    total_wins = {n: 0 for n in deck_names}
    total_games = {n: 0 for n in deck_names}

    for key, r in results.items():
        n1, n2 = r["deck1"], r["deck2"]
        matrix[f"{n1}|{n2}"] = r["deck1_win_rate"]
        matrix[f"{n2}|{n1}"] = r["deck2_win_rate"]
        total_wins[n1] += r["deck1_wins"]
        total_wins[n2] += r["deck2_wins"]
        total_games[n1] += r["deck1_wins"] + r["deck2_wins"]
        total_games[n2] += r["deck1_wins"] + r["deck2_wins"]

    rankings = []
    for name in deck_names:
        wr = (total_wins[name] / total_games[name] * 100) if total_games[name] > 0 else 0
        rankings.append({"name": name, "win_rate": round(wr, 1), "wins": total_wins[name], "games": total_games[name]})

    rankings.sort(key=lambda x: x["win_rate"], reverse=True)

    # Save
    save_session_log("web_matchup", results)

    return jsonify({
        "deck_names": deck_names,
        "matchups": results,
        "matrix": matrix,
        "rankings": rankings,
        "games_per_matchup": n_games,
    })


@app.get("/api/logs")
def api_logs():
    """List all saved log files."""
    logs = []
    for f in sorted(glob.glob(os.path.join(LOGS_DIR, "*.json")), reverse=True):
        try:
            with open(f) as fh:
                data = json.load(fh)
            logs.append({
                "filename": os.path.basename(f),
                "log_filename": os.path.basename(f).replace(".json", ".log"),
                "timestamp": data.get("timestamp", ""),
                "type": data.get("session_type", ""),
            })
        except Exception:
            pass
    return jsonify(logs)


@app.get("/api/logs/<filename>")
def api_log_detail(filename):
    """Read a specific log file."""
    # Try JSON first
    json_path = os.path.join(LOGS_DIR, filename)
    if filename.endswith(".json") and os.path.exists(json_path):
        with open(json_path) as f:
            return jsonify(json.load(f))

    # Try .log
    log_path = os.path.join(LOGS_DIR, filename)
    if filename.endswith(".log") and os.path.exists(log_path):
        with open(log_path) as f:
            return jsonify({"content": f.read()})

    return jsonify({"error": "File not found"}), 404


if __name__ == "__main__":
    print("\n  Pokemon TCG Pocket Simulator - Web UI")
    print("  Open http://localhost:5000 in your browser\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
