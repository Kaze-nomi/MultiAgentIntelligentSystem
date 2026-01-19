from fastapi import FastAPI, HTTPException
from .models import PowerCalculationRequest, PowerCalculationResponse
from .power_of_two_calculator import PowerOfTwoCalculator


app = FastAPI(title="Power of Two Calculator", description="API for calculating powers of two")


calculator = PowerOfTwoCalculator()


@app.post("/calculate", response_model=PowerCalculationResponse)
async def power_calculation_endpoint(request: PowerCalculationRequest) -> PowerCalculationResponse:
    """Эндпоинт для вычисления n-ой степени двойки.

    Принимает запрос с показателем степени n и возвращает результат 2^n.

    Args:
        request: Запрос с параметром n (неотрицательное целое число).

    Returns:
        PowerCalculationResponse: Ответ с результатом вычисления.

    Raises:
        HTTPException: Если n отрицательное или другая ошибка валидации.
    """
    try:
        result = calculator.calculate_power_of_two(request.n)
        return PowerCalculationResponse(result=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
