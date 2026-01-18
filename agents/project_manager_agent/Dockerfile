FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копирование и установка Python зависимостей
COPY agents/project_manager_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY agents/project_manager_agent/models.py .
COPY agents/project_manager_agent/server.py .
COPY logging_config.py .

# Порт
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Переменные окружения
ENV DEFAULT_MODEL=1
ENV PYTHONUNBUFFERED=1
ENV OPENROUTER_MCP_URL=http://openrouter-proxy:8000
ENV ARCHITECT_URL=http://architect:8000
ENV CODE_WRITER_URL=http://code-writer:8000
ENV CODE_REVIEWER_URL=http://code-reviewer:8000
ENV DOCUMENTATION_URL=http://documentation:8000
ENV DEFAULT_MODEL=

# Запуск
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]