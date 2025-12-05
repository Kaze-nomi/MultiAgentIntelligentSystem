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
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/responses"

# Модели данных
class Role(str, Enum):
    """Роли сообщений"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

class ContentPart(BaseModel):
    """Часть контента"""
    type: str = "input_text"
    text: str

class Message(BaseModel):
    """Модель сообщения для Responses API"""
    type: str = "message"
    role: Role
    content: List[ContentPart]
    id: Optional[str] = None
    status: Optional[str] = None

class ToolFunction(BaseModel):
    """Функция инструмента"""
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]

class Tool(BaseModel):
    """Инструмент для вызова"""
    type: str = "function"
    function: ToolFunction

class ReasoningConfig(BaseModel):
    """Конфигурация reasoning"""
    effort: Optional[str] = None  # minimal, low, medium, high

class ChatRequest(BaseModel):
    """Запрос на чат для Responses API"""
    model: str
    input: Union[str, List[Message]]  # Может быть строкой или массивом сообщений
    tools: Optional[List[Tool]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_output_tokens: Optional[int] = Field(default=None, ge=1)
    stream: bool = False
    reasoning: Optional[ReasoningConfig] = None

    @validator('model')
    def validate_model(cls, v):
        """Проверка модели"""
        if not v or v.strip() == "":
            raise ValueError("Model is required")
        return v
    
    @validator('input')
    def validate_input(cls, v):
        """Валидация input"""
        if isinstance(v, str):
            if not v or v.strip() == "":
                raise ValueError("Input cannot be empty")
        elif isinstance(v, list):
            if len(v) == 0:
                raise ValueError("Input list cannot be empty")
        return v

# Модели для ответов
class OutputText(BaseModel):
    type: str = "output_text"
    text: str
    annotations: Optional[List[Any]] = []

class OutputMessage(BaseModel):
    type: str = "message"
    id: str
    status: str
    role: str
    content: List[OutputText]

class ChatResponse(BaseModel):
    """Ответ от Responses API"""
    id: str
    object: str = "response"
    created_at: int
    model: str
    output: List[Union[OutputMessage, Dict[str, Any]]]
    usage: Optional[Dict[str, Any]] = None
    status: str = "completed"

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

def convert_openai_to_responses_format(messages: List[Dict]) -> List[Message]:
    """Конвертация из OpenAI формата в Responses API формат"""
    responses_messages = []
    
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        
        # Создаем content parts
        content_parts = []
        if isinstance(content, list):
            for part in content:
                if part.get("type") == "text":
                    content_parts.append(ContentPart(type="input_text", text=part.get("text", "")))
        else:
            # Если content - строка
            content_parts.append(ContentPart(type="input_text", text=str(content)))
        
        # Создаем сообщение
        message = Message(
            type="message",
            role=role,
            content=content_parts
        )
        
        # Добавляем id и status для assistant сообщений
        if role == "assistant":
            message.id = f"msg_{uuid.uuid4().hex[:8]}"
            message.status = "completed"
        
        responses_messages.append(message)
    
    return responses_messages

def build_openrouter_request(chat_request: Dict) -> Dict[str, Any]:
    """Построение запроса для OpenRouter Responses API"""
    
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
        request_data["input"] = convert_openai_to_responses_format(messages)
    else:
        # Если нет messages, проверяем, есть ли content в другом формате
        content = chat_request.get("content")
        if content:
            request_data["input"] = str(content)
    
    # Добавляем дополнительные параметры
    if "temperature" in chat_request and chat_request["temperature"] is not None:
        request_data["temperature"] = chat_request["temperature"]
    
    if "max_tokens" in chat_request and chat_request["max_tokens"] is not None:
        request_data["max_output_tokens"] = chat_request["max_tokens"]
    elif "max_output_tokens" in chat_request and chat_request["max_output_tokens"] is not None:
        request_data["max_output_tokens"] = chat_request["max_output_tokens"]
    
    if "tools" in chat_request and chat_request["tools"]:
        request_data["tools"] = chat_request["tools"]
    
    if "tool_choice" in chat_request and chat_request["tool_choice"]:
        request_data["tool_choice"] = chat_request["tool_choice"]
    
    if "reasoning" in chat_request and chat_request["reasoning"]:
        request_data["reasoning"] = chat_request["reasoning"]
    
    return request_data

def handle_openrouter_error(response: requests.Response) -> HTTPException:
    """Обработка ошибок от OpenRouter API"""
    
    try:
        error_data = response.json()
        logger.error(f"OpenRouter API error: {error_data}")
        
        error_info = error_data.get("error", {})
        error_code = error_info.get("code", "unknown_error")
        error_message = error_info.get("message", "Unknown error")
        
        raise HTTPException(
            status_code=response.status_code,
            detail={
                "error": {
                    "code": error_code,
                    "message": error_message
                }
            }
        )
    
    except ValueError:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"OpenRouter API error: {response.text}"
        )

@app.post("/chat/completions", response_model=ChatResponse)
async def chat_completion(
    chat_request: Dict[str, Any],
    api_key: str = Depends(verify_api_key)
):
    """
    Основная конечная точка для чата
    Поддерживает OpenAI-совместимый интерфейс
    """
    
    try:
        # Построение запроса для OpenRouter Responses API
        request_data = build_openrouter_request(chat_request)
        
        logger.info(f"Sending request to OpenRouter with model: {request_data.get('model')}")
        
        # Отправка запроса
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://mcp-server.openrouter",
            "X-Title": "OpenRouter MCP Server"
        }
        
        response = requests.post(
            OPENROUTER_BASE_URL,
            headers=headers,
            json=request_data,
            stream=request_data.get("stream", False)
        )
        
        # Проверка на ошибки
        if response.status_code != 200:
            handle_openrouter_error(response)
        
        # Обработка streaming response
        if request_data.get("stream", False):
            def generate():
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith("data: "):
                            yield line_str + "\n\n"
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream"
            )
        
        # Обработка обычного ответа
        response_data = response.json()
        
        # Преобразование ответа Responses API в OpenAI-совместимый формат
        openai_response = convert_responses_to_openai_format(response_data)
        
        return openai_response
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Connection error to OpenRouter API: {str(e)}"
        )

def convert_responses_to_openai_format(responses_data: Dict) -> Dict:
    """Конвертация ответа из Responses API в OpenAI формат"""
    
    # Базовый ответ
    openai_response = {
        "id": responses_data.get("id", f"chatcmpl-{uuid.uuid4().hex}"),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": responses_data.get("model", "unknown"),
        "choices": [],
        "usage": responses_data.get("usage", {})
    }
    
    # Обрабатываем output
    output = responses_data.get("output", [])
    
    for i, output_item in enumerate(output):
        if isinstance(output_item, dict) and output_item.get("type") == "message":
            if output_item.get("role") == "assistant":
                # Извлекаем текст из content
                content_text = ""
                tool_calls = []
                
                content_list = output_item.get("content", [])
                for content_item in content_list:
                    if content_item.get("type") == "output_text":
                        content_text += content_item.get("text", "")
                    elif content_item.get("type") == "tool_call":
                        tool_calls.append({
                            "id": content_item.get("tool_call_id", f"call_{uuid.uuid4().hex[:8]}"),
                            "type": "function",
                            "function": {
                                "name": content_item.get("name", ""),
                                "arguments": content_item.get("arguments", "{}")
                            }
                        })
                
                # Создаем choice
                choice = {
                    "index": i,
                    "message": {
                        "role": "assistant",
                        "content": content_text if content_text else None
                    },
                    "finish_reason": output_item.get("status", "stop")
                }
                
                if tool_calls:
                    choice["message"]["tool_calls"] = tool_calls
                    choice["finish_reason"] = "tool_calls"
                
                openai_response["choices"].append(choice)
    
    return openai_response

@app.post("/v1/responses", response_model=ChatResponse)
async def direct_responses_api(
    chat_request: Dict[str, Any],
    api_key: str = Depends(verify_api_key)
):
    """
    Прямой доступ к OpenRouter Responses API
    """
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://mcp-server.openrouter",
            "X-Title": "OpenRouter MCP Server"
        }
        
        response = requests.post(
            OPENROUTER_BASE_URL,
            headers=headers,
            json=chat_request,
            stream=chat_request.get("stream", False)
        )
        
        if response.status_code != 200:
            handle_openrouter_error(response)
        
        if chat_request.get("stream", False):
            def generate():
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith("data: "):
                            yield line_str + "\n\n"
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream"
            )
        
        return response.json()
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Connection error to OpenRouter API: {str(e)}"
        )

@app.get("/models")
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
            headers=headers
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
        "timestamp": int(time.time())
    }

@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "service": "OpenRouter MCP Server",
        "version": "1.0.0",
        "endpoints": {
            "chat_completions": "/chat/completions (POST)",
            "direct_responses": "/v1/responses (POST)",
            "models": "/models (GET)",
            "health": "/health (GET)"
        }
    }

if __name__ == "__main__":
    import sys
    
    port = int(os.getenv("PORT", 8000))
    
    logger.info(f"Starting OpenRouter MCP Server on port {port}")
    logger.info(f"Using OpenRouter base URL: {OPENROUTER_BASE_URL}")
    logger.info(f"OpenRouter API Key: {'SET' if OPENROUTER_API_KEY else 'NOT SET'}")
    
    # Проверка API ключа
    if not OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY environment variable is not set!")
        logger.warning("Set it via: export OPENROUTER_API_KEY='your-key-here'")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )