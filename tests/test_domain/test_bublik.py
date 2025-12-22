"""Tests for Bublik domain model."""

import pytest
from pydantic import ValidationError

from src.my_project.domain.bublik import Bublik


class TestBublik:
    """Test cases for the Bublik class."""

    def test_bublik_creation_success(self):
        """Test successful creation of a Bublik instance."""
        bublik = Bublik(
            name="Сладкий бублик",
            filling="Варенье",
            price=50.0,
        )

        assert bublik.name == "Сладкий бублик"
        assert bublik.filling == "Варенье"
        assert bublik.price == 50.0
        assert isinstance(bublik.id, str)
        assert len(bublik.id) > 0

    def test_bublik_creation_with_custom_id(self):
        """Test creation of Bublik with custom ID."""
        custom_id = "custom-bublik-123"
        bublik = Bublik(
            id=custom_id,
            name="Сдобный бублик",
            filling="Творог",
            price=45.5,
        )

        assert bublik.id == custom_id

    def test_bublik_name_validation(self):
        """Test name field validation."""
        # Test empty name
        with pytest.raises(ValidationError) as exc_info:
            Bublik(name="", filling="Варенье", price=50.0)

        errors = exc_info.value.errors()
        assert any(error["type"] == "value_error" for error in errors)

        # Test name too short
        with pytest.raises(ValidationError) as exc_info:
            Bublik(name="А", filling="Варенье", price=50.0)

        errors = exc_info.value.errors()
        assert any(error["type"] == "value_error" for error in errors)

        # Test name too long
        with pytest.raises(ValidationError) as exc_info:
            Bublik(name="А" * 101, filling="Варенье", price=50.0)

        errors = exc_info.value.errors()
        assert any(error["type"] == "value_error" for error in errors)

    def test_bublik_filling_validation(self):
        """Test filling field validation."""
        # Test empty filling
        with pytest.raises(ValidationError) as exc_info:
            Bublik(name="Бублик", filling="", price=50.0)

        errors = exc_info.value.errors()
        assert any(error["type"] == "value_error" for error in errors)

        # Test filling too long
        with pytest.raises(ValidationError) as exc_info:
            Bublik(name="Бублик", filling="Варенье" * 21, price=50.0)

        errors = exc_info.value.errors()
        assert any(error["type"] == "value_error" for error in errors)

    def test_bublik_price_validation(self):
        """Test price field validation."""
        # Test negative price
        with pytest.raises(ValidationError) as exc_info:
            Bublik(name="Бублик", filling="Варенье", price=-10.0)

        errors = exc_info.value.errors()
        assert any(error["type"] == "value_error" for error in errors)

        # Test zero price
        with pytest.raises(ValidationError) as exc_info:
            Bublik(name="Бублик", filling="Варенье", price=0.0)

        errors = exc_info.value.errors()
        assert any(error["type"] == "value_error" for error in errors)

        # Test price too high
        with pytest.raises(ValidationError) as exc_info:
            Bublik(name="Бублик", filling="Варенье", price=10000.0)

        errors = exc_info.value.errors()
        assert any(error["type"] == "value_error" for error in errors)

    def test_bublik_id_validation(self):
        """Test ID field validation."""
        # Test empty ID
        with pytest.raises(ValidationError) as exc_info:
            Bublik(id="", name="Бублик", filling="Варенье", price=50.0)

        errors = exc_info.value.errors()
        assert any(error["type"] == "value_error" for error in errors)

    def test_bublik_equality(self):
        """Test Bublik equality comparison."""
        bublik1 = Bublik(name="Бублик", filling="Варенье", price=50.0)
        bublik2 = Bublik(name="Бублик", filling="Варенье", price=50.0)
        bublik3 = Bublik(name="Сдобный", filling="Творог", price=45.0)

        # Different IDs should not be equal
        assert bublik1 != bublik2
        assert bublik1 != bublik3

        # Same ID should be equal
        same_id = "test-id-123"
        bublik4 = Bublik(id=same_id, name="Бублик", filling="Варенье", price=50.0)
        bublik5 = Bublik(id=same_id, name="Сдобный", filling="Творог", price=45.0)
        assert bublik4 == bublik5

    def test_bublik_hash(self):
        """Test Bublik hash method for use in sets/dicts."""
        bublik1 = Bublik(name="Бублик", filling="Варенье", price=50.0)
        bublik2 = Bublik(name="Бублик", filling="Варенье", price=50.0)

        # Different IDs should have different hashes
        assert hash(bublik1) != hash(bublik2)

        # Same ID should have same hash
        same_id = "test-id-456"
        bublik3 = Bublik(id=same_id, name="Бублик", filling="Варенье", price=50.0)
        bublik4 = Bublik(id=same_id, name="Сдобный", filling="Творог", price=45.0)
        assert hash(bublik3) == hash(bublik4)

        # Test in set
        bublik_set = {bublik1, bublik2, bublik3, bublik4}
        assert len(bublik_set) == 3  # bublik3 and bublik4 have same ID

    def test_bublik_repr(self):
        """Test Bublik string representation."""
        bublik = Bublik(name="Сладкий бублик", filling="Варенье", price=50.0)
        repr_str = repr(bublik)

        assert "Bublik" in repr_str
        assert bublik.id in repr_str
        assert "Сладкий бублик" in repr_str
        assert "Варенье" in repr_str
        assert "50.0" in repr_str

    def test_bublik_dict_conversion(self):
        """Test conversion to dictionary."""
        bublik = Bublik(name="Сдобный", filling="Творог", price=45.5)
        bublik_dict = bublik.dict()

        expected_keys = {"id", "name", "filling", "price"}
        assert set(bublik_dict.keys()) == expected_keys
        assert bublik_dict["name"] == "Сдобный"
        assert bublik_dict["filling"] == "Творог"
        assert bublik_dict["price"] == 45.5

    def test_bublik_copy(self):
        """Test Bublik copy method."""
        original = Bublik(name="Бублик", filling="Варенье", price=50.0)
        copied = original.copy()

        assert copied == original
        assert copied is not original  # Different instances
        assert copied.id == original.id

    def test_bublik_copy_with_updates(self):
        """Test Bublik copy with updates."""
        original = Bublik(name="Бублик", filling="Варенье", price=50.0)
        updated = original.copy(update={"price": 55.0, "filling": "Шоколад"})

        assert updated.id == original.id
        assert updated.name == original.name
        assert updated.price == 55.0
        assert updated.filling == "Шоколад"

    def test_bublik_from_orm(self):
        """Test creating Bublik from ORM-like object."""
        class MockORM:
            def __init__(self):
                self.id = "orm-123"
                self.name = "ORM Бублик"
                self.filling = "Сгущенка"
                self.price = 60.0

        mock_obj = MockORM()
        bublik = Bublik.from_orm(mock_obj)

        assert bublik.id == "orm-123"
        assert bublik.name == "ORM Бублик"
        assert bublik.filling == "Сгущенка"
        assert bublik.price == 60.0

    def test_bublik_json_serialization(self):
        """Test JSON serialization."""
        bublik = Bublik(name="Бублик", filling="Варенье", price=50.0)
        json_str = bublik.json()

        assert "\"id\"" in json_str
        assert "\"name\"" in json_str
        assert "\"filling\"" in json_str
        assert "\"price\"" in json_str
        assert "50.0" in json_str

        # Test deserialization
        deserialized = Bublik.parse_raw(json_str)
        assert deserialized == bublik

    def test_bublik_edge_cases(self):
        """Test edge cases for Bublik creation."""
        # Test minimum valid price
        bublik = Bublik(name="Бублик", filling="Варенье", price=0.01)
        assert bublik.price == 0.01

        # Test maximum valid price
        bublik = Bublik(name="Бублик", filling="Варенье", price=9999.99)
        assert bublik.price == 9999.99

        # Test minimum valid name length
        bublik = Bublik(name="АБ", filling="Варенье", price=50.0)
        assert bublik.name == "АБ"

        # Test maximum valid name length
        bublik = Bublik(name="А" * 100, filling="Варенье", price=50.0)
        assert len(bublik.name) == 100

        # Test maximum valid filling length
        bublik = Bublik(name="Бублик", filling="В" * 100, price=50.0)
        assert len(bublik.filling) == 100
