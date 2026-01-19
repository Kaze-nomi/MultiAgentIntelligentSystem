from typing import Protocol
from pydantic import BaseModel, Field


class IPowerCalculator(Protocol):
    """Интерфейс для калькулятора степеней."""

    def calculate_power_of_two(self, n: int) -> int:
        """Вычисляет 2 в степени n.

        Args:
            n: Показатель степени.

        Returns:
            2 ** n как целое число.
        """
        ...


class PowerCalculationRequest(BaseModel):
    """Модель запроса для вычисления степени двойки."""

    n: int = Field(..., ge=0, description="Показатель степени, должен быть неотрицательным")


class PowerCalculationResponse(BaseModel):
    """Модель ответа для вычисления степени двойки."""

    result: int = Field(..., description="Результат вычисления 2 ** n")


class PowerOfTwoCalculator:
    """Калькулятор степени двойки, реализующий паттерн Singleton."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def calculate_power_of_two(self, n: int) -> int:
        """Вычисляет 2 в степени n.

        Args:
            n: Показатель степени, должен быть неотрицательным целым числом.

        Returns:
            2 ** n как целое число.

        Raises:
            ValueError: Если n отрицательное.
        """
        if n < 0:
            raise ValueError("n must be non-negative")
        return 2 ** n
