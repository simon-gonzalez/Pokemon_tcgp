from enum import Enum, auto


class EnergyType(Enum):
    GRASS = "Grass"
    FIRE = "Fire"
    WATER = "Water"
    LIGHTNING = "Lightning"
    PSYCHIC = "Psychic"
    FIGHTING = "Fighting"
    DARK = "Dark"
    METAL = "Metal"
    DRAGON = "Dragon"
    COLORLESS = "Colorless"


class CardType(Enum):
    POKEMON = auto()
    ITEM = auto()
    SUPPORTER = auto()


class PokemonStage(Enum):
    BASIC = auto()
    STAGE1 = auto()
    STAGE2 = auto()


class StatusCondition(Enum):
    NONE = auto()
    POISONED = auto()
    ASLEEP = auto()
    PARALYZED = auto()
    CONFUSED = auto()


class Zone(Enum):
    DECK = auto()
    HAND = auto()
    ACTIVE = auto()
    BENCH = auto()
    DISCARD = auto()
    PRIZES = auto()


class TurnPhase(Enum):
    SETUP = auto()
    DRAW = auto()
    ENERGY_ZONE = auto()
    MAIN = auto()
    ATTACK = auto()
    END = auto()
