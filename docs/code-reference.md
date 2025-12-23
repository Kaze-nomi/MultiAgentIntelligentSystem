# Справочник по коду

## Содержание

- [Справочник по коду](#справочник-по-коду)
  - [Содержание](#содержание)
  - [Модуль `src.my_project.domain`](#модуль-srcmy_projectdomain)
    - [Класс `Watermelon`](#класс-watermelon)
      - [Атрибуты](#атрибуты)
      - [Методы](#методы)
      - [Примеры использования](#примеры-использования)
    - [Перечисление `RipenessStatus`](#перечисление-ripenessstatus)
      - [Значения](#значения)
      - [Примеры использования](#примеры-использования-1)
  - [Модуль `src.my_project.service.protocols`](#модуль-srcmy_projectserviceprotocols)
    - [Класс `IRipenessEvaluator`](#класс-iripenessevaluator)
      - [Методы](#методы-1)
      - [Примеры использования](#примеры-использования-2)
    - [Протокол `RipenessEvaluatorProtocol`](#протокол-ripenessevaluatorprotocol)
      - [Методы](#методы-2)
      - [Примеры использования](#примеры-использования-3)
  - [Модуль `src.my_project.service`](#модуль-srcmy_projectservice)
    - [Функция `create_ripeness_evaluator`](#функция-create_ripeness_evaluator)
      - [Параметры](#параметры)
      - [Возвращаемое значение](#возвращаемое-значение)
      - [Примеры использования](#примеры-использования-4)
    - [Функция `evaluate_watermelon_ripeness`](#функция-evaluate_watermelon_ripeness)
      - [Параметры](#параметры-1)
      - [Возвращаемое значение](#возвращаемое-значение-1)
      - [Примеры использования](#примеры-использования-5)
    - [Класс `ServiceConfig`](#класс-serviceconfig)
      - [Атрибуты класса](#атрибуты-класса)
      - [Методы класса](#методы-класса)
      - [Примеры использования](#примеры-использования-6)

---

## Модуль `src.my_project.domain`

Модуль `src.my_project.domain` содержит основные доменные модели и перечисления для представления арбуза и оценки его зрелости.

### Класс `Watermelon`

Класс `Watermelon` представляет собой доменную модель арбуза с его физическими свойствами. Использует Pydantic для валидации данных.

#### Атрибуты

| Имя | Тип | Описание | Обязательный | По умолчанию | Ограничения |
|---|---|---|---|---|---|
| `weight` | `float` | Вес арбуза в граммах. | Да | Нет | `ge=0.5`, `le=30.0` |
| `diameter` | `float` | Диаметр арбуза в сантиметрах. | Да | Нет | `ge=10.0`, `le=80.0` |
| `color_code` | `str` | Hex-код цвета, представляющий внешний вид. | Да | Нет | `regex=r'^#[0-9A-Fa-f]{6}$'` |
| `stripe_pattern` | `bool` | Наличие характерных полосок на корке. | Нет | `True` | - |
| `spot_size` | `Optional[float]` | Размер желтого пятна, где арбуз лежал на земле (см). | Нет | `None` | `ge=0.0`, `le=20.0` |
| `sound_hollowness` | `Optional[int]` | Воспринимаемая полость при постукивании (шкала 1-10). | Нет | `None` | `ge=1`, `le=10` |
| `surface_texture` | `Optional[str]` | Описание текстуры поверхности. | Нет | `None` | `max_length=50` |

#### Методы

- `get_density() -> float`
  - **Описание**: Рассчитывает приблизительную плотность арбуза.
  - **Возвращает**: Плотность в кг/см³, рассчитанная на основе веса и диаметра.

- `is_oval_shaped() -> bool`
  - **Описание**: Определяет, является ли арбуз, вероятно, овальной формы, на основе соотношения веса и диаметра.
  - **Возвращает**: `True`, если, вероятно, овальной формы, иначе `False`.

- `__str__() -> str`
  - **Описание**: Возвращает строковое представление арбуза.
  - **Возвращает**: Человекочитаемое описание арбуза.

- `__repr__() -> str`
  - **Описание**: Возвращает подробное строковое представление арбуза.
  - **Возвращает**: Подробное представление, включающее все атрибуты.

#### Примеры использования

```python
from src.my_project.domain import Watermelon

# Создание экземпляра арбуза
watermelon = Watermelon(
    weight=5000.0,
    diameter=30.0,
    color_code="#4CAF50",
    surface_texture="smooth"
)

# Расчет плотности
density = watermelon.get_density()
print(f"Плотность арбуза: {density} кг/см³")

# Проверка формы
is_oval = watermelon.is_oval_shaped()
print(f"Арбуз овальной формы: {is_oval}")

# Строковое представление
print(watermelon)
# Вывод: Watermelon(weight=5000.0kg, diameter=30.0cm, color=#4CAF50, striped=True)
```

### Перечисление `RipenessStatus`

Перечисление `RipenessStatus` описывает возможные состояния зрелости арбуза.

#### Значения

| Имя | Значение | Описание |
|---|---|---|
| `UNRIPE` | `"unripe"` | Арбуз еще не созрел и требует больше времени для созревания. |
| `EARLY_RIPE` | `"early_ripe"` | Арбуз начинает созревать, но еще не полностью готов. |
| `RIPE` | `"ripe"` | Арбуз идеально созрел и готов к употреблению. |
| `LATE_RIPE` | `"late_ripe"` | Арбуз прошел пик зрелости, но все еще съедобен. |
| `OVERRIPE` | `"overripe"` | Арбуз слишком спелый и может иметь ухудшенное качество. |

#### Примеры использования

```python
from src.my_project.domain import RipenessStatus

# Проверка статуса
if RipenessStatus.RIPE == "ripe":
    print("Арбуз готов к употреблению!")

# Итерация по статусам
for status in RipenessStatus:
    print(f"Статус: {status.name}, Значение: {status.value}")
```

---

## Модуль `src.my_project.service.protocols`

Модуль `src.my_project.service.protocols` определяет абстрактные базовые классы и протоколы, которые устанавливают контракты для сервисов оценки зрелости арбуза.

### Класс `IRipenessEvaluator`

Абстрактный базовый класс для сервисов оценки зрелости арбуза. Этот интерфейс определяет контракт для сервисов, которые оценивают зрелость арбуза на основе его физических свойств.

#### Методы

- `evaluate(watermelon: Watermelon) -> RipenessStatus`
  - **Описание**: Оценивает статус зрелости арбуза.
  - **Параметры**:
    - `watermelon` (`Watermelon`): Экземпляр арбуза для оценки. Должен содержать валидные физические свойства.
  - **Возвращает**: `RipenessStatus`: Оцененный статус зрелости арбуза.
  - **Исключения**:
    - `ValueError`: Если у арбуза недействительные или неполные свойства, которые мешают оценке.
    - `TypeError`: Если параметр `watermelon` не является действительным экземпляром `Watermelon`.

#### Примеры использования

```python
from abc import ABC, abstractmethod
from src.my_project.domain import Watermelon, RipenessStatus
from src.my_project.service.protocols import IRipenessEvaluator

class MyCustomEvaluator(IRipenessEvaluator):
    def evaluate(self, watermelon: Watermelon) -> RipenessStatus:
        # Пользовательская логика оценки
        if watermelon.weight > 6000:
            return RipenessStatus.OVERRIPE
        return RipenessStatus.RIPE

evaluator = MyCustomEvaluator()
status = evaluator.evaluate(watermelon)
```

### Протокол `RipenessEvaluatorProtocol`

Протокол типа для реализаций оценки зрелости. Этот протокол обеспечивает структурную типизацию для оценщиков зрелости, позволяя любому классу с методом `evaluate` использоваться как оценщик зрелости без явного наследования.

#### Методы

- `evaluate(watermelon: Watermelon) -> RipenessStatus`
  - **Описание**: Оценивает зрелость арбуза.
  - **Параметры**:
    - `watermelon` (`Watermelon`): Экземпляр арбуза для оценки.
  - **Возвращает**: `RipenessStatus`: Оцененный статус зрелости.

#### Примеры использования

```python
from typing import Protocol
from src.my_project.domain import Watermelon, RipenessStatus
from src.my_project.service.protocols import RipenessEvaluatorProtocol

class SimpleEvaluator:
    def evaluate(self, watermelon: Watermelon) -> RipenessStatus:
        # Простая логика
        return RipenessStatus.RIPE

def use_evaluator(evaluator: RipenessEvaluatorProtocol, watermelon: Watermelon):
    status = evaluator.evaluate(watermelon)
    print(f"Статус зрелости: {status}")

simple_evaluator = SimpleEvaluator()
use_evaluator(simple_evaluator, watermelon)
```

---

## Модуль `src.my_project.service`

Модуль `src.my_project.service` предоставляет сервисы и реализации для оценки зрелости арбуза на основе его физических свойств.

### Функция `create_ripeness_evaluator`

Фабричная функция для создания экземпляров оценщиков зрелости.

#### Параметры

| Имя | Тип | Описание | Обязательный | По умолчанию |
|---|---|---|---|---|
| `evaluator_type` | `str` | Тип создаваемого оценщика. Варианты: `"default"`, `"heuristic"`. | Нет | `"default"` |
| `config` | `Optional[dict]` | Опциональный словарь конфигурации для переопределения значений по умолчанию. | Нет | `None` |

#### Возвращаемое значение

- `IRipenessEvaluator`: Настроенный экземпляр оценщика.

#### Примеры использования

```python
from src.my_project.service import create_ripeness_evaluator, Watermelon

# Создание оценщика по умолчанию
default_evaluator = create_ripeness_evaluator()

# Создание эвристического оценщика
heuristic_evaluator = create_ripeness_evaluator(evaluator_type="heuristic")

# Создание оценщика с кастомной конфигурацией
custom_config = {"min_ripe_weight_kg": 4.5}
custom_evaluator = create_ripeness_evaluator(config=custom_config)
```

### Функция `evaluate_watermelon_ripeness`

Удобная функция для быстрой оценки зрелости арбуза.

#### Параметры

| Имя | Тип | Описание | Обязательный | По умолчанию |
|---|---|---|---|---|
| `watermelon` | `Watermelon` | Экземпляр арбуза для оценки. | Да | Нет |
| `evaluator_type` | `str` | Тип используемого оценщика (`"default"` или `"heuristic"`). | Нет | `"default"` |

#### Возвращаемое значение

- `RipenessStatus`: Оцененный статус зрелости.

#### Примеры использования

```python
from src.my_project.service import evaluate_watermelon_ripeness, Watermelon

watermelon = Watermelon(
    weight=5000.0,
    diameter=30.0,
    color_code="#4CAF50",
    surface_texture="smooth"
)

# Быстрая оценка
status = evaluate_watermelon_ripeness(watermelon)
print(f"Статус зрелости: {status}")
```

### Класс `ServiceConfig`

Класс конфигурации для сервисного слоя. Предоставляет централизованную конфигурацию для всех сервисов в пакете, позволяя легко настраивать параметры оценки и поведение.

#### Атрибуты класса

| Имя | Тип | Описание | По умолчанию |
|---|---|---|---|
| `DEFAULT_MIN_WEIGHT` | `float` | Минимальный вес для оценки (граммы). | `2000.0` |
| `DEFAULT_MAX_WEIGHT` | `float` | Максимальный вес для оценки (граммы). | `15000.0` |
| `DEFAULT_MIN_DIAMETER` | `float` | Минимальный диаметр для оценки (см). | `15.0` |
| `DEFAULT_MAX_DIAMETER` | `float` | Максимальный диаметр для оценки (см). | `50.0` |
| `WEIGHT_FACTOR` | `float` | Весовой коэффициент для веса в общей оценке. | `0.3` |
| `DIAMETER_FACTOR` | `float` | Весовой коэффициент для диаметра. | `0.25` |
| `COLOR_FACTOR` | `float` | Весовой коэффициент для цвета. | `0.25` |
| `TEXTURE_FACTOR` | `float` | Весовой коэффициент для текстуры. | `0.2` |
| `MIN_COLOR_QUALITY` | `float` | Минимальный порог качества цвета. | `0.3` |
| `MAX_COLOR_QUALITY` | `float` | Максимальный порог качества цвета. | `0.8` |
| `TEXTURE_SCORES` | `dict` | Словарь с оценками для различных текстур. | `{"smooth": 1.0, ...}` |

#### Методы класса

- `validate_config() -> bool`
  - **Описание**: Проверяет параметры конфигурации на валидность.
  - **Возвращает**: `True`, если конфигурация валидна, иначе `False`.

#### Примеры использования

```python
from src.my_project.service import ServiceConfig

# Доступ к параметрам конфигурации
min_weight = ServiceConfig.DEFAULT_MIN_WEIGHT
print(f"Минимальный вес: {min_weight} г")

# Проверка валидности конфигурации
is_valid = ServiceConfig.validate_config()
print(f"Конфигурация валидна: {is_valid}")

# Изменение параметра (не рекомендуется, но возможно)
ServiceConfig.WEIGHT_FACTOR = 0.35