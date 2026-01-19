from typing import Optional

from .interfaces import IPowerCalculator


class PowerOfTwoCalculator(IPowerCalculator):
    """Калькулятор степени двойки с использованием паттерна Singleton.

    Этот класс реализует интерфейс IPowerCalculator и обеспечивает
    вычисление n-ой степени двойки. Использует паттерн Singleton для
    гарантии единственного экземпляра.
    """

    _instance: Optional['PowerOfTwoCalculator'] = None

    def __new__(cls) -> 'PowerOfTwoCalculator':
        """Создает или возвращает единственный экземпляр класса.

        Returns:
            PowerOfTwoCalculator: Единственный экземпляр калькулятора.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def calculate_power_of_two(self, n: int) -> int:
        """Вычисляет 2 в степени n.

        Args:
            n: Показатель степени. Должен быть неотрицательным целым числом.

        Returns:
            int: Результат вычисления 2 ** n.

        Raises:
            ValueError: Если n отрицательное.
        """
        if n < 0:
            raise ValueError("Показатель степени должен быть неотрицательным")
        return 1 << n  # Используем битовый сдвиг для эффективного вычисления
