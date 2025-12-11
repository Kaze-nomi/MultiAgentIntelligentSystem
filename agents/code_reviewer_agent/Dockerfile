FROM python:3.11-slim

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python зависимости
COPY agents/code_reviewer_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Исходный код
COPY agents/code_reviewer_agent/models.py .
COPY agents/code_reviewer_agent/server.py .
COPY logging_config.py .

# Порт
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Переменные окружения
ENV DEFAULT_MODEL=1
ENV PYTHONUNBUFFERED=1
ENV OPENROUTER_MCP_URL=http://openrouter-mcp:8000

# Запуск
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]