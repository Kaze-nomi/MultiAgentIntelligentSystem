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
            raise ValueError("API key is required for weather service")

    def get_weather(self, city: str) -> WeatherData:
        """
        Retrieve weather data for a given city.

        This method makes an API call to OpenWeatherMap to fetch current weather information
        for the specified city and returns it as a structured WeatherData object.

        Args:
            city (str): The name of the city to get weather for.

        Returns:
            WeatherData: The structured weather data for the city.

        Raises:
            ValueError: If the city name is invalid or empty.
            ConnectionError: If there is an issue connecting to the weather service.
            RuntimeError: If the weather data cannot be retrieved or parsed.
        """
        if not city or not isinstance(city, str) or city.strip() == '':
            raise ValueError("City name must be a non-empty string")

        url = f"https://api.openweathermap.org/data/2.5/weather?q={city.strip()}&appid={self.api_key}&units=metric"

        try:
            response = httpx.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            # Extract relevant data from the API response
            city_name = data.get('name')
            if not city_name:
                raise RuntimeError("City name not found in API response")

            main = data.get('main', {})
            weather = data.get('weather', [{}])[0]
            wind = data.get('wind', {})

            temperature = main.get('temp')
            if temperature is None:
                raise RuntimeError("Temperature data not available")

            description = weather.get('description')
            if not description:
                raise RuntimeError("Weather description not available")

            humidity = main.get('humidity')
            wind_speed = wind.get('speed')

            return WeatherData(
                city=city_name,
                temperature=temperature,
                description=description,
                humidity=humidity,
                wind_speed=wind_speed,
                timestamp=datetime.utcnow()
            )

        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Failed to retrieve weather data: HTTP {e.response.status_code} - {e.response.text}")
        except httpx.TimeoutException:
            raise ConnectionError("Request timed out while connecting to weather service")
        except httpx.RequestError as e:
            raise ConnectionError(f"Connection error while accessing weather service: {str(e)}")
        except (KeyError, TypeError) as e:
            raise RuntimeError(f"Invalid or unexpected response format from weather service: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error occurred: {str(e)}")
