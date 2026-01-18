import unittest
from business.factorial_calculator import FactorialCalculator


class TestFactorialCalculator(unittest.TestCase):
    """
    Unit tests for the FactorialCalculator class.

    This test suite verifies the correctness of the factorial computation
    for various inputs, including edge cases and error handling.
    """

    def setUp(self):
        """
        Set up the test fixture.

        Initializes a new instance of FactorialCalculator for each test.
        """
        self.calculator = FactorialCalculator()

    def test_factorial_of_zero(self):
        """
        Test factorial of 0.

        The factorial of 0 is defined as 1.
        """
        result = self.calculator.compute_factorial(0)
        self.assertEqual(result, 1)

    def test_factorial_of_one(self):
        """
        Test factorial of 1.

        The factorial of 1 is 1.
        """
        result = self.calculator.compute_factorial(1)
        self.assertEqual(result, 1)

    def test_factorial_of_small_positive_integer(self):
        """
        Test factorial of a small positive integer.

        For example, 5! = 120.
        """
        result = self.calculator.compute_factorial(5)
        self.assertEqual(result, 120)

    def test_factorial_of_larger_integer(self):
        """
        Test factorial of a larger integer.

        For example, 10! = 3628800.
        """
        result = self.calculator.compute_factorial(10)
        self.assertEqual(result, 3628800)

    def test_factorial_of_negative_integer(self):
        """
        Test factorial of a negative integer.

        Should raise ValueError for negative inputs.
        """
        with self.assertRaises(ValueError):
            self.calculator.compute_factorial(-1)

    def test_factorial_of_non_integer(self):
        """
        Test factorial with non-integer input.

        Since the method expects int, but to test robustness,
        note that type hints are not enforced at runtime,
        but in practice, it should handle as per implementation.
        However, based on the interface, we assume int input.
        This test is for completeness if float is passed.
        """
        # Assuming implementation raises TypeError or similar for non-int,
        # but per code, it checks isinstance(n, int), raises TypeError.
        with self.assertRaises(TypeError):
            self.calculator.compute_factorial(5.5)


if __name__ == '__main__':
    unittest.main()
