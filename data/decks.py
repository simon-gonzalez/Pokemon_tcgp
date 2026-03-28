"""Meta deck definitions for Pokemon TCG Pocket."""
from data.cards_db import *


def charizard_ex_deck():
    """Charizard ex deck - Stage 2 powerhouse with Moltres energy acceleration."""
    return [
        CHARMANDER, CHARMANDER,
        CHARMELEON, CHARMELEON,
        CHARIZARD_EX, CHARIZARD_EX,
        MOLTRES, MOLTRES,
        GROWLITHE, GROWLITHE,
        ARCANINE, ARCANINE,
        POKE_BALL, POKE_BALL,
        POTION, POTION,
        X_SPEED, X_SPEED,
        PROFESSOR_OAK, BLAINE,
    ]


def pikachu_ex_deck():
    """Pikachu ex deck - Fast aggro, bench-based damage."""
    return [
        PIKACHU_EX, PIKACHU_EX,
        PIKACHU, PIKACHU,
        VOLTORB, VOLTORB,
        ELECTRODE, ELECTRODE,
        PACHIRISU, PACHIRISU,
        ZAPDOS, ZAPDOS,
        POKE_BALL, POKE_BALL,
        POTION, POTION,
        X_SPEED, RED_CARD,
        PROFESSOR_OAK, GIOVANNI,
    ]


def mewtwo_ex_deck():
    """Mewtwo ex deck - Psychic energy acceleration with Gardevoir."""
    return [
        MEWTWO_EX, MEWTWO_EX,
        RALTS, RALTS,
        KIRLIA, KIRLIA,
        GARDEVOIR, GARDEVOIR,
        MEW_EX,
        GASTLY, GASTLY,
        POKE_BALL, POKE_BALL,
        POTION, POTION,
        X_SPEED, X_SPEED,
        RED_CARD,
        PROFESSOR_OAK, SABRINA,
    ]


def celebi_ex_deck():
    """Celebi ex deck - Grass energy coin flip damage."""
    return [
        CELEBI_EX, CELEBI_EX,
        SNIVY, SNIVY,
        SERVINE, SERVINE,
        SERPERIOR, SERPERIOR,
        EXEGGCUTE, EXEGGCUTE,
        EXEGGUTOR, EXEGGUTOR,
        POKE_BALL, POKE_BALL,
        POTION, POTION,
        X_SPEED, RED_CARD,
        PROFESSOR_OAK, ERIKA,
    ]


def starmie_ex_deck():
    """Starmie ex deck - Fast Water attacker with Misty acceleration."""
    return [
        STARYU, STARYU,
        STARMIE_EX, STARMIE_EX,
        SQUIRTLE, SQUIRTLE,
        WARTORTLE, WARTORTLE,
        MAGIKARP, MAGIKARP,
        GYARADOS_EX, GYARADOS_EX,
        POKE_BALL, POKE_BALL,
        POTION, POTION,
        X_SPEED, RED_CARD,
        MISTY, PROFESSOR_OAK,
    ]


# All available decks
META_DECKS = {
    "Charizard ex": charizard_ex_deck,
    "Pikachu ex": pikachu_ex_deck,
    "Mewtwo ex": mewtwo_ex_deck,
    "Celebi ex": celebi_ex_deck,
    "Starmie ex": starmie_ex_deck,
}


def validate_deck(deck, name=""):
    """Validate a deck follows TCG Pocket rules."""
    errors = []
    if len(deck) != 20:
        errors.append(f"Deck must have exactly 20 cards, has {len(deck)}")

    # Count cards by name
    from collections import Counter
    counts = Counter(card.name for card in deck)
    for card_name, count in counts.items():
        if count > 2:
            errors.append(f"'{card_name}' appears {count} times (max 2)")

    # Check supporter count
    from ptcgp.cards import SupporterCard
    supporters = [c for c in deck if isinstance(c, SupporterCard)]
    if len(supporters) > 2:
        errors.append(f"Max 2 Supporter cards, has {len(supporters)}")

    # Check at least 1 basic Pokemon
    from ptcgp.cards import PokemonCard
    from ptcgp.enums import PokemonStage
    basics = [c for c in deck if isinstance(c, PokemonCard) and c.stage == PokemonStage.BASIC]
    if not basics:
        errors.append("Deck must have at least 1 Basic Pokemon")

    if errors:
        print(f"Deck '{name}' validation errors:")
        for e in errors:
            print(f"  - {e}")
        return False
    return True
