"""
MCP сервер для OpenRouter API
Поддерживает OpenAI-совместимый Responses API Beta
"""

import os
import json
import logging
import uuid
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import time

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator
import requests
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,  # Включаем DEBUG для отладки
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/responses"

# Инициализация FastAPI приложения
app = FastAPI(
    title="OpenRouter MCP Server",
    description="MCP сервер для работы с OpenRouter Responses API Beta",
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


def convert_openai_to_responses_format(messages: List[Dict]) -> List[Dict]:
    """
    Конвертация из OpenAI Chat Completions формата в Responses API формат
    
    OpenAI формат:
    {
        "role": "user",
        "content": "Hello" или [{"type": "text", "text": "Hello"}]
    }
    
    Responses API формат:
    {
        "type": "message",
        "role": "user",
        "content": [{"type": "input_text", "text": "Hello"}]
    }
    
    Для assistant:
    {
        "type": "message",
        "role": "assistant",
        "id": "msg_xxx",
        "status": "completed",
        "content": [{"type": "output_text", "text": "Response", "annotations": []}]
    }
    """
    responses_messages = []
    
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        # Пропускаем пустые сообщения
        if not content and content != "":
            continue
        
        # Создаем content parts
        content_parts = []
        
        if isinstance(content, list):
            # Контент уже в виде массива (multimodal)
            for part in content:
                part_type = part.get("type", "text")
                
                if part_type == "text":
                    text_content = part.get("text", "")
                    if role == "assistant":
                        content_parts.append({
                            "type": "output_text",
                            "text": text_content,
                            "annotations": []
                        })
                    else:
                        content_parts.append({
                            "type": "input_text",
                            "text": text_content
                        })
                elif part_type == "image_url":
                    # Поддержка изображений (если Responses API поддерживает)
                    content_parts.append({
                        "type": "input_image",
                        "image_url": part.get("image_url", {}).get("url", "")
                    })
        elif isinstance(content, str):
            # Контент - простая строка
            if role == "assistant":
                content_parts.append({
                    "type": "output_text",
                    "text": content,
                    "annotations": []
                })
            else:
                content_parts.append({
                    "type": "input_text",
                    "text": content
                })
        else:
            # Преобразуем в строку
            text_content = str(content) if content else ""
            if role == "assistant":
                content_parts.append({
                    "type": "output_text",
                    "text": text_content,
                    "annotations": []
                })
            else:
                content_parts.append({
                    "type": "input_text",
                    "text": text_content
                })
        
        # Создаем сообщение в формате Responses API
        message = {
            "type": "message",
            "role": role,
            "content": content_parts
        }
        
        # Для assistant сообщений добавляем обязательные поля id и status
        if role == "assistant":
            message["id"] = msg.get("id", f"msg_{uuid.uuid4().hex[:12]}")
            message["status"] = "completed"
        
        responses_messages.append(message)
    
    return responses_messages


def convert_tools_to_responses_format(tools: List[Dict]) -> List[Dict]:
    """Конвертация tools из OpenAI формата в Responses API формат"""
    # Формат практически идентичен, но на всякий случай проверяем структуру
    responses_tools = []
    
    for tool in tools:
        if tool.get("type") == "function":
            responses_tools.append({
                "type": "function",
                "name": tool.get("function", {}).get("name", ""),
                "description": tool.get("function", {}).get("description", ""),
                "parameters": tool.get("function", {}).get("parameters", {})
            })
        else:
            # Передаём как есть
            responses_tools.append(tool)
    
    return responses_tools


def build_openrouter_request(chat_request: Dict) -> Dict[str, Any]:
    """
    Построение запроса для OpenRouter Responses API
    из OpenAI-совместимого формата
    """
    
    # Извлекаем данные из запроса
    model = chat_request.get("model")
    messages = chat_request.get("messages", [])
    stream = chat_request.get("stream", False)
    
    # Базовый запрос
    request_data = {
        "model": model,
        "stream": stream
    }
    
    # Конвертируем сообщения в формат Responses API
    if messages:
        converted_messages = convert_openai_to_responses_format(messages)
        request_data["input"] = converted_messages
        logger.debug(f"Converted messages: {json.dumps(converted_messages, indent=2, ensure_ascii=False)}")
    elif "input" in chat_request:
        # Если уже есть input (прямой формат Responses API)
        request_data["input"] = chat_request["input"]
    
    # Добавляем temperature
    if "temperature" in chat_request and chat_request["temperature"] is not None:
        request_data["temperature"] = chat_request["temperature"]
    
    # Добавляем max_tokens -> max_output_tokens
    if "max_tokens" in chat_request and chat_request["max_tokens"] is not None:
        request_data["max_output_tokens"] = chat_request["max_tokens"]
    elif "max_output_tokens" in chat_request and chat_request["max_output_tokens"] is not None:
        request_data["max_output_tokens"] = chat_request["max_output_tokens"]
    
    # Добавляем top_p
    if "top_p" in chat_request and chat_request["top_p"] is not None:
        request_data["top_p"] = chat_request["top_p"]
    
    # Добавляем tools
    if "tools" in chat_request and chat_request["tools"]:
        request_data["tools"] = convert_tools_to_responses_format(chat_request["tools"])
    
    # Добавляем tool_choice
    if "tool_choice" in chat_request and chat_request["tool_choice"]:
        request_data["tool_choice"] = chat_request["tool_choice"]
    
    # Добавляем reasoning (специфично для Responses API)
    if "reasoning" in chat_request and chat_request["reasoning"]:
        request_data["reasoning"] = chat_request["reasoning"]
    
    # Добавляем instructions (system prompt альтернатива)
    if "instructions" in chat_request and chat_request["instructions"]:
        request_data["instructions"] = chat_request["instructions"]
    
    logger.debug(f"Built request: {json.dumps(request_data, indent=2, ensure_ascii=False)}")
    
    return request_data


def convert_responses_to_openai_format(responses_data: Dict) -> Dict:
    """
    Конвертация ответа из Responses API в OpenAI Chat Completions формат
    """
    
    # Базовый ответ в формате OpenAI
    openai_response = {
        "id": responses_data.get("id", f"chatcmpl-{uuid.uuid4().hex}"),
        "object": "chat.completion",
        "created": responses_data.get("created_at", int(time.time())),
        "model": responses_data.get("model", "unknown"),
        "choices": [],
        "usage": responses_data.get("usage", {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        })
    }
    
    # Конвертируем usage поля
    usage = responses_data.get("usage", {})
    openai_response["usage"] = {
        "prompt_tokens": usage.get("input_tokens", 0),
        "completion_tokens": usage.get("output_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0)
    }
    
    # Обрабатываем output
    output = responses_data.get("output", [])
    choice_index = 0
    
    for output_item in output:
        if isinstance(output_item, dict) and output_item.get("type") == "message":
            if output_item.get("role") == "assistant":
                # Извлекаем текст из content
                content_text = ""
                tool_calls = []
                
                content_list = output_item.get("content", [])
                for content_item in content_list:
                    content_type = content_item.get("type", "")
                    
                    if content_type == "output_text":
                        content_text += content_item.get("text", "")
                    elif content_type == "tool_call":
                        tool_calls.append({
                            "id": content_item.get("id", f"call_{uuid.uuid4().hex[:8]}"),
                            "type": "function",
                            "function": {
                                "name": content_item.get("name", ""),
                                "arguments": content_item.get("arguments", "{}")
                            }
                        })
                
                # Определяем finish_reason
                status = output_item.get("status", "completed")
                if tool_calls:
                    finish_reason = "tool_calls"
                elif status == "completed":
                    finish_reason = "stop"
                elif status == "incomplete":
                    finish_reason = "length"
                else:
                    finish_reason = "stop"
                
                # Создаем choice
                choice = {
                    "index": choice_index,
                    "message": {
                        "role": "assistant",
                        "content": content_text if content_text else None
                    },
                    "finish_reason": finish_reason
                }
                
                if tool_calls:
                    choice["message"]["tool_calls"] = tool_calls
                
                openai_response["choices"].append(choice)
                choice_index += 1
    
    # Если нет choices, создаём пустой
    if not openai_response["choices"]:
        openai_response["choices"].append({
            "index": 0,
            "message": {
                "role": "assistant",
                "content": ""
            },
            "finish_reason": "stop"
        })
    
    return openai_response


@app.post("/chat/completions")
@app.post("/v1/chat/completions")
async def chat_completion(
    chat_request: Dict[str, Any],
    api_key: str = Depends(verify_api_key)
):
    """
    Основная конечная точка для чата
    Поддерживает OpenAI-совместимый интерфейс и конвертирует в Responses API
    """
    
    try:
        logger.info(f"Received chat request for model: {chat_request.get('model')}")
        logger.debug(f"Original request: {json.dumps(chat_request, indent=2, ensure_ascii=False)}")
        
        # Построение запроса для OpenRouter Responses API
        request_data = build_openrouter_request(chat_request)
        
        # Отправка запроса
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("HTTP_REFERER", "https://mcp-server.openrouter"),
            "X-Title": os.getenv("X_TITLE", "OpenRouter MCP Server")
        }
        
        logger.info(f"Sending request to OpenRouter: {OPENROUTER_BASE_URL}")
        
        response = requests.post(
            OPENROUTER_BASE_URL,
            headers=headers,
            json=request_data,
            stream=request_data.get("stream", False),
            timeout=120  # 2 минуты таймаут
        )
        
        logger.info(f"OpenRouter response status: {response.status_code}")
        
        # Проверка на ошибки
        if response.status_code != 200:
            error_text = response.text
            logger.error(f"OpenRouter API error: {error_text}")
            
            try:
                error_data = response.json()
                error_info = error_data.get("error", {})
                raise HTTPException(
                    status_code=response.status_code,
                    detail={
                        "error": {
                            "code": error_info.get("code", "api_error"),
                            "message": error_info.get("message", error_text),
                            "type": error_info.get("type", "api_error")
                        }
                    }
                )
            except (ValueError, json.JSONDecodeError):
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"OpenRouter API error: {error_text}"
                )
        
        # Обработка streaming response
        if request_data.get("stream", False):
            def generate_stream():
                """Генератор для streaming ответа с конвертацией в OpenAI формат"""
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith("data: "):
                            data = line_str[6:]
                            
                            if data == "[DONE]":
                                yield "data: [DONE]\n\n"
                                break
                            
                            try:
                                parsed = json.loads(data)
                                # Конвертируем streaming chunk в OpenAI формат
                                openai_chunk = convert_stream_chunk_to_openai(parsed)
                                yield f"data: {json.dumps(openai_chunk)}\n\n"
                            except json.JSONDecodeError:
                                # Пропускаем невалидный JSON
                                continue
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive"
                }
            )
        
        # Обработка обычного ответа
        response_data = response.json()
        logger.debug(f"OpenRouter response: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        
        # Преобразование ответа Responses API в OpenAI-совместимый формат
        openai_response = convert_responses_to_openai_format(response_data)
        logger.debug(f"Converted response: {json.dumps(openai_response, indent=2, ensure_ascii=False)}")
        
        return openai_response
    
    except HTTPException:
        raise
    except requests.exceptions.Timeout:
        logger.error("Request timeout")
        raise HTTPException(
            status_code=504,
            detail="Request to OpenRouter API timed out"
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Connection error to OpenRouter API: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


def convert_stream_chunk_to_openai(chunk: Dict) -> Dict:
    """
    Конвертация streaming chunk из Responses API в OpenAI формат
    """
    chunk_type = chunk.get("type", "")
    
    base_chunk = {
        "id": chunk.get("response_id", f"chatcmpl-{uuid.uuid4().hex}"),
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": chunk.get("model", "unknown"),
        "choices": []
    }
    
    if chunk_type == "response.content_part.delta":
        # Текстовый delta
        delta_text = chunk.get("delta", "")
        base_chunk["choices"].append({
            "index": chunk.get("output_index", 0),
            "delta": {
                "content": delta_text
            },
            "finish_reason": None
        })
    
    elif chunk_type == "response.output_item.done":
        # Завершение output item
        item = chunk.get("item", {})
        if item.get("role") == "assistant":
            base_chunk["choices"].append({
                "index": chunk.get("output_index", 0),
                "delta": {},
                "finish_reason": "stop"
            })
    
    elif chunk_type == "response.done":
        # Завершение всего response
        response_data = chunk.get("response", {})
        base_chunk["usage"] = {
            "prompt_tokens": response_data.get("usage", {}).get("input_tokens", 0),
            "completion_tokens": response_data.get("usage", {}).get("output_tokens", 0),
            "total_tokens": response_data.get("usage", {}).get("total_tokens", 0)
        }
    
    elif chunk_type == "response.created":
        # Начало response
        response_data = chunk.get("response", {})
        base_chunk["id"] = response_data.get("id", base_chunk["id"])
        base_chunk["choices"].append({
            "index": 0,
            "delta": {
                "role": "assistant",
                "content": ""
            },
            "finish_reason": None
        })
    
    else:
        # Другие типы событий - возвращаем пустой chunk
        base_chunk["choices"].append({
            "index": 0,
            "delta": {},
            "finish_reason": None
        })
    
    return base_chunk


@app.post("/v1/responses")
async def direct_responses_api(
    chat_request: Dict[str, Any],
    api_key: str = Depends(verify_api_key)
):
    """
    Прямой доступ к OpenRouter Responses API без конвертации
    """
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("HTTP_REFERER", "https://mcp-server.openrouter"),
            "X-Title": os.getenv("X_TITLE", "OpenRouter MCP Server")
        }
        
        logger.info(f"Direct Responses API request for model: {chat_request.get('model')}")
        
        response = requests.post(
            OPENROUTER_BASE_URL,
            headers=headers,
            json=chat_request,
            stream=chat_request.get("stream", False),
            timeout=120
        )
        
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
                    detail=error_text
                )
        
        if chat_request.get("stream", False):
            def generate():
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        yield line_str + "\n"
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream"
            )
        
        return response.json()
    
    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Connection error to OpenRouter API: {str(e)}"
        )


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
        
        return {"object": "list", "data": []}
    
    except Exception as e:
        logger.error(f"Error fetching models: {str(e)}")
        return {"object": "list", "data": []}


@app.get("/health")
async def health_check():
    """Проверка здоровья сервера"""
    return {
        "status": "healthy",
        "service": "OpenRouter MCP Server",
        "timestamp": int(time.time()),
        "api_key_configured": bool(OPENROUTER_API_KEY)
    }


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "service": "OpenRouter MCP Server",
        "version": "1.0.0",
        "description": "Converts OpenAI Chat Completions API to OpenRouter Responses API",
        "endpoints": {
            "chat_completions": "/chat/completions, /v1/chat/completions (POST)",
            "direct_responses": "/v1/responses (POST)",
            "models": "/models, /v1/models (GET)",
            "health": "/health (GET)"
        }
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