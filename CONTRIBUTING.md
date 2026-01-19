# CONTRIBUTING.md

## Как начать разработку

Этот проект написан на Python с использованием фреймворка Pydantic для валидации данных. Чтобы начать разработку, вам потребуется базовое понимание Python и Pydantic. Если вы новичок, ознакомьтесь с [документацией Pydantic](https://pydantic-docs.helpmanual.io/).

## Настройка окружения

1. Убедитесь, что у вас установлен Python версии 3.8 или выше.
2. Клонируйте репозиторий:
   ```
   git clone https://github.com/your-repo/your-project.git
   cd your-project
   ```
3. Создайте виртуальное окружение:
   ```
   python -m venv venv
   source venv/bin/activate  # На Windows: venv\Scripts\activate
   ```
4. Установите зависимости с помощью pip:
   ```
   pip install -r requirements.txt
   ```
   Если файла `requirements.txt` нет, установите Pydantic вручную:
   ```
   pip install pydantic
   ```

## Code style guidelines

Код должен соответствовать стандартам Python. Используйте следующие инструменты:

- **Форматирование**: Используйте [Black](https://black.readthedocs.io/en/stable/) для автоматического форматирования кода. Запустите:
  ```
  black .
  ```
- **Линтинг**: Используйте [Flake8](https://flake8.pycqa.org/en/latest/) для проверки стиля. Запустите:
  ```
  flake8 .
  ```
- **Типизация**: Поскольку проект использует Pydantic, добавляйте аннотации типов. Используйте [MyPy](https://mypy.readthedocs.io/en/stable/) для проверки типов:
  ```
  mypy .
  ```
- Следуйте PEP 8. Избегайте длинных строк (не более 88 символов, как в Black). Используйте осмысленные имена переменных и функций.

## Процесс создания PR

1. Создайте форк репозитория на GitHub.
2. Создайте новую ветку для вашей фичи или исправления:
   ```
   git checkout -b feature/your-feature-name
   ```
3. Внесите изменения, следуя правилам коммитов и code style.
4. Протестируйте изменения локально (если применимо).
5. Отправьте изменения в ваш форк:
   ```
   git push origin feature/your-feature-name
   ```
6. Создайте Pull Request (PR) на GitHub. В описании PR укажите:
   - Что было изменено.
   - Почему это изменение необходимо.
   - Ссылки на связанные issues, если есть.

## Правила коммитов (Conventional Commits)

Все коммиты должны следовать стандарту [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/). Формат:

```
<type>[optional scope]: <description>

[optional body]

[optional footer]
```

Типы:
- `feat`: новая фича
- `fix`: исправление бага
- `docs`: изменения в документации
- `style`: изменения стиля (форматирование, пробелы)
- `refactor`: рефакторинг кода
- `test`: добавление или исправление тестов
- `chore`: прочие изменения (обновление зависимостей и т.д.)

Пример:
```
feat: add user validation with Pydantic

- Added BaseModel for user data
- Implemented validation for email and age fields
```

## Процесс ревью

После создания PR:
1. Автоматические проверки (CI/CD, если настроены) проверят code style и типы.
2. Ревьюеры (обычно мейнтейнеры проекта) проверят код на:
   - Соответствие code style.
   - Корректность логики.
   - Наличие тестов (если применимо).
   - Безопасность и производительность.
3. Если есть замечания, внесите исправления в ту же ветку и обновите PR.
4. После одобрения PR будет смержен в main ветку.

## Тестирование

В проекте тестирование не предусмотрено (N/A). Если вы хотите добавить тесты, используйте [pytest](https://docs.pytest.org/en/stable/) для unit-тестов и интеграции с Pydantic. Пример структуры:
- Создайте папку `tests/`.
- Напишите тесты для моделей Pydantic, например:
  ```python
  from pydantic import ValidationError
  import pytest
  from your_module import YourModel

  def test_valid_model():
      data = {"name": "John", "age": 30}
      model = YourModel(**data)
      assert model.name == "John"

  def test_invalid_model():
      with pytest.raises(ValidationError):
          YourModel(name="John", age="not_a_number")
  ```
  Запустите тесты: `pytest`. Однако, поскольку тестирование не является частью текущего проекта, добавление тестов обсуждается отдельно.