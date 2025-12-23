# infrastructure/arbuz_client/interfaces.py

from abc import ABC, abstractmethod
from typing import Dict, Optional


class IArbuzClient(ABC):
    """Interface for the Arbuz API client.

    This abstract base class defines the contract for interacting with the ARBUZ API,
    including methods for retrieving and sending data.
    """

    @abstractmethod
    def get_data(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Retrieve data from the specified endpoint.

        Args:
            endpoint (str): The API endpoint to query.
            params (Optional[Dict[str, str]]): Optional query parameters.

        Returns:
            Dict[str, str]: The response data as a dictionary.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError("Subclasses must implement get_data method.")

    @abstractmethod
    def post_data(self, endpoint: str, data: Dict[str, str]) -> Dict[str, str]:
        """Send data to the specified endpoint.

        Args:
            endpoint (str): The API endpoint to send data to.
            data (Dict[str, str]): The data to send in the request body.

        Returns:
            Dict[str, str]: The response data as a dictionary.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError("Subclasses must implement post_data method.")
