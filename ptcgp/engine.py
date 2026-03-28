from __future__ import annotations
import random
from typing import Optional, TYPE_CHECKING

from .enums import EnergyType, CardType, PokemonStage, StatusCondition, TurnPhase
from .cards import Card, PokemonCard, ItemCard, SupporterCard, Attack
from .game_state import GameState, PlayerState, InPlayPokemon
from .actions import (
    Action, PlayBasicPokemonAction, EvolvePokemonAction, AttachEnergyAction,
    PlayItemAction, PlaySupporterAction, AttackAction, RetreatAction,
    PassAction, ChooseActiveAction,
)
from .combat import calculate_damage, apply_damage, handle_knockout, apply_status_effects

if TYPE_CHECKING:
    from .player import Player


MAX_TURNS = 50  # Safety limit


def get_deck_energy_types(deck: list[Card]) -> set[EnergyType]:
    types = set()
    for card in deck:
        if isinstance(card, PokemonCard) and card.energy_type != EnergyType.COLORLESS:
            types.add(card.energy_type)
    if not types:
        types.add(EnergyType.COLORLESS)
    return types


def setup_game(deck1: list[Card], deck2: list[Card]) -> GameState:
    state = GameState()

    for i, deck in enumerate([deck1, deck2]):
        player = state.players[i]
        player.deck = list(deck)
        random.shuffle(player.deck)

        # Mulligan: ensure at least 1 basic Pokemon in starting hand
        for attempt in range(100):
            player.hand = player.deck[:5]
            remaining = player.deck[5:]
            has_basic = any(
                isinstance(c, PokemonCard) and c.stage == PokemonStage.BASIC
                for c in player.hand
            )
            if has_basic:
                player.deck = remaining
                break
            # Reshuffle
            player.deck = player.hand + remaining
            random.shuffle(player.deck)

        # Set prizes (3 cards)
        player.prizes = player.deck[:3]
        player.deck = player.deck[3:]

    state.phase = TurnPhase.SETUP
    state.turn_number = 1
    return state


def setup_active_pokemon(state: GameState, player_index: int, agent) -> GameState:
    """Let the player choose their starting active Pokemon from basics in hand."""
    old_current = state.current_player
    state.current_player = player_index
    player = state.players[player_index]
    basics_in_hand = [
        (i, c) for i, c in enumerate(player.hand)
        if isinstance(c, PokemonCard) and c.stage == PokemonStage.BASIC
    ]

    if not basics_in_hand:
        state.current_player = old_current
        return state

    if len(basics_in_hand) == 1:
        idx = basics_in_hand[0][0]
    else:
        actions = [PlayBasicPokemonAction(hand_index=i, to_active=True) for i, _ in basics_in_hand]
        chosen = agent.choose_action(state, actions)
        idx = chosen.hand_index

    card = player.hand.pop(idx)
    player.active = InPlayPokemon(card=card, turn_played=0)
    state.log(f"Player {player_index} places {card.name} as active!")
    state.current_player = old_current
    return state


def setup_bench(state: GameState, player_index: int, agent) -> GameState:
    """Let the player optionally place basic Pokemon on bench during setup."""
    old_current = state.current_player
    state.current_player = player_index
    player = state.players[player_index]

    while player.has_bench_space():
        basics = [
            (i, c) for i, c in enumerate(player.hand)
            if isinstance(c, PokemonCard) and c.stage == PokemonStage.BASIC
        ]
        if not basics:
            break

        actions = [PlayBasicPokemonAction(hand_index=i, to_active=False) for i, _ in basics]
        actions.append(PassAction())

        chosen = agent.choose_action(state, actions)
        if isinstance(chosen, PassAction):
            break

        card = player.hand.pop(chosen.hand_index)
        player.bench.append(InPlayPokemon(card=card, turn_played=0))
        state.log(f"Player {player_index} benches {card.name}!")

    state.current_player = old_current

    return state


def get_legal_actions(state: GameState) -> list[Action]:
    actions = []
    player = state.current
    turn = state.turn_number

    # Play basic Pokemon to bench
    if player.has_bench_space():
        for i, card in enumerate(player.hand):
            if isinstance(card, PokemonCard) and card.stage == PokemonStage.BASIC:
                actions.append(PlayBasicPokemonAction(hand_index=i, to_active=False))

    # Play basic to active if no active
    if player.active is None:
        for i, card in enumerate(player.hand):
            if isinstance(card, PokemonCard) and card.stage == PokemonStage.BASIC:
                actions.append(PlayBasicPokemonAction(hand_index=i, to_active=True))

    # Evolve Pokemon (not on first turn of the game, not on turn Pokemon was played)
    if not state.first_turn:
        for i, card in enumerate(player.hand):
            if isinstance(card, PokemonCard) and card.stage in (PokemonStage.STAGE1, PokemonStage.STAGE2):
                # Check active
                if (player.active and
                    player.active.card.name == card.evolves_from and
                    not player.active.evolved_this_turn and
                    player.active.turn_played < turn):
                    actions.append(EvolvePokemonAction(hand_index=i, target_position=-1))

                # Check bench
                for bi, bench_poke in enumerate(player.bench):
                    if (bench_poke.card.name == card.evolves_from and
                        not bench_poke.evolved_this_turn and
                        bench_poke.turn_played < turn):
                        actions.append(EvolvePokemonAction(hand_index=i, target_position=bi))

    # Attach energy (once per turn)
    if not player.energy_attached_this_turn and player.energy_zone_type is not None:
        if player.active:
            actions.append(AttachEnergyAction(target_position=-1))
        for bi in range(len(player.bench)):
            actions.append(AttachEnergyAction(target_position=bi))

    # Play item cards
    for i, card in enumerate(player.hand):
        if isinstance(card, ItemCard):
            # Items with targets
            if card.id in ("potion", "x_speed"):
                if player.active:
                    actions.append(PlayItemAction(hand_index=i, target_position=-1))
                for bi in range(len(player.bench)):
                    actions.append(PlayItemAction(hand_index=i, target_position=bi))
            else:
                actions.append(PlayItemAction(hand_index=i))

    # Play supporter (once per turn)
    if not player.supporter_played_this_turn:
        for i, card in enumerate(player.hand):
            if isinstance(card, SupporterCard):
                actions.append(PlaySupporterAction(hand_index=i))

    # Attack
    if player.active and player.active.status != StatusCondition.PARALYZED:
        for ai, attack in enumerate(player.active.card.attacks):
            if player.active.can_attack(attack):
                actions.append(AttackAction(attack_index=ai))

    # Retreat
    if (player.active and player.active.can_retreat() and
        player.bench and player.active.status != StatusCondition.PARALYZED):
        for bi in range(len(player.bench)):
            actions.append(RetreatAction(bench_index=bi))

    # Can always pass
    actions.append(PassAction())

    return actions


def apply_action(state: GameState, action: Action) -> GameState:
    player = state.current
    opp = state.opponent

    if isinstance(action, PlayBasicPokemonAction):
        card = player.hand.pop(action.hand_index)
        pokemon = InPlayPokemon(card=card, turn_played=state.turn_number)
        if action.to_active and player.active is None:
            player.active = pokemon
            state.log(f"Player {state.current_player}: {card.name} to active!")
        else:
            player.bench.append(pokemon)
            state.log(f"Player {state.current_player}: {card.name} to bench!")

    elif isinstance(action, EvolvePokemonAction):
        card = player.hand.pop(action.hand_index)
        if action.target_position == -1:
            old = player.active
            player.active = InPlayPokemon(
                card=card,
                damage=old.damage,
                attached_energy=list(old.attached_energy),
                status=StatusCondition.NONE,  # Evolution cures status
                turn_played=old.turn_played,
                evolved_this_turn=True,
            )
            state.log(f"Player {state.current_player}: {old.card.name} evolves into {card.name}!")
        else:
            old = player.bench[action.target_position]
            player.bench[action.target_position] = InPlayPokemon(
                card=card,
                damage=old.damage,
                attached_energy=list(old.attached_energy),
                status=StatusCondition.NONE,
                turn_played=old.turn_played,
                evolved_this_turn=True,
            )
            state.log(f"Player {state.current_player}: {old.card.name} evolves into {card.name}!")

    elif isinstance(action, AttachEnergyAction):
        energy = player.energy_zone_type
        if energy:
            if action.target_position == -1 and player.active:
                player.active.attached_energy.append(energy)
                state.log(f"Player {state.current_player}: Attach {energy.value} energy to {player.active.card.name}")
            elif 0 <= action.target_position < len(player.bench):
                target = player.bench[action.target_position]
                target.attached_energy.append(energy)
                state.log(f"Player {state.current_player}: Attach {energy.value} energy to {target.card.name}")
            player.energy_attached_this_turn = True
            player.energy_zone_type = None

    elif isinstance(action, PlayItemAction):
        card = player.hand.pop(action.hand_index)
        state.log(f"Player {state.current_player}: Plays {card.name}!")
        if card.effect:
            state = card.effect(state, state.current_player, action.target_position)
        player.discard.append(card)

    elif isinstance(action, PlaySupporterAction):
        card = player.hand.pop(action.hand_index)
        state.log(f"Player {state.current_player}: Plays supporter {card.name}!")
        if card.effect:
            state = card.effect(state, state.current_player, action.target_position)
        player.supporter_played_this_turn = True
        player.discard.append(card)

    elif isinstance(action, AttackAction):
        attack = player.active.card.attacks[action.attack_index]
        state.log(f"Player {state.current_player}: {player.active.card.name} uses {attack.name}!")

        # Calculate and apply damage
        damage = calculate_damage(player.active, opp.active, attack, state)

        # Apply attack effect (some effects are side effects beyond damage)
        if attack.effect:
            result = attack.effect(state, player.active, opp.active, damage)
            if isinstance(result, tuple):
                if len(result) == 2:
                    state, damage = result

        if damage > 0 and opp.active:
            opp.active.damage += damage
            state.log(f"  {opp.active.card.name} takes {damage} damage! ({opp.active.remaining_hp()} HP remaining)")

            if opp.active.is_knocked_out():
                state.log(f"  {opp.active.card.name} is knocked out!")
                state = handle_knockout(state, state.opponent_index, -1)

    elif isinstance(action, RetreatAction):
        # Pay retreat cost
        retreat_cost = player.active.card.retreat_cost
        for _ in range(retreat_cost):
            if player.active.attached_energy:
                player.active.attached_energy.pop(0)

        # Swap
        old_active = player.active
        player.active = player.bench.pop(action.bench_index)
        player.bench.append(old_active)
        state.log(f"Player {state.current_player}: Retreats {old_active.card.name}, sends in {player.active.card.name}!")

    return state


def promote_after_ko(state: GameState, player_index: int, agent) -> GameState:
    """After a KO, the player must promote a benched Pokemon."""
    old_current = state.current_player
    state.current_player = player_index
    player = state.players[player_index]
    if player.active is None and player.bench:
        if len(player.bench) == 1:
            player.active = player.bench.pop(0)
        else:
            actions = [ChooseActiveAction(bench_index=i) for i in range(len(player.bench))]
            chosen = agent.choose_action(state, actions)
            player.active = player.bench.pop(chosen.bench_index)
        state.log(f"Player {player_index}: Promotes {player.active.card.name} to active!")
    state.current_player = old_current
    return state


def run_turn(state: GameState, agents: list) -> GameState:
    player = state.current
    pi = state.current_player

    state.log(f"\n=== Turn {state.turn_number} - Player {pi} ===")

    # Draw phase
    if state.turn_number > 1 or pi == 1:  # First player doesn't draw on turn 1 in some variants
        if player.deck:
            card = player.deck.pop(0)
            player.hand.append(card)
            state.log(f"Player {pi}: Draws a card ({len(player.hand)} in hand)")
        else:
            state.winner = 1 - pi
            state.log(f"Player {pi} cannot draw! Player {1-pi} wins!")
            return state

    # Energy zone: generate 1 random energy from deck types
    all_cards = player.deck + player.hand + [p.card for p in player.all_in_play()]
    energy_types = get_deck_energy_types(all_cards + player.discard + player.prizes)
    if energy_types:
        player.energy_zone_type = random.choice(list(energy_types))
        state.log(f"Player {pi}: Energy zone generates {player.energy_zone_type.value}!")

    # Reset turn flags
    player.supporter_played_this_turn = False
    player.energy_attached_this_turn = False
    for p in player.all_in_play():
        p.evolved_this_turn = False

    # Main phase
    state.phase = TurnPhase.MAIN
    agent = agents[pi]
    attack_used = False

    for _ in range(50):  # Safety limit for actions per turn
        if state.winner is not None:
            return state

        legal = get_legal_actions(state)
        if not legal:
            break

        chosen = agent.choose_action(state, legal)

        if isinstance(chosen, PassAction):
            state.log(f"Player {pi}: Passes.")
            break

        if isinstance(chosen, AttackAction):
            state = apply_action(state, chosen)
            attack_used = True

            # After attack, opponent may need to promote
            if state.opponent.active is None and state.opponent.bench:
                state = promote_after_ko(state, state.opponent_index, agents[state.opponent_index])
            break

        state = apply_action(state, chosen)

    # End of turn effects
    if state.winner is None:
        state = apply_status_effects(state, pi)

        # After status, check if our active got KO'd (poison)
        if player.active is None and player.bench:
            state = promote_after_ko(state, pi, agents[pi])
        elif player.active is None and not player.bench:
            state.winner = 1 - pi
            state.log(f"Player {pi} has no Pokemon! Player {1-pi} wins!")

    return state


def run_game(deck1: list[Card], deck2: list[Card], agent1, agent2, verbose: bool = False) -> GameState:
    state = setup_game(deck1, deck2)
    agents = [agent1, agent2]

    # Setup phase: each player places their active Pokemon
    for i in range(2):
        state = setup_active_pokemon(state, i, agents[i])
        state = setup_bench(state, i, agents[i])

    state.phase = TurnPhase.MAIN
    state.first_turn = True

    # Game loop
    while state.winner is None and state.turn_number <= MAX_TURNS:
        state = run_turn(state, agents)

        if state.winner is not None:
            break

        # Switch to next player
        state.current_player = 1 - state.current_player
        if state.current_player == 0:
            state.turn_number += 1
            state.first_turn = False

    if state.winner is None and state.turn_number > MAX_TURNS:
        state.log("Game ended in a draw (max turns reached)")

    if verbose:
        for line in state.turn_log:
            print(line)

    return state
