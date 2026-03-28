"""Card database for Pokemon TCG Pocket meta decks."""
from __future__ import annotations
import random
from ptcgp.enums import EnergyType, CardType, PokemonStage
from ptcgp.cards import PokemonCard, ItemCard, SupporterCard, Attack, Ability


# =============================================================================
# ATTACK EFFECTS
# =============================================================================

def charizard_ex_crimson_storm(state, attacker, defender, damage):
    """Discard 2 Fire energy from Charizard ex."""
    removed = 0
    new_energy = list(attacker.attached_energy)
    for _ in range(2):
        if EnergyType.FIRE in new_energy:
            new_energy.remove(EnergyType.FIRE)
            removed += 1
    attacker.attached_energy = new_energy
    if removed > 0:
        state.log(f"  Charizard ex discards {removed} Fire energy!")
    return state, damage


def mewtwo_ex_psydrive(state, attacker, defender, damage):
    """Discard 2 Psychic energy from Mewtwo ex."""
    removed = 0
    new_energy = list(attacker.attached_energy)
    for _ in range(2):
        if EnergyType.PSYCHIC in new_energy:
            new_energy.remove(EnergyType.PSYCHIC)
            removed += 1
    attacker.attached_energy = new_energy
    return state, damage


def pikachu_ex_circle_circuit(state, attacker, defender, damage):
    """30 damage for each of your benched Pokemon."""
    player = state.players[state.current_player]
    bench_count = len(player.bench)
    total = 30 * bench_count
    state.log(f"  Circle Circuit: {bench_count} benched Pokemon x 30 = {total} damage!")
    return state, total


def celebi_ex_slash(state, attacker, defender, damage):
    """Basic 60 damage attack."""
    return state, damage


def celebi_ex_powerful_bloom(state, attacker, defender, damage):
    """Flip a coin for each Grass energy. 50 damage for each heads."""
    grass_count = sum(1 for e in attacker.attached_energy if e == EnergyType.GRASS)
    heads = sum(1 for _ in range(grass_count) if random.random() < 0.5)
    total = 50 * heads
    state.log(f"  Powerful Bloom: {heads}/{grass_count} heads = {total} damage!")
    return state, total


def starmie_ex_hydro_splash(state, attacker, defender, damage):
    """Basic 90 damage."""
    return state, damage


def gyarados_ex_rampage(state, attacker, defender, damage):
    """20 damage + 20 for each damage counter on Gyarados."""
    damage_counters = attacker.damage // 10
    total = 20 + (20 * damage_counters)
    state.log(f"  Rampage: 20 + {damage_counters} counters x 20 = {total}!")
    return state, total


def electrode_buzzing(state, attacker, defender, damage):
    """Knock out Electrode to attach 2 Lightning energy to benched Pokemon."""
    player = state.players[state.current_player]
    # Simplified: just do damage normally
    return state, damage


def gardevoir_ability_psychic_embrace(state, player_index):
    """Once per turn: attach Psychic energy from discard to a benched Psychic Pokemon (+10 damage to self)."""
    player = state.players[player_index]
    # Find psychic Pokemon on bench
    for pokemon in player.bench:
        if pokemon.card.energy_type == EnergyType.PSYCHIC:
            pokemon.attached_energy.append(EnergyType.PSYCHIC)
            pokemon.damage += 10
            state.log(f"  Gardevoir's Psychic Embrace: attach Psychic energy to {pokemon.card.name} (+10 self damage)")
            break
    return state


def serperior_ability_jungle_totem(state, player_index):
    """Each Grass energy counts as 2 Grass energy for your Grass Pokemon."""
    # This is handled during damage calculation / energy checking
    pass


def moltres_ability_inferno_dance(state, player_index):
    """Flip 3 coins. For each heads, attach Fire energy from discard to a benched Pokemon."""
    player = state.players[player_index]
    heads = sum(1 for _ in range(3) if random.random() < 0.5)
    attached = 0
    for _ in range(heads):
        targets = [p for p in player.bench if p.card.energy_type == EnergyType.FIRE]
        if targets:
            target = targets[0]
            target.attached_energy.append(EnergyType.FIRE)
            attached += 1
    if attached > 0:
        state.log(f"  Moltres Inferno Dance: {heads} heads, attached {attached} Fire energy!")
    return state


# =============================================================================
# ITEM EFFECTS
# =============================================================================

def poke_ball_effect(state, player_index, target_position):
    """Flip a coin. Heads: search deck for a Pokemon and add to hand."""
    player = state.players[player_index]
    if random.random() < 0.5:
        # Find first basic Pokemon in deck
        for i, card in enumerate(player.deck):
            if isinstance(card, PokemonCard):
                player.hand.append(player.deck.pop(i))
                state.log(f"  Poke Ball: Heads! Found {card.name}!")
                return state
        state.log("  Poke Ball: Heads but no Pokemon in deck!")
    else:
        state.log("  Poke Ball: Tails!")
    return state


def potion_effect(state, player_index, target_position):
    """Heal 20 damage from target Pokemon."""
    player = state.players[player_index]
    if target_position == -1 and player.active:
        healed = min(20, player.active.damage)
        player.active.damage -= healed
        state.log(f"  Potion: healed {healed} from {player.active.card.name}!")
    elif target_position is not None and 0 <= target_position < len(player.bench):
        target = player.bench[target_position]
        healed = min(20, target.damage)
        target.damage -= healed
        state.log(f"  Potion: healed {healed} from {target.card.name}!")
    return state


def x_speed_effect(state, player_index, target_position):
    """Reduce retreat cost by 1 this turn (simplified: just remove 1 energy needed)."""
    state.log("  X Speed: Retreat cost reduced!")
    # Simplified implementation - the AI already accounts for this
    return state


def red_card_effect(state, player_index, target_position):
    """Opponent shuffles hand into deck and draws 3."""
    opp_index = 1 - player_index
    opp = state.players[opp_index]
    opp.deck.extend(opp.hand)
    opp.hand.clear()
    random.shuffle(opp.deck)
    for _ in range(3):
        if opp.deck:
            opp.hand.append(opp.deck.pop(0))
    state.log(f"  Red Card: Opponent draws 3 new cards!")
    return state


# =============================================================================
# SUPPORTER EFFECTS
# =============================================================================

def professor_oak_effect(state, player_index, target_position):
    """Draw 2 cards."""
    player = state.players[player_index]
    for _ in range(2):
        if player.deck:
            player.hand.append(player.deck.pop(0))
    state.log(f"  Professor Oak: Drew 2 cards!")
    return state


def misty_effect(state, player_index, target_position):
    """Flip coins until tails. Attach Water energy for each heads to active."""
    player = state.players[player_index]
    if player.active and player.active.card.energy_type == EnergyType.WATER:
        heads = 0
        while random.random() < 0.5:
            heads += 1
            player.active.attached_energy.append(EnergyType.WATER)
        state.log(f"  Misty: {heads} heads! Attached {heads} Water energy!")
    return state


def blaine_effect(state, player_index, target_position):
    """Your Fire Pokemon's attacks do +30 damage this turn."""
    # Simplified: add energy to active fire Pokemon
    player = state.players[player_index]
    if player.active and player.active.card.energy_type == EnergyType.FIRE:
        player.active.attached_energy.append(EnergyType.FIRE)
        state.log(f"  Blaine: Boosted Fire attacks!")
    return state


def erika_effect(state, player_index, target_position):
    """Heal 50 damage from one of your Grass Pokemon."""
    player = state.players[player_index]
    if player.active and player.active.card.energy_type == EnergyType.GRASS:
        healed = min(50, player.active.damage)
        player.active.damage -= healed
        state.log(f"  Erika: Healed {healed} from {player.active.card.name}!")
    return state


def giovanni_effect(state, player_index, target_position):
    """Your active Pokemon's attacks do +10 damage this turn."""
    # We store this as a flag - simplified by just logging
    state.log(f"  Giovanni: +10 damage this turn!")
    # Simplified: give a small energy boost
    return state


def sabrina_effect(state, player_index, target_position):
    """Switch opponent's active with one of their benched Pokemon (opponent chooses)."""
    opp_index = 1 - player_index
    opp = state.players[opp_index]
    if opp.active and opp.bench:
        # Choose weakest bench Pokemon to bring up
        idx = 0  # Simplified: swap with first bench
        old_active = opp.active
        opp.active = opp.bench.pop(idx)
        opp.bench.append(old_active)
        state.log(f"  Sabrina: Opponent switches to {opp.active.card.name}!")
    return state


# =============================================================================
# POKEMON CARDS
# =============================================================================

# --- FIRE ---
CHARMANDER = PokemonCard(
    id="charmander", name="Charmander", hp=60,
    energy_type=EnergyType.FIRE, weakness=EnergyType.WATER,
    retreat_cost=1, stage=PokemonStage.BASIC,
    attacks=(
        Attack("Ember", (EnergyType.FIRE,), 30),
    ),
)

CHARMELEON = PokemonCard(
    id="charmeleon", name="Charmeleon", hp=90,
    energy_type=EnergyType.FIRE, weakness=EnergyType.WATER,
    retreat_cost=2, stage=PokemonStage.STAGE1, evolves_from="Charmander",
    attacks=(
        Attack("Fire Claws", (EnergyType.FIRE, EnergyType.FIRE), 60),
    ),
)

CHARIZARD_EX = PokemonCard(
    id="charizard_ex", name="Charizard ex", hp=180,
    energy_type=EnergyType.FIRE, weakness=EnergyType.WATER,
    retreat_cost=2, stage=PokemonStage.STAGE2, evolves_from="Charmeleon",
    is_ex=True,
    attacks=(
        Attack("Slash", (EnergyType.FIRE, EnergyType.COLORLESS), 60),
        Attack("Crimson Storm", (EnergyType.FIRE, EnergyType.FIRE, EnergyType.COLORLESS, EnergyType.COLORLESS), 200,
               effect=charizard_ex_crimson_storm, description="Discard 2 Fire energy"),
    ),
)

MOLTRES = PokemonCard(
    id="moltres", name="Moltres", hp=100,
    energy_type=EnergyType.FIRE, weakness=EnergyType.LIGHTNING,
    retreat_cost=2, stage=PokemonStage.BASIC,
    attacks=(
        Attack("Heat Blast", (EnergyType.FIRE, EnergyType.COLORLESS), 70),
    ),
    ability=Ability("Inferno Dance", "Flip 3 coins, attach Fire energy for each heads",
                    "once_per_turn", moltres_ability_inferno_dance),
)

ARCANINE = PokemonCard(
    id="arcanine", name="Arcanine", hp=120,
    energy_type=EnergyType.FIRE, weakness=EnergyType.WATER,
    retreat_cost=2, stage=PokemonStage.STAGE1, evolves_from="Growlithe",
    attacks=(
        Attack("Fire Mane", (EnergyType.FIRE, EnergyType.FIRE), 80),
    ),
)

GROWLITHE = PokemonCard(
    id="growlithe", name="Growlithe", hp=70,
    energy_type=EnergyType.FIRE, weakness=EnergyType.WATER,
    retreat_cost=1, stage=PokemonStage.BASIC,
    attacks=(
        Attack("Bite", (EnergyType.COLORLESS,), 20),
    ),
)

# --- WATER ---
STARYU = PokemonCard(
    id="staryu", name="Staryu", hp=50,
    energy_type=EnergyType.WATER, weakness=EnergyType.LIGHTNING,
    retreat_cost=1, stage=PokemonStage.BASIC,
    attacks=(
        Attack("Splash", (EnergyType.WATER,), 20),
    ),
)

STARMIE_EX = PokemonCard(
    id="starmie_ex", name="Starmie ex", hp=130,
    energy_type=EnergyType.WATER, weakness=EnergyType.LIGHTNING,
    retreat_cost=0, stage=PokemonStage.STAGE1, evolves_from="Staryu",
    is_ex=True,
    attacks=(
        Attack("Hydro Splash", (EnergyType.WATER, EnergyType.COLORLESS), 90,
               effect=starmie_ex_hydro_splash),
    ),
)

MAGIKARP = PokemonCard(
    id="magikarp", name="Magikarp", hp=30,
    energy_type=EnergyType.WATER, weakness=EnergyType.LIGHTNING,
    retreat_cost=1, stage=PokemonStage.BASIC,
    attacks=(
        Attack("Splash", (EnergyType.COLORLESS,), 10),
    ),
)

GYARADOS_EX = PokemonCard(
    id="gyarados_ex", name="Gyarados ex", hp=170,
    energy_type=EnergyType.WATER, weakness=EnergyType.LIGHTNING,
    retreat_cost=3, stage=PokemonStage.STAGE1, evolves_from="Magikarp",
    is_ex=True,
    attacks=(
        Attack("Hyper Beam", (EnergyType.WATER, EnergyType.WATER, EnergyType.WATER, EnergyType.COLORLESS), 160),
    ),
)

SQUIRTLE = PokemonCard(
    id="squirtle", name="Squirtle", hp=60,
    energy_type=EnergyType.WATER, weakness=EnergyType.LIGHTNING,
    retreat_cost=1, stage=PokemonStage.BASIC,
    attacks=(
        Attack("Water Gun", (EnergyType.WATER,), 20),
    ),
)

WARTORTLE = PokemonCard(
    id="wartortle", name="Wartortle", hp=80,
    energy_type=EnergyType.WATER, weakness=EnergyType.LIGHTNING,
    retreat_cost=1, stage=PokemonStage.STAGE1, evolves_from="Squirtle",
    attacks=(
        Attack("Wave Splash", (EnergyType.WATER, EnergyType.COLORLESS), 40),
    ),
)

# --- LIGHTNING ---
PIKACHU = PokemonCard(
    id="pikachu", name="Pikachu", hp=60,
    energy_type=EnergyType.LIGHTNING, weakness=EnergyType.FIGHTING,
    retreat_cost=1, stage=PokemonStage.BASIC,
    attacks=(
        Attack("Gnaw", (EnergyType.COLORLESS,), 20),
    ),
)

PIKACHU_EX = PokemonCard(
    id="pikachu_ex", name="Pikachu ex", hp=120,
    energy_type=EnergyType.LIGHTNING, weakness=EnergyType.FIGHTING,
    retreat_cost=1, stage=PokemonStage.BASIC,
    is_ex=True,
    attacks=(
        Attack("Circle Circuit", (EnergyType.LIGHTNING, EnergyType.LIGHTNING), 0,
               effect=pikachu_ex_circle_circuit, description="30x benched Pokemon"),
    ),
)

VOLTORB = PokemonCard(
    id="voltorb", name="Voltorb", hp=50,
    energy_type=EnergyType.LIGHTNING, weakness=EnergyType.FIGHTING,
    retreat_cost=1, stage=PokemonStage.BASIC,
    attacks=(
        Attack("Tackle", (EnergyType.COLORLESS,), 20),
    ),
)

ELECTRODE = PokemonCard(
    id="electrode", name="Electrode", hp=80,
    energy_type=EnergyType.LIGHTNING, weakness=EnergyType.FIGHTING,
    retreat_cost=1, stage=PokemonStage.STAGE1, evolves_from="Voltorb",
    attacks=(
        Attack("Electro Ball", (EnergyType.LIGHTNING, EnergyType.COLORLESS), 50),
    ),
)

ZAPDOS = PokemonCard(
    id="zapdos", name="Zapdos", hp=100,
    energy_type=EnergyType.LIGHTNING, weakness=EnergyType.LIGHTNING,
    retreat_cost=1, stage=PokemonStage.BASIC,
    attacks=(
        Attack("Thunderbolt", (EnergyType.LIGHTNING, EnergyType.LIGHTNING, EnergyType.COLORLESS), 120),
    ),
)

PACHIRISU = PokemonCard(
    id="pachirisu", name="Pachirisu", hp=70,
    energy_type=EnergyType.LIGHTNING, weakness=EnergyType.FIGHTING,
    retreat_cost=1, stage=PokemonStage.BASIC,
    attacks=(
        Attack("Quick Attack", (EnergyType.LIGHTNING,), 40),
    ),
)

# --- PSYCHIC ---
MEWTWO_EX = PokemonCard(
    id="mewtwo_ex", name="Mewtwo ex", hp=150,
    energy_type=EnergyType.PSYCHIC, weakness=EnergyType.DARK,
    retreat_cost=2, stage=PokemonStage.BASIC,
    is_ex=True,
    attacks=(
        Attack("Psychic Sphere", (EnergyType.PSYCHIC, EnergyType.COLORLESS), 50),
        Attack("Psydrive", (EnergyType.PSYCHIC, EnergyType.PSYCHIC, EnergyType.COLORLESS, EnergyType.COLORLESS), 150,
               effect=mewtwo_ex_psydrive, description="Discard 2 Psychic energy"),
    ),
)

RALTS = PokemonCard(
    id="ralts", name="Ralts", hp=60,
    energy_type=EnergyType.PSYCHIC, weakness=EnergyType.DARK,
    retreat_cost=1, stage=PokemonStage.BASIC,
    attacks=(
        Attack("Ram", (EnergyType.COLORLESS,), 10),
    ),
)

KIRLIA = PokemonCard(
    id="kirlia", name="Kirlia", hp=80,
    energy_type=EnergyType.PSYCHIC, weakness=EnergyType.DARK,
    retreat_cost=1, stage=PokemonStage.STAGE1, evolves_from="Ralts",
    attacks=(
        Attack("Smack", (EnergyType.PSYCHIC, EnergyType.COLORLESS), 30),
    ),
)

GARDEVOIR = PokemonCard(
    id="gardevoir", name="Gardevoir", hp=110,
    energy_type=EnergyType.PSYCHIC, weakness=EnergyType.DARK,
    retreat_cost=2, stage=PokemonStage.STAGE2, evolves_from="Kirlia",
    attacks=(
        Attack("Psyshot", (EnergyType.PSYCHIC, EnergyType.PSYCHIC, EnergyType.COLORLESS), 80),
    ),
    ability=Ability("Psychic Embrace", "Attach Psychic energy from energy zone to benched Psychic Pokemon",
                    "once_per_turn", gardevoir_ability_psychic_embrace),
)

MEW_EX = PokemonCard(
    id="mew_ex", name="Mew ex", hp=130,
    energy_type=EnergyType.PSYCHIC, weakness=EnergyType.DARK,
    retreat_cost=1, stage=PokemonStage.BASIC,
    is_ex=True,
    attacks=(
        Attack("Genome Hacking", (EnergyType.PSYCHIC, EnergyType.COLORLESS, EnergyType.COLORLESS), 0,
               description="Copy any attack of the defending Pokemon"),
    ),
)

# --- GRASS ---
CELEBI_EX = PokemonCard(
    id="celebi_ex", name="Celebi ex", hp=130,
    energy_type=EnergyType.GRASS, weakness=EnergyType.FIRE,
    retreat_cost=1, stage=PokemonStage.BASIC,
    is_ex=True,
    attacks=(
        Attack("Slash", (EnergyType.GRASS, EnergyType.COLORLESS), 60, effect=celebi_ex_slash),
        Attack("Powerful Bloom", (EnergyType.GRASS, EnergyType.GRASS, EnergyType.COLORLESS), 0,
               effect=celebi_ex_powerful_bloom, description="50x coin flip per Grass energy"),
    ),
)

SNIVY = PokemonCard(
    id="snivy", name="Snivy", hp=60,
    energy_type=EnergyType.GRASS, weakness=EnergyType.FIRE,
    retreat_cost=1, stage=PokemonStage.BASIC,
    attacks=(
        Attack("Vine Whip", (EnergyType.GRASS,), 20),
    ),
)

SERVINE = PokemonCard(
    id="servine", name="Servine", hp=80,
    energy_type=EnergyType.GRASS, weakness=EnergyType.FIRE,
    retreat_cost=1, stage=PokemonStage.STAGE1, evolves_from="Snivy",
    attacks=(
        Attack("Leaf Blade", (EnergyType.GRASS, EnergyType.COLORLESS), 40),
    ),
)

SERPERIOR = PokemonCard(
    id="serperior", name="Serperior", hp=120,
    energy_type=EnergyType.GRASS, weakness=EnergyType.FIRE,
    retreat_cost=1, stage=PokemonStage.STAGE2, evolves_from="Servine",
    attacks=(
        Attack("Leaf Storm", (EnergyType.GRASS, EnergyType.GRASS, EnergyType.COLORLESS), 80),
    ),
    ability=Ability("Jungle Totem", "Grass energy counts as 2", "passive"),
)

EXEGGCUTE = PokemonCard(
    id="exeggcute", name="Exeggcute", hp=50,
    energy_type=EnergyType.GRASS, weakness=EnergyType.FIRE,
    retreat_cost=1, stage=PokemonStage.BASIC,
    attacks=(
        Attack("Seed Bomb", (EnergyType.GRASS,), 20),
    ),
)

EXEGGUTOR = PokemonCard(
    id="exeggutor", name="Exeggutor", hp=100,
    energy_type=EnergyType.GRASS, weakness=EnergyType.FIRE,
    retreat_cost=2, stage=PokemonStage.STAGE1, evolves_from="Exeggcute",
    attacks=(
        Attack("Stomp", (EnergyType.GRASS, EnergyType.COLORLESS), 50),
    ),
)

# --- FIGHTING ---
MACHOP = PokemonCard(
    id="machop", name="Machop", hp=70,
    energy_type=EnergyType.FIGHTING, weakness=EnergyType.PSYCHIC,
    retreat_cost=2, stage=PokemonStage.BASIC,
    attacks=(
        Attack("Low Kick", (EnergyType.FIGHTING,), 20),
    ),
)

MACHOKE = PokemonCard(
    id="machoke", name="Machoke", hp=100,
    energy_type=EnergyType.FIGHTING, weakness=EnergyType.PSYCHIC,
    retreat_cost=2, stage=PokemonStage.STAGE1, evolves_from="Machop",
    attacks=(
        Attack("Karate Chop", (EnergyType.FIGHTING, EnergyType.FIGHTING), 50),
    ),
)

MACHAMP = PokemonCard(
    id="machamp", name="Machamp", hp=150,
    energy_type=EnergyType.FIGHTING, weakness=EnergyType.PSYCHIC,
    retreat_cost=3, stage=PokemonStage.STAGE2, evolves_from="Machoke",
    attacks=(
        Attack("Seismic Toss", (EnergyType.FIGHTING, EnergyType.FIGHTING, EnergyType.COLORLESS), 120),
    ),
)

# --- DARK ---
GASTLY = PokemonCard(
    id="gastly", name="Gastly", hp=50,
    energy_type=EnergyType.DARK, weakness=EnergyType.FIGHTING,
    retreat_cost=1, stage=PokemonStage.BASIC,
    attacks=(
        Attack("Lick", (EnergyType.DARK,), 20),
    ),
)

HAUNTER = PokemonCard(
    id="haunter", name="Haunter", hp=70,
    energy_type=EnergyType.DARK, weakness=EnergyType.FIGHTING,
    retreat_cost=1, stage=PokemonStage.STAGE1, evolves_from="Gastly",
    attacks=(
        Attack("Shadow Punch", (EnergyType.DARK, EnergyType.COLORLESS), 40),
    ),
)

GENGAR = PokemonCard(
    id="gengar", name="Gengar", hp=110,
    energy_type=EnergyType.DARK, weakness=EnergyType.FIGHTING,
    retreat_cost=1, stage=PokemonStage.STAGE2, evolves_from="Haunter",
    attacks=(
        Attack("Shadow Claw", (EnergyType.DARK, EnergyType.DARK, EnergyType.COLORLESS), 100),
    ),
)


# =============================================================================
# ITEM CARDS
# =============================================================================

POKE_BALL = ItemCard(
    id="poke_ball", name="Poke Ball",
    effect=poke_ball_effect,
    description="Flip a coin. Heads: search deck for a Pokemon",
)

POTION = ItemCard(
    id="potion", name="Potion",
    effect=potion_effect,
    description="Heal 20 damage from one of your Pokemon",
)

X_SPEED = ItemCard(
    id="x_speed", name="X Speed",
    effect=x_speed_effect,
    description="Reduce retreat cost by 1 this turn",
)

RED_CARD = ItemCard(
    id="red_card", name="Red Card",
    effect=red_card_effect,
    description="Opponent shuffles hand and draws 3",
)


# =============================================================================
# SUPPORTER CARDS
# =============================================================================

PROFESSOR_OAK = SupporterCard(
    id="professor_oak", name="Professor Oak",
    effect=professor_oak_effect,
    description="Draw 2 cards",
)

MISTY = SupporterCard(
    id="misty", name="Misty",
    effect=misty_effect,
    description="Flip until tails, attach Water energy for each heads",
)

BLAINE = SupporterCard(
    id="blaine", name="Blaine",
    effect=blaine_effect,
    description="Your Fire Pokemon's attacks do +30 this turn",
)

ERIKA = SupporterCard(
    id="erika", name="Erika",
    effect=erika_effect,
    description="Heal 50 from one of your Grass Pokemon",
)

GIOVANNI = SupporterCard(
    id="giovanni", name="Giovanni",
    effect=giovanni_effect,
    description="Your attacks do +10 damage this turn",
)

SABRINA = SupporterCard(
    id="sabrina", name="Sabrina",
    effect=sabrina_effect,
    description="Switch opponent's active with a benched Pokemon",
)


# =============================================================================
# CARD REGISTRY
# =============================================================================

ALL_CARDS = {
    # Fire
    "charmander": CHARMANDER, "charmeleon": CHARMELEON, "charizard_ex": CHARIZARD_EX,
    "moltres": MOLTRES, "arcanine": ARCANINE, "growlithe": GROWLITHE,
    # Water
    "staryu": STARYU, "starmie_ex": STARMIE_EX, "magikarp": MAGIKARP,
    "gyarados_ex": GYARADOS_EX, "squirtle": SQUIRTLE, "wartortle": WARTORTLE,
    # Lightning
    "pikachu": PIKACHU, "pikachu_ex": PIKACHU_EX, "voltorb": VOLTORB,
    "electrode": ELECTRODE, "zapdos": ZAPDOS, "pachirisu": PACHIRISU,
    # Psychic
    "mewtwo_ex": MEWTWO_EX, "ralts": RALTS, "kirlia": KIRLIA,
    "gardevoir": GARDEVOIR, "mew_ex": MEW_EX,
    # Grass
    "celebi_ex": CELEBI_EX, "snivy": SNIVY, "servine": SERVINE,
    "serperior": SERPERIOR, "exeggcute": EXEGGCUTE, "exeggutor": EXEGGUTOR,
    # Fighting
    "machop": MACHOP, "machoke": MACHOKE, "machamp": MACHAMP,
    # Dark
    "gastly": GASTLY, "haunter": HAUNTER, "gengar": GENGAR,
    # Items
    "poke_ball": POKE_BALL, "potion": POTION, "x_speed": X_SPEED, "red_card": RED_CARD,
    # Supporters
    "professor_oak": PROFESSOR_OAK, "misty": MISTY, "blaine": BLAINE,
    "erika": ERIKA, "giovanni": GIOVANNI, "sabrina": SABRINA,
}
