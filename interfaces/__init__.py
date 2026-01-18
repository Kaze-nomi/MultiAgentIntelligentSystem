"""
Interfaces package for the project.

This package contains all the interfaces used in the system, including
service interfaces like IWeatherService.
"""

from .i_weather_service import IWeatherService

__all__ = [
    "IWeatherService",
]
