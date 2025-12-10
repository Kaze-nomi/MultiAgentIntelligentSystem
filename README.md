# MusicSynthesizerAgent 🥁

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/your-org/music-synthesizer-agent/actions)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/your-org/music-synthesizer-agent/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://hub.docker.com/r/your-org/music-synthesizer-agent)

## 📖 Содержание

- [Описание](#описание)
- [Особенности](#особенности)
- [Установка](#установка)
- [Конфигурация](#конфигурация)
- [Использование](#использование)
- [API](#api)
- [Архитектура](#архитектура)
- [Вклад в разработку](#вклад-в-разработку)
- [Лицензия](#лицензия)

## 📦 Описание

**MusicSynthesizerAgent** — это мощный агент для синтеза музыки в экосистеме агентов. Он генерирует оригинальные музыкальные композиции в различных стилях, сохраняя их как сырые PCM-данные (без WAV-заголовка) в репозитории с поддержкой лимитов на пользователя (максимум 10 файлов, 100 МБ). 

Агент использует паттерны **Strategy** (для стратегий синтеза), **Builder** (для построения композиций), **Facade** (для упрощенного интерфейса) и **Repository** (для хранения файлов). Реализован на Python с использованием Pydantic для валидации моделей и Docker для развертывания.

Идеален для интеграции в чат-боты, креативные приложения или системы ИИ, где требуется генерация музыки по текстовым описаниям.

## 🚀 Особенности

- 🎵 **Синтез музыки**: Генерация треков в стилях (Rock, Jazz, Classical и др.) с контролем длительности и количества элементов.
- 💾 **Хранение с лимитами**: Репозиторий с уникальными именами (UUID), атомарным экспортом и очисткой при ошибках. Лимиты: 10 файлов/пользователь, 100 МБ.
- 🛡️ **Валидация**: Pydantic v2 модели (`MusicFile`, `MusicStyle`) с `model_dump()`.
- 🌐 **Сервер**: HTTP-сервер с обработкой ошибок (HTTP 400 при превышении лимитов).
- 🐳 **Docker-поддержка**: Легкое развертывание в контейнерах.
- 🔄 **Стратегии**: Возвращают сырые PCM-байты для гибкости.

## 🛠️ Установка

### Предварительные требования
- Python 3.10+
- Docker (рекомендуется)

### Через pip (локальная разработка)
```bash
git clone https://github.com/your-org/music-synthesizer-agent.git
cd music-synthesizer-agent
pip install -r requirements.txt
```

### Через Docker
```bash
docker pull your-org/music-synthesizer-agent:latest
docker run -p 8000:8000 your-org/music-synthesizer-agent:latest
```

## ⚙️ Конфигурация

Создайте файл `.env` в корне проекта:

```env
# Репозиторий
REPO_PATH=/tmp/music_repo
MAX_FILES_PER_USER=10
MAX_TOTAL_SIZE_MB=100

# Сервер
HOST=0.0.0.0
PORT=8000

# Синтезатор (пример)
SAMPLE_RATE=44100
MAX_DURATION_SEC=300
```

Загрузите переменные в коде:
```python
from dotenv import load_dotenv
load_dotenv()
```

## 📖 Использование

### Запуск сервера
```bash
python src/agents/music_synthesizer_agent/server.py
```
Сервер доступен на `http://localhost:8000`.

### Пример генерации музыки (CLI)
```python
from src.agents.music_synthesizer_agent.agent import MusicSynthesizerAgent
from src.agents.music_synthesizer_agent.models import MusicStyle, MusicFile

agent = MusicSynthesizerAgent(user_id="user123")
style = MusicStyle(name="Rock", tempo=120, max_length=60)
file = agent.synthesize(style)  # Возвращает MusicFile с pcm_bytes

print(f"Сгенерировано: {file.duration} сек, {len(file.pcm_bytes)} байт")
```

### HTTP-запрос (cURL)
```bash
curl -X POST http://localhost:8000/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "style": {"name": "Jazz", "tempo": 90, "max_length": 30}
  }'
```
Ответ:
```json
{
  "file_id": "uuid-123",
  "duration": 30.5,
  "pcm_bytes": "AQAAAA=="  // base64-encoded PCM
}
```

## 📚 API

### Ключевые модели (Pydantic)
```python
from pydantic import BaseModel
from typing import bytes

class MusicStyle(BaseModel):
    name: str
    tempo: int
    max_length: int = 60  # сек
    max_items: int = 100

class MusicFile(BaseModel):
    file_id: str
    pcm_bytes: bytes
    duration: float
    sample_rate: int = 44100
```

### Эндпоинты сервера
| Метод | Путь              | Описание                  |
|-------|-------------------|---------------------------|
| POST  | `/synthesize`     | Синтез музыки по стилю   |
| GET   | `/files/{user_id}`| Список файлов пользователя|

Подробности в [server.py](src/agents/music_synthesizer_agent/server.py).

## 🏗️ Архитектура

- **Компоненты**: `MusicSynthesizerAgent` (Facade), `MusicFile`/`MusicStyle` (Models), `MusicSynthesizerServer` (HTTP).
- **Паттерны**:
  | Паттерн   | Использование                  |
  |-----------|--------------------------------|
  | Strategy  | Стратегии синтеза (RockStrategy и др.) |
  | Builder   | Построение композиций         |
  | Facade    | Упрощенный API агента         |
  | Repository| Хранение с лимитами и UUID    |

Диаграмма:
```
User → MusicSynthesizerAgent (Facade)
         ↓
Strategies → PCM Bytes → Repository → MusicFile
         ↓
MusicSynthesizerServer (HTTP)
```

## 🤝 Вклад в разработку

1. Форкните репозиторий.
2. Создайте ветку: `git checkout -b feature/new-strategy`.
3. Коммитьте изменения: `git commit -m "Add new Jazz strategy"`.
4. Пушьте: `git push origin feature/new-strategy`.
5. Откройте Pull Request.

Следуйте PEP 8. Тесты добавляются в `tests/`.

## 📄 Лицензия

[MIT License](LICENSE). См. файл `LICENSE` для деталей.