# Справочник по коду Arbuz Client

## Оглавление

- [Обзор](#обзор)
- [Модули](#модули)
  - [infrastructure/arbuz_client/__init__.py](#infrastructurearbuz_client__init__py)
  - [infrastructure/arbuz_client/interfaces.py](#infrastructurearbuz_clientinterfacespy)
  - [infrastructure/arbuz_client/models.py](#infrastructurearbuz_clientmodelspy)
  - [infrastructure/arbuz_client/client.py](#infrastructurearbuz_clientclientpy)
  - [tests/test_arbuz_client.py](#teststest_arbuz_clientpy)

## Обзор

Этот справочник документирует код пакета `arbuz_client`, который предоставляет клиент для взаимодействия с внешним API ARBUZ. Пакет включает интерфейсы, модели данных и реализацию клиента. Код написан на Python и использует библиотеки `requests` для HTTP-запросов и `pydantic` для моделей данных.

## Модули

### infrastructure/arbuz_client/__init__.py

#### Описание модуля
Этот модуль является файлом инициализации пакета `arbuz_client`. Он импортирует основные компоненты и определяет публичный API пакета.

#### Классы
В этом модуле нет классов.

#### Функции
В этом модуле нет функций.

#### Примеры использования
```python
from infrastructure.arbuz_client import ArbuzClient, IArbuzClient, ArbuzRequest, ArbuzResponse

# Использование импортированных компонентов
client = ArbuzClient(base_url="https://api.arbuz.com", api_key="your_api_key")
```

### infrastructure/arbuz_client/interfaces.py

#### Описание модуля
Этот модуль определяет абстрактный интерфейс для клиента Arbuz API с использованием ABC (Abstract Base Classes).

#### Классы
- **IArbuzClient**: Интерфейс для клиента Arbuz API. Этот абстрактный базовый класс определяет контракт для взаимодействия с API ARBUZ, включая методы для получения и отправки данных.

  ##### Методы
  - `get_data(endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict[str, str]`: Получает данные из указанного endpoint. Параметры: `endpoint` (str, обязательный) - endpoint API для запроса; `params` (Optional[Dict[str, str]], необязательный) - дополнительные параметры запроса. Возвращает словарь с данными ответа.
  - `post_data(endpoint: str, data: Dict[str, str]) -> Dict[str, str]`: Отправляет данные в указанный endpoint. Параметры: `endpoint` (str, обязательный) - endpoint API для отправки; `data` (Dict[str, str], обязательный) - данные для отправки. Возвращает словарь с данными ответа.

#### Функции
В этом модуле нет функций.

#### Примеры использования
```python
from infrastructure.arbuz_client.interfaces import IArbuzClient

# IArbuzClient является абстрактным классом и не может быть инстанцирован напрямую.
# Для использования создайте подкласс, реализующий методы.
```

### infrastructure/arbuz_client/models.py

#### Описание модуля
Этот модуль определяет модели Pydantic для запросов и ответов Arbuz API, обеспечивая структурированную обработку данных с валидацией.

#### Классы
- **ArbuzRequest**: Модель, представляющая запрос к API ARBUZ. Атрибуты: `endpoint` (str) - endpoint API; `params` (Optional[Dict[str, Any]]) - параметры запроса; `data` (Optional[Dict[str, Any]]) - данные для POST-запросов.

- **ArbuzResponse**: Модель, представляющая ответ от API ARBUZ. Атрибуты: `status_code` (int) - HTTP-код статуса; `data` (Optional[Dict[str, Any]]) - данные ответа; `error` (Optional[str]) - сообщение об ошибке; `success` (bool) - индикатор успешности.

  ##### Методы
  - `from_success(status_code: int, data: Dict[str, Any]) -> ArbuzResponse`: Создает успешный ответ. Параметры: `status_code` (int) - HTTP-код; `data` (Dict[str, Any]) - данные ответа. Возвращает экземпляр ArbuzResponse.
  - `from_error(status_code: int, error: str) -> ArbuzResponse`: Создает ответ с ошибкой. Параметры: `status_code` (int) - HTTP-код; `error` (str) - сообщение об ошибке. Возвращает экземпляр ArbuzResponse.

#### Функции
В этом модуле нет функций.

#### Примеры использования
```python
from infrastructure.arbuz_client.models import ArbuzRequest, ArbuzResponse

# Создание запроса
request = ArbuzRequest(endpoint="/data", params={"key": "value"})

# Создание успешного ответа
response = ArbuzResponse.from_success(status_code=200, data={"result": "ok"})

# Создание ответа с ошибкой
error_response = ArbuzResponse.from_error(status_code=404, error="Not found")
```

### infrastructure/arbuz_client/client.py

#### Описание модуля
Этот модуль содержит реализацию класса ArbuzClient, который обрабатывает HTTP-запросы к API ARBUZ, реализуя интерфейс IArbuzClient с обработкой ошибок и парсингом ответов.

#### Классы
- **ArbuzClient**: Конкретная реализация клиента Arbuz API. Этот класс предоставляет методы для взаимодействия с API ARBUZ путем отправки GET и POST запросов. Обрабатывает аутентификацию, ошибки и сериализацию данных с использованием моделей Pydantic.

  ##### Свойства
  - `base_url` (str): Базовый URL API.
  - `api_key` (Optional[str]): Ключ API для аутентификации (приватное).
  - `timeout` (int): Таймаут запросов в секундах (по умолчанию 30).

  ##### Методы
  - `__init__(base_url: str, api_key: Optional[str] = None, timeout: int = 30)`: Инициализирует клиент. Параметры: `base_url` (str, обязательный) - базовый URL API; `api_key` (Optional[str], необязательный) - ключ API; `timeout` (int, необязательный) - таймаут.
  - `get_data(endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict[str, str]`: Получает данные из endpoint с помощью GET-запроса. Параметры: `endpoint` (str, обязательный) - endpoint (относительно base_url); `params` (Optional[Dict[str, str]], необязательный) - параметры запроса. Возвращает словарь с данными ответа. Может вызывать исключения: APIError, TimeoutError.
  - `post_data(endpoint: str, data: Dict[str, str]) -> Dict[str, str]`: Отправляет данные в endpoint с помощью POST-запроса. Параметры: `endpoint` (str, обязательный) - endpoint; `data` (Dict[str, str], обязательный) - данные для отправки. Возвращает словарь с данными ответа. Может вызывать исключения: APIError, ValidationError.

#### Функции
В этом модуле нет функций.

#### Примеры использования
```python
from infrastructure.arbuz_client.client import ArbuzClient

# Инициализация клиента
client = ArbuzClient(base_url="https://api.arbuz.com", api_key="your_api_key")

# GET-запрос
response = client.get_data(endpoint="/users", params={"id": "123"})
print(response)

# POST-запрос
response = client.post_data(endpoint="/users", data={"name": "John", "email": "john@example.com"})
print(response)
```

### tests/test_arbuz_client.py

#### Описание модуля
Этот модуль содержит юнит-тесты для ArbuzClient и IArbuzClient, обеспечивая корректную функциональность и обработку ошибок.

#### Классы
- **TestArbuzClient**: Тесты для класса ArbuzClient. Тестирует операции GET и POST, обработку ошибок и парсинг ответов.

  ##### Методы
  - `setUp()`: Настраивает фикстуры перед каждым тестом.
  - `test_get_data_success()`: Тестирует успешный GET-запрос.
  - `test_get_data_failure()`: Тестирует неудачный GET-запрос.
  - `test_post_data_success()`: Тестирует успешный POST-запрос.
  - `test_post_data_failure()`: Тестирует неудачный POST-запрос.
  - `test_init_without_api_key()`: Тестирует инициализацию без API-ключа.

- **TestIArbuzClient**: Тесты для интерфейса IArbuzClient. Проверяет, что это абстрактный базовый класс и не может быть инстанцирован напрямую.

  ##### Методы
  - `test_abstract_methods()`: Тестирует, что абстрактные методы вызывают NotImplementedError.

#### Функции
В этом модуле нет функций.

#### Примеры использования
```python
# Запуск тестов
import unittest
from tests.test_arbuz_client import TestArbuzClient, TestIArbuzClient

if __name__ == '__main__':
    unittest.main()