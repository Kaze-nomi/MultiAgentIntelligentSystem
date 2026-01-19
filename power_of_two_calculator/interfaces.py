from typing import Protocol


class IPowerCalculator(Protocol):
    """Интерфейс для калькулятора степеней.

    Определяет контракт для классов, реализующих вычисление степеней двойки.
    """

    def calculate_power_of_two(self, n: int) -> int:
        """Вычисляет 2 в степени n.

        Args:
            n: Показатель степени. Должен быть неотрицательным целым числом.

        Returns:
            2 ** n как целое число.

        Raises:
            ValueError: Если n отрицательное.
        """
        ...
