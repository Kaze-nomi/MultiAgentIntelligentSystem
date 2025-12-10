# API Документация Music Synthesis Service

## Содержание

- [Общая информация](#общая-информация)
- [Аутентификация](#аутентификация)
- [Synthesis](#synthesis)
  - [POST /synthesize](#post--synthesize)
- [Files](#files)
  - [GET /files](#get--files)
  - [GET /files/{name}](#get--filesname)
- [Health](#health)
  - [GET /health](#get--health)

## Общая информация {#общая-информация}

**Base URL:** `https://api.music-synth.com`

Сервис предоставляет API для синтеза музыки по заданным параметрам, управления файлами пользователя и проверки состояния сервера.  
Фреймворк валидации: Pydantic.  

**Лимиты хранения:** Максимум 10 файлов на пользователя, общий объём 100 МБ.

## Аутентификация {#аутентификация}

Все эндпоинты, кроме `/health`, требуют аутентификации с помощью API-ключа в заголовке `X-API-Key`.  
Ключ выдаётся при регистрации.  

Пример заголовка:  
```
X-API-Key: YOUR_API_KEY
```

## Synthesis {#synthesis}

### POST /synthesize {#post--synthesize}

**Описание:** Синтезирует музыку по заданному стилю с использованием стратегии (classical/rock), сохраняет файл в репозитории пользователя и возвращает анализ. Опционально включает base64-кодированные аудиоданные.

**Метод:** `POST`  
**Путь:** `/synthesize`

**Параметры:**

| Имя          | Тип     | Обязательный | Расположение | Описание                                      | Значение по умолчанию |
|--------------|---------|--------------|--------------|-----------------------------------------------|-----------------------|
| include_audio | boolean | Нет         | query       | Флаг для включения base64-кодированных аудиоданных в ответ | -                     |

**Request Body:** `application/json`

```json
{
  "genre": "classical",
  "bpm": 120,
  "duration_seconds": 30.0
}
```

**Responses:**

- **200 Успешный синтез и сохранение файла** (`application/json`):
  ```json
  {
    "success": true,
    "file_name": "generated_song",
    "analysis": {
      "duration_seconds": 30.0
    },
    "audio_b64": "UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSb..."
  }
  ```

- **400 Ошибка валидации стиля или превышены лимиты хранения (10 файлов, 100MB на пользователя)** (`application/json`)

- **401 Неверный API-ключ** (`application/json`)

- **500 Внутренняя ошибка сервера** (`application/json`)

**Примеры запросов:**

**curl:**
```bash
curl -X POST https://api.music-synth.com/synthesize \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "genre": "classical",
    "bpm": 120,
    "duration_seconds": 30.0
  }?include_audio=true'
```

**httpie:**
```bash
http POST https://api.music-synth.com/synthesize \
  genre:=classical bpm:=120 duration_seconds:=30.0 include_audio:=true \
  X-API-Key:=YOUR_API_KEY
```

## Files {#files}

### GET /files {#get--files}

**Описание:** Возвращает список всех сохраненных музыкальных файлов пользователя с базовой информацией (имя, длительность, жанр).

**Метод:** `GET`  
**Путь:** `/files`

**Параметры:** Отсутствуют.

**Request Body:** Отсутствует.

**Responses:**

- **200 Список файлов пользователя** (`application/json`):
  ```json
  [
    {
      "name": "generated_song",
      "duration": 30.0,
      "genre": "classical"
    }
  ]
  ```

- **401 Неверный API-ключ** (`application/json`)

**Примеры запросов:**

**curl:**
```bash
curl -X GET https://api.music-synth.com/files \
  -H "X-API-Key: YOUR_API_KEY"
```

**httpie:**
```bash
http GET https://api.music-synth.com/files \
  X-API-Key:=YOUR_API_KEY
```

### GET /files/{name} {#get--filesname}

**Описание:** Возвращает информацию о конкретном музыкальном файле пользователя, включая анализ. Опционально включает base64-кодированные аудиоданные. Имя файла проверяется на формат (`^[a-zA-Z0-9_-]+$`).

**Метод:** `GET`  
**Путь:** `/files/{name}`

**Параметры:**

| Имя          | Тип    | Обязательный | Расположение | Описание                                      | Значение по умолчанию |
|--------------|--------|--------------|--------------|-----------------------------------------------|-----------------------|
| name         | string | Да          | path        | Имя музыкального файла (формат: ^[a-zA-Z0-9_-]+$ ) | -                     |
| include_audio | boolean | Нет       | query       | Флаг для включения base64-кодированных аудиоданных в ответ | -                     |

**Request Body:** Отсутствует.

**Responses:**

- **200 Информация о файле** (`application/json`):
  ```json
  {
    "name": "generated_song",
    "analysis": {
      "duration_seconds": 30.0
    },
    "audio_b64": "UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSb..."
  }
  ```

- **400 Неверный формат имени файла** (`application/json`)

- **404 Файл не найден** (`application/json`)

- **401 Неверный API-ключ** (`application/json`)

**Примеры запросов:**

**curl:**
```bash
curl -X GET https://api.music-synth.com/files/generated_song?include_audio=true \
  -H "X-API-Key: YOUR_API_KEY"
```

**httpie:**
```bash
http GET https://api.music-synth.com/files/generated_song include_audio=true \
  X-API-Key:=YOUR_API_KEY
```

## Health {#health}

### GET /health {#get--health}

**Описание:** Проверяет доступность сервера.

**Метод:** `GET`  
**Путь:** `/health`

**Параметры:** Отсутствуют.

**Request Body:** Отсутствует.

**Responses:**

- **200 Сервер работает** (`application/json`):
  ```json
  {
    "status": "healthy"
  }
  ```

**Примеры запросов:**

**curl:**
```bash
curl -X GET https://api.music-synth.com/health
```

**httpie:**
```bash
http GET https://api.music-synth.com/health