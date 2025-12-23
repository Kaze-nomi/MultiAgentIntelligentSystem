# infrastructure/arbuz_client/client.py

"""
Arbuz Client Implementation

This module provides the concrete implementation of the Arbuz API client,
implementing the IArbuzClient interface. It handles HTTP requests to the ARBUZ API,
including GET and POST operations, with proper error handling and response parsing.
"""

import requests
from typing import Dict, Optional

from .interfaces import IArbuzClient
from .models import ArbuzRequest, ArbuzResponse


class ArbuzClient(IArbuzClient):
    """Concrete implementation of the Arbuz API client.

    This class provides methods to interact with the ARBUZ API by sending GET and POST requests.
    It handles authentication, error responses, and data serialization using Pydantic models.

    Attributes:
        base_url (str): The base URL of the ARBUZ API.
        api_key (Optional[str]): Optional API key for authentication.
        timeout (int): Request timeout in seconds (default: 30).
    """

    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: int = 30):
        """Initialize the Arbuz client.

        Args:
            base_url (str): The base URL of the ARBUZ API.
            api_key (Optional[str]): Optional API key for authentication.
            timeout (int): Request timeout in seconds.
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({'Authorization': f'Bearer {self.api_key}'})

    def get_data(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Retrieve data from the specified endpoint using a GET request.

        Args:
            endpoint (str): The API endpoint to query (relative to base_url).
            params (Optional[Dict[str, str]]): Optional query parameters.

        Returns:
            Dict[str, str]: A dictionary containing the response data with keys:
                - 'status_code': HTTP status code.
                - 'data': Response data if successful, None otherwise.
                - 'error': Error message if any, None otherwise.

        Raises:
            requests.RequestException: If there's a network-related error.
        """
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()  # Raise for bad status codes
            arbuz_response = ArbuzResponse.from_success(
                status_code=response.status_code,
                data=response.json() if response.content else {}
            )
            return arbuz_response.model_dump()
        except requests.RequestException as e:
            arbuz_response = ArbuzResponse.from_error(
                status_code=getattr(e.response, 'status_code', 500) if hasattr(e, 'response') else 500,
                error=str(e)
            )
            return arbuz_response.model_dump()
        except ValueError as e:
            # JSON parsing error
            arbuz_response = ArbuzResponse.from_error(
                status_code=500,
                error=f"Invalid JSON response: {str(e)}"
            )
            return arbuz_response.model_dump()

    def post_data(self, endpoint: str, data: Dict[str, str]) -> Dict[str, str]:
        """Send data to the specified endpoint using a POST request.

        Args:
            endpoint (str): The API endpoint to send data to (relative to base_url).
            data (Dict[str, str]): The data payload to send.

        Returns:
            Dict[str, str]: A dictionary containing the response data with keys:
                - 'status_code': HTTP status code.
                - 'data': Response data if successful, None otherwise.
                - 'error': Error message if any, None otherwise.

        Raises:
            requests.RequestException: If there's a network-related error.
        """
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            response = self.session.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()  # Raise for bad status codes
            arbuz_response = ArbuzResponse.from_success(
                status_code=response.status_code,
                data=response.json() if response.content else {}
            )
            return arbuz_response.model_dump()
        except requests.RequestException as e:
            arbuz_response = ArbuzResponse.from_error(
                status_code=getattr(e.response, 'status_code', 500) if hasattr(e, 'response') else 500,
                error=str(e)
            )
            return arbuz_response.model_dump()
        except ValueError as e:
            # JSON parsing error
            arbuz_response = ArbuzResponse.from_error(
                status_code=500,
                error=f"Invalid JSON response: {str(e)}"
            )
            return arbuz_response.model_dump()
