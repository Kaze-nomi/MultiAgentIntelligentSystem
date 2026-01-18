# Справочник по коду (Code Reference)

## Оглавление

- [Обзор проекта](#обзор-проекта)
- [Пакет business.factorial_calculator](#пакет-businessfactorial_calculator)
  - [Модуль __init__.py](#модуль-__init__py)
  - [Модуль factorial_calculator.py](#модуль-factorial_calculatorpy)
  - [Модуль ifactorial_calculator.py](#модуль-ifactorial_calculatorpy)
- [Модуль tests/test_factorial_calculator.py](#модуль-teststest_factorial_calculatorpy)

## Обзор проекта

Этот проект предоставляет функциональность для вычисления факториала неотрицательных целых чисел. Он включает интерфейс и реализацию с использованием итеративного подхода. Архитектура основана на компоненте `FactorialCalculator`, который реализует интерфейс `IFactorialCalculator`. Проект написан на Python и включает модульные тесты.

## Пакет business.factorial_calculator

Пакет `business.factorial_calculator` содержит модули для вычисления факториала. Он включает инициализатор пакета, абстрактный интерфейс и конкретную реализацию.

### Модуль __init__.py

**Описание модуля:**  
Инициализатор пакета для модуля `factorial_calculator`, импортирующий и экспортирующий интерфейс и классы реализации.

**Классы:**  
В этом модуле классы отсутствуют.

**Функции:**  
В этом модуле функции отсутствуют.

**Примеры использования:**  
```python
from business.factorial_calculator import IFactorialCalculator, FactorialCalculator
```

### Модуль factorial_calculator.py

**Описание модуля:**  
Реализация класса `FactorialCalculator`, который вычисляет факториал итеративно, наследуя от `IFactorialCalculator`.

**Классы:**  

#### Класс FactorialCalculator

**Описание:**  
Конкретная реализация интерфейса `IFactorialCalculator` с использованием итеративного метода. Предоставляет эффективный способ вычисления факториала неотрицательного целого числа, избегая ограничений глубины рекурсии.

**Методы:**  

- **compute_factorial(n: int) -> int**  
  Вычисляет факториал неотрицательного целого числа.  
  **Параметры:**  
  - `n` (int): Неотрицательное целое число (>= 0).  
  **Возвращает:**  
  - int: Факториал числа n (n!).  
  **Исключения:**  
  - ValueError: Если n отрицательное.  
  - TypeError: Если n не является целым числом.  
  **Примеры использования:**  
  ```python
  calculator = FactorialCalculator()
  result = calculator.compute_factorial(5)  # Возвращает 120
  result_zero = calculator.compute_factorial(0)  # Возвращает 1
  ```

**Функции:**  
В этом модуле функции отсутствуют.

### Модуль ifactorial_calculator.py

**Описание модуля:**  
Абстрактный интерфейс для вычисления факториала, определяющий контракт для метода `compute_factorial`.

**Классы:**  

#### Класс IFactorialCalculator

**Описание:**  
Абстрактный интерфейс для вычисления факториала. Определяет контракт для классов, которые вычисляют факториал неотрицательного целого числа. Реализации должны обрабатывать валидацию входных данных и крайние случаи.

**Методы:**  

- **compute_factorial(n: int) -> int** (абстрактный)  
  Вычисляет факториал неотрицательного целого числа.  
  **Параметры:**  
  - `n` (int): Неотрицательное целое число (>= 0).  
  **Возвращает:**  
  - int: Факториал числа n (n!).  
  **Исключения:**  
  - ValueError: Если n отрицательное.  
  - TypeError: Если n не является целым числом.  

**Функции:**  
В этом модуле функции отсутствуют.

**Примеры использования:**  
```python
# Пример использования через реализацию
from business.factorial_calculator import FactorialCalculator
calculator = FactorialCalculator()
result = calculator.compute_factorial(4)  # Возвращает 24
```

## Модуль tests/test_factorial_calculator.py

**Описание модуля:**  
Модульные тесты для класса `FactorialCalculator`, покрывающие вычисление факториала для различных входных данных, включая крайние случаи и обработку ошибок.

**Классы:**  

#### Класс TestFactorialCalculator

**Описание:**  
Набор модульных тестов для проверки корректности вычисления факториала. Тесты включают проверки для нулевого, единичного, положительных чисел, а также обработку ошибок для отрицательных и нецелых чисел.

**Методы:**  
(Методы являются тестовыми и не документируются как публичные API; они используются для тестирования.)

**Функции:**  
В этом модуле функции отсутствуют.

**Примеры использования:**  
Запуск тестов:  
```bash
python -m unittest tests.test_factorial_calculator
```  

Пример теста (внутри кода):  
```python
import unittest
from business.factorial_calculator import FactorialCalculator

calculator = FactorialCalculator()
result = calculator.compute_factorial(5)
assert result == 120