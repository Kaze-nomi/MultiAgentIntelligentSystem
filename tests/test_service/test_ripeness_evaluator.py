"""Test module for watermelon ripeness evaluation services.

This module contains comprehensive unit tests for the ripeness evaluation
services, ensuring proper evaluation logic, edge case handling, and
conformance to the IRipenessEvaluator interface.
"""

import pytest
from typing import List

from src.my_project.domain import Watermelon, RipenessStatus
from src.my_project.service.protocols import IRipenessEvaluator
from src.my_project.service.ripeness_evaluator import RipenessEvaluator


class TestRipenessEvaluator:
    """Test cases for RipenessEvaluator service implementation.

    This test class validates the heuristic-based ripeness evaluation
    logic, ensuring that watermelons are correctly classified based on
    their physical properties.
    """

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.evaluator = RipenessEvaluator()

    def test_implements_interface(self):
        """Test that RipenessEvaluator implements IRipenessEvaluator interface."""
        assert isinstance(self.evaluator, IRipenessEvaluator)

    def test_evaluate_unripe_watermelon(self):
        """Test evaluation of clearly unripe watermelon."""
        watermelon = Watermelon(
            weight=2000.0,  # Very light
            diameter=20.0,  # Small
            color_code="#90EE90",  # Light green
            surface_texture="rough"
        )
        result = self.evaluator.evaluate(watermelon)
        assert result == RipenessStatus.UNRIPE

    def test_evaluate_early_ripe_watermelon(self):
        """Test evaluation of early ripe watermelon."""
        watermelon = Watermelon(
            weight=3500.0,
            diameter=25.0,
            color_code="#7CFC00",  # Medium green
            surface_texture="slightly_rough"
        )
        result = self.evaluator.evaluate(watermelon)
        assert result == RipenessStatus.EARLY_RRIPE

    def test_evaluate_perfectly_ripe_watermelon(self):
        """Test evaluation of perfectly ripe watermelon."""
        watermelon = Watermelon(
            weight=5000.0,  # Ideal weight
            diameter=30.0,  # Ideal size
            color_code="#228B22",  # Deep green
            surface_texture="smooth"
        )
        result = self.evaluator.evaluate(watermelon)
        assert result == RipenessStatus.RIPE

    def test_evaluate_late_ripe_watermelon(self):
        """Test evaluation of late ripe watermelon."""
        watermelon = Watermelon(
            weight=5500.0,
            diameter=32.0,
            color_code="#006400",  # Very dark green
            surface_texture="slightly_soft"
        )
        result = self.evaluator.evaluate(watermelon)
        assert result == RipenessStatus.LATE_RIPE

    def test_evaluate_overripe_watermelon(self):
        """Test evaluation of overripe watermelon."""
        watermelon = Watermelon(
            weight=7000.0,  # Too heavy
            diameter=35.0,  # Too large
            color_code="#8B4513",  # Brownish
            surface_texture="soft"
        )
        result = self.evaluator.evaluate(watermelon)
        assert result == RipenessStatus.OVERRIPE

    def test_evaluate_edge_case_minimum_values(self):
        """Test evaluation with minimum valid values."""
        watermelon = Watermelon(
            weight=1000.0,
            diameter=15.0,
            color_code="#FFFFFF",
            surface_texture="very_rough"
        )
        result = self.evaluator.evaluate(watermelon)
        assert result in [RipenessStatus.UNRIPE, RipenessStatus.EARLY_RIPE]

    def test_evaluate_edge_case_maximum_values(self):
        """Test evaluation with maximum valid values."""
        watermelon = Watermelon(
            weight=10000.0,
            diameter=50.0,
            color_code="#000000",
            surface_texture="very_soft"
        )
        result = self.evaluator.evaluate(watermelon)
        assert result in [RipenessStatus.LATE_RIPE, RipenessStatus.OVERRIPE]

    def test_evaluate_density_factor(self):
        """Test that density is properly factored into evaluation."""
        # Same weight but different diameters (different densities)
        dense_watermelon = Watermelon(
            weight=5000.0,
            diameter=25.0,  # Smaller diameter = higher density
            color_code="#228B22",
            surface_texture="smooth"
        )

        light_watermelon = Watermelon(
            weight=5000.0,
            diameter=35.0,  # Larger diameter = lower density
            color_code="#228B22",
            surface_texture="smooth"
        )

        dense_result = self.evaluator.evaluate(dense_watermelon)
        light_result = self.evaluator.evaluate(light_watermelon)

        # Higher density should indicate better ripeness
        assert dense_result.value <= light_result.value

    def test_evaluate_color_weighting(self):
        """Test that color is properly weighted in evaluation."""
        # Same physical properties but different colors
        light_green = Watermelon(
            weight=5000.0,
            diameter=30.0,
            color_code="#90EE90",  # Light green
            surface_texture="smooth"
        )

        dark_green = Watermelon(
            weight=5000.0,
            diameter=30.0,
            color_code="#006400",  # Dark green
            surface_texture="smooth"
        )

        light_result = self.evaluator.evaluate(light_green)
        dark_result = self.evaluator.evaluate(dark_green)

        # Darker green should indicate better ripeness
        assert light_result.value <= dark_result.value

    def test_evaluate_texture_impact(self):
        """Test that surface texture impacts evaluation."""
        # Same properties but different textures
        rough = Watermelon(
            weight=5000.0,
            diameter=30.0,
            color_code="#228B22",
            surface_texture="rough"
        )

        smooth = Watermelon(
            weight=5000.0,
            diameter=30.0,
            color_code="#228B22",
            surface_texture="smooth"
        )

        rough_result = self.evaluator.evaluate(rough)
        smooth_result = self.evaluator.evaluate(smooth)

        # Smooth texture should indicate better ripeness
        assert rough_result.value <= smooth_result.value

    def test_evaluate_consistency(self):
        """Test that evaluation is consistent for identical inputs."""
        watermelon = Watermelon(
            weight=4500.0,
            diameter=28.0,
            color_code="#32CD32",
            surface_texture="mostly_smooth"
        )

        result1 = self.evaluator.evaluate(watermelon)
        result2 = self.evaluator.evaluate(watermelon)
        result3 = self.evaluator.evaluate(watermelon)

        assert result1 == result2 == result3

    def test_evaluate_multiple_watermelons(self):
        """Test evaluation of multiple watermelons with varying properties."""
        test_cases = [
            {
                "watermelon": Watermelon(
                    weight=3000.0, diameter=22.0,
                    color_code="#ADFF2F", surface_texture="rough"
                ),
                "expected": RipenessStatus.UNRIPE
            },
            {
                "watermelon": Watermelon(
                    weight=4000.0, diameter=26.0,
                    color_code="#7FFF00", surface_texture="slightly_rough"
                ),
                "expected": RipenessStatus.EARLY_RIPE
            },
            {
                "watermelon": Watermelon(
                    weight=5000.0, diameter=30.0,
                    color_code="#228B22", surface_texture="smooth"
                ),
                "expected": RipenessStatus.RIPE
            },
            {
                "watermelon": Watermelon(
                    weight=6000.0, diameter=33.0,
                    color_code="#008000", surface_texture="slightly_soft"
                ),
                "expected": RipenessStatus.LATE_RIPE
            },
            {
                "watermelon": Watermelon(
                    weight=8000.0, diameter=40.0,
                    color_code="#8B0000", surface_texture="soft"
                ),
                "expected": RipenessStatus.OVERRIPE
            }
        ]

        for case in test_cases:
            result = self.evaluator.evaluate(case["watermelon"])
            assert result == case["expected"], \
                f"Failed for watermelon with weight {case['watermelon'].weight}"

    def test_evaluate_boundary_conditions(self):
        """Test evaluation at boundary conditions between ripeness levels."""
        # Test boundaries around RIPE status
        boundary_cases = [
            # Just before ripe
            Watermelon(weight=4800.0, diameter=29.0, color_code="#32CD32", surface_texture="mostly_smooth"),
            # Exactly ripe
            Watermelon(weight=5000.0, diameter=30.0, color_code="#228B22", surface_texture="smooth"),
            # Just after ripe
            Watermelon(weight=5200.0, diameter=31.0, color_code="#006400", surface_texture="slightly_soft")
        ]

        results = [self.evaluator.evaluate(w) for w in boundary_cases]

        # Should progress through ripeness levels
        assert results[0].value <= results[1].value <= results[2].value

    def test_invalid_watermelon_input(self):
        """Test that evaluator handles invalid watermelon objects gracefully."""
        # This test assumes the evaluator validates input
        # If validation happens at a different level, adjust accordingly
        with pytest.raises((TypeError, AttributeError)):
            self.evaluator.evaluate(None)

        with pytest.raises((TypeError, AttributeError)):
            self.evaluator.evaluate("not a watermelon")

    def test_evaluator_stateless(self):
        """Test that evaluator is stateless and can be reused."""
        watermelon1 = Watermelon(
            weight=3000.0, diameter=22.0,
            color_code="#ADFF2F", surface_texture="rough"
        )
        watermelon2 = Watermelon(
            weight=6000.0, diameter=33.0,
            color_code="#008000", surface_texture="slightly_soft"
        )

        # Alternate evaluations
        result1 = self.evaluator.evaluate(watermelon1)
        result2 = self.evaluator.evaluate(watermelon2)
        result3 = self.evaluator.evaluate(watermelon1)
        result4 = self.evaluator.evaluate(watermelon2)

        # Results should be consistent
        assert result1 == result3 == RipenessStatus.UNRIPE
        assert result2 == result4 == RipenessStatus.LATE_RIPE

    def test_performance_with_large_dataset(self):
        """Test evaluator performance with a large number of watermelons."""
        # Generate test data
        watermelons = []
        for i in range(1000):
            weight = 2000.0 + (i * 6.0)
            diameter = 20.0 + (i * 0.03)
            color_code = f"#{i%256:02x}{(i+128)%256:02x}00"
            texture = "rough" if i < 333 else ("smooth" if i < 666 else "soft")

            watermelons.append(Watermelon(
                weight=weight,
                diameter=diameter,
                color_code=color_code,
                surface_texture=texture
            ))

        # Evaluate all
        results = [self.evaluator.evaluate(w) for w in watermelons]

        # Verify we got results for all
        assert len(results) == 1000
        assert all(isinstance(r, RipenessStatus) for r in results)

        # Verify progression
        status_values = [r.value for r in results]
        assert status_values[0] <= status_values[-1]
