from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Callable, Any, TYPE_CHECKING

from .enums import EnergyType, CardType, PokemonStage

if TYPE_CHECKING:
    from .game_state import GameState


@dataclass(frozen=True)
class Attack:
    name: str
    energy_cost: tuple[EnergyType, ...]
    base_damage: int
    effect: Optional[Callable] = None
    description: str = ""


@dataclass(frozen=True)
class Ability:
    name: str
    description: str
    trigger: str  # "on_play", "once_per_turn", "passive", "when_attacking"
    effect: Optional[Callable] = None


@dataclass(frozen=True)
class Card:
    id: str
    name: str
    card_type: CardType = CardType.POKEMON

    def __repr__(self):
        return f"{self.name} ({self.id})"


@dataclass(frozen=True)
class PokemonCard(Card):
    hp: int = 0
    energy_type: EnergyType = EnergyType.COLORLESS
    weakness: Optional[EnergyType] = None
    retreat_cost: int = 0
    stage: PokemonStage = PokemonStage.BASIC
    evolves_from: Optional[str] = None
    attacks: tuple[Attack, ...] = ()
    ability: Optional[Ability] = None
    is_ex: bool = False

    def __post_init__(self):
        object.__setattr__(self, 'card_type', CardType.POKEMON)


@dataclass(frozen=True)
class ItemCard(Card):
    effect: Optional[Callable] = None
    description: str = ""

    def __post_init__(self):
        object.__setattr__(self, 'card_type', CardType.ITEM)


@dataclass(frozen=True)
class SupporterCard(Card):
    effect: Optional[Callable] = None
    description: str = ""

    def __post_init__(self):
        object.__setattr__(self, 'card_type', CardType.SUPPORTER)
