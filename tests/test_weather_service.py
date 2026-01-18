import unittest
from unittest.mock import patch, MagicMock
from business.weather_service import WeatherService
from data.weather_data import WeatherData
from interfaces.i_weather_service import IWeatherService


class TestWeatherService(unittest.TestCase):
    """
    Test suite for the WeatherService class.

    This class tests the functionality of the WeatherService, including
    successful weather retrieval and error handling scenarios.
    """

    def setUp(self):
        """
        Set up test fixtures before each test method.
        """
        self.api_key = "test_api_key"
        self.weather_service = WeatherService(api_key=self.api_key)

    @patch('business.weather_service.httpx.get')
    def test_get_weather_success(self, mock_get):
        """
        Test successful retrieval of weather data.
        """
        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "name": "London",
            "main": {
                "temp": 15.0,
                "humidity": 80
            },
            "weather": [{"description": "clear sky"}],
            "wind": {"speed": 5.0}
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Call the method
        result = self.weather_service.get_weather("London")

        # Assertions
        self.assertIsInstance(result, WeatherData)
        self.assertEqual(result.city, "London")
        self.assertEqual(result.temperature, 15.0)
        self.assertEqual(result.description, "clear sky")
        self.assertEqual(result.humidity, 80)
        self.assertEqual(result.wind_speed, 5.0)
        self.assertIsNotNone(result.timestamp)

    @patch('business.weather_service.httpx.get')
    def test_get_weather_invalid_city(self, mock_get):
        """
        Test handling of invalid city name.
        """
        # Mock the API response for invalid city
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("City not found")
        mock_get.return_value = mock_response

        # Call the method and expect RuntimeError
        with self.assertRaises(RuntimeError):
            self.weather_service.get_weather("InvalidCity")

    @patch('business.weather_service.httpx.get')
    def test_get_weather_connection_error(self, mock_get):
        """
        Test handling of connection errors.
        """
        # Mock connection error
        mock_get.side_effect = ConnectionError("Network error")

        # Call the method and expect ConnectionError
        with self.assertRaises(ConnectionError):
            self.weather_service.get_weather("London")

    def test_init_without_api_key(self):
        """
        Test initialization without API key, expecting ValueError.
        """
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(ValueError):
                WeatherService()

    def test_init_with_env_api_key(self):
        """
        Test initialization using API key from environment variable.
        """
        with patch.dict('os.environ', {'OPENWEATHER_API_KEY': 'env_api_key'}):
            service = WeatherService()
            self.assertEqual(service.api_key, 'env_api_key')

    @patch('business.weather_service.httpx.get')
    def test_get_weather_empty_city(self, mock_get):
        """
        Test handling of empty city name.
        """
        # Call the method with empty string and expect ValueError
        with self.assertRaises(ValueError):
            self.weather_service.get_weather("")


if __name__ == '__main__':
    unittest.main()
