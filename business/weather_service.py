from interfaces.i_weather_service import IWeatherService
from data.weather_data import WeatherData
import httpx
from typing import Optional
import os
from datetime import datetime


class WeatherService(IWeatherService):
    """
    Implementation of the weather service interface.

    This class provides functionality to retrieve current weather data for a given city
    using the OpenWeatherMap API. It handles API calls, response parsing, and error handling.

    Attributes:
        api_key (str): The API key for accessing the OpenWeatherMap service.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the WeatherService with an API key.

        Args:
            api_key (Optional[str]): The API key for OpenWeatherMap. If not provided,
                                     it will be retrieved from the environment variable 'OPENWEATHER_API_KEY'.

        Raises:
            ValueError: If no API key is provided or found in the environment.
        """
        self.api_key = api_key or os.getenv('OPENWEATHER_API_KEY')
        if not self.api_key:
            raise ValueError("API key for OpenWeatherMap is required. Provide it as a parameter or set the 'OPENWEATHER_API_KEY' environment variable.")

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
        if not city or not isinstance(city, str) or not city.strip():
            raise ValueError("City name must be a non-empty string.")

        city = city.strip()
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.api_key}&units=metric"

        try:
            response = httpx.get(url, timeout=10.0)
            response.raise_for_status()
        except httpx.TimeoutException:
            raise ConnectionError(f"Timeout occurred while fetching weather data for city: {city}.")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise RuntimeError(f"Invalid API key provided.")
            elif e.response.status_code == 404:
                raise ValueError(f"City '{city}' not found.")
            else:
                raise RuntimeError(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            raise ConnectionError(f"Network error occurred while fetching weather data for city: {city}. Details: {str(e)}")

        try:
            data = response.json()
            weather_main = data['weather'][0]['main']
            weather_description = data['weather'][0]['description']
            temperature = data['main']['temp']
            humidity = data['main'].get('humidity')
            wind_speed = data['wind'].get('speed') if 'wind' in data else None

            weather_data = WeatherData(
                city=city,
                temperature=temperature,
                description=f"{weather_main}: {weather_description}",
                humidity=humidity,
                wind_speed=wind_speed,
                timestamp=datetime.utcnow()
            )
            return weather_data
        except KeyError as e:
            raise RuntimeError(f"Unexpected response structure from weather API. Missing key: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Failed to parse weather data for city: {city}. Details: {str(e)}")
