# Справка по коду (Code Reference)

## Оглавление

- [Пакет interfaces](#пакет-interfaces)
  - [Модуль interfaces/__init__.py](#модуль-interfaces__init__py)
  - [Модуль interfaces/i_weather_service.py](#модуль-interfacesi_weather_servicepy)
- [Пакет data](#пакет-data)
  - [Модуль data/__init__.py](#модуль-data__init__py)
  - [Модуль data/weather_data.py](#модуль-dataweather_datapy)
- [Пакет business](#пакет-business)
  - [Модуль business/__init__.py](#модуль-business__init__py)
  - [Модуль business/weather_service.py](#модуль-businessweather_servicepy)
- [Пакет tests](#пакет-tests)
  - [Модуль tests/test_weather_service.py](#модуль-teststest_weather_servicepy)
  - [Модуль tests/test_weather_data.py](#модуль-teststest_weather_datapy)

## Пакет interfaces

### Модуль interfaces/__init__.py

**Описание модуля:**  
Инициализационный файл для пакета interfaces, импортирующий и экспортирующий интерфейс IWeatherService.

**Классы:**  
Нет классов.

**Функции:**  
Нет функций.

**Примеры использования:**  
```python
from interfaces import IWeatherService
```

### Модуль interfaces/i_weather_service.py

**Описание модуля:**  
Абстрактный интерфейс, определяющий контракт для сервисов погоды, включая метод get_weather.

**Классы:**  
- **IWeatherService (ABC)**: Интерфейс для сервиса погоды. Определяет контракт для получения данных о погоде. Реализации должны предоставлять логику для извлечения информации о погоде из внешних API или источников.  
  - **Методы:**  
    - `get_weather(self, city: str) -> WeatherData`: Получить данные о погоде для указанного города.  
      - **Параметры:**  
        - `city (str)`: Название города.  
      - **Возвращает:** WeatherData: Структурированные данные о погоде для города.  
      - **Исключения:** ValueError (если название города недействительно или пустое), ConnectionError (если проблема с подключением к сервису погоды), RuntimeError (если данные о погоде не могут быть получены или разобраны).

**Функции:**  
Нет функций.

**Примеры использования:**  
```python
from interfaces.i_weather_service import IWeatherService

# Реализация интерфейса
class MyWeatherService(IWeatherService):
    def get_weather(self, city: str):
        # Логика реализации
        pass
```

## Пакет data

### Модуль data/__init__.py

**Описание модуля:**  
Инициализационный файл для пакета data, импортирующий и экспортирующий класс WeatherData.

**Классы:**  
Нет классов.

**Функции:**  
Нет функций.

**Примеры использования:**  
```python
from data import WeatherData
```

### Модуль data/weather_data.py

**Описание модуля:**  
Модель данных для информации о погоде с использованием Pydantic для валидации и структуры.

**Классы:**  
- **WeatherData (BaseModel)**: Модель данных, представляющая информацию о погоде для конкретного города. Инкапсулирует структурированные данные о погоде, полученные из внешнего сервиса погоды. Включает основные параметры погоды, такие как температура, влажность и описание.  
  - **Атрибуты:**  
    - `city (str)`: Название города.  
    - `temperature (float)`: Текущая температура в градусах Цельсия.  
    - `description (str)`: Текстовое описание текущих погодных условий (например, 'clear sky', 'rainy').  
    - `humidity (Optional[int])`: Процент влажности, если доступно.  
    - `wind_speed (Optional[float])`: Скорость ветра в метрах в секунду, если доступно.  
    - `timestamp (datetime)`: Временная метка, когда данные о погоде были получены.  
  - **Методы:**  
    Нет методов.

**Функции:**  
Нет функций.

**Примеры использования:**  
```python
from data.weather_data import WeatherData
from datetime import datetime

weather = WeatherData(
    city="Moscow",
    temperature=15.5,
    description="clear sky",
    humidity=60,
    wind_speed=3.2,
    timestamp=datetime.utcnow()
)
print(weather.city)  # Moscow
```

## Пакет business

### Модуль business/__init__.py

**Описание модуля:**  
Реализация класса WeatherService, предоставляющего API для получения данных о погоде, интегрирующая существующий интерфейс IWeatherService и модель WeatherData.

**Классы:**  
- **WeatherService (IWeatherService)**: Реализация интерфейса сервиса погоды. Предоставляет функциональность для получения текущих данных о погоде для указанного города с использованием API OpenWeatherMap. Обрабатывает вызовы API, разбор ответов и обработку ошибок.  
  - **Атрибуты:**  
    - `api_key (str)`: Ключ API для доступа к сервису OpenWeatherMap.  
  - **Методы:**  
    - `__init__(self, api_key: Optional[str] = None)`: Инициализировать WeatherService с ключом API.  
      - **Параметры:**  
        - `api_key (Optional[str])`: Ключ API для OpenWeatherMap. Если не предоставлен, будет получен из переменной окружения 'OPENWEATHER_API_KEY'.  
      - **Исключения:** ValueError (если ключ API не предоставлен или не найден в окружении).  
    - `get_weather(self, city: str) -> WeatherData`: Получить данные о погоде для указанного города. Делает вызов API к OpenWeatherMap для получения текущей информации о погоде и возвращает её как объект WeatherData.  
      - **Параметры:**  
        - `city (str)`: Название города.  
      - **Возвращает:** WeatherData: Структурированные данные о погоде для города.  
      - **Исключения:** ValueError (если название города недействительно или пустое), ConnectionError (если проблема с подключением к сервису погоды), RuntimeError (если данные о погоде не могут быть получены или разобраны).

**Функции:**  
Нет функций.

**Примеры использования:**  
```python
from business.weather_service import WeatherService

service = WeatherService(api_key="your_api_key")
weather = service.get_weather("London")
print(weather.temperature)  # 15.0
```

### Модуль business/weather_service.py

**Описание модуля:**  
Реализация класса WeatherService, получающего данные о погоде из API OpenWeatherMap.

**Классы:**  
- **WeatherService (IWeatherService)**: Реализация интерфейса сервиса погоды. Предоставляет функциональность для получения текущих данных о погоде для указанного города с использованием API OpenWeatherMap. Обрабатывает вызовы API, разбор ответов и обработку ошибок.  
  - **Атрибуты:**  
    - `api_key (str)`: Ключ API для доступа к сервису OpenWeatherMap.  
  - **Методы:**  
    - `__init__(self, api_key: Optional[str] = None)`: Инициализировать WeatherService с ключом API.  
      - **Параметры:**  
        - `api_key (Optional[str])`: Ключ API для OpenWeatherMap. Если не предоставлен, будет получен из переменной окружения 'OPENWEATHER_API_KEY'.  
      - **Исключения:** ValueError (если ключ API не предоставлен или не найден в окружении).  
    - `get_weather(self, city: str) -> WeatherData`: Получить данные о погоде для указанного города.  
      - **Параметры:**  
        - `city (str)`: Название города.  
      - **Возвращает:** WeatherData: Структурированные данные о погоде для города.  
      - **Исключения:** ValueError (если название города недействительно или пустое), ConnectionError (если проблема с подключением к сервису погоды), RuntimeError (если данные о погоде не могут быть получены или разобраны).

**Функции:**  
Нет функций.

**Примеры использования:**  
```python
from business.weather_service import WeatherService

service = WeatherService(api_key="your_api_key")
weather = service.get_weather("London")
print(weather.temperature)  # 15.0
```

## Пакет tests

### Модуль tests/test_weather_service.py

**Описание модуля:**  
Файл модульных тестов для класса WeatherService, покрывающий успешные операции и обработку ошибок.

**Классы:**  
- **TestWeatherService (unittest.TestCase)**: Набор тестов для класса WeatherService. Тестирует функциональность WeatherService, включая успешное получение данных о погоде и сценарии обработки ошибок.  
  - **Методы:**  
    - `setUp(self)`: Настроить фикстуры тестов перед каждым методом теста.  
    - `test_get_weather_success(self, mock_get)`: Тест успешного получения данных о погоде.  
    - `test_get_weather_invalid_city(self, mock_get)`: Тест обработки недействительного названия города.  
    - `test_get_weather_connection_error(self, mock_get)`: Тест обработки ошибок подключения.  
    - `test_init_without_api_key(self)`: Тест инициализации без ключа API, ожидая ValueError.  
    - `test_init_with_env_api_key(self)`: Тест инициализации с использованием ключа API из переменной окружения.  
    - `test_get_weather_empty_city(self, mock_get)`: Тест обработки пустого названия города.

**Функции:**  
Нет функций.

**Примеры использования:**  
```python
import unittest
from tests.test_weather_service import TestWeatherService

if __name__ == '__main__':
    unittest.main()
```

### Модуль tests/test_weather_data.py

**Описание модуля:**  
Файл модульных тестов для класса WeatherData, покрывающий создание, валидацию и обработку ошибок.

**Классы:**  
- **TestWeatherData (unittest.TestCase)**: Набор тестов для класса WeatherData. Тестирует функциональность модели WeatherData Pydantic, включая успешное создание, валидацию полей, опциональные поля и обработку ошибок.  
  - **Методы:**  
    - `test_create_weather_data_with_all_fields(self)`: Тест создания экземпляра WeatherData со всеми полями.  
    - `test_create_weather_data_with_required_fields_only(self)`: Тест создания экземпляра WeatherData только с обязательными полями.  
    - `test_default_timestamp(self)`: Тест, что timestamp по умолчанию устанавливается на текущее время UTC.  
    - `test_validation_error_for_missing_required_field_city(self)`: Тест, что ValidationError возникает при отсутствии обязательного поля 'city'.  
    - `test_validation_error_for_missing_required_field_temperature(self)`: Тест, что ValidationError возникает при отсутствии обязательного поля 'temperature'.  
    - `test_validation_error_for_missing_required_field_description(self)`: Тест, что ValidationError возникает при отсутствии обязательного поля 'description'.  
    - `test_validation_error_for_invalid_temperature_type(self)`: Тест, что ValidationError возникает, когда 'temperature' не является float.  
    - `test_validation_error_for_invalid_humidity_type(self)`: Тест, что ValidationError возникает, когда 'humidity' не является int.  
    - `test_validation_error_for_invalid_wind_speed_type(self)`: Тест, что ValidationError возникает, когда 'wind_speed' не является float.  
    - `test_optional_fields_can_be_none(self)`: Тест, что опциональные поля могут быть явно установлены в None.

**Функции:**  
Нет функций.

**Примеры использования:**  
```python
import unittest
from tests.test_weather_data import TestWeatherData

if __name__ == '__main__':
    unittest.main()