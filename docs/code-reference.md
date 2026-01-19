# Code Reference

## Table of Contents

- [Модуль `power_of_two_calculator/__init__.py`](#модуль-power_of_two_calculator__init__py)
- [Модуль `power_of_two_calculator/interfaces.py`](#модуль-power_of_two_calculatorinterfacespy)
- [Модуль `power_of_two_calculator/power_of_two_calculator.py`](#модуль-power_of_two_calculatorpower_of_two_calculatorpy)
- [Модуль `power_of_two_calculator/models.py`](#модуль-power_of_two_calculatormodelspy)
- [Модуль `power_of_two_calculator/server.py`](#модуль-power_of_two_calculatorserverpy)
- [Модуль `tests/test_power_of_two_calculator.py`](#модуль-teststest_power_of_two_calculatorpy)

## Модуль `power_of_two_calculator/__init__.py`

Модуль для вычисления n-ой степени двойки, содержащий интерфейс, модели и реализацию калькулятора с паттерном Singleton.

### Классы

#### `IPowerCalculator (Protocol)`

Интерфейс для калькулятора степеней.

**Методы:**

- `calculate_power_of_two(self, n: int) -> int`
  - Вычисляет 2 в степени n.
  - **Параметры:**
    - `n` (int): Показатель степени.
  - **Возвращает:** 2 ** n как целое число.

#### `PowerCalculationRequest (BaseModel)`

Модель запроса для вычисления степени двойки.

**Атрибуты:**
- `n` (int): Показатель степени, должен быть неотрицательным.

#### `PowerCalculationResponse (BaseModel)`

Модель ответа для вычисления степени двойки.

**Атрибуты:**
- `result` (int): Результат вычисления 2 ** n.

#### `PowerOfTwoCalculator`

Калькулятор степени двойки, реализующий паттерн Singleton.

**Методы:**

- `calculate_power_of_two(self, n: int) -> int`
  - Вычисляет 2 в степени n.
  - **Параметры:**
    - `n` (int): Показатель степени, должен быть неотрицательным целым числом.
  - **Возвращает:** 2 ** n как целое число.
  - **Исключения:** ValueError, если n отрицательное.

### Примеры использования

```python
from power_of_two_calculator import PowerOfTwoCalculator, PowerCalculationRequest, PowerCalculationResponse

# Создание экземпляра калькулятора (Singleton)
calculator = PowerOfTwoCalculator()

# Вычисление 2^3
result = calculator.calculate_power_of_two(3)
print(result)  # Вывод: 8

# Использование моделей
request = PowerCalculationRequest(n=4)
response = PowerCalculationResponse(result=calculator.calculate_power_of_two(request.n))
print(response.result)  # Вывод: 16
```

## Модуль `power_of_two_calculator/interfaces.py`

Файл содержит интерфейсы для калькулятора степеней двойки, включая IPowerCalculator как Protocol.

### Классы

#### `IPowerCalculator (Protocol)`

Интерфейс для калькулятора степеней. Определяет контракт для классов, реализующих вычисление степеней двойки.

**Методы:**

- `calculate_power_of_two(self, n: int) -> int`
  - Вычисляет 2 в степени n.
  - **Параметры:**
    - `n` (int): Показатель степени. Должен быть неотрицательным целым числом.
  - **Возвращает:** 2 ** n как целое число.
  - **Исключения:** ValueError, если n отрицательное.

### Примеры использования

```python
from power_of_two_calculator.interfaces import IPowerCalculator

# IPowerCalculator является Protocol, используется для типизации
def use_calculator(calc: IPowerCalculator, n: int) -> int:
    return calc.calculate_power_of_two(n)
```

## Модуль `power_of_two_calculator/power_of_two_calculator.py`

Реализация калькулятора степени двойки с паттерном Singleton, реализующим интерфейс IPowerCalculator.

### Классы

#### `PowerOfTwoCalculator`

Калькулятор степени двойки с использованием паттерна Singleton. Этот класс реализует интерфейс IPowerCalculator и обеспечивает вычисление n-ой степени двойки. Использует паттерн Singleton для гарантии единственного экземпляра.

**Методы:**

- `__new__(cls) -> 'PowerOfTwoCalculator'`
  - Создает или возвращает единственный экземпляр класса.
  - **Возвращает:** PowerOfTwoCalculator: Единственный экземпляр калькулятора.

- `calculate_power_of_two(self, n: int) -> int`
  - Вычисляет 2 в степени n.
  - **Параметры:**
    - `n` (int): Показатель степени. Должен быть неотрицательным целым числом.
  - **Возвращает:** int: Результат вычисления 2 ** n.
  - **Исключения:** ValueError, если n отрицательное.

### Примеры использования

```python
from power_of_two_calculator.power_of_two_calculator import PowerOfTwoCalculator

# Создание экземпляра (Singleton)
calc = PowerOfTwoCalculator()

# Вычисление
result = calc.calculate_power_of_two(5)
print(result)  # Вывод: 32

# Проверка Singleton
calc2 = PowerOfTwoCalculator()
print(calc is calc2)  # Вывод: True
```

## Модуль `power_of_two_calculator/models.py`

Файл содержит Pydantic модели для запроса и ответа при вычислении n-ой степени двойки, обеспечивая валидацию данных.

### Классы

#### `PowerCalculationRequest (BaseModel)`

Модель запроса для вычисления степени двойки.

**Атрибуты:**
- `n` (int): Показатель степени, должен быть неотрицательным.

#### `PowerCalculationResponse (BaseModel)`

Модель ответа для вычисления степени двойки.

**Атрибуты:**
- `result` (int): Результат вычисления 2 ** n.

### Примеры использования

```python
from power_of_two_calculator.models import PowerCalculationRequest, PowerCalculationResponse

# Создание запроса
request = PowerCalculationRequest(n=10)
print(request.n)  # Вывод: 10

# Создание ответа
response = PowerCalculationResponse(result=1024)
print(response.result)  # Вывод: 1024
```

## Модуль `power_of_two_calculator/server.py`

FastAPI сервер для вычисления n-ой степени двойки, содержащий приложение и эндпоинт для расчетов.

### Классы

#### `app (FastAPI)`

FastAPI приложение с заголовком "Power of Two Calculator" и описанием "API for calculating powers of two".

### Функции

- `power_calculation_endpoint(request: PowerCalculationRequest) -> PowerCalculationResponse`
  - Эндпоинт для вычисления n-ой степени двойки. Принимает запрос с показателем степени n и возвращает результат 2^n.
  - **Параметры:**
    - `request` (PowerCalculationRequest): Запрос с параметром n (неотрицательное целое число).
  - **Возвращает:** PowerCalculationResponse: Ответ с результатом вычисления.
  - **Исключения:** HTTPException, если n отрицательное или другая ошибка валидации.

### Примеры использования

Запуск сервера:

```bash
uvicorn power_of_two_calculator.server:app --reload
```

API вызов:

```python
import requests

# POST запрос к /calculate
response = requests.post("http://localhost:8000/calculate", json={"n": 3})
print(response.json())  # Вывод: {"result": 8}
```

## Модуль `tests/test_power_of_two_calculator.py`

Файл с юнит-тестами для PowerOfTwoCalculator и интерфейса IPowerCalculator, проверяющий корректность вычислений, обработку ошибок и паттерны.

### Классы

#### `TestPowerOfTwoCalculator (unittest.TestCase)`

Тесты для класса PowerOfTwoCalculator. Проверяет корректность вычисления n-ой степени двойки, работу паттерна Singleton и обработку ошибок.

**Методы:**

- `setUp(self)`: Подготовка к тестам: сброс экземпляра Singleton для чистоты тестов.

- `test_calculate_power_of_two_zero(self)`: Тест вычисления 2^0 = 1.

- `test_calculate_power_of_two_positive(self)`: Тест вычисления 2^n для положительных n.

- `test_calculate_power_of_two_large_n(self)`: Тест вычисления для большого n (например, 100).

- `test_calculate_power_of_two_negative_raises_error(self)`: Тест, что отрицательные n вызывают ValueError.

- `test_singleton_pattern(self)`: Тест паттерна Singleton: два экземпляра должны быть одинаковыми.

#### `TestIPowerCalculator (unittest.TestCase)`

Тесты для интерфейса IPowerCalculator. Проверяет, что реализации интерфейса работают корректно, используя мок для тестирования контракта.

**Методы:**

- `setUp(self)`: Подготовка: создание мока для IPowerCalculator.

- `test_calculate_power_of_two_called_correctly(self)`: Тест, что метод calculate_power_of_two вызывается с правильными аргументами.

- `test_interface_compliance(self)`: Тест, что PowerOfTwoCalculator соответствует интерфейсу IPowerCalculator.

### Примеры использования

Запуск тестов:

```bash
python -m unittest tests/test_power_of_two_calculator.py