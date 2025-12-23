"""
Service package for watermelon ripeness evaluation.

This package provides services and implementations for evaluating watermelon
ripeness based on physical properties. It includes interfaces and concrete
implementations following the Strategy pattern.

Main exports:
    - IRipenessEvaluator: Abstract interface for ripeness evaluation services
    - RipenessEvaluator: Default heuristic-based implementation
    - HeuristicRipenessEvaluator: Alternative heuristic implementation
    - RipenessEvaluatorProtocol: Protocol-based interface for type checking

Example usage:
    from src.my_project.service import RipenessEvaluator, Watermelon, RipenessStatus

    evaluator = RipenessEvaluator()
    watermelon = Watermelon(
        weight=5000.0,
        diameter=30.0,
        color_code="#4CAF50",
        surface_texture="smooth"
    )

    status = evaluator.evaluate(watermelon)
    if status == RipenessStatus.RIPE:
        print("Watermelon is ready to eat!")
"""

from .protocols import (
    IRipenessEvaluator,
    HeuristicRipenessEvaluator,
    RipenessEvaluatorProtocol,
)
from .ripeness_evaluator import RipenessEvaluator

# Re-export domain models for convenience
from ..domain import Watermelon, RipenessStatus

__all__ = [
    # Service interfaces and protocols
    "IRipenessEvaluator",
    "RipenessEvaluatorProtocol",
    # Service implementations
    "RipenessEvaluator",
    "HeuristicRipenessEvaluator",
    # Domain models (re-exported for convenience)
    "Watermelon",
    "RipenessStatus",
]

# Version information
__version__ = "1.0.0"
__author__ = "My Project Team"

# Package-level configuration
class ServiceConfig:
    """Configuration class for service layer.

    This class provides centralized configuration for all services
    in the package, allowing for easy customization of evaluation
    parameters and behavior.
    """

    # Default evaluation thresholds
    DEFAULT_MIN_WEIGHT = 2000.0  # grams
    DEFAULT_MAX_WEIGHT = 15000.0  # grams
    DEFAULT_MIN_DIAMETER = 15.0  # cm
    DEFAULT_MAX_DIAMETER = 50.0  # cm

    # Ripeness evaluation weights
    WEIGHT_FACTOR = 0.3
    DIAMETER_FACTOR = 0.25
    COLOR_FACTOR = 0.25
    TEXTURE_FACTOR = 0.2

    # Color quality thresholds (hex color intensity)
    MIN_COLOR_QUALITY = 0.3
    MAX_COLOR_QUALITY = 0.8

    # Texture quality scores
    TEXTURE_SCORES = {
        "smooth": 1.0,
        "slight_rough": 0.8,
        "rough": 0.6,
        "very_rough": 0.4,
        "cracked": 0.2,
    }

    @classmethod
    def validate_config(cls) -> bool:
        """Validate configuration parameters.

        Returns:
            bool: True if configuration is valid, False otherwise.
        """
        # Check weight thresholds
        if cls.DEFAULT_MIN_WEIGHT >= cls.DEFAULT_MAX_WEIGHT:
            return False

        # Check diameter thresholds
        if cls.DEFAULT_MIN_DIAMETER >= cls.DEFAULT_MAX_DIAMETER:
            return False

        # Check factor sum
        factor_sum = (
            cls.WEIGHT_FACTOR +
            cls.DIAMETER_FACTOR +
            cls.COLOR_FACTOR +
            cls.TEXTURE_FACTOR
        )
        if abs(factor_sum - 1.0) > 0.01:  # Allow small floating point errors
            return False

        # Check color quality thresholds
        if not (0 <= cls.MIN_COLOR_QUALITY <= cls.MAX_COLOR_QUALITY <= 1.0):
            return False

        # Check texture scores
        for score in cls.TEXTURE_SCORES.values():
            if not (0 <= score <= 1.0):
                return False

        return True

# Validate configuration on import
if not ServiceConfig.validate_config():
    raise ValueError("Invalid service configuration detected")

# Factory function for creating evaluators
def create_ripeness_evaluator(
    evaluator_type: str = "default",
    config: Optional[dict] = None
) -> IRipenessEvaluator:
    """Factory function for creating ripeness evaluator instances.

    This function provides a convenient way to create evaluator instances
    with optional configuration customization.

    Args:
        evaluator_type: Type of evaluator to create. Options:
            - "default": Standard RipenessEvaluator
            - "heuristic": HeuristicRipenessEvaluator
        config: Optional configuration dictionary to override defaults.

    Returns:
        IRipenessEvaluator: Configured evaluator instance.

    Raises:
        ValueError: If evaluator_type is not supported.
    """
    if evaluator_type == "default":
        evaluator = RipenessEvaluator()
    elif evaluator_type == "heuristic":
        evaluator = HeuristicRipenessEvaluator()
    else:
        raise ValueError(
            f"Unsupported evaluator type: {evaluator_type}. "
            f"Supported types: 'default', 'heuristic'"
        )

    # Apply custom configuration if provided
    if config:
        for key, value in config.items():
            if hasattr(evaluator, key):
                setattr(evaluator, key, value)
            else:
                raise ValueError(
                    f"Invalid configuration parameter: {key}. "
                    f"Evaluator does not have this attribute."
                )

    return evaluator

# Convenience function for quick evaluation
def evaluate_watermelon_ripeness(
    watermelon: Watermelon,
    evaluator_type: str = "default"
) -> RipenessStatus:
    """Convenience function for quick watermelon ripeness evaluation.

    This function provides a simple interface for evaluating watermelon
    ripeness without needing to manually create evaluator instances.

    Args:
        watermelon: Watermelon instance to evaluate.
        evaluator_type: Type of evaluator to use ('default' or 'heuristic').

    Returns:
        RipenessStatus: The evaluated ripeness status.

    Raises:
        ValueError: If evaluator_type is not supported.
        TypeError: If watermelon is not a valid Watermelon instance.
    """
    if not isinstance(watermelon, Watermelon):
        raise TypeError(
            f"Expected Watermelon instance, got {type(watermelon).__name__}"
        )

    evaluator = create_ripeness_evaluator(evaluator_type)
    return evaluator.evaluate(watermelon)
