# API Документация

## Содержание

- [Аутентификация](#аутентификация)
- [LLM и Generation](#llm-и-generation)
  - [POST /api/v1/chat/completions](#post-apiv1chatcompletions)

## Аутентификация

Для доступа к API требуется аутентификация с использованием Bearer токена. Передайте API-ключ в заголовке `Authorization` в формате `Bearer <API_KEY>`.

## LLM и Generation

### POST /api/v1/chat/completions

**Описание:**  
Генерирует завершения чата с использованием LLM. Отправляет промпт указанной модели LLM и получает сгенерированный ответ, используемый для создания данных музыкальной композиции.

**HTTP Метод и Путь:**  
`POST /api/v1/chat/completions`

**Параметры:**

| Имя      | Тип    | Обязательный | Описание                                                                 | Расположение |
|----------|--------|--------------|--------------------------------------------------------------------------|--------------|
| model    | string | true         | Модель LLM для генерации (например, 'openai/gpt-3.5-turbo').            | body         |
| messages | array  | true         | Список сообщений для завершения чата, включая промпт пользователя.      | body         |

**Request Body:**  
Content-Type: `application/json`  

Пример:
```json
{
  "model": "openai/gpt-3.5-turbo",
  "messages": [
    {
      "role": "user",
      "content": "Generate a musical composition in classical style, key C minor, based on: Write a symphony."
    }
  ]
}
```

**Responses:**

- **200 OK**  
  Успешная генерация завершения чата.  
  Content-Type: `application/json`  

  Пример:
  ```json
  {
    "choices": [
      {
        "message": {
          "content": "{\"title\": \"Symphony in C minor\", \"composer\": \"AI Composer\", \"notes\": [\"C4\", \"D4\"], \"tempo\": 120, \"genre\": \"Classical\", \"metadata\": {}}"
        }
      }
    ]
  }
  ```

- **400 Bad Request**  
  Неверный запрос, например, некорректные параметры ввода.  
  Content-Type: `application/json`

- **401 Unauthorized**  
  Неавторизован, недействительный API-ключ.  
  Content-Type: `application/json`

- **500 Internal Server Error**  
  Внутренняя ошибка сервера.  
  Content-Type: `application/json`

**Примеры:**

- **curl:**
  ```bash
  curl -X POST "https://api.example.com/api/v1/chat/completions" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-3.5-turbo",
    "messages": [
      {
        "role": "user",
        "content": "Generate a musical composition in classical style, key C minor, based on: Write a symphony."
      }
    ]
  }'
  ```

- **httpie:**
  ```bash
  http POST https://api.example.com/api/v1/chat/completions \
  Authorization:"Bearer YOUR_API_KEY" \
  Content-Type:application/json \
  model="openai/gpt-3.5-turbo" \
  messages:='[{"role": "user", "content": "Generate a musical composition in classical style, key C minor, based on: Write a symphony."}]'