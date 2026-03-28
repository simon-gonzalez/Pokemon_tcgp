from __future__ import annotations
from typing import TYPE_CHECKING

from .player import Player
from .actions import (
    Action, PlayBasicPokemonAction, EvolvePokemonAction, AttachEnergyAction,
    PlayItemAction, PlaySupporterAction, AttackAction, RetreatAction,
    PassAction, ChooseActiveAction,
)
from .cards import PokemonCard, ItemCard, SupporterCard, Attack
from .enums import EnergyType, PokemonStage, CardType, StatusCondition
from .combat import calculate_damage

if TYPE_CHECKING:
    from .game_state import GameState, InPlayPokemon


class AIPlayer(Player):
    """Smart AI player using heuristic scoring."""

    def __init__(self, name: str = "AI"):
        super().__init__(name)

    def choose_action(self, state: GameState, legal_actions: list[Action]) -> Action:
        if len(legal_actions) == 1:
            return legal_actions[0]

        scored = [(self._score_action(state, action), action) for action in legal_actions]
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    def _score_action(self, state: GameState, action: Action) -> float:
        player = state.current
        opp = state.opponent
        pi = state.current_player

        if isinstance(action, PlayBasicPokemonAction):
            card = player.hand[action.hand_index]
            if action.to_active:
                return 1000  # Must have active Pokemon
            # Prioritize placing evolution bases
            score = 50
            if self._has_evolution_in_hand(player.hand, card.name):
                score += 30
            if card.is_ex:
                score += 10  # ex basics are good attackers
            if card.hp >= 70:
                score += 10
            return score

        elif isinstance(action, EvolvePokemonAction):
            card = player.hand[action.hand_index]
            score = 200  # Evolution is almost always good

            if action.target_position == -1 and player.active:
                # Evolving active is high priority
                score += 50
                # Even higher if active is damaged
                if player.active.damage > 0:
                    score += 30
            # Stage 2 evolutions are especially valuable
            if card.stage == PokemonStage.STAGE2:
                score += 40
            return score

        elif isinstance(action, AttachEnergyAction):
            score = 100  # Always want to attach energy
            target = self._get_pokemon_at(player, action.target_position)
            if target is None:
                return 0

            # Prefer attaching to active attacker
            if action.target_position == -1:
                score += 30

            # Prefer Pokemon closer to being able to attack
            for attack in target.card.attacks:
                needed = self._energy_needed(target, attack)
                if needed == 1:
                    score += 80  # One energy away from attacking
                elif needed == 0:
                    score -= 20  # Already can attack, less priority

            # Prefer matching energy type
            if player.energy_zone_type == target.card.energy_type:
                score += 20

            return score

        elif isinstance(action, AttackAction):
            if player.active is None or opp.active is None:
                return 0

            attack = player.active.card.attacks[action.attack_index]
            damage = calculate_damage(player.active, opp.active, attack, state)
            score = 300 + damage

            # Huge bonus for KO
            if damage >= opp.active.remaining_hp():
                score += 500
                if opp.active.card.is_ex:
                    score += 300  # KO'ing ex = 2 prizes

            # Prefer higher damage attacks
            score += damage * 2

            return score

        elif isinstance(action, RetreatAction):
            score = 0
            if player.active is None:
                return 0

            bench_poke = player.bench[action.bench_index]

            # Retreat if active is about to be KO'd and bench has a good option
            if opp.active:
                # Estimate opponent's max damage
                opp_max_damage = self._estimate_max_damage(opp.active, player.active, state)
                if opp_max_damage >= player.active.remaining_hp():
                    score += 200  # Active is in danger

            # Retreat to exploit weakness
            if (opp.active and opp.active.card.weakness and
                opp.active.card.weakness == bench_poke.card.energy_type):
                score += 100

            # Retreat if bench Pokemon can KO opponent
            for attack in bench_poke.card.attacks:
                if bench_poke.can_attack(attack):
                    damage = calculate_damage(bench_poke, opp.active, attack, state) if opp.active else 0
                    if opp.active and damage >= opp.active.remaining_hp():
                        score += 300

            # Don't retreat if active can still attack well
            if player.active.remaining_hp() > player.active.card.hp * 0.4:
                score -= 50

            return score

        elif isinstance(action, PlayItemAction):
            card = player.hand[action.hand_index]
            return self._score_item(state, card, action.target_position)

        elif isinstance(action, PlaySupporterAction):
            card = player.hand[action.hand_index]
            return self._score_supporter(state, card)

        elif isinstance(action, ChooseActiveAction):
            # ChooseActiveAction can be called for any player (e.g. after KO)
            # Find which player needs to promote
            promoting = player if player.active is None else opp
            other = opp if promoting is player else player
            if action.bench_index >= len(promoting.bench):
                return 0
            bench_poke = promoting.bench[action.bench_index]
            score = 50

            # Prefer Pokemon that can attack
            for attack in bench_poke.card.attacks:
                if bench_poke.can_attack(attack):
                    score += 100
                    if other.active:
                        damage = calculate_damage(bench_poke, other.active, attack, state)
                        score += damage
                        if damage >= other.active.remaining_hp():
                            score += 500

            # Prefer more HP
            score += bench_poke.remaining_hp()

            # Prefer type advantage
            if (other.active and other.active.card.weakness and
                other.active.card.weakness == bench_poke.card.energy_type):
                score += 80

            # Avoid promoting ex Pokemon if possible (give 2 prizes)
            if bench_poke.card.is_ex:
                score -= 30

            return score

        elif isinstance(action, PassAction):
            return -10  # Only pass as last resort

        return 0

    def _get_pokemon_at(self, player, position: int):
        if position == -1:
            return player.active
        if 0 <= position < len(player.bench):
            return player.bench[position]
        return None

    def _energy_needed(self, pokemon, attack: Attack) -> int:
        available = list(pokemon.attached_energy)
        needed = 0
        for cost in attack.energy_cost:
            if cost == EnergyType.COLORLESS:
                if available:
                    available.pop(0)
                else:
                    needed += 1
            elif cost in available:
                available.remove(cost)
            else:
                needed += 1
        return needed

    def _has_evolution_in_hand(self, hand, pokemon_name: str) -> bool:
        for card in hand:
            if isinstance(card, PokemonCard) and card.evolves_from == pokemon_name:
                return True
        return False

    def _estimate_max_damage(self, attacker, defender, state) -> int:
        max_dmg = 0
        for attack in attacker.card.attacks:
            if attacker.can_attack(attack):
                dmg = calculate_damage(attacker, defender, attack, state)
                max_dmg = max(max_dmg, dmg)
        return max_dmg

    def _score_item(self, state, card, target_position) -> float:
        player = state.current
        score = 30

        if card.id == "poke_ball":
            # Good if we need Pokemon
            basics_in_deck = sum(
                1 for c in player.deck
                if isinstance(c, PokemonCard) and c.stage == PokemonStage.BASIC
            )
            if player.has_bench_space() and basics_in_deck > 0:
                score += 50
            if not player.active:
                score += 100

        elif card.id == "potion":
            target = self._get_pokemon_at(player, target_position)
            if target and target.damage > 0:
                heal = min(20, target.damage)
                score += heal * 3
                # Higher priority if it saves from KO
                if target == player.active:
                    score += 20

        elif card.id == "x_speed":
            target = self._get_pokemon_at(player, target_position)
            if target and target == player.active:
                if not target.can_retreat() and player.bench:
                    score += 60

        elif card.id == "red_card":
            if len(state.opponent.hand) > 3:
                score += 40

        elif card.id == "professors_research":
            if len(player.hand) <= 3:
                score += 60

        return score

    def _score_supporter(self, state, card) -> float:
        player = state.current
        score = 80

        if card.id == "professor_oak":
            if len(player.hand) <= 2:
                score += 80
            elif len(player.hand) <= 4:
                score += 40

        elif card.id == "misty":
            # Good for water decks that need energy acceleration
            if player.active and player.active.card.energy_type == EnergyType.WATER:
                score += 60

        elif card.id == "blaine":
            if player.active and player.active.card.energy_type == EnergyType.FIRE:
                score += 60

        elif card.id == "erika":
            if player.active and player.active.card.energy_type == EnergyType.GRASS:
                score += 60

        elif card.id == "giovanni":
            # +10 damage this turn - great if it secures a KO
            if player.active and state.opponent.active:
                for attack in player.active.card.attacks:
                    if player.active.can_attack(attack):
                        damage = calculate_damage(player.active, state.opponent.active, attack, state)
                        if damage + 10 >= state.opponent.active.remaining_hp() > damage:
                            score += 200  # Secures a KO!

        elif card.id == "sabrina":
            # Force opponent to switch - good against setup Pokemon
            if state.opponent.bench:
                score += 50

        return score
