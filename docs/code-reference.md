# Справочник по коду (Code Reference)

## Оглавление

- [Введение](#введение)
- [Пакет music_composer_agent](#пакет-music_composer_agent)
  - [Модуль __init__.py](#модуль-__init__py)
  - [Модуль models.py](#модуль-models_py)
  - [Модуль server.py](#модуль-server_py)
  - [Модуль interfaces.py](#модуль-interfaces_py)
  - [Модуль services.py](#модуль-services_py)
  - [Модуль constants.py](#модуль-constants_py)
- [Пакет tests](#пакет-tests)
  - [Модуль test_music_composer_agent.py](#модуль-test_music_composer_agent_py)

## Введение

Этот справочник документирует код проекта Music Composer Agent, написанного на Python. Проект предоставляет инструменты для генерации и валидации музыкальных композиций с использованием LLM-сервисов. Документация основана на реальном коде и архитектуре проекта, включая компоненты, интерфейсы и модули.

## Пакет music_composer_agent

Пакет `music_composer_agent` содержит основные компоненты для работы с музыкальными композициями.

### Модуль __init__.py

**Описание модуля:**  
Этот модуль инициализирует пакет `music_composer_agent`. Он содержит импорты основных классов, интерфейсов, исключений и сервисов, а также определяет публичный API пакета через `__all__`.

**Классы:**  
Нет классов.

**Функции:**  
Нет функций.

**Примеры использования:**  
```python
from music_composer_agent import MusicalComposition, MusicComposerAgent, IMusicComposer

# Использование импортированных классов
composition = MusicalComposition(title="Test", composer="AI", key="C major", notes=["C4", "D4"])
```

### Модуль models.py

**Описание модуля:**  
Модуль определяет структуры данных для музыкальных композиций, включая класс `MusicalComposition`, который представляет композицию с метаданными и нотами.

**Классы:**

- **MusicalComposition**  
  Класс представляет музыкальную композицию с атрибутами, такими как заголовок, композитор, тональность, темп, жанр, ноты и метаданные. Включает методы для валидации, добавления нот и сериализации.

  **Свойства:**
  - `title` (str): Заголовок композиции.
  - `composer` (str): Композитор композиции.
  - `key` (str): Тональность композиции (например, 'C major', 'E minor').
  - `tempo` (Optional[int]): Темп в BPM, если указан.
  - `genre` (Optional[str]): Жанр композиции, если указан.
  - `notes` (List[str]): Список нот или музыкальных элементов в текстовом представлении.
  - `metadata` (Dict[str, Any]): Дополнительные метаданные в виде пар ключ-значение.

  **Методы:**

  - `__post_init__()`: Пост-инициализация с валидацией.  
    **Параметры:** Нет.  
    **Возвращает:** Нет.  
    **Исключения:** ValueError, если поля недействительны.

  - `_validate()`: Валидирует поля композиции.  
    **Параметры:** Нет.  
    **Возвращает:** Нет.  
    **Исключения:** ValueError, если валидация не пройдена.

  - `add_note(note: str)`: Добавляет ноту к композиции.  
    **Параметры:**  
      - `note` (str): Нота для добавления.  
    **Возвращает:** Нет.  
    **Исключения:** ValueError, если нота не является строкой.

  - `get_notes_as_string() -> str`: Возвращает ноты как единую строку.  
    **Параметры:** Нет.  
    **Возвращает:** str - Ноты, объединенные пробелами.  
    **Исключения:** Нет.

  - `to_dict() -> Dict[str, Any]`: Преобразует композицию в словарь.  
    **Параметры:** Нет.  
    **Возвращает:** Dict[str, Any] - Словарь с данными композиции.  
    **Исключения:** Нет.

  - `from_dict(data: Dict[str, Any]) -> 'MusicalComposition'`: Создает композицию из словаря (класс-метод).  
    **Параметры:**  
      - `data` (Dict[str, Any]): Словарь с данными композиции.  
    **Возвращает:** MusicalComposition - Созданная композиция.  
    **Исключения:** ValueError, если данные недействительны.

**Функции:**  
Нет функций.

**Примеры использования:**  
```python
from music_composer_agent.models import MusicalComposition

# Создание композиции
composition = MusicalComposition(
    title="Waltz in C minor",
    composer="AI Composer",
    key="C minor",
    notes=["C4", "Eb4", "G4"]
)

# Добавление ноты
composition.add_note("Bb4")

# Получение нот как строки
notes_str = composition.get_notes_as_string()  # "C4 Eb4 G4 Bb4"

# Сериализация
data = composition.to_dict()

# Десериализация
new_composition = MusicalComposition.from_dict(data)
```

### Модуль server.py

**Описание модуля:**  
Модуль содержит класс `MusicComposerAgent`, который реализует интерфейс `IMusicComposer` и предоставляет сервис для генерации и валидации композиций с использованием LLM-сервисов.

**Классы:**

- **MusicComposerAgent**  
  Сервис для генерации и валидации музыкальных композиций с использованием LLM-подходов.

  **Свойства:**
  - `llm_service` (OpenRouterMCPService): Экземпляр сервиса для взаимодействия с LLM.
  - `composition_style` (str): Стиль композиции (по умолчанию 'classical').
  - `api_key` (str): API-ключ для аутентификации.

  **Методы:**

  - `__init__(llm_service: OpenRouterMCPService, composition_style: str = "classical", api_key: str = None)`: Инициализирует агент.  
    **Параметры:**  
      - `llm_service` (OpenRouterMCPService): LLM-сервис.  
      - `composition_style` (str): Стиль композиции.  
      - `api_key` (str): API-ключ.  
    **Возвращает:** Нет.  
    **Исключения:** ValueError, если API-ключ не предоставлен.

  - `generate_composition(prompt: str, key: str = "C minor") -> MusicalComposition`: Генерирует композицию на основе запроса (асинхронный).  
    **Параметры:**  
      - `prompt` (str): Запрос на композицию.  
      - `key` (str): Тональность.  
    **Возвращает:** MusicalComposition - Сгенерированная композиция.  
    **Исключения:** CompositionGenerationError, если генерация не удалась.

  - `validate_composition(composition: MusicalComposition) -> bool`: Валидирует композицию.  
    **Параметры:**  
      - `composition` (MusicalComposition): Композиция для валидации.  
    **Возвращает:** bool - True, если валидна.  
    **Исключения:** TypeError, если вход не является MusicalComposition.

**Функции:**  
Нет функций.

**Примеры использования:**  
```python
import asyncio
from music_composer_agent.server import MusicComposerAgent
from music_composer_agent.services import OpenRouterMCPService

async def main():
    llm_service = OpenRouterMCPService(api_key="your_api_key")
    agent = MusicComposerAgent(llm_service=llm_service, api_key="your_api_key")
    
    # Генерация композиции
    composition = await agent.generate_composition("Вальс Шуберта в ми миноре", key="E minor")
    
    # Валидация
    is_valid = agent.validate_composition(composition)
    print(is_valid)  # True

asyncio.run(main())
```

### Модуль interfaces.py

**Описание модуля:**  
Модуль определяет абстрактный интерфейс `IMusicComposer` для композиторов музыки.

**Классы:**

- **IMusicComposer**  
  Абстрактный интерфейс для композитора музыки, определяющий методы генерации и валидации композиций.

  **Свойства:**  
  Нет.

  **Методы:**

  - `generate_composition(prompt: str, key: str = "C minor") -> MusicalComposition`: Абстрактный метод для генерации композиции (асинхронный).  
    **Параметры:**  
      - `prompt` (str): Описание или запрос для генерации.  
      - `key` (str): Тональность.  
    **Возвращает:** MusicalComposition - Сгенерированная композиция.  
    **Исключения:** CompositionGenerationError, если запрос недействителен.

  - `validate_composition(composition: MusicalComposition) -> bool`: Абстрактный метод для валидации композиции.  
    **Параметры:**  
      - `composition` (MusicalComposition): Композиция для валидации.  
    **Возвращает:** bool - True, если валидна.  
    **Исключения:** TypeError, если объект не является MusicalComposition.

**Функции:**  
Нет функций.

**Примеры использования:**  
```python
from music_composer_agent.interfaces import IMusicComposer

# Реализация интерфейса
class MyComposer(IMusicComposer):
    async def generate_composition(self, prompt: str, key: str = "C minor"):
        # Реализация
        pass
    
    def validate_composition(self, composition):
        # Реализация
        pass
```

### Модуль services.py

**Описание модуля:**  
Модуль содержит класс `OpenRouterMCPService` для взаимодействия с API OpenRouter для генерации композиций с использованием LLM.

**Классы:**

- **OpenRouterMCPService**  
  Сервис для взаимодействия с OpenRouter MCP API для LLM-генерации.

  **Свойства:**
  - `api_key` (str): API-ключ для OpenRouter.
  - `base_url` (str): Базовый URL API.
  - `model` (str): Модель LLM.
  - `session` (aiohttp.ClientSession): Сессия для HTTP-запросов.

  **Методы:**

  - `__init__(api_key: str = None, base_url: str = "https://openrouter.ai/api/v1", model: str = "openai/gpt-3.5-turbo")`: Инициализирует сервис.  
    **Параметры:**  
      - `api_key` (str): API-ключ.  
      - `base_url` (str): Базовый URL.  
      - `model` (str): Модель.  
    **Возвращает:** Нет.  
    **Исключения:** ValueError, если API-ключ не предоставлен.

  - `__aenter__()`: Вход в асинхронный контекст-менеджер.  
    **Параметры:** Нет.  
    **Возвращает:** Self.  
    **Исключения:** Нет.

  - `__aexit__(exc_type, exc_val, exc_tb)`: Выход из асинхронного контекст-менеджера.  
    **Параметры:** Нет.  
    **Возвращает:** Нет.  
    **Исключения:** Нет.

  - `generate(prompt: str, key: str, style: str) -> Dict[str, Any]`: Генерирует данные композиции с использованием LLM.  
    **Параметры:**  
      - `prompt` (str): Запрос.  
      - `key` (str): Тональность.  
      - `style` (str): Стиль.  
    **Возвращает:** Dict[str, Any] - Данные композиции.  
    **Исключения:** ValueError, если вход недействителен; Exception, если API-вызов не удался.

**Функции:**  
Нет функций.

**Примеры использования:**  
```python
import asyncio
from music_composer_agent.services import OpenRouterMCPService

async def main():
    async with OpenRouterMCPService(api_key="your_api_key") as service:
        result = await service.generate("Вальс", "C minor", "classical")
        print(result)  # {'title': '...', 'notes': [...]}

asyncio.run(main())
```

### Модуль constants.py

**Описание модуля:**  
Модуль содержит константы для валидных ключей и стилей композиций.

**Классы:**  
Нет классов.

**Функции:**  
Нет функций.

**Константы:**
- `VALID_KEYS`: Список допустимых тональностей (например, ["C major", "C minor", ...]).
- `VALID_STYLES`: Список допустимых стилей (["classical", "jazz", "rock", "pop"]).

**Примеры использования:**  
```python
from music_composer_agent.constants import VALID_KEYS, VALID_STYLES

print(VALID_KEYS)  # ['C major', 'C minor', ...]
print(VALID_STYLES)  # ['classical', 'jazz', 'rock', 'pop']
```

## Пакет tests

Пакет `tests` содержит модульные тесты для проекта.

### Модуль test_music_composer_agent.py

**Описание модуля:**  
Модуль содержит тесты для классов `MusicalComposition`, `MusicComposerAgent` и `IMusicComposer` с использованием unittest.

**Классы:**

- **TestMusicalComposition**: Тесты для `MusicalComposition`.
- **TestMusicComposerAgent**: Тесты для `MusicComposerAgent`.
- **TestIMusicComposer**: Тесты для интерфейса `IMusicComposer`.

**Функции:**  
Нет функций.

**Примеры использования:**  
Запуск тестов:  
```bash
python -m unittest tests.test_music_composer_agent
```

Пример теста:  
```python
import unittest
from music_composer_agent.models import MusicalComposition

class TestMusicalComposition(unittest.TestCase):
    def test_initialization_valid(self):
        composition = MusicalComposition(
            title="Test Waltz",
            composer="Test Composer",
            notes=["C4", "D4", "E4"],
            tempo=120,
            key="C major"
        )
        self.assertEqual(composition.title, "Test Waltz")

if __name__ == '__main__':
    unittest.main()