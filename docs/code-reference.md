# Справочник по коду: Music Synthesizer Agent

## Оглавление

- [Обзор архитектуры](#обзор-архитектуры)
- [Пакет `src/agents/music_synthesizer_agent/`](#пакет-srcagentsmusic_synthesizer_agent)
  - [`__init__.py`](#initpy)
  - [`models.py`](#modelspy)
  - [`agent.py`](#agentpy)
  - [`server.py`](#serverpy)

## Обзор архитектуры

Music Synthesizer Agent — это модульная система для синтеза музыки на основе пользовательских спецификаций. Основные компоненты:

- **MusicSynthesizerAgent** (модуль): Синтез музыки с поддержкой стилей и Pydantic-моделей.
- **MusicFile** (класс): Модель файла музыки с метаданными, аудиоданными и методами экспорта/анализа.
- **MusicStyle** (класс): Конфигурация стиля музыки (жанр, темп, инструменты, длительность, формат).
- **MusicSynthesizerServer** (модуль): FastAPI-сервер для обработки запросов с аутентификацией и интеграцией.

Система использует стратегии синтеза (ClassicalStrategy, RockStrategy), хранит сырые PCM-данные, применяет лимиты на пользователя (10 файлов, 100 МБ) и обеспечивает атомарный экспорт.

**Технологии**: Python, Pydantic v2, NumPy, SciPy, FastAPI.

## Пакет `src/agents/music_synthesizer_agent/`

### `__init__.py`

#### Описание модуля
Инициализационный файл пакета, экспортирующий ключевые классы и модули для удобного импорта.

#### Экспортируемые элементы
```python
from .models import MusicStyle, MusicFile
from .agent import MusicSynthesizerAgent
from .server import MusicSynthesizerServer

__all__ = [
    "MusicStyle",
    "MusicFile",
    "MusicSynthesizerAgent",
    "MusicSynthesizerServer",
]
```

#### Пример использования
```python
from src.agents.music_synthesizer_agent import MusicStyle, MusicSynthesizerAgent

style = MusicStyle(genre="classical", bpm=120)
agent = MusicSynthesizerAgent()
```

### `models.py`

#### Описание модуля
Модели Pydantic для стилей музыки и файлов. Хранит сырые PCM-данные (без WAV-заголовка). Поддерживает валидацию, экспорт в WAV с атомарной записью и очисткой при ошибках. Лимиты: max_length/max_items на поля.

#### Классы

##### `MusicStyle` (наследует `BaseModel`)
**Описание**: Конфигурация стиля музыки.

**Поля**:
- `genre: str` (обязательное, длина 1–50 символов)
- `bpm: int` (по умолчанию 120, диапазон 60–200)
- `instruments: List[str]` (по умолчанию пустой список, max_items=10)
- `duration_seconds: float` (по умолчанию 30.0, диапазон 1.0–60.0)
- `audio_format: str` (по умолчанию "wav", regex `^wav$`)

**Пример**:
```python
from src.agents.music_synthesizer_agent.models import MusicStyle

style = MusicStyle(
    genre="rock",
    bpm=140,
    instruments=["guitar", "drums"],
    duration_seconds=45.0
)
print(style.model_dump())  # {'genre': 'rock', 'bpm': 140, ...}
```

##### `MusicFile` (наследует `BaseModel`)
**Описание**: Представление музыкального файла с метаданными и аудиоданными (raw PCM bytes).

**Поля**:
- `name: str` (обязательное, длина 1–100, regex `^[a-zA-Z0-9_-]+$`)
- `style: MusicStyle` (обязательное)
- `audio_data: bytes` (обязательное)
- `sample_rate: int` (по умолчанию 44100)
- `channels: int` (по умолчанию 1, диапазон 1–8)
- `bits_per_sample: int` (по умолчанию 16, диапазон 8–32, кратно 8)

**Методы**:
- `export(self, filepath: str) -> None`  
  **Описание**: Экспорт в WAV в временную директорию (использует basename пути для безопасности). Атомарная запись с очисткой при ошибке.  
  **Аргументы**:  
    - `filepath: str` — путь, basename которого используется для имени файла.  
  **Исключения**: `ValueError` при неверном формате или ошибке.  
  **Примечание**: Файлы накапливаются во временной директории; рекомендуется внешняя очистка.

**Пример**:
```python
from src.agents.music_synthesizer_agent.models import MusicStyle, MusicFile
import numpy as np

style = MusicStyle(genre="classical")
audio_data = np.sin(np.linspace(0, 2*np.pi, 44100)).astype(np.int16).tobytes()
file = MusicFile(name="test_track", style=style, audio_data=audio_data)

file.export("/tmp/my_track.wav")  # Экспорт в /tmp/test_track.wav
```

### `agent.py`

#### Описание модуля
Реализация агента синтеза с паттерном Strategy. Стратегии возвращают raw PCM bytes. Репозиторий с лимитами на пользователя (10 файлов, 100 МБ), уникальные имена с UUID. Полная реализация `MusicSynthesizerAgent`.

#### Классы

##### `SynthesisStrategy` (абстрактный, наследует `ABC`)
**Описание**: Абстрактная стратегия синтеза.

**Методы**:
- `synthesize(self, style: MusicStyle, sample_rate: int) -> bytes` (абстрактный)  
  **Описание**: Синтез raw PCM аудио (без WAV-заголовка).

##### `ClassicalStrategy` (наследует `SynthesisStrategy`)
**Описание**: Стратегия для классической музыки (синусоидальные волны с гармониками).

**Методы**: `synthesize` (реализация с базовой частотой 440 Гц, модуляцией по BPM).

##### `RockStrategy` (наследует `SynthesisStrategy`)
**Описание**: Стратегия для рок-музыки (дисторшн с tanh).

**Методы**: `synthesize` (реализация с базовой частотой 220 Гц, дисторшн).

##### `MusicSynthesizerAgent`
**Описание**: Основной агент. Выбирает стратегию по жанру, синтезирует `MusicFile`, учитывает лимиты пользователя.

**Пример** (предполагаемый на основе описания):
```python
from src.agents.music_synthesizer_agent import MusicSynthesizerAgent, MusicStyle

agent = MusicSynthesizerAgent()
style = MusicStyle(genre="classical", bpm=120, duration_seconds=10.0)
music_file = agent.synthesize(style, user_id="demo_user")  # Возвращает MusicFile
print(music_file.name)  # Уникальное имя с UUID
```

### `server.py`

#### Описание модуля
FastAPI-сервер для обработки запросов. Аутентификация по API-ключам (DEMO_API_KEY, CLASSICAL_API_KEY, ROCK_API_KEY). Лимиты репозитория передаются как HTTP 400. Роуты настраиваются в `_setup_routes()`.

#### Классы

##### `MusicSynthesizerServer`
**Описание**: Сервер с FastAPI-приложением и агентом.

**Инициализация** (`__init__`):  
Создает `app`, `agent`, настраивает хост/порт из env, API-ключи, схему аутентификации, роуты.

**Методы**:
- `_get_user_id(self, api_key: str) -> str`  
  **Описание**: Получает user_id по API-ключу.  
  **Исключения**: HTTP 401 при неверном ключе.
- `_setup_routes(self)`: Настраивает эндпоинты (предполагаемые: POST /synthesize с MusicStyle, GET /files/{user_id}).

**Запуск** (предполагаемый):
```python
from src.agents.music_synthesizer_agent.server import MusicSynthesizerServer

server = MusicSynthesizerServer()
server.app.run(host=server.host, port=server.port)  # uvicorn в продакшене
```

**Пример запроса** (Swagger: http://127.0.0.1:8000/docs):
```bash
curl -X POST "http://127.0.0.1:8000/synthesize" \
  -H "X-API-Key: demo_key" \
  -H "Content-Type: application/json" \
  -d '{"genre": "rock", "bpm": 140}'