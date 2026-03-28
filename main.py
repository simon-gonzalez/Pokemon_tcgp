#!/usr/bin/env python3
"""
Pokemon TCG Pocket Simulator
=============================
Simulates games between the top meta decks using AI players.
All results are saved to the logs/ directory.

Usage:
    python main.py                                  # Full matchup table (all vs all)
    python main.py --match "Pikachu ex" "Charizard ex"  # Specific matchup
    python main.py --verbose                        # Show turn-by-turn for 1 game
    python main.py --games 200                      # Change games per matchup
    python main.py --vs-random "Charizard ex"       # Test AI vs Random
    python main.py --list-decks                     # List available decks
    python main.py --validate                       # Validate all decks
"""
import argparse
import sys
from datetime import datetime

from data.decks import META_DECKS, validate_deck
from ptcgp.ai import AIPlayer
from ptcgp.player import RandomPlayer
from ptcgp.simulator import (
    simulate, run_matchup_table, print_matchup_table, save_session_log,
)


def print_header():
    print()
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║        POKEMON TCG POCKET SIMULATOR             ║")
    print("  ║        AI Battle Arena                          ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Pokemon TCG Pocket Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                                    Run all matchups
  python main.py --match "Pikachu ex" "Charizard ex" --verbose
  python main.py --vs-random "Charizard ex" --games 200
  python main.py --list-decks

Logs are saved in the logs/ directory after each run.
        """,
    )
    parser.add_argument("--match", nargs=2, metavar="DECK",
                        help="Run a specific matchup between two decks")
    parser.add_argument("--games", type=int, default=100,
                        help="Number of games per matchup (default: 100)")
    parser.add_argument("--verbose", action="store_true",
                        help="Show turn-by-turn log for one game")
    parser.add_argument("--save-all-games", action="store_true",
                        help="Save detailed log for every game (not just verbose)")
    parser.add_argument("--vs-random", metavar="DECK",
                        help="Test AI vs Random player with specified deck")
    parser.add_argument("--list-decks", action="store_true",
                        help="List available decks")
    parser.add_argument("--validate", action="store_true",
                        help="Validate all deck builds")

    args = parser.parse_args()

    # List decks
    if args.list_decks:
        print_header()
        print("  Available Meta Decks:")
        print("  " + "=" * 48)
        for name, factory in META_DECKS.items():
            deck = factory()
            pokemon_count = sum(1 for c in deck if hasattr(c, 'hp'))
            trainer_count = len(deck) - pokemon_count
            print(f"  - {name:<20} ({pokemon_count} Pokemon, {trainer_count} Trainers)")
        print()
        print("  Use these names with --match or --vs-random")
        print()
        return

    # Validate
    if args.validate:
        print_header()
        print("  Validating Decks:")
        print("  " + "=" * 48)
        all_valid = True
        for name, factory in META_DECKS.items():
            deck = factory()
            valid = validate_deck(deck, name)
            icon = "[OK]" if valid else "[FAIL]"
            print(f"  {icon} {name}")
            if not valid:
                all_valid = False
        print()
        if all_valid:
            print("  All decks are valid!")
        else:
            print("  Some decks have errors. Fix them before simulating.")
        print()
        return

    print_header()

    # Build decks
    decks = {name: factory() for name, factory in META_DECKS.items()}
    save_logs = args.save_all_games

    # AI vs Random
    if args.vs_random:
        deck_name = args.vs_random
        if deck_name not in decks:
            print(f"  [ERROR] Unknown deck: '{deck_name}'")
            print(f"  Available: {', '.join(decks.keys())}")
            return

        print(f"  Mode:  AI vs Random")
        print(f"  Deck:  {deck_name}")
        print(f"  Games: {args.games}")
        print()

        ai = AIPlayer("AI")
        rng = RandomPlayer("Random")

        result = simulate(
            decks[deck_name], decks[deck_name],
            ai, rng,
            n_games=args.games,
            deck1_name=f"AI ({deck_name})",
            deck2_name=f"Random ({deck_name})",
            verbose_game=0 if args.verbose else None,
            save_all_logs=save_logs or args.verbose,
        )
        print(result.summary())

        # Save logs
        log_path, json_path = save_session_log("ai_vs_random", result)
        print(f"\n  Logs saved:")
        print(f"    {log_path}")
        print(f"    {json_path}")
        print()
        return

    # Specific matchup
    if args.match:
        name1, name2 = args.match
        for name in [name1, name2]:
            if name not in decks:
                print(f"  [ERROR] Unknown deck: '{name}'")
                print(f"  Available: {', '.join(decks.keys())}")
                return

        print(f"  Mode:  1v1 Matchup (AI vs AI)")
        print(f"  Deck1: {name1}")
        print(f"  Deck2: {name2}")
        print(f"  Games: {args.games}")
        print()

        result = simulate(
            decks[name1], decks[name2],
            AIPlayer("AI-1"), AIPlayer("AI-2"),
            n_games=args.games,
            deck1_name=name1,
            deck2_name=name2,
            verbose_game=0 if args.verbose else None,
            save_all_logs=save_logs or args.verbose,
        )
        print(result.summary())

        # Save logs
        safe_name = f"match_{name1.replace(' ', '_')}_vs_{name2.replace(' ', '_')}"
        log_path, json_path = save_session_log(safe_name, result)
        print(f"\n  Logs saved:")
        print(f"    {log_path}")
        print(f"    {json_path}")
        print()
        return

    # Full matchup table
    print(f"  Mode:  Full Matchup Table (all vs all)")
    print(f"  Decks: {len(decks)}")
    print(f"  Games: {args.games} per matchup")
    print(f"  Total: {args.games * len(decks) * (len(decks)-1) // 2} games")
    print()

    results = run_matchup_table(
        decks,
        lambda: AIPlayer("AI"),
        n_games=args.games,
        save_logs=save_logs,
    )

    matchup_text = print_matchup_table(decks, results)

    # Save logs
    log_path, json_path = save_session_log("full_matchup", results, matchup_text)
    print(f"\n  Logs saved:")
    print(f"    {log_path}")
    print(f"    {json_path}")
    print()


if __name__ == "__main__":
    main()
