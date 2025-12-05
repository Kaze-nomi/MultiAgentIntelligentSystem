import os
import json
import logging
import uuid
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import requests
import markdown

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentationType(str, Enum):
    API = "api"
    CODE = "code"
    README = "readme"
    USER_GUIDE = "user_guide"
    CHANGELOG = "changelog"

class DocumentationRequest(BaseModel):
    task: str
    data: Dict[str, Any] = {}
    doc_type: DocumentationType = DocumentationType.CODE
    format: str = "markdown"

class DocumentationResponse(BaseModel):
    task_id: str
    status: str
    documentation: Dict[str, Any]
    structured_output: Dict[str, Any]

app = FastAPI(title="Documentation Agent", version="1.0.0")

OPENROUTER_MCP_URL = os.getenv("OPENROUTER_MCP_URL", "http://openrouter-mcp:8000")

def call_llm(prompt: str, model: str = "deepseek/deepseek-chat-v3-0324") -> str:
    try:
        response = requests.post(
            f"{OPENROUTER_MCP_URL}/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "Ты технический писатель. Создавай качественную, понятную документацию."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return ""
    except Exception as e:
        logger.error(f"Error calling LLM: {str(e)}")
        return ""

def analyze_code_for_documentation(code: str) -> Dict[str, Any]:
    """Анализ кода для документации"""
    prompt = f"""
    Проанализируй следующий код и извлеки информацию для документации:
    
    ```python
    {code}
    ```
    
    Извлеки:
    1. Основные функции/методы с параметрами
    2. Классы и их назначение
    3. Ключевые алгоритмы
    4. Зависимости
    5. Примеры использования
    
    Верни JSON с информацией.
    """
    
    response = call_llm(prompt)
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        return json.loads(json_match.group()) if json_match else {}
    except:
        return {}

def generate_api_documentation(api_info: Dict[str, Any]) -> str:
    """Генерация API документации"""
    prompt = f"""
    Создай API документацию на основе следующей информации:
    
    {json.dumps(api_info, ensure_ascii=False, indent=2)}
    
    Документация должна включать:
    1. Описание API
    2. Список эндпоинтов
    3. Параметры запросов
    4. Примеры ответов
    5. Коды ошибок
    
    Используй формат Markdown.
    """
    
    return call_llm(prompt)

def generate_readme(project_info: Dict[str, Any]) -> str:
    """Генерация README"""
    prompt = f"""
    Создай README.md файл на русском языке для проекта со следующей информацией:
    
    Название: {project_info.get('name', 'Проект')}
    Описание: {project_info.get('description', '')}
    Установка: {project_info.get('installation', '')}
    Использование: {project_info.get('usage', '')}
    Примеры: {project_info.get('examples', '')}
    
    README должен содержать:
    1. Заголовок и описание
    2. Быстрый старт
    3. Установка
    4. Использование
    5. Примеры
    6. Лицензия
    
    Верни только Markdown код.
    """
    
    return call_llm(prompt)

def generate_code_documentation(code_info: Dict[str, Any]) -> str:
    """Генерация документации для кода"""
    prompt = f"""
    Создай документацию для кода на основе следующей информации:
    
    {json.dumps(code_info, ensure_ascii=False, indent=2)}
    
    Документация должна включать:
    1. Обзор модуля
    2. Описание классов и методов
    3. Примеры использования
    4. Примечания
    
    Используй формат Markdown.
    """
    
    return call_llm(prompt)

@app.post("/process")
async def process_documentation(request: DocumentationRequest):
    """Генерация документации"""
    task_id = str(uuid.uuid4())
    
    try:
        # Извлекаем данные
        code = request.data.get("code", "")
        commit_message = request.data.get("commit_message", "")
        project_info = request.data.get("project_info", {})
        
        # Анализируем код
        code_info = {}
        if code:
            code_info = analyze_code_for_documentation(code)
        
        # Генерируем документацию в зависимости от типа
        markdown_content = ""
        
        if request.doc_type == DocumentationType.API:
            markdown_content = generate_api_documentation({
                "description": request.task,
                "code_info": code_info,
                "data": request.data
            })
        elif request.doc_type == DocumentationType.README:
            markdown_content = generate_readme(project_info)
        elif request.doc_type == DocumentationType.CODE:
            markdown_content = generate_code_documentation(code_info)
        else:
            # Общая документация
            prompt = f"Создай документацию типа {request.doc_type.value} для:\n{request.task}\n\nДополнительная информация: {json.dumps(request.data, ensure_ascii=False)}"
            markdown_content = call_llm(prompt)
        
        # Конвертируем в HTML если нужно
        html_content = ""
        if request.format == "html":
            html_content = markdown.markdown(markdown_content)
        
        response_data = DocumentationResponse(
            task_id=task_id,
            status="completed",
            documentation={
                "markdown": markdown_content,
                "html": html_content,
                "format": request.format,
                "metadata": {
                    "doc_type": request.doc_type.value,
                    "generated_at": datetime.now().isoformat(),
                    "length": len(markdown_content)
                }
            },
            structured_output={
                "documentation": markdown_content,
                "code_analysis": code_info,
                "metadata": {
                    "task": request.task,
                    "doc_type": request.doc_type.value,
                    "timestamp": datetime.now().isoformat()
                }
            }
        )
        
        return JSONResponse(content=response_data.dict())
        
    except Exception as e:
        logger.error(f"Error generating documentation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate/readme")
async def generate_readme_endpoint(request: Dict[str, Any]):
    """Генерация README файла"""
    project_info = request.get("project_info", {})
    
    if not project_info.get("name") and not project_info.get("description"):
        raise HTTPException(status_code=400, detail="Project name or description is required")
    
    readme_content = generate_readme(project_info)
    
    return {
        "readme": readme_content,
        "html": markdown.markdown(readme_content),
        "project_info": project_info
    }

@app.post("/generate/api-docs")
async def generate_api_docs(request: Dict[str, Any]):
    """Генерация API документации"""
    api_info = request.get("api_info", {})
    code = request.get("code", "")
    
    if not api_info and not code:
        raise HTTPException(status_code=400, detail="API info or code is required")
    
    if code:
        api_info = analyze_code_for_documentation(code)
    
    api_docs = generate_api_documentation(api_info)
    
    return {
        "api_documentation": api_docs,
        "html": markdown.markdown(api_docs)
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "documentation"}

@app.get("/")
async def root():
    return {
        "service": "Documentation Agent",
        "version": "1.0.0",
        "endpoints": {
            "process": "POST /process - Generate documentation",
            "generate_readme": "POST /generate/readme - Generate README",
            "generate_api_docs": "POST /generate/api-docs - Generate API docs"
        },
        "supported_doc_types": ["api", "code", "readme", "user_guide", "changelog"]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)