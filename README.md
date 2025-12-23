# КОМПИЛЯТОРЫ

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Table of Contents
- [📦 Описание](#-описание)
- [🚀 Возможности](#-возможности)
- [⚙️ Установка](#️-установка)
- [💻 Использование](#-использование)
- [🔧 Конфигурация](#-конфигурация)
- [📚 API](#-api)
- [🤝 Вклад в проект](#-вклад-в-проект)
- [📄 Лицензия](#-лицензия)

## 📦 Описание

Проект "КОМПИЛЯТОРЫ" представляет собой систему для работы с компиляторами различных языков программирования. Основная цель — предоставить унифицированный интерфейс для компиляции и выполнения кода с использованием современных технологий и подходов.

## 🚀 Возможности

- Поддержка множества языков программирования
- Унифицированный API для работы с компиляторами
- Интеграция с Docker для изолированного выполнения кода
- Использование Pydantic для валидации данных
- Поддержка AI-агентов для автоматизации задач

## ⚙️ Установка

### Требования
- Python 3.8+
- Docker
- Git

### Шаги установки

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-repo/compilers.git
cd compilers
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Настройте Docker:
```bash
docker build -t compilers .
```

## 💻 Использование

### Базовый пример

```python
from pydantic import BaseModel
from compilers import Compiler

class CodeRequest(BaseModel):
    language: str
    code: str

# Инициализация компилятора
compiler = Compiler()

# Компиляция кода
request = CodeRequest(
    language="python",
    code="print('Hello, World!')"
)

result = compiler.compile(request)
print(result.output)
```

### Продвинутый пример

```python
from compilers import AdvancedCompiler

# Использование расширенных возможностей
adv_compiler = AdvancedCompiler()

# Компиляция с опциями
options = {
    "optimization": True,
    "debug": False
}

result = adv_compiler.compile_with_options(
    language="cpp",
    code="#include <iostream>\nint main() { std::cout << \"Hello\"; return 0; }",
    options=options
)
```

## 🔧 Конфигурация

Конфигурация проекта осуществляется через файл `config.yaml`:

```yaml
compilers:
  python:
    version: "3.9"
    docker_image: "python:3.9-slim"
  cpp:
    version: "gcc-9"
    docker_image: "gcc:9"

logging:
  level: "INFO"
  file: "compilers.log"
```

## 📚 API

### Основные классы

#### `Compiler`
Основной класс для работы с компиляторами.

**Методы:**
- `compile(request: CodeRequest) -> CompilationResult`
- `get_supported_languages() -> List[str]`

#### `AdvancedCompiler`
Расширенный класс с дополнительными возможностями.

**Методы:**
- `compile_with_options(language: str, code: str, options: dict) -> CompilationResult`
- `validate_code(language: str, code: str) -> ValidationResult`

### Модели данных

#### `CodeRequest`
```python
class CodeRequest(BaseModel):
    language: str
    code: str
    timeout: Optional[int] = 30
```

#### `CompilationResult`
```python
class CompilationResult(BaseModel):
    success: bool
    output: Optional[str]
    error: Optional[str]
    execution_time: float
```

## 🤝 Вклад в проект

Мы приветствуем вклад в развитие проекта! Пожалуйста, следуйте этим шагам:

1. Форкните репозиторий
2. Создайте ветку для вашей фичи (`git checkout -b feature/AmazingFeature`)
3. Закоммитьте изменения (`git commit -m 'Add some AmazingFeature'`)
4. Отправьте в репозиторий (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📄 Лицензия

Этот проект лицензирован под MIT License - подробности см. в файле [LICENSE](LICENSE).