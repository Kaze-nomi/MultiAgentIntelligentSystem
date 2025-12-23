# tests/test_arbuz_client.py

"""
Unit tests for ArbuzClient and IArbuzClient.

This module contains comprehensive unit tests for the ArbuzClient implementation
and the IArbuzClient interface. Tests use mocking to simulate HTTP requests
and ensure proper error handling.
"""

import unittest
from unittest.mock import patch, MagicMock
from typing import Dict, Optional

from infrastructure.arbuz_client import ArbuzClient, IArbuzClient, ArbuzRequest, ArbuzResponse


class TestArbuzClient(unittest.TestCase):
    """Test cases for the ArbuzClient class.

    This class tests the concrete implementation of the ArbuzClient,
    focusing on GET and POST operations, error handling, and response parsing.
    """

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.base_url = "http://test.arbuz.api"
        self.api_key = "test_api_key"
        self.client = ArbuzClient(base_url=self.base_url, api_key=self.api_key, timeout=10)

    @patch('infrastructure.arbuz_client.client.requests.get')
    def test_get_data_success(self, mock_get):
        """Test successful GET request."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "value"}
        mock_get.return_value = mock_response

        result = self.client.get_data(endpoint="/test", params={"param": "value"})

        self.assertEqual(result, {"key": "value"})
        mock_get.assert_called_once_with(
            f"{self.base_url}/test",
            headers={"Authorization": f"Bearer {self.api_key}"},
            params={"param": "value"},
            timeout=10
        )

    @patch('infrastructure.arbuz_client.client.requests.get')
    def test_get_data_failure(self, mock_get):
        """Test GET request failure."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("Not Found")
        mock_get.return_value = mock_response

        with self.assertRaises(Exception):
            self.client.get_data(endpoint="/test")

    @patch('infrastructure.arbuz_client.client.requests.post')
    def test_post_data_success(self, mock_post):
        """Test successful POST request."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"created": True}
        mock_post.return_value = mock_response

        data = {"name": "test"}
        result = self.client.post_data(endpoint="/create", data=data)

        self.assertEqual(result, {"created": True})
        mock_post.assert_called_once_with(
            f"{self.base_url}/create",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=data,
            timeout=10
        )

    @patch('infrastructure.arbuz_client.client.requests.post')
    def test_post_data_failure(self, mock_post):
        """Test POST request failure."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Internal Server Error")
        mock_post.return_value = mock_response

        with self.assertRaises(Exception):
            self.client.post_data(endpoint="/create", data={})

    def test_init_without_api_key(self):
        """Test initialization without API key."""
        client = ArbuzClient(base_url=self.base_url)
        self.assertIsNone(client.api_key)


class TestIArbuzClient(unittest.TestCase):
    """Test cases for the IArbuzClient interface.

    This class tests that IArbuzClient is an abstract base class
    and cannot be instantiated directly.
    """

    def test_abstract_methods(self):
        """Test that abstract methods raise NotImplementedError."""
        # Attempting to instantiate should fail
        with self.assertRaises(TypeError):
            IArbuzClient()

        # Create a mock subclass to test method calls
        class MockArbuzClient(IArbuzClient):
            def get_data(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict[str, str]:
                return {"mock": "data"}

            def post_data(self, endpoint: str, data: Dict[str, str]) -> Dict[str, str]:
                return {"posted": "data"}

        mock_client = MockArbuzClient()
        self.assertEqual(mock_client.get_data("/test"), {"mock": "data"})
        self.assertEqual(mock_client.post_data("/test", {"key": "value"}), {"posted": "data"})


if __name__ == '__main__':
    unittest.main()
