from __future__ import annotations
import copy
from dataclasses import dataclass, field
from typing import Optional, List

from .enums import EnergyType, StatusCondition, TurnPhase
from .cards import Card, PokemonCard, Attack


@dataclass
class InPlayPokemon:
    card: PokemonCard
    damage: int = 0
    attached_energy: list[EnergyType] = field(default_factory=list)
    status: StatusCondition = StatusCondition.NONE
    turn_played: int = 0
    evolved_this_turn: bool = False

    def remaining_hp(self) -> int:
        return max(0, self.card.hp - self.damage)

    def is_knocked_out(self) -> bool:
        return self.damage >= self.card.hp

    def can_attack(self, attack: Attack) -> bool:
        available = list(self.attached_energy)
        for cost in attack.energy_cost:
            if cost == EnergyType.COLORLESS:
                if available:
                    available.pop(0)
                else:
                    return False
            elif cost in available:
                available.remove(cost)
            else:
                return False
        return True

    def can_retreat(self) -> bool:
        return len(self.attached_energy) >= self.card.retreat_cost

    def energy_count(self, energy_type: Optional[EnergyType] = None) -> int:
        if energy_type is None:
            return len(self.attached_energy)
        return sum(1 for e in self.attached_energy if e == energy_type)

    def copy(self) -> InPlayPokemon:
        return InPlayPokemon(
            card=self.card,
            damage=self.damage,
            attached_energy=list(self.attached_energy),
            status=self.status,
            turn_played=self.turn_played,
            evolved_this_turn=self.evolved_this_turn,
        )


@dataclass
class PlayerState:
    deck: list[Card] = field(default_factory=list)
    hand: list[Card] = field(default_factory=list)
    active: Optional[InPlayPokemon] = None
    bench: list[InPlayPokemon] = field(default_factory=list)
    prizes: list[Card] = field(default_factory=list)
    discard: list[Card] = field(default_factory=list)
    energy_zone_type: Optional[EnergyType] = None
    supporter_played_this_turn: bool = False
    energy_attached_this_turn: bool = False
    item_played_this_turn: bool = False

    def all_in_play(self) -> list[InPlayPokemon]:
        result = []
        if self.active:
            result.append(self.active)
        result.extend(self.bench)
        return result

    def has_bench_space(self) -> bool:
        return len(self.bench) < 3

    def copy(self) -> PlayerState:
        return PlayerState(
            deck=list(self.deck),
            hand=list(self.hand),
            active=self.active.copy() if self.active else None,
            bench=[p.copy() for p in self.bench],
            prizes=list(self.prizes),
            discard=list(self.discard),
            energy_zone_type=self.energy_zone_type,
            supporter_played_this_turn=self.supporter_played_this_turn,
            energy_attached_this_turn=self.energy_attached_this_turn,
            item_played_this_turn=self.item_played_this_turn,
        )


@dataclass
class GameState:
    players: list[PlayerState] = field(default_factory=lambda: [PlayerState(), PlayerState()])
    current_player: int = 0
    turn_number: int = 0
    phase: TurnPhase = TurnPhase.SETUP
    winner: Optional[int] = None
    first_turn: bool = True
    turn_log: list[str] = field(default_factory=list)

    @property
    def current(self) -> PlayerState:
        return self.players[self.current_player]

    @property
    def opponent(self) -> PlayerState:
        return self.players[1 - self.current_player]

    @property
    def opponent_index(self) -> int:
        return 1 - self.current_player

    def log(self, msg: str):
        self.turn_log.append(msg)

    def copy(self) -> GameState:
        return GameState(
            players=[p.copy() for p in self.players],
            current_player=self.current_player,
            turn_number=self.turn_number,
            phase=self.phase,
            winner=self.winner,
            first_turn=self.first_turn,
            turn_log=list(self.turn_log),
        )
