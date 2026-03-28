#!/usr/bin/env python3
"""
Pokemon TCG Pocket Simulator
=============================
Simulates games between the top meta decks using AI players.

Usage:
    python main.py                    # Run full matchup table
    python main.py --match DECK1 DECK2  # Run specific matchup
    python main.py --verbose          # Show one game turn-by-turn
    python main.py --games N          # Number of games per matchup
    python main.py --vs-random DECK   # Test AI vs Random player
"""
import argparse
import sys

from data.decks import META_DECKS, validate_deck
from ptcgp.ai import AIPlayer
from ptcgp.player import RandomPlayer
from ptcgp.simulator import simulate, run_matchup_table, print_matchup_table


def main():
    parser = argparse.ArgumentParser(description="Pokemon TCG Pocket Simulator")
    parser.add_argument("--match", nargs=2, metavar="DECK",
                        help="Run a specific matchup between two decks")
    parser.add_argument("--games", type=int, default=100,
                        help="Number of games per matchup (default: 100)")
    parser.add_argument("--verbose", action="store_true",
                        help="Show turn-by-turn log for one game")
    parser.add_argument("--vs-random", metavar="DECK",
                        help="Test AI vs Random player with specified deck")
    parser.add_argument("--list-decks", action="store_true",
                        help="List available decks")
    parser.add_argument("--validate", action="store_true",
                        help="Validate all deck builds")

    args = parser.parse_args()

    # List decks
    if args.list_decks:
        print("\nAvailable Meta Decks:")
        print("=" * 40)
        for name in META_DECKS:
            deck = META_DECKS[name]()
            print(f"  - {name} ({len(deck)} cards)")
        return

    # Validate
    if args.validate:
        print("\nValidating Decks:")
        print("=" * 40)
        all_valid = True
        for name, factory in META_DECKS.items():
            deck = factory()
            valid = validate_deck(deck, name)
            status = "OK" if valid else "INVALID"
            print(f"  {name}: {status}")
            if not valid:
                all_valid = False
        if all_valid:
            print("\nAll decks are valid!")
        return

    # Build decks
    decks = {name: factory() for name, factory in META_DECKS.items()}

    # AI vs Random
    if args.vs_random:
        deck_name = args.vs_random
        if deck_name not in decks:
            print(f"Unknown deck: {deck_name}")
            print(f"Available: {', '.join(decks.keys())}")
            return

        print(f"\n{'='*50}")
        print(f"  AI vs Random - {deck_name}")
        print(f"  {args.games} games")
        print(f"{'='*50}")

        ai = AIPlayer("AI")
        rng = RandomPlayer("Random")

        result = simulate(
            decks[deck_name], decks[deck_name],
            ai, rng,
            n_games=args.games,
            deck1_name=f"AI ({deck_name})",
            deck2_name=f"Random ({deck_name})",
            verbose_game=0 if args.verbose else None,
        )
        print(result.summary())
        return

    # Specific matchup
    if args.match:
        name1, name2 = args.match
        if name1 not in decks:
            print(f"Unknown deck: {name1}")
            print(f"Available: {', '.join(decks.keys())}")
            return
        if name2 not in decks:
            print(f"Unknown deck: {name2}")
            print(f"Available: {', '.join(decks.keys())}")
            return

        print(f"\n{'='*50}")
        print(f"  {name1} vs {name2}")
        print(f"  {args.games} games (AI vs AI)")
        print(f"{'='*50}")

        result = simulate(
            decks[name1], decks[name2],
            AIPlayer("AI-1"), AIPlayer("AI-2"),
            n_games=args.games,
            deck1_name=name1,
            deck2_name=name2,
            verbose_game=0 if args.verbose else None,
        )
        print(result.summary())
        return

    # Full matchup table
    print(f"\n{'='*50}")
    print("  POKEMON TCG POCKET SIMULATOR")
    print(f"  Running all matchups ({args.games} games each)")
    print(f"{'='*50}\n")

    results = run_matchup_table(
        decks,
        lambda: AIPlayer("AI"),
        n_games=args.games,
    )

    print_matchup_table(decks, results)


if __name__ == "__main__":
    main()
