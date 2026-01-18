import unittest
from data.weather_data import WeatherData
from pydantic import ValidationError
from datetime import datetime
from typing import Optional


class TestWeatherData(unittest.TestCase):
    """
    Test suite for the WeatherData class.

    This class tests the functionality of the WeatherData Pydantic model,
    including successful creation, field validation, optional fields, and error handling.
    """

    def test_create_weather_data_with_all_fields(self):
        """
        Test creating WeatherData instance with all fields provided.
        """
        # Arrange
        city = "Moscow"
        temperature = 15.5
        description = "clear sky"
        humidity = 60
        wind_speed = 3.2
        timestamp = datetime(2023, 10, 1, 12, 0, 0)

        # Act
        weather_data = WeatherData(
            city=city,
            temperature=temperature,
            description=description,
            humidity=humidity,
            wind_speed=wind_speed,
            timestamp=timestamp
        )

        # Assert
        self.assertEqual(weather_data.city, city)
        self.assertEqual(weather_data.temperature, temperature)
        self.assertEqual(weather_data.description, description)
        self.assertEqual(weather_data.humidity, humidity)
        self.assertEqual(weather_data.wind_speed, wind_speed)
        self.assertEqual(weather_data.timestamp, timestamp)

    def test_create_weather_data_with_required_fields_only(self):
        """
        Test creating WeatherData instance with only required fields.
        """
        # Arrange
        city = "London"
        temperature = 20.0
        description = "sunny"

        # Act
        weather_data = WeatherData(
            city=city,
            temperature=temperature,
            description=description
        )

        # Assert
        self.assertEqual(weather_data.city, city)
        self.assertEqual(weather_data.temperature, temperature)
        self.assertEqual(weather_data.description, description)
        self.assertIsNone(weather_data.humidity)
        self.assertIsNone(weather_data.wind_speed)
        self.assertIsInstance(weather_data.timestamp, datetime)

    def test_default_timestamp(self):
        """
        Test that timestamp defaults to current UTC time if not provided.
        """
        # Arrange
        city = "Tokyo"
        temperature = 25.0
        description = "cloudy"
        before_creation = datetime.utcnow()

        # Act
        weather_data = WeatherData(
            city=city,
            temperature=temperature,
            description=description
        )
        after_creation = datetime.utcnow()

        # Assert
        self.assertGreaterEqual(weather_data.timestamp, before_creation)
        self.assertLessEqual(weather_data.timestamp, after_creation)

    def test_validation_error_for_missing_required_field_city(self):
        """
        Test that ValidationError is raised when required field 'city' is missing.
        """
        # Act & Assert
        with self.assertRaises(ValidationError) as context:
            WeatherData(
                temperature=10.0,
                description="rainy"
            )
        self.assertIn("city", str(context.exception))

    def test_validation_error_for_missing_required_field_temperature(self):
        """
        Test that ValidationError is raised when required field 'temperature' is missing.
        """
        # Act & Assert
        with self.assertRaises(ValidationError) as context:
            WeatherData(
                city="Paris",
                description="windy"
            )
        self.assertIn("temperature", str(context.exception))

    def test_validation_error_for_missing_required_field_description(self):
        """
        Test that ValidationError is raised when required field 'description' is missing.
        """
        # Act & Assert
        with self.assertRaises(ValidationError) as context:
            WeatherData(
                city="Berlin",
                temperature=5.0
            )
        self.assertIn("description", str(context.exception))

    def test_validation_error_for_invalid_temperature_type(self):
        """
        Test that ValidationError is raised when 'temperature' is not a float.
        """
        # Act & Assert
        with self.assertRaises(ValidationError) as context:
            WeatherData(
                city="Rome",
                temperature="hot",
                description="sunny"
            )
        self.assertIn("temperature", str(context.exception))

    def test_validation_error_for_invalid_humidity_type(self):
        """
        Test that ValidationError is raised when 'humidity' is not an int.
        """
        # Act & Assert
        with self.assertRaises(ValidationError) as context:
            WeatherData(
                city="Madrid",
                temperature=30.0,
                description="hot",
                humidity="high"
            )
        self.assertIn("humidity", str(context.exception))

    def test_validation_error_for_invalid_wind_speed_type(self):
        """
        Test that ValidationError is raised when 'wind_speed' is not a float.
        """
        # Act & Assert
        with self.assertRaises(ValidationError) as context:
            WeatherData(
                city="Athens",
                temperature=28.0,
                description="breezy",
                wind_speed="fast"
            )
        self.assertIn("wind_speed", str(context.exception))

    def test_optional_fields_can_be_none(self):
        """
        Test that optional fields can be explicitly set to None.
        """
        # Arrange
        city = "Sydney"
        temperature = 22.0
        description = "pleasant"

        # Act
        weather_data = WeatherData(
            city=city,
            temperature=temperature,
            description=description,
            humidity=None,
            wind_speed=None
        )

        # Assert
        self.assertIsNone(weather_data.humidity)
        self.assertIsNone(weather_data.wind_speed)


if __name__ == '__main__':
    unittest.main()
