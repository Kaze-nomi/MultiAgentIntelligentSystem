"""
MCP сервер для OpenRouter API
Поддерживает стандартный OpenAI Chat Completions API формат
"""

import os
import json
import logging
import uuid
from typing import Dict, List, Optional, Any
import time

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import StreamingResponse
import requests
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# Используем стандартный Chat Completions endpoint
OPENROUTER_BASE_URL = "https://api.proxyapi.ru/openrouter/v1/chat/completions"

# Инициализация FastAPI приложения
app = FastAPI(
    title="OpenRouter MCP Server",
    description="MCP сервер для работы с OpenRouter Chat Completions API",
    version="1.0.0"
)


async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Проверка API ключа"""
    api_key = x_api_key or OPENROUTER_API_KEY

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key is required. Set OPENROUTER_API_KEY environment variable or provide X-API-Key header"
        )

    return api_key


def build_openrouter_request(chat_request: Dict) -> Dict[str, Any]:
    """
    Построение запроса для OpenRouter Chat Completions API
    Формат полностью совместим с OpenAI
    """
    
    # Базовые обязательные поля
    request_data = {
        "model": chat_request.get("model"),
        "messages": chat_request.get("messages", []),
    }
    
    # Опциональные параметры
    optional_params = [
        "temperature",
        "max_tokens",
        "top_p",
        "frequency_penalty",
        "presence_penalty",
        "stop",
        "stream",
        "n",
        "logprobs",
        "top_logprobs",
        "response_format",
        "seed",
        "tools",
        "tool_choice",
        "user",
    ]
    
    for param in optional_params:
        if param in chat_request and chat_request[param] is not None:
            request_data[param] = chat_request[param]
    
    # OpenRouter специфичные параметры (если нужны)
    if "transforms" in chat_request:
        request_data["transforms"] = chat_request["transforms"]
    
    if "route" in chat_request:
        request_data["route"] = chat_request["route"]
    
    if "provider" in chat_request:
        request_data["provider"] = chat_request["provider"]
    
    logger.debug(f"Built request: {json.dumps(request_data, indent=2, ensure_ascii=False)}")
    
    return request_data


@app.post("/chat/completions")
@app.post("/v1/chat/completions")
async def chat_completion(
    chat_request: Dict[str, Any],
    api_key: str = Depends(verify_api_key)
):
    """
    Основная конечная точка для чата
    Полностью совместима с OpenAI Chat Completions API
    """
    
    try:
        logger.info(f"Received chat request for model: {chat_request.get('model')}")
        logger.debug(f"Original request: {json.dumps(chat_request, indent=2, ensure_ascii=False)}")
        
        # Проверка обязательных полей
        if not chat_request.get("model"):
            raise HTTPException(
                status_code=400,
                detail={"error": {"message": "model is required", "type": "invalid_request_error"}}
            )
        
        if not chat_request.get("messages"):
            raise HTTPException(
                status_code=400,
                detail={"error": {"message": "messages is required", "type": "invalid_request_error"}}
            )
        
        # Построение запроса
        request_data = build_openrouter_request(chat_request)
        
        # Заголовки для OpenRouter
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("HTTP_REFERER", "https://mcp-server.local"),
            "X-Title": os.getenv("X_TITLE", "OpenRouter MCP Server")
        }
        
        is_stream = request_data.get("stream", False)
        
        logger.info(f"Sending request to OpenRouter: {OPENROUTER_BASE_URL}")
        logger.debug(f"Stream mode: {is_stream}")
        
        response = requests.post(
            OPENROUTER_BASE_URL,
            headers=headers,
            json=request_data,
            stream=is_stream,
            timeout=240
        )
        
        logger.info(f"OpenRouter response status: {response.status_code}")
        
        # Обработка ошибок
        if response.status_code != 200:
            error_text = response.text
            logger.error(f"OpenRouter API error: {error_text}")
            
            try:
                error_data = response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_data
                )
            except (ValueError, json.JSONDecodeError):
                raise HTTPException(
                    status_code=response.status_code,
                    detail={"error": {"message": error_text, "type": "api_error"}}
                )
        
        # Обработка streaming response
        if is_stream:
            def generate_stream():
                """Генератор для streaming ответа"""
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        # Просто пробрасываем данные как есть - формат уже OpenAI-совместимый
                        yield line_str + "\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        
        # Обработка обычного ответа
        response_data = response.json()
        logger.debug(f"OpenRouter response: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        
        # OpenRouter возвращает данные в OpenAI-совместимом формате,
        # поэтому просто возвращаем как есть
        return response_data
    
    except HTTPException:
        raise
    except requests.exceptions.Timeout:
        logger.error("Request timeout")
        raise HTTPException(
            status_code=504,
            detail={"error": {"message": "Request to OpenRouter API timed out", "type": "timeout_error"}}
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={"error": {"message": f"Connection error to OpenRouter API: {str(e)}", "type": "connection_error"}}
        )
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": f"Internal server error: {str(e)}", "type": "server_error"}}
        )


@app.post("/completions")
@app.post("/v1/completions")
async def completions(
    request: Dict[str, Any],
    api_key: str = Depends(verify_api_key)
):
    """
    Legacy completions endpoint (для совместимости)
    Конвертирует в chat completions формат
    """
    
    # Конвертируем prompt в messages формат
    prompt = request.get("prompt", "")
    
    chat_request = {
        "model": request.get("model"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": request.get("temperature"),
        "max_tokens": request.get("max_tokens"),
        "top_p": request.get("top_p"),
        "stream": request.get("stream", False),
        "stop": request.get("stop"),
    }
    
    # Удаляем None значения
    chat_request = {k: v for k, v in chat_request.items() if v is not None}
    
    return await chat_completion(chat_request, api_key)


@app.get("/models")
@app.get("/v1/models")
async def list_models(api_key: str = Depends(verify_api_key)):
    """
    Получение списка доступных моделей
    """
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        response = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        
        logger.warning(f"Failed to fetch models: {response.status_code}")
        return {"object": "list", "data": []}
    
    except Exception as e:
        logger.error(f"Error fetching models: {str(e)}")
        return {"object": "list", "data": []}


@app.get("/models/{model_id}")
@app.get("/v1/models/{model_id}")
async def get_model(model_id: str, api_key: str = Depends(verify_api_key)):
    """
    Получение информации о конкретной модели
    """
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        response = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            models = response.json().get("data", [])
            for model in models:
                if model.get("id") == model_id:
                    return model
        
        raise HTTPException(
            status_code=404,
            detail={"error": {"message": f"Model {model_id} not found", "type": "not_found_error"}}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching model: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": str(e), "type": "server_error"}}
        )


@app.get("/health")
async def health_check():
    """Проверка здоровья сервера"""
    return {
        "status": "healthy",
        "service": "OpenRouter MCP Server",
        "timestamp": int(time.time()),
        "api_key_configured": bool(OPENROUTER_API_KEY),
        "openrouter_url": OPENROUTER_BASE_URL
    }


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "service": "OpenRouter MCP Server",
        "version": "1.0.0",
        "description": "OpenAI-compatible API proxy for OpenRouter",
        "endpoints": {
            "chat_completions": "POST /v1/chat/completions",
            "completions": "POST /v1/completions",
            "models": "GET /v1/models",
            "model_info": "GET /v1/models/{model_id}",
            "health": "GET /health"
        },
        "documentation": "/docs"
    }


if __name__ == "__main__":
    import sys
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting OpenRouter MCP Server on {host}:{port}")
    logger.info(f"Using OpenRouter base URL: {OPENROUTER_BASE_URL}")
    logger.info(f"OpenRouter API Key: {'SET' if OPENROUTER_API_KEY else 'NOT SET'}")
    
    if not OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY environment variable is not set!")
        logger.warning("Set it via: export OPENROUTER_API_KEY='your-key-here'")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )