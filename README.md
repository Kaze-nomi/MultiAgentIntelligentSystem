# RepoAnalyzer 📊

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/yourusername/repoanalyzer/actions)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/yourusername/repoanalyzer/releases)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-latest-blue.svg)](https://hub.docker.com/r/yourusername/repoanalyzer)

## 📖 Содержание

- [Описание](#описание-📖)
- [Возможности](#возможности-🚀)
- [Установка](#установка-📦)
- [Использование](#использование-⚙️)
- [Конфигурация](#конфигурация-🔧)
- [API](#api-📚)
- [Вклад в разработку](#вклад-в-разработку-🤝)
- [Лицензия](#лицензия-📄)

## Описание 📖

**RepoAnalyzer** — это мощный инструмент на Python для анализа структуры Git-репозиториев. Он автоматически извлекает ключевые файлы (конфигурации, точки входа, исходный код), фильтрует их по паттернам, исключает ненужные артефакты (node_modules, build-директории и т.д.) и готовит данные для дальнейшей обработки, например, для AI-анализа или документации.

Проект использует **Pydantic** для строгой валидации моделей данных и **Docker** для удобного развертывания. Идеален для разработчиков, DevOps и инструментов автоматизации.

## Возможности 🚀

- 🔍 **Автоматический парсинг репозитория**: Анализ tree-структуры из GitHub API.
- 📂 **Умная фильтрация**: Поддержка 50+ паттернов для ключевых файлов (Python, JS/TS, Go, Rust и др.).
- ❌ **Исключения**: Игнорирование build-артефактов, тестов, кэша и больших файлов (>100KB).
- ⚡ **Приоритизация**: Загрузка важных файлов (README, requirements.txt, main.py) первыми.
- 🛡️ **Валидация**: Pydantic-модели для типобезопасности.
- 🐳 **Docker-поддержка**: Контейнеризированное развертывание.
- 📊 **Логирование и отладка**: Детальные логи для анализа.

## Установка 📦

### Через pip (рекомендуется)

```bash
pip install repoanalyzer
```

### Через Docker

```bash
docker pull yourusername/repoanalyzer:latest
docker run -it --rm yourusername/repoanalyzer --help
```

### Локальная установка из исходников

```bash
git clone https://github.com/yourusername/repoanalyzer.git
cd repoanalyzer
pip install -e .[dev]
```

Требования: Python 3.8+, Pydantic 2.x.

## Использование ⚙️

### Базовый пример

```python
from repoanalyzer import RepoAnalyzer
import requests

# Получаем tree из GitHub API
response = requests.get("https://api.github.com/repos/user/repo/git/trees/main?recursive=1")
tree_data = response.json()

analyzer = RepoAnalyzer(tree_data)
files = analyzer.get_key_files(max_files=50)

print(files)  # Список отфильтрованных файлов с SHA, размером и путями
```

### CLI-интерфейс

```bash
repoanalyzer analyze https://github.com/user/repo --output json --max-files 50
```

Вывод:
```json
[
  {
    "path": "README.md",
    "type": "file",
    "size": 2048,
    "sha": "abc123..."
  }
]
```

## Конфигурация 🔧

Создайте файл `config.yaml`:

```yaml
key_patterns:
  - /^readme\.md$/i
  - /\.py$/
exclude_patterns:
  - /node_modules/
  - /__pycache__/
max_size_kb: 100
priority_patterns:
  - /^requirements\.txt$/
```

Загрузка:
```python
analyzer = RepoAnalyzer.from_config("config.yaml")
```

## API 📚

### Основные классы (Pydantic-модели)

```python
from pydantic import BaseModel
from typing import List

class RepoFile(BaseModel):
    path: str
    type: str  # 'file' | 'dir'
    size: int
    sha: str

class RepoAnalyzer:
    def __init__(self, tree_data: dict):
        ...
    
    def get_key_files(self, max_files: int = 50) -> List[RepoFile]:
        """Возвращает топ ключевых файлов."""
        ...
```

Полный API в [docs/api.md](docs/api.md).

## Вклад в разработку 🤝

1. Форкните репозиторий.
2. Создайте ветку: `git checkout -b feature/awesome`.
3. Коммитьте изменения: `git commit -m 'Add awesome feature'`.
4. Пушьте: `git push origin feature/awesome`.
5. Откройте Pull Request.

### Тестирование

```bash
pytest tests/
docker-compose up test
```

Используйте pre-commit: `pre-commit install`.

## Лицензия 📄

MIT License. См. файл [LICENSE](LICENSE).