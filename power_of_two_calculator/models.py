from pydantic import BaseModel, Field


class PowerCalculationRequest(BaseModel):
    """Модель запроса для вычисления степени двойки.

    Attributes:
        n (int): Показатель степени, должен быть неотрицательным.
    """
    n: int = Field(..., ge=0, description="Показатель степени, должен быть неотрицательным")


class PowerCalculationResponse(BaseModel):
    """Модель ответа для вычисления степени двойки.

    Attributes:
        result (int): Результат вычисления 2 ** n.
    """
    result: int = Field(..., description="Результат вычисления 2 ** n")
