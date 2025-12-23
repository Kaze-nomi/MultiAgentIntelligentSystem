"""
Service protocols and interfaces for watermelon evaluation.

This module defines abstract base classes and protocols that establish contracts
for watermelon ripeness evaluation services. These interfaces enable dependency
injection and allow for multiple implementation strategies.
"""

from abc import ABC, abstractmethod
from typing import Protocol

from ..domain import Watermelon, RipenessStatus


class IRipenessEvaluator(ABC):
    """Abstract base class for watermelon ripeness evaluation services.

    This interface defines the contract for services that evaluate watermelon
    ripeness based on physical properties. Implementations can use various
    strategies such as heuristic rules, machine learning models, or physical
    simulations.

    The interface follows the Strategy pattern, allowing different evaluation
    algorithms to be used interchangeably.

    Example:
        class HeuristicRipenessEvaluator(IRipenessEvaluator):
            def evaluate(self, watermelon: Watermelon) -> RipenessStatus:
                # Implementation based on heuristic rules
                pass
    """

    @abstractmethod
    def evaluate(self, watermelon: Watermelon) -> RipenessStatus:
        """Evaluate the ripeness status of a watermelon.

        Args:
            watermelon: The watermelon instance to evaluate. Must contain
                valid physical properties (weight, diameter, color, etc.).

        Returns:
            RipenessStatus: The evaluated ripeness status of the watermelon.
                Returns one of the enum values: UNRIPE, EARLY_RIPE, RIPE,
                LATE_RIPE, or OVERRIPE.

        Raises:
            ValueError: If the watermelon has invalid or incomplete properties
                that prevent evaluation.
            TypeError: If the watermelon parameter is not a valid Watermelon
                instance.
        """
        pass


class RipenessEvaluatorProtocol(Protocol):
    """Protocol type for ripeness evaluator implementations.

    This protocol provides structural typing for ripeness evaluators,
    allowing any class with an evaluate method to be used as a ripeness
    evaluator without explicit inheritance.

    This is useful for duck typing and when working with external libraries
    or third-party implementations that cannot inherit from IRipenessEvaluator.
    """

    def evaluate(self, watermelon: Watermelon) -> RipenessStatus:
        """Evaluate watermelon ripeness.

        Args:
            watermelon: Watermelon instance to evaluate.

        Returns:
            RipenessStatus: The evaluated ripeness status.
        """
        ...


__all__ = [
    "IRipenessEvaluator",
    "RipenessEvaluatorProtocol",
]
