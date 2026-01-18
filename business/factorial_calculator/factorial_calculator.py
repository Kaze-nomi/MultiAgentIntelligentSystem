"""
Factorial Calculator Implementation

This module contains the concrete implementation of the FactorialCalculator class,
which computes the factorial of a non-negative integer using an iterative approach.
"""

from .ifactorial_calculator import IFactorialCalculator


class FactorialCalculator(IFactorialCalculator):
    """
    Concrete implementation of IFactorialCalculator using an iterative method.

    This class provides an efficient way to compute the factorial of a non-negative
    integer. It uses iteration to avoid recursion depth limits and potential stack
    overflow issues.
    """

    def compute_factorial(self, n: int) -> int:
        """
        Compute the factorial of a non-negative integer.

        Args:
            n (int): A non-negative integer for which to compute the factorial.
                     Must be >= 0.

        Returns:
            int: The factorial of n (n!).

        Raises:
            ValueError: If n is negative.
            TypeError: If n is not an integer.

        Examples:
            >>> calculator = FactorialCalculator()
            >>> calculator.compute_factorial(0)
            1
            >>> calculator.compute_factorial(5)
            120
        """
        if not isinstance(n, int):
            raise TypeError(f"Expected an integer, got {type(n).__name__}")
        if n < 0:
            raise ValueError("Factorial is not defined for negative numbers")
        if n == 0 or n == 1:
            return 1
        result = 1
        for i in range(2, n + 1):
            result *= i
        return result
