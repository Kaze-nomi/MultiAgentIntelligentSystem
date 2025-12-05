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
    ARCHITECTURE = "architecture"


class DocumentationRequest(BaseModel):
    task: str
    data: Dict[str, Any] = {}
    doc_type: DocumentationType = DocumentationType.CODE
    format: str = "markdown"


class DocumentationResponse(BaseModel):
    task_id: str
    status: str
    documentation: Dict[str, Any]
    files_generated: List[Dict[str, Any]]
    structured_output: Dict[str, Any]


app = FastAPI(title="Documentation Agent", version="2.0.0")

OPENROUTER_MCP_URL = os.getenv("OPENROUTER_MCP_URL", "http://openrouter-mcp:8000")


def call_llm(prompt: str, system_prompt: str = None) -> str:
    if not system_prompt:
        system_prompt = """Ты профессиональный технический писатель.
Создаёшь понятную, структурированную документацию.
Используешь примеры кода и диаграммы где уместно.
Адаптируешь стиль под существующую документацию проекта."""

    try:
        response = requests.post(
            f"{OPENROUTER_MCP_URL}/chat/completions",
            json={
                "model": "deepseek/deepseek-chat-v3-0324",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3
            },
            timeout=90
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return ""
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return ""


def analyze_existing_docs(repo_context: Dict[str, Any]) -> Dict[str, Any]:
    key_files = repo_context.get("key_files", {})
    
    doc_files = {}
    for path, content in key_files.items():
        if any(x in path.lower() for x in ["readme", "doc", "guide", "changelog"]):
            doc_files[path] = content[:3000]
    
    if not doc_files:
        return {
            "has_docs": False,
            "style": "standard",
            "sections": []
        }
    
    prompt = f"""
Проанализируй существующую документацию проекта:

{json.dumps(doc_files, indent=2, ensure_ascii=False)}

Определи:
1. Стиль документации (формальный/неформальный)
2. Структуру секций
3. Используемые форматы (markdown features)
4. Язык документации

Верни JSON:
{{
    "has_docs": true,
    "style": "formal/informal",
    "language": "ru/en",
    "sections": ["список типичных секций"],
    "markdown_features": ["используемые фичи markdown"],
    "conventions": ["соглашения по документации"]
}}
"""
    
    response = call_llm(prompt)
    
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except:
        pass
    
    return {"has_docs": True, "style": "standard", "sections": []}


def generate_documentation(
    task: str,
    doc_type: DocumentationType,
    tech_stack: Dict[str, Any],
    repo_context: Dict[str, Any],
    existing_docs_style: Dict[str, Any]
) -> Dict[str, Any]:
    
    structure = repo_context.get("structure", [])[:50]
    key_files = repo_context.get("key_files", {})
    
    type_instructions = {
        DocumentationType.README: """
Создай README.md с секциями:
- Заголовок и бейджи
- Описание проекта
- Особенности
- Требования
- Установка
- Быстрый старт
- Примеры использования
- API (если есть)
- Конфигурация
- Разработка
- Тестирование
- Лицензия
""",
        DocumentationType.API: """
Создай API документацию:
- Обзор API
- Аутентификация
- Endpoints с примерами
- Модели данных
- Коды ответов
- Примеры curl/httpie
""",
        DocumentationType.ARCHITECTURE: """
Создай документацию архитектуры:
- Обзор системы
- Компоненты
- Потоки данных
- Интеграции
- Решения и обоснования
""",
        DocumentationType.CODE: """
Создай документацию кода:
- Обзор модуля
- Классы и функции
- Примеры использования
- Зависимости
""",
        DocumentationType.CHANGELOG: """
Создай CHANGELOG.md:
- Версия и дата
- Добавлено
- Изменено
- Исправлено
- Удалено
""",
        DocumentationType.USER_GUIDE: """
Создай руководство пользователя:
- Введение
- Начало работы
- Основные функции
- Примеры
- FAQ
- Решение проблем
"""
    }
    
    doc_style = existing_docs_style.get("style", "standard")
    doc_lang = existing_docs_style.get("language", "ru")
    
    prompt = f"""
Создай документацию типа {doc_type.value} для проекта.

## ЗАДАЧА:
{task}

## ТИП ДОКУМЕНТАЦИИ:
{type_instructions.get(doc_type, "Создай подходящую документацию")}

## ТЕХНОЛОГИЧЕСКИЙ СТЕК:
- Язык: {tech_stack.get('primary_language', 'unknown')}
- Фреймворки: {', '.join(tech_stack.get('frameworks', []))}

## СТРУКТУРА ПРОЕКТА:
{json.dumps(structure, indent=2)}

## СУЩЕСТВУЮЩИЙ КОД:
{json.dumps(key_files, indent=2, ensure_ascii=False)[:10000]}

## СТИЛЬ ДОКУМЕНТАЦИИ:
- Стиль: {doc_style}
- Язык: {doc_lang}
- Соглашения: {existing_docs_style.get('conventions', [])}

Создай полную, готовую к использованию документацию в формате Markdown.
"""
    
    content = call_llm(prompt)
    
    return {
        "markdown": content,
        "html": markdown.markdown(content) if content else "",
        "doc_type": doc_type.value,
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "style": doc_style,
            "language": doc_lang
        }
    }


def generate_inline_docs(
    code: str,
    language: str,
    tech_stack: Dict[str, Any]
) -> str:
    docstring_style = "Google" if language == "python" else "JSDoc" if language in ["javascript", "typescript"] else "standard"
    
    prompt = f"""
Добавь документацию к следующему коду.

Язык: {language}
Стиль docstrings: {docstring_style}

Код:
```{language}
{code[:8000]}
Добавь:

Docstrings для всех функций/методов/классов
Типизацию параметров и возвращаемых значений
Примеры использования в docstrings
Краткие комментарии для сложной логики
Верни полный код с добавленной документацией.
"""
    return call_llm(prompt)

@app.post("/process")
async def process_documentation(request: DocumentationRequest):
    task_id = str(uuid.uuid4())


    try:
        data = request.data
        tech_stack = data.get("tech_stack", {})
        repo_context = data.get("repo_context", {})
        
        existing_docs_style = analyze_existing_docs(repo_context)
        
        documentation = generate_documentation(
            task=request.task,
            doc_type=request.doc_type,
            tech_stack=tech_stack,
            repo_context=repo_context,
            existing_docs_style=existing_docs_style
        )
        
        files_generated = []
        
        file_paths = {
            DocumentationType.README: "README.md",
            DocumentationType.API: "docs/api.md",
            DocumentationType.ARCHITECTURE: "docs/architecture.md",
            DocumentationType.CODE: "docs/code.md",
            DocumentationType.CHANGELOG: "CHANGELOG.md",
            DocumentationType.USER_GUIDE: "docs/user-guide.md"
        }
        
        if documentation.get("markdown"):
            files_generated.append({
                "path": file_paths.get(request.doc_type, "docs/documentation.md"),
                "content": documentation["markdown"],
                "description": f"Generated {request.doc_type.value} documentation"
            })
        
        response = DocumentationResponse(
            task_id=task_id,
            status="completed",
            documentation=documentation,
            files_generated=files_generated,
            structured_output={
                "doc_type": request.doc_type.value,
                "existing_style": existing_docs_style,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return JSONResponse(content=response.dict())
    
    except Exception as e:
        logger.error(f"Documentation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/generate/inline")
async def generate_inline_documentation(request: Dict[str, Any]):
    code = request.get("code", "")
    language = request.get("language", "python")
    tech_stack = request.get("tech_stack", {})

    if not code:
        raise HTTPException(status_code=400, detail="Code is required")

    documented_code = generate_inline_docs(code, language, tech_stack)

    return {
        "original_code": code,
        "documented_code": documented_code,
        "language": language
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "documentation", "version": "2.0.0"}

if __name__ == "main":
    uvicorn.run(app, host="0.0.0.0", port=8000)