import unittest
from unittest.mock import Mock
from power_of_two_calculator.power_of_two_calculator import PowerOfTwoCalculator
from power_of_two_calculator.interfaces import IPowerCalculator


class TestPowerOfTwoCalculator(unittest.TestCase):
    """Тесты для класса PowerOfTwoCalculator.

    Проверяет корректность вычисления n-ой степени двойки,
    работу паттерна Singleton и обработку ошибок.
    """

    def setUp(self):
        """Подготовка к тестам: сброс экземпляра Singleton для чистоты тестов."""
        PowerOfTwoCalculator._instance = None
        self.calculator = PowerOfTwoCalculator()

    def test_calculate_power_of_two_zero(self):
        """Тест вычисления 2^0 = 1."""
        result = self.calculator.calculate_power_of_two(0)
        self.assertEqual(result, 1)

    def test_calculate_power_of_two_positive(self):
        """Тест вычисления 2^n для положительных n."""
        test_cases = [
            (1, 2),
            (2, 4),
            (3, 8),
            (10, 1024),
        ]
        for n, expected in test_cases:
            with self.subTest(n=n):
                result = self.calculator.calculate_power_of_two(n)
                self.assertEqual(result, expected)

    def test_calculate_power_of_two_large_n(self):
        """Тест вычисления для большого n (например, 100)."""
        n = 100
        result = self.calculator.calculate_power_of_two(n)
        expected = 1 << n  # 2 ** n
        self.assertEqual(result, expected)

    def test_calculate_power_of_two_negative_raises_error(self):
        """Тест, что отрицательные n вызывают ValueError."""
        with self.assertRaises(ValueError):
            self.calculator.calculate_power_of_two(-1)

    def test_singleton_pattern(self):
        """Тест паттерна Singleton: два экземпляра должны быть одинаковыми."""
        calculator2 = PowerOfTwoCalculator()
        self.assertIs(self.calculator, calculator2)


class TestIPowerCalculator(unittest.TestCase):
    """Тесты для интерфейса IPowerCalculator.

    Проверяет, что реализации интерфейса работают корректно,
    используя мок для тестирования контракта.
    """

    def setUp(self):
        """Подготовка: создание мока для IPowerCalculator."""
        self.mock_calculator = Mock(spec=IPowerCalculator)

    def test_calculate_power_of_two_called_correctly(self):
        """Тест, что метод calculate_power_of_two вызывается с правильными аргументами."""
        self.mock_calculator.calculate_power_of_two.return_value = 16
        result = self.mock_calculator.calculate_power_of_two(4)
        self.mock_calculator.calculate_power_of_two.assert_called_once_with(4)
        self.assertEqual(result, 16)

    def test_interface_compliance(self):
        """Тест, что PowerOfTwoCalculator соответствует интерфейсу IPowerCalculator."""
        # Проверяем, что PowerOfTwoCalculator имеет метод calculate_power_of_two
        self.assertTrue(hasattr(PowerOfTwoCalculator(), 'calculate_power_of_two'))
        self.assertTrue(callable(getattr(PowerOfTwoCalculator(), 'calculate_power_of_two')))


if __name__ == '__main__':
    unittest.main()
