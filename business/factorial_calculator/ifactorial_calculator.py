"""
Factorial Calculator Interface

This module defines the abstract interface for computing factorials.
It provides a contract that concrete implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Protocol


class IFactorialCalculator(ABC):
    """
    Abstract interface for factorial computation.

    This interface defines the contract for classes that compute the factorial
    of a non-negative integer. Implementations should handle input validation
    and edge cases appropriately.
    """

    @abstractmethod
    def compute_factorial(self, n: int) -> int:
        """
        Compute the factorial of a non-negative integer.

        Args:
            n (int): A non-negative integer (>= 0) for which to compute the factorial.

        Returns:
            int: The factorial of n (n!).

        Raises:
            ValueError: If n is negative.
            TypeError: If n is not an integer.
        """
        pass
