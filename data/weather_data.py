from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class WeatherData(BaseModel):
    """
    Data model representing weather information for a specific city.

    This model encapsulates structured weather data retrieved from an external weather service.
    It includes essential weather parameters such as temperature, humidity, and description.

    Attributes:
        city (str): The name of the city for which the weather data is provided.
        temperature (float): The current temperature in Celsius.
        description (str): A textual description of the current weather conditions (e.g., 'clear sky', 'rainy').
        humidity (Optional[int]): The humidity percentage, if available.
        wind_speed (Optional[float]): The wind speed in meters per second, if available.
        timestamp (datetime): The timestamp when the weather data was retrieved.
    """
    city: str = Field(..., description="The name of the city")
    temperature: float = Field(..., description="Current temperature in Celsius")
    description: str = Field(..., description="Weather description")
    humidity: Optional[int] = Field(None, description="Humidity percentage")
    wind_speed: Optional[float] = Field(None, description="Wind speed in m/s")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Time of data retrieval")
