# API Документация

## Оглавление

- [Аутентификация](#аутентификация)
- [Weather](#weather)
  - [Получить текущие погодные данные для города](#получить-текущие-погодные-данные-для-города)

## Аутентификация

Для доступа к API требуется API-ключ от OpenWeatherMap. Ключ передается в параметре запроса `appid`.

## Weather

### Получить текущие погодные данные для города

**HTTP метод и путь:** GET /data/2.5/weather

**Описание:** Получает текущие погодные данные для указанного города с использованием API OpenWeatherMap. Требуется API-ключ для аутентификации.

**Параметры:**

- `q` (string, required): Название города для получения погоды. Расположение: query.
- `appid` (string, required): API-ключ для OpenWeatherMap. Расположение: query.
- `units` (string, optional): Единицы измерения (например, metric). Расположение: query.

**Request Body:** Отсутствует.

**Responses:**

- **200** (application/json): Успешный ответ с погодными данными.
  Пример:
  ```json
  {
    "name": "London",
    "main": {
      "temp": 15.0,
      "humidity": 80
    },
    "weather": [
      {
        "description": "clear sky"
      }
    ],
    "wind": {
      "speed": 5.0
    }
  }
  ```

- **401** (application/json): Недействительный API-ключ.

- **404** (application/json): Город не найден.

- **500** (application/json): Внутренняя ошибка сервера или неожиданный ответ.

**Примеры запросов:**

- **curl:**
  ```bash
  curl -X GET "http://example.com/data/2.5/weather?q=London&appid=YOUR_API_KEY&units=metric"
  ```

- **httpie:**
  ```bash
  http GET "http://example.com/data/2.5/weather" q==London appid==YOUR_API_KEY units==metric