"""Biomechanics calculator registry — maps movement_type to calculator class."""

from app.modules.biomechanics.squatting import SquattingCalculator
from app.modules.biomechanics.landing import LandingCalculator
from app.modules.biomechanics.running import RunningCalculator
from app.modules.biomechanics.sprinting import SprintingCalculator
from app.modules.biomechanics.jumping import JumpingCalculator
from app.modules.biomechanics.throwing import ThrowingCalculator
from app.modules.biomechanics.cutting import CuttingCalculator

_CALCULATORS = {
    "squatting": SquattingCalculator,
    "landing": LandingCalculator,
    "running": RunningCalculator,
    "sprinting": SprintingCalculator,
    "jumping": JumpingCalculator,
    "throwing": ThrowingCalculator,
    "cutting": CuttingCalculator,
}


def get_calculator(movement_type: str):
    """Get a calculator instance for the given movement type."""
    cls = _CALCULATORS.get(movement_type)
    if cls is None:
        # Default to squatting calculator
        return SquattingCalculator()
    return cls()


def list_movement_types() -> list[str]:
    return list(_CALCULATORS.keys())