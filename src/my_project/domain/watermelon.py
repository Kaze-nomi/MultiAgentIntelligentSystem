"""
Domain module for watermelon entities.

Contains core domain models and enums for watermelon representation
and ripeness status evaluation.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, validator


class RipenessStatus(str, Enum):
    """Enumeration representing the ripeness status of a watermelon.

    This enum provides type-safe representation of watermelon ripeness
    levels from unripe to overripe.
    """
    UNRIPE = "unripe"
    """Watermelon is not yet ripe and needs more time to mature."""

    EARLY_RIPE = "early_ripe"
    """Watermelon is starting to ripen but not fully ready yet."""

    RIPE = "ripe"
    """Watermelon is perfectly ripe and ready for consumption."""

    LATE_RIPE = "late_ripe"
    """Watermelon is past its peak ripeness but still edible."""

    OVERRIPE = "overripe"
    """Watermelon is too ripe and may have degraded quality."""


class Watermelon(BaseModel):
    """Domain model representing a watermelon with its physical properties.

    This value object encapsulates all the physical characteristics of a watermelon
    that are relevant for ripeness evaluation and quality assessment.

    Attributes:
        weight: Weight of the watermelon in kilograms.
        diameter: Diameter of the watermelon in centimeters.
        color_code: Color code representing the external color (hex format).
        stripe_pattern: Whether the watermelon has characteristic stripes.
        spot_size: Size of the yellow spot where it rested on the ground (cm).
        sound_hollowness: Perceived hollowness when tapped (1-10 scale).
        surface_texture: Surface texture description.
    """

    weight: float = Field(
        ...,
        ge=0.5,
        le=30.0,
        description="Weight of the watermelon in kilograms"
    )

    diameter: float = Field(
        ...,
        ge=10.0,
        le=80.0,
        description="Diameter of the watermelon in centimeters"
    )

    color_code: str = Field(
        ...,
        regex=r'^#[0-9A-Fa-f]{6}$',
        description="Hex color code representing the external color"
    )

    stripe_pattern: bool = Field(
        default=True,
        description="Whether the watermelon has characteristic stripes"
    )

    spot_size: Optional[float] = Field(
        None,
        ge=0.0,
        le=20.0,
        description="Size of the yellow spot where it rested on ground (cm)"
    )

    sound_hollowness: Optional[int] = Field(
        None,
        ge=1,
        le=10,
        description="Perceived hollowness when tapped (1-10 scale)"
    )

    surface_texture: Optional[str] = Field(
        None,
        max_length=50,
        description="Surface texture description"
    )

    class Config:
        """Pydantic configuration for Watermelon model."""
        validate_assignment = True
        use_enum_values = True
        extra = "forbid"

    @validator('weight')
    def validate_weight(cls, v: float) -> float:
        """Validate weight is within reasonable bounds for a watermelon.

        Args:
            v: Weight value in kilograms.

        Returns:
            Validated weight value.

        Raises:
            ValueError: If weight is outside reasonable range.
        """
        if v < 0.5:
            raise ValueError("Watermelon weight too small (minimum 0.5 kg)")
        if v > 30.0:
            raise ValueError("Watermelon weight too large (maximum 30 kg)")
        return v

    @validator('diameter')
    def validate_diameter(cls, v: float) -> float:
        """Validate diameter is within reasonable bounds for a watermelon.

        Args:
            v: Diameter value in centimeters.

        Returns:
            Validated diameter value.

        Raises:
            ValueError: If diameter is outside reasonable range.
        """
        if v < 10.0:
            raise ValueError("Watermelon diameter too small (minimum 10 cm)")
        if v > 80.0:
            raise ValueError("Watermelon diameter too large (maximum 80 cm)")
        return v

    @validator('color_code')
    def validate_color_code(cls, v: str) -> str:
        """Validate color code is a valid hex color.

        Args:
            v: Color code string.

        Returns:
            Validated color code in uppercase.

        Raises:
            ValueError: If color code is not a valid hex color.
        """
        if not v.startswith('#'):
            raise ValueError("Color code must start with '#'")
        try:
            int(v[1:], 16)
        except ValueError:
            raise ValueError("Color code must be valid hex color")
        return v.upper()

    @validator('surface_texture')
    def validate_surface_texture(cls, v: Optional[str]) -> Optional[str]:
        """Validate surface texture if provided.

        Args:
            v: Surface texture description.

        Returns:
            Validated surface texture.

        Raises:
            ValueError: If texture contains invalid characters.
        """
        if v is not None:
            if not v.strip():
                raise ValueError("Surface texture cannot be empty")
            if any(char.isdigit() for char in v):
                raise ValueError("Surface texture should not contain numbers")
        return v.strip() if v else None

    def get_density(self) -> float:
        """Calculate approximate density of the watermelon.

        Returns:
            Density in kg/cm³ calculated from weight and diameter.
        """
        # Approximate volume of sphere: V = 4/3 * π * r³
        radius = self.diameter / 2
        volume = (4.0 / 3.0) * 3.14159 * (radius ** 3)
        return self.weight / volume if volume > 0 else 0.0

    def is_oval_shaped(self) -> bool:
        """Determine if watermelon is likely oval-shaped based on weight to diameter ratio.

        Returns:
            True if likely oval-shaped, False if likely round.
        """
        # Higher weight for given diameter suggests oval shape
        density = self.get_density()
        return density > 0.0001  # Threshold for oval shape

    def __str__(self) -> str:
        """String representation of the watermelon.

        Returns:
            Human-readable description of the watermelon.
        """
        return (
            f"Watermelon(weight={self.weight}kg, "
            f"diameter={self.diameter}cm, "
            f"color={self.color_code}, "
            f"striped={self.stripe_pattern})"
        )

    def __repr__(self) -> str:
        """Detailed string representation of the watermelon.

        Returns:
            Detailed representation including all attributes.
        """
        return (
            f"Watermelon(weight={self.weight}, diameter={self.diameter}, "
            f"color_code='{self.color_code}', stripe_pattern={self.stripe_pattern}, "
            f"spot_size={self.spot_size}, sound_hollowness={self.sound_hollowness}, "
            f"surface_texture={self.surface_texture})"
        )
