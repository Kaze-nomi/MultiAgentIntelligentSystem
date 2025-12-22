"""Domain module for my_project.

This module contains domain models and business logic for the application.
Currently includes the Bublik model for representing sweet bagels.
"""

from typing import Any

try:
    from .bublik import Bublik
except ImportError as e:
    raise ImportError(
        "Failed to import Bublik from bublik module. "
        "Ensure that bublik.py exists in the same directory."
    ) from e


__all__: list[str] = ["Bublik"]

__version__: str = "1.0.0"

# Module-level attributes for better introspection
__author__: str = "My Project Team"
__description__: str = "Domain models for my_project application"


def get_domain_models() -> dict[str, Any]:
    """Get all available domain models.

    Returns:
        dict[str, Any]: Dictionary containing all exported domain models.
    """
    return {name: globals()[name] for name in __all__ if name in globals()}


def __dir__() -> list[str]:
    """Return list of attributes for dir() on the module.

    Returns:
        list[str]: List of public attributes and functions.
    """
    return sorted(
        list(globals().keys()) + __all__
    )
