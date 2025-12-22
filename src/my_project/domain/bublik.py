"""Domain model for Bublik (bagel) entities.

This module defines the Bublik class which represents a bagel-like pastry
with attributes such as name, filling, price, and unique identifier.
Uses Pydantic for data validation and serialization.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional, Union

from pydantic import BaseModel, Field, validator, confloat, constr


class Bublik(BaseModel):
    """Represents a sweet bagel (bublik) with its attributes.

    Attributes:
        id: Unique identifier for the bublik instance.
        name: Name of the bublik (must be non-empty).
        filling: Type of filling inside the bublik.
        price: Price of the bublik in decimal format.
        is_sweet: Boolean flag indicating if the bublik is sweet.
        description: Optional description of the bublik.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier")
    name: constr(min_length=1, max_length=100) = Field(
        ..., description="Name of the bublik"
    )
    filling: constr(min_length=1, max_length=50) = Field(
        ..., description="Type of filling"
    )
    price: confloat(gt=0, ge=0.01) = Field(
        ..., description="Price must be positive"
    )
    is_sweet: bool = Field(default=True, description="Whether the bublik is sweet")
    description: Optional[constr(max_length=500)] = Field(
        None, description="Optional description"
    )

    @validator('price')
    def validate_price(cls, v: Union[float, Decimal]) -> Decimal:
        """Validate and convert price to Decimal for precision.

        Args:
            v: The price value to validate.

        Returns:
            Decimal: The validated price as Decimal.

        Raises:
            ValueError: If price is negative or has too many decimal places.
        """
        if isinstance(v, float):
            # Convert float to string first to avoid floating point precision issues
            v = str(v)

        try:
            decimal_price = Decimal(str(v))
        except Exception as e:
            raise ValueError(f"Invalid price format: {v}") from e

        if decimal_price <= 0:
            raise ValueError("Price must be positive")

        # Ensure price has at most 2 decimal places
        if decimal_price.as_tuple().exponent < -2:
            raise ValueError("Price cannot have more than 2 decimal places")

        return decimal_price

    @validator('name', 'filling')
    def validate_strings(cls, v: str) -> str:
        """Validate string fields.

        Args:
            v: The string value to validate.

        Returns:
            str: The validated and normalized string.

        Raises:
            ValueError: If the string contains only whitespace.
        """
        if not v or not v.strip():
            raise ValueError("Value cannot be empty or whitespace only")
        return v.strip().title()

    def get_price_with_currency(self, currency: str = "RUB") -> str:
        """Get formatted price with currency symbol.

        Args:
            currency: Currency code (default: RUB).

        Returns:
            str: Formatted price string with currency.
        """
        currency_symbols = {
            "RUB": "₽",
            "USD": "$",
            "EUR": "€",
        }
        symbol = currency_symbols.get(currency.upper(), currency)
        return f"{self.price:.2f} {symbol}"

    def is_expensive(self, threshold: Decimal = Decimal("100.00")) -> bool:
        """Check if the bublik is considered expensive.

        Args:
            threshold: Price threshold to consider as expensive.

        Returns:
            bool: True if price exceeds threshold, False otherwise.
        """
        return self.price > threshold

    def update_price(self, new_price: Union[float, Decimal, str]) -> None:
        """Update the price of the bublik.

        Args:
            new_price: The new price to set.

        Raises:
            ValueError: If the new price is invalid.
        """
        try:
            validated_price = self.validate_price(new_price)
            self.price = validated_price
        except Exception as e:
            raise ValueError(f"Failed to update price: {e}") from e

    class Config:
        """Pydantic configuration for Bublik model."""

        json_encoders = {
            uuid.UUID: lambda v: str(v),
            Decimal: lambda v: float(v),
        }
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Chocolate Dream",
                "filling": "Chocolate Cream",
                "price": 45.50,
                "is_sweet": True,
                "description": "Delicious chocolate-filled bublik",
            }
        }
