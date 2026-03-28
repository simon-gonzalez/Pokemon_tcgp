from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class Action:
    """Base action class."""
    pass


@dataclass
class PlayBasicPokemonAction(Action):
    """Play a basic Pokemon from hand to bench or active."""
    hand_index: int = 0
    to_active: bool = False


@dataclass
class EvolvePokemonAction(Action):
    """Evolve a Pokemon in play using a card from hand."""
    hand_index: int = 0
    target_position: int = -1  # -1 = active, 0+ = bench index


@dataclass
class AttachEnergyAction(Action):
    """Attach the energy zone energy to an in-play Pokemon."""
    target_position: int = -1  # -1 = active, 0+ = bench index


@dataclass
class PlayItemAction(Action):
    """Play an item card from hand."""
    hand_index: int = 0
    target_position: Optional[int] = None  # -1 = active, 0+ = bench, None = no target


@dataclass
class PlaySupporterAction(Action):
    """Play a supporter card from hand."""
    hand_index: int = 0
    target_position: Optional[int] = None


@dataclass
class AttackAction(Action):
    """Use an attack of the active Pokemon."""
    attack_index: int = 0


@dataclass
class RetreatAction(Action):
    """Retreat active Pokemon and swap with a benched Pokemon."""
    bench_index: int = 0


@dataclass
class PassAction(Action):
    """End the main phase without attacking."""
    pass


@dataclass
class ChooseActiveAction(Action):
    """Choose a Pokemon from bench to become active (after KO or start)."""
    bench_index: int = 0
