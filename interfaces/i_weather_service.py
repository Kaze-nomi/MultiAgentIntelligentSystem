from abc import ABC, abstractmethod
from typing import Optional

from data.weather_data import WeatherData


class IWeatherService(ABC):
    """
    Interface for weather service.

    This interface defines the contract for retrieving weather data.
    Implementations should provide the actual logic for fetching weather
    information from external APIs or sources.
    """

    @abstractmethod
    def get_weather(self, city: str) -> WeatherData:
        """
        Retrieve weather data for a given city.

        Args:
            city (str): The name of the city to get weather for.

        Returns:
            WeatherData: The structured weather data for the city.

        Raises:
            ValueError: If the city name is invalid or empty.
            ConnectionError: If there is an issue connecting to the weather service.
            RuntimeError: If the weather data cannot be retrieved or parsed.
        """
        pass
