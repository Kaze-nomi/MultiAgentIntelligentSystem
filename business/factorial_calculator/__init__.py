"""
Factorial Calculator Module

This module provides functionality for calculating factorials of non-negative integers.
It includes an interface and a concrete implementation using an iterative approach.
"""

from .ifactorial_calculator import IFactorialCalculator
from .factorial_calculator import FactorialCalculator

__all__ = [
    "IFactorialCalculator",
    "FactorialCalculator",
]
