"""Test module for watermelon domain models.

This module contains comprehensive unit tests for the Watermelon domain model
and RipenessStatus enum, ensuring proper validation, behavior, and edge case
handling.
"""

import pytest
from pydantic import ValidationError
from src.my_project.domain import Watermelon, RipenessStatus, Config


class TestRipenessStatus:
    """Test cases for RipenessStatus enum."""

    def test_ripeness_status_values(self):
        """Test that all enum values are correctly defined."""
        assert RipenessStatus.UNRIPE.value == "unripe"
        assert RipenessStatus.EARLY_RIPE.value == "early_ripe"
        assert RipenessStatus.RIPE.value == "ripe"
        assert RipenessStatus.LATE_RIPE.value == "late_ripe"
        assert RipenessStatus.OVERRIPE.value == "overripe"

    def test_ripeness_status_ordering(self):
        """Test that ripeness status follows logical progression."""
        statuses = list(RipenessStatus)
        expected_order = [
            RipenessStatus.UNRIPE,
            RipenessStatus.EARLY_RIPE,
            RipenessStatus.RIPE,
            RipenessStatus.LATE_RIPE,
            RipenessStatus.OVERRIPE
        ]
        assert statuses == expected_order

    def test_ripeness_status_string_representation(self):
        """Test string representation of enum values."""
        assert str(RipenessStatus.RIPE) == "ripe"
        assert repr(RipenessStatus.RIPE) == "<RipenessStatus.RIPE: 'ripe'>"

    def test_ripeness_status_equality(self):
        """Test equality comparison between enum values."""
        assert RipenessStatus.RIPE == RipenessStatus.RIPE
        assert RipenessStatus.RIPE != RipenessStatus.UNRIPE
        assert RipenessStatus.RIPE == "ripe"

    def test_ripeness_status_iteration(self):
        """Test that enum can be iterated."""
        all_statuses = list(RipenessStatus)
        assert len(all_statuses) == 5
        assert RipenessStatus.RIPE in all_statuses


class TestWatermelon:
    """Test cases for Watermelon domain model."""

    def test_watermelon_creation_valid_data(self):
        """Test successful creation of Watermelon with valid data."""
        watermelon = Watermelon(
            weight=5000.0,
            diameter=30.0,
            color_code="#4CAF50",
            surface_texture="smooth"
        )

        assert watermelon.weight == 5000.0
        assert watermelon.diameter == 30.0
        assert watermelon.color_code == "#4CAF50"
        assert watermelon.surface_texture == "smooth"
        assert watermelon.ripeness_status == RipenessStatus.UNRIPE  # Default value

    def test_watermelon_creation_with_ripeness(self):
        """Test creation of Watermelon with specified ripeness status."""
        watermelon = Watermelon(
            weight=6000.0,
            diameter=35.0,
            color_code="#FF5722",
            surface_texture="rough",
            ripeness_status=RipenessStatus.RIPE
        )

        assert watermelon.ripeness_status == RipenessStatus.RIPE

    def test_watermelon_weight_validation(self):
        """Test weight validation constraints."""
        # Valid weight
        watermelon = Watermelon(
            weight=1000.0,
            diameter=20.0,
            color_code="#4CAF50",
            surface_texture="smooth"
        )
        assert watermelon.weight == 1000.0

        # Invalid weight - too small
        with pytest.raises(ValidationError, match="Weight must be between"):
            Watermelon(
                weight=100.0,
                diameter=20.0,
                color_code="#4CAF50",
                surface_texture="smooth"
            )

        # Invalid weight - too large
        with pytest.raises(ValidationError, match="Weight must be between"):
            Watermelon(
                weight=50000.0,
                diameter=20.0,
                color_code="#4CAF50",
                surface_texture="smooth"
            )

        # Invalid weight - negative
        with pytest.raises(ValidationError, match="Weight must be between"):
            Watermelon(
                weight=-1000.0,
                diameter=20.0,
                color_code="#4CAF50",
                surface_texture="smooth"
            )

    def test_watermelon_diameter_validation(self):
        """Test diameter validation constraints."""
        # Valid diameter
        watermelon = Watermelon(
            weight=5000.0,
            diameter=25.0,
            color_code="#4CAF50",
            surface_texture="smooth"
        )
        assert watermelon.diameter == 25.0

        # Invalid diameter - too small
        with pytest.raises(ValidationError, match="Diameter must be between"):
            Watermelon(
                weight=5000.0,
                diameter=5.0,
                color_code="#4CAF50",
                surface_texture="smooth"
            )

        # Invalid diameter - too large
        with pytest.raises(ValidationError, match="Diameter must be between"):
            Watermelon(
                weight=5000.0,
                diameter=100.0,
                color_code="#4CAF50",
                surface_texture="smooth"
            )

    def test_watermelon_color_code_validation(self):
        """Test color code validation."""
        # Valid hex colors
        valid_colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFFFF", "#000000"]
        for color in valid_colors:
            watermelon = Watermelon(
                weight=5000.0,
                diameter=30.0,
                color_code=color,
                surface_texture="smooth"
            )
            assert watermelon.color_code == color

        # Invalid color codes
        invalid_colors = [
            "FF0000",  # Missing #
            "#FF000",  # Too short
            "#FF00000",  # Too long
            "#GG0000",  # Invalid hex character
            "ff0000",  # Lowercase without #
            "#F0000G",  # Invalid hex character
        ]

        for color in invalid_colors:
            with pytest.raises(ValidationError, match="Invalid color code format"):
                Watermelon(
                    weight=5000.0,
                    diameter=30.0,
                    color_code=color,
                    surface_texture="smooth"
                )

    def test_watermelon_surface_texture_validation(self):
        """Test surface texture validation."""
        # Valid textures
        valid_textures = ["smooth", "rough", "bumpy", "waxy"]
        for texture in valid_textures:
            watermelon = Watermelon(
                weight=5000.0,
                diameter=30.0,
                color_code="#4CAF50",
                surface_texture=texture
            )
            assert watermelon.surface_texture == texture

        # Invalid texture
        with pytest.raises(ValidationError, match="Surface texture must be one of"):
            Watermelon(
                weight=5000.0,
                diameter=30.0,
                color_code="#4CAF50",
                surface_texture="metallic"
            )

    def test_watermelon_get_density(self):
        """Test density calculation method."""
        watermelon = Watermelon(
            weight=5000.0,  # grams
            diameter=30.0,  # cm
            color_code="#4CAF50",
            surface_texture="smooth"
        )

        # Volume of sphere: (4/3) * pi * r^3
        # radius = diameter / 2 = 15 cm
        # volume = (4/3) * pi * 15^3 ≈ 14137.17 cm^3
        # density = weight / volume ≈ 0.3536 g/cm^3
        expected_density = 5000.0 / ((4.0 / 3.0) * 3.14159 * (15.0 ** 3))
        actual_density = watermelon.get_density()

        assert abs(actual_density - expected_density) < 0.001

    def test_watermelon_get_volume(self):
        """Test volume calculation method."""
        watermelon = Watermelon(
            weight=5000.0,
            diameter=30.0,
            color_code="#4CAF50",
            surface_texture="smooth"
        )

        # Volume of sphere: (4/3) * pi * r^3
        # radius = diameter / 2 = 15 cm
        expected_volume = (4.0 / 3.0) * 3.14159 * (15.0 ** 3)
        actual_volume = watermelon.get_volume()

        assert abs(actual_volume - expected_volume) < 0.001

    def test_watermelon_is_ripe(self):
        """Test ripeness check method."""
        # Unripe watermelon
        unripe = Watermelon(
            weight=5000.0,
            diameter=30.0,
            color_code="#4CAF50",
            surface_texture="smooth",
            ripeness_status=RipenessStatus.UNRIPE
        )
        assert not unripe.is_ripe()

        # Early ripe watermelon
        early_ripe = Watermelon(
            weight=5000.0,
            diameter=30.0,
            color_code="#4CAF50",
            surface_texture="smooth",
            ripeness_status=RipenessStatus.EARLY_RIPE
        )
        assert not early_ripe.is_ripe()

        # Ripe watermelon
        ripe = Watermelon(
            weight=5000.0,
            diameter=30.0,
            color_code="#4CAF50",
            surface_texture="smooth",
            ripeness_status=RipenessStatus.RIPE
        )
        assert ripe.is_ripe()

        # Late ripe watermelon
        late_ripe = Watermelon(
            weight=5000.0,
            diameter=30.0,
            color_code="#4CAF50",
            surface_texture="smooth",
            ripeness_status=RipenessStatus.LATE_RIPE
        )
        assert not late_ripe.is_ripe()

        # Overripe watermelon
        overripe = Watermelon(
            weight=5000.0,
            diameter=30.0,
            color_code="#4CAF50",
            surface_texture="smooth",
            ripeness_status=RipenessStatus.OVERRIPE
        )
        assert not overripe.is_ripe()

    def test_watermelon_update_ripeness_status(self):
        """Test ripeness status update method."""
        watermelon = Watermelon(
            weight=5000.0,
            diameter=30.0,
            color_code="#4CAF50",
            surface_texture="smooth",
            ripeness_status=RipenessStatus.UNRIPE
        )

        assert watermelon.ripeness_status == RipenessStatus.UNRIPE

        watermelon.update_ripeness_status(RipenessStatus.RIPE)
        assert watermelon.ripeness_status == RipenessStatus.RIPE

    def test_watermelon_to_dict(self):
        """Test dictionary serialization."""
        watermelon = Watermelon(
            weight=5000.0,
            diameter=30.0,
            color_code="#4CAF50",
            surface_texture="smooth",
            ripeness_status=RipenessStatus.RIPE
        )

        data = watermelon.to_dict()
        expected = {
            "weight": 5000.0,
            "diameter": 30.0,
            "color_code": "#4CAF50",
            "surface_texture": "smooth",
            "ripeness_status": "ripe"
        }

        assert data == expected

    def test_watermelon_from_dict(self):
        """Test dictionary deserialization."""
        data = {
            "weight": 6000.0,
            "diameter": 35.0,
            "color_code": "#FF5722",
            "surface_texture": "rough",
            "ripeness_status": "late_ripe"
        }

        watermelon = Watermelon.from_dict(data)

        assert watermelon.weight == 6000.0
        assert watermelon.diameter == 35.0
        assert watermelon.color_code == "#FF5722"
        assert watermelon.surface_texture == "rough"
        assert watermelon.ripeness_status == RipenessStatus.LATE_RIPE

    def test_watermelon_equality(self):
        """Test equality comparison between watermelons."""
        w1 = Watermelon(
            weight=5000.0,
            diameter=30.0,
            color_code="#4CAF50",
            surface_texture="smooth",
            ripeness_status=RipenessStatus.RIPE
        )

        w2 = Watermelon(
            weight=5000.0,
            diameter=30.0,
            color_code="#4CAF50",
            surface_texture="smooth",
            ripeness_status=RipenessStatus.RIPE
        )

        w3 = Watermelon(
            weight=6000.0,
            diameter=30.0,
            color_code="#4CAF50",
            surface_texture="smooth",
            ripeness_status=RipenessStatus.RIPE
        )

        assert w1 == w2
        assert w1 != w3

    def test_watermelon_hash(self):
        """Test that watermelon can be used in sets and as dict keys."""
        w1 = Watermelon(
            weight=5000.0,
            diameter=30.0,
            color_code="#4CAF50",
            surface_texture="smooth"
        )

        w2 = Watermelon(
            weight=5000.0,
            diameter=30.0,
            color_code="#4CAF50",
            surface_texture="smooth"
        )

        # Should be hashable
        assert hash(w1) is not None
        assert hash(w2) is not None

        # Equal objects should have equal hashes
        assert w1 == w2
        assert hash(w1) == hash(w2)

        # Can be used in set
        watermelon_set = {w1, w2}
        assert len(watermelon_set) == 1

        # Can be used as dict key
        watermelon_dict = {w1: "first"}
        watermelon_dict[w2] = "second"
        assert len(watermelon_dict) == 1
        assert watermelon_dict[w1] == "second"

    def test_watermelon_repr(self):
        """Test string representation of watermelon."""
        watermelon = Watermelon(
            weight=5000.0,
            diameter=30.0,
            color_code="#4CAF50",
            surface_texture="smooth",
            ripeness_status=RipenessStatus.RIPE
        )

        repr_str = repr(watermelon)
        assert "Watermelon" in repr_str
        assert "5000.0" in repr_str
        assert "30.0" in repr_str
        assert "#4CAF50" in repr_str
        assert "smooth" in repr_str
        assert "ripe" in repr_str


class TestConfig:
    """Test cases for Config class."""

    def test_config_attributes(self):
        """Test that Config class has expected attributes."""
        assert hasattr(Config, "title")
        assert hasattr(Config, "anystr_strip_whitespace")
        assert hasattr(Config, "validate_assignment")
        assert hasattr(Config, "use_enum_values")
        assert hasattr(Config, "arbitrary_types_allowed")

    def test_config_values(self):
        """Test Config class configuration values."""
        assert Config.title == "Watermelon"
        assert Config.anystr_strip_whitespace is True
        assert Config.validate_assignment is True
        assert Config.use_enum_values is True
        assert Config.arbitrary_types_allowed is True

    def test_config_inheritance(self):
        """Test that Config is properly inherited by Watermelon."""
        watermelon = Watermelon(
            weight=5000.0,
            diameter=30.0,
            color_code="#4CAF50",
            surface_texture="smooth"
        )

        # Test that config is applied
        assert watermelon.__config__.title == "Watermelon"
        assert watermelon.__config__.anystr_strip_whitespace is True
        assert watermelon.__config__.validate_assignment is True
        assert watermelon.__config__.use_enum_values is True
        assert watermelon.__config__.arbitrary_types_allowed is True

    def test_config_whitespace_stripping(self):
        """Test that whitespace is stripped from string fields."""
        watermelon = Watermelon(
            weight=5000.0,
            diameter=30.0,
            color_code="  #4CAF50  ",
            surface_texture="  smooth  "
        )

        assert watermelon.color_code == "#4CAF50"
        assert watermelon.surface_texture == "smooth"

    def test_config_validate_assignment(self):
        """Test that assignment validation is enabled."""
        watermelon = Watermelon(
            weight=5000.0,
            diameter=30.0,
            color_code="#4CAF50",
            surface_texture="smooth"
        )

        # Valid assignment should work
        watermelon.weight = 6000.0
        assert watermelon.weight == 6000.0

        # Invalid assignment should raise error
        with pytest.raises(ValidationError):
            watermelon.weight = -1000.0

    def test_config_use_enum_values(self):
        """Test that enum values are used instead of enum objects."""
        watermelon = Watermelon(
            weight=5000.0,
            diameter=30.0,
            color_code="#4CAF50",
            surface_texture="smooth",
            ripeness_status=RipenessStatus.RIPE
        )

        # When serializing, enum should be converted to its value
        data = watermelon.dict()
        assert data["ripeness_status"] == "ripe"
        assert isinstance(data["ripeness_status"], str)
