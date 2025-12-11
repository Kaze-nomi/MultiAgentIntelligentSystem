# Dockerfile для MCP сервера OpenRouter
FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY openrouter_mcp/requirements.txt .
# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY openrouter_mcp/server.py .
COPY logging_config.py .

# Порт приложения
EXPOSE 8000

# Переменные окружения по умолчанию
ENV PORT=8000
ENV OPENROUTER_API_KEY=""
ENV LOG_LEVEL="INFO"
ENV DEBUG="false"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Команда запуска
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]