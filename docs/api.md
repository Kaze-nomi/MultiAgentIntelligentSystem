# API Документация

## Table of Contents

- [Введение](#введение)
- [Аутентификация](#аутентификация)
- [Calculate](#calculate)
  - [POST /calculate](#post-calculate)

## Введение

Эта документация описывает API для вычисления степени двойки. API построено с использованием фреймворка Pydantic для валидации данных.

## Аутентификация

Аутентификация не требуется для доступа к этому API.

## Calculate

### POST /calculate

**Описание:** Эндпоинт для вычисления n-ой степени двойки. Принимает запрос с показателем степени n и возвращает результат 2^n.

**HTTP метод и путь:** POST /calculate

**Параметры:**

| Имя | Тип | Обязательный | Описание | Пример |
|-----|-----|-------------|----------|--------|
| n | integer | true | Показатель степени (неотрицательное целое число) | 5 |

**Request Body:**

- Content-Type: application/json
- Пример:

```json
{
  "n": 5
}
```

**Responses:**

- **200 OK** - Ответ с результатом вычисления
  - Content-Type: application/json
  - Пример:

```json
{
  "result": 32
}
```

- **400 Bad Request** - Если n отрицательное или другая ошибка валидации
  - Content-Type: application/json
  - Пример:

```json
{
  "error": "n must be non-negative"
}
```

- **500 Internal Server Error** - Internal server error
  - Content-Type: application/json
  - Пример:

```json
{
  "error": "Internal server error"
}
```

**Примеры запросов:**

- **curl:**

```bash
curl -X POST http://localhost/calculate \
  -H "Content-Type: application/json" \
  -d '{"n": 5}'
```

- **httpie:**

```bash
http POST http://localhost/calculate n=5