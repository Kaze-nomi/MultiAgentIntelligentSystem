"""
Domain package for watermelon entities.

This package contains core domain models and enums for watermelon representation,
ripeness status evaluation, and related domain logic.

Main exports:
    - Watermelon: Domain model representing a watermelon with physical properties
    - RipenessStatus: Enum representing ripeness status levels
    - Config: Configuration class for domain models

Example usage:
    from src.my_project.domain import Watermelon, RipenessStatus

    watermelon = Watermelon(
        weight=5000.0,
        diameter=30.0,
        color_code="#4CAF50",
        surface_texture="smooth"
    )

    if watermelon.ripeness_status == RipenessStatus.RIPE:
        print("Watermelon is ready to eat!")
"""

from .watermelon import Watermelon, RipenessStatus, Config

__all__ = [
    "Watermelon",
    "RipenessStatus",
    "Config"
]

__version__ = "1.0.0"
__author__ = "My Project Team"
__description__ = "Domain models for watermelon representation and evaluation"
