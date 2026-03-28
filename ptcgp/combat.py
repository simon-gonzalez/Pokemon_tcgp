from __future__ import annotations
from typing import TYPE_CHECKING

from .enums import EnergyType, StatusCondition
from .cards import Attack

if TYPE_CHECKING:
    from .game_state import GameState, InPlayPokemon


def calculate_damage(
    attacker: InPlayPokemon,
    defender: InPlayPokemon,
    attack: Attack,
    state: GameState,
) -> int:
    damage = attack.base_damage

    # Apply weakness: +20 damage in TCG Pocket
    if defender.card.weakness and defender.card.weakness == attacker.card.energy_type:
        damage += 20

    # Apply attack effect modifiers (some attacks modify damage)
    if attack.effect:
        result = attack.effect(state, attacker, defender, damage)
        if isinstance(result, tuple):
            state_mod, damage = result
        elif isinstance(result, int):
            damage = result

    return max(0, damage)


def apply_damage(state: GameState, damage: int, player_index: int, position: int) -> GameState:
    """Apply damage to a Pokemon. position: -1 = active, 0+ = bench."""
    player = state.players[player_index]
    if position == -1:
        if player.active:
            player.active.damage += damage
    elif 0 <= position < len(player.bench):
        player.bench[position].damage += damage
    return state


def handle_knockout(state: GameState, ko_player_index: int, position: int) -> GameState:
    """Handle a knocked out Pokemon. Returns state. May need active promotion."""
    player = state.players[ko_player_index]
    attacker_index = 1 - ko_player_index

    if position == -1 and player.active:
        knocked_out = player.active
        player.discard.append(knocked_out.card)
        for e_card in knocked_out.attached_energy:
            pass  # Energy is just discarded (tracked as types, not cards)
        player.active = None

        # Award prizes
        prizes_to_take = 2 if knocked_out.card.is_ex else 1
        attacker_state = state.players[attacker_index]
        for _ in range(prizes_to_take):
            if attacker_state.prizes:
                card = attacker_state.prizes.pop(0)
                attacker_state.hand.append(card)

        # Check win by prizes
        if not attacker_state.prizes:
            state.winner = attacker_index
            state.log(f"Player {attacker_index} wins by taking all prizes!")

        # Check win by no Pokemon
        if player.active is None and not player.bench:
            state.winner = attacker_index
            state.log(f"Player {attacker_index} wins - opponent has no Pokemon!")

    return state


def apply_status_effects(state: GameState, player_index: int) -> GameState:
    """Apply end-of-turn status effects (poison damage, status recovery)."""
    import random
    player = state.players[player_index]

    if player.active:
        pokemon = player.active
        if pokemon.status == StatusCondition.POISONED:
            pokemon.damage += 10
            state.log(f"{pokemon.card.name} takes 10 poison damage!")
            if pokemon.is_knocked_out():
                state = handle_knockout(state, player_index, -1)

        elif pokemon.status == StatusCondition.ASLEEP:
            if random.random() < 0.5:
                pokemon.status = StatusCondition.NONE
                state.log(f"{pokemon.card.name} woke up!")

        elif pokemon.status == StatusCondition.PARALYZED:
            # Paralysis wears off at end of the afflicted player's next turn
            pokemon.status = StatusCondition.NONE
            state.log(f"{pokemon.card.name} is no longer paralyzed!")

    return state
