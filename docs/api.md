# API Документация

## Оглавление

- [Аутентификация](#аутентификация)
- [Health](#health)
  - [GET /health](#get-health)
- [Process](#process)
  - [POST /process](#post-process)

## Аутентификация

Для всех эндпоинтов аутентификация не требуется.

## Health

### GET /health

**Описание:**  
Health check endpoint. Возвращает простой JSON-ответ, указывающий, что сервис работает корректно.

**HTTP Метод и Путь:**  
`GET /health`

**Параметры:**  
Нет параметров.

**Request Body:**  
Не требуется.

**Responses:**

- **200 OK** - Сервис работает корректно  
  Content-Type: `application/json`  
  Пример ответа:  
  ```json
  {
    "status": "healthy"
  }
  ```

**Примеры:**

- **curl:**  
  ```bash
  curl -X GET http://localhost:8000/health
  ```

- **httpie:**  
  ```bash
  http GET http://localhost:8000/health
  ```

## Process

### POST /process

**Описание:**  
Process task endpoint. Принимает JSON-пейлоад с полем 'task', симулирует обработку путем логирования задачи и возвращает ответ, указывающий, что задача была "поглощена".

**HTTP Метод и Путь:**  
`POST /process`

**Параметры:**  
- `task` (string, required) - Задача для поглощения. Расположение: body.

**Request Body:**  
Content-Type: `application/json`  
Пример:  
```json
{
  "task": "example task"
}
```

**Responses:**

- **200 OK** - Задача успешно поглощена  
  Content-Type: `application/json`  
  Пример ответа:  
  ```json
  {
    "message": "Task absorbed by black hole",
    "status": "success"
  }
  ```

- **400 Bad Request** - Неверный запрос: отсутствует поле task  
  Content-Type: `application/json`  
  Пример ответа:  
  ```json
  {
    "error": "Invalid request: missing task field"
  }
  ```

- **500 Internal Server Error** - Внутренняя ошибка сервера  
  Content-Type: `application/json`  
  Пример ответа:  
  ```json
  {
    "error": "Internal server error"
  }
  ```

**Примеры:**

- **curl:**  
  ```bash
  curl -X POST http://localhost:8000/process \
    -H "Content-Type: application/json" \
    -d '{"task": "example task"}'
  ```

- **httpie:**  
  ```bash
  http POST http://localhost:8000/process \
    task="example task"