# infrastructure/arbuz_client/models.py

from typing import Dict, Optional, Any
from pydantic import BaseModel, Field


class ArbuzRequest(BaseModel):
    """Model representing a request to the ARBUZ API.

    This model encapsulates the data needed to make a request to the ARBUZ API,
    including the endpoint, optional parameters, and optional data payload.

    Attributes:
        endpoint (str): The API endpoint to target.
        params (Optional[Dict[str, Any]]): Optional query parameters for the request.
        data (Optional[Dict[str, Any]]): Optional data payload for POST requests.
    """
    endpoint: str = Field(..., description="The API endpoint to target")
    params: Optional[Dict[str, Any]] = Field(None, description="Optional query parameters for the request")
    data: Optional[Dict[str, Any]] = Field(None, description="Optional data payload for POST requests")


class ArbuzResponse(BaseModel):
    """Model representing a response from the ARBUZ API.

    This model encapsulates the data received from the ARBUZ API,
    including status information, response data, and any errors.

    Attributes:
        status_code (int): The HTTP status code of the response.
        data (Optional[Dict[str, Any]]): The response data, if any.
        error (Optional[str]): An error message, if the request failed.
        success (bool): Indicates if the request was successful.
    """
    status_code: int = Field(..., description="The HTTP status code of the response")
    data: Optional[Dict[str, Any]] = Field(None, description="The response data, if any")
    error: Optional[str] = Field(None, description="An error message, if the request failed")
    success: bool = Field(..., description="Indicates if the request was successful")

    @classmethod
    def from_success(cls, status_code: int, data: Dict[str, Any]) -> "ArbuzResponse":
        """Create a successful response.

        Args:
            status_code (int): The HTTP status code.
            data (Dict[str, Any]): The response data.

        Returns:
            ArbuzResponse: A successful response instance.
        """
        return cls(status_code=status_code, data=data, success=True)

    @classmethod
    def from_error(cls, status_code: int, error: str) -> "ArbuzResponse":
        """Create an error response.

        Args:
            status_code (int): The HTTP status code.
            error (str): The error message.

        Returns:
            ArbuzResponse: An error response instance.
        """
        return cls(status_code=status_code, error=error, success=False)
