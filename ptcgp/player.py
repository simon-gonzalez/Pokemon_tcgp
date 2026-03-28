from __future__ import annotations
import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .actions import Action

if TYPE_CHECKING:
    from .game_state import GameState


class Player(ABC):
    def __init__(self, name: str = "Player"):
        self.name = name

    @abstractmethod
    def choose_action(self, state: GameState, legal_actions: list[Action]) -> Action:
        pass


class RandomPlayer(Player):
    """Picks a random action from legal actions."""

    def __init__(self, name: str = "Random"):
        super().__init__(name)

    def choose_action(self, state: GameState, legal_actions: list[Action]) -> Action:
        return random.choice(legal_actions)
