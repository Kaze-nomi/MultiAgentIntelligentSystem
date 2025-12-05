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
from prometheus_client import Counter, Histogram, generate_latest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Метрики
CODE_REVIEWS_TOTAL = Counter('code_reviews_total', 'Total code reviews')
ISSUES_FOUND = Counter('code_issues_found_total', 'Issues found', ['severity'])

class IssueType(str, Enum):
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    MAINTAINABILITY = "maintainability"
    DOCUMENTATION = "documentation"
    COMPATIBILITY = "compatibility"

class CodeIssue(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: IssueType
    severity: str  # low, medium, high, critical
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    description: str
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None

class CodeReviewRequest(BaseModel):
    task: str
    data: Dict[str, Any] = {}
    priority: str = "medium"
    code: Optional[str] = None
    language: str = "python"

class CodeReviewResponse(BaseModel):
    task_id: str
    status: str
    issues: List[CodeIssue]
    summary: Dict[str, Any]
    recommendations: List[str]
    compatibility_notes: List[str]
    structured_output: Dict[str, Any]

app = FastAPI(title="Code Reviewer Agent", version="2.0.0")

OPENROUTER_MCP_URL = os.getenv("OPENROUTER_MCP_URL", "http://openrouter-mcp:8000")


def call_llm(prompt: str, system_prompt: str = None) -> str:
    if not system_prompt:
        system_prompt = """Ты опытный код-ревьюер с 10+ лет опыта.
Ты отлично знаешь лучшие практики, паттерны проектирования, безопасность и производительность.
Всегда даёшь конкретные, actionable рекомендации.
Возвращай ответы в JSON когда указано."""

    try:
        response = requests.post(
            f"{OPENROUTER_MCP_URL}/chat/completions",
            json={
                "model": "deepseek/deepseek-chat-v3-0324",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1
            },
            timeout=90
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return ""
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return ""


def analyze_code_with_context(
    code: str, 
    language: str, 
    tech_stack: Dict[str, Any],
    task_context: str,
    repo_context: Dict[str, Any]
) -> Dict[str, Any]:
    
    # Извлекаем информацию о стеке
    frameworks = tech_stack.get("frameworks", [])
    patterns = tech_stack.get("architecture_patterns", [])
    
    prompt = f"""
Проведи детальный код-ревью с учётом контекста проекта.

## КОНТЕКСТ ЗАДАЧИ:
{task_context}

## ТЕХНОЛОГИЧЕСКИЙ СТЕК:
- Язык: {language}
- Фреймворки: {', '.join(frameworks) or 'не указаны'}
- Архитектура: {', '.join(patterns) or 'не указана'}

## КОД ДЛЯ АНАЛИЗА:
```{language}
{code[:15000]}
СУЩЕСТВУЮЩИЕ ФАЙЛЫ ПРОЕКТА:
{json.dumps(repo_context.get('structure', [])[:30], indent=2)}

ПРОВЕРЬ:
Баги и ошибки - логические ошибки, неправильная обработка edge cases
Безопасность - SQL injection, XSS, утечки данных, небезопасные зависимости
Производительность - N+1 queries, утечки памяти, неоптимальные алгоритмы
Совместимость - соответствие стилю проекта, конфликты с существующим кодом
Качество - читаемость, SOLID принципы, DRY, тестируемость
Документация - docstrings, комментарии, типизация
ВЕРНИ JSON:
{{
"overall_score": 8.5,
"issues": [
{{
"type": "bug/security/performance/style/maintainability/documentation/compatibility",
"severity": "critical/high/medium/low",
"file_path": "путь к файлу если известен",
"line_number": 42,
"description": "Подробное описание проблемы",
"suggestion": "Конкретное решение с примером кода",
"code_snippet": "проблемный код"
}}
],
"recommendations": [
"Общие рекомендации по улучшению"
],
"compatibility_notes": [
"Заметки о совместимости с существующим кодом"
],
"summary": {{
"total_issues": 5,
"critical": 1,
"high": 2,
"medium": 1,
"low": 1,
"verdict": "Краткий вердикт"
}}
}}
"""

    response = call_llm(prompt)

    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            
            # Обновляем метрики
            for issue in result.get("issues", []):
                ISSUES_FOUND.labels(severity=issue.get("severity", "unknown")).inc()
            
            CODE_REVIEWS_TOTAL.inc()
            return result
    except Exception as e:
        logger.error(f"Parse error: {e}")

    return {
        "overall_score": 0,
        "issues": [],
        "recommendations": ["Не удалось проанализировать код"],
        "compatibility_notes": [],
        "summary": {"total_issues": 0, "verdict": "Ошибка анализа"}
    }
def analyze_for_new_code_generation(
task: str,
tech_stack: Dict[str, Any],
existing_code: Dict[str, str]
) -> Dict[str, Any]:

    prompt = f"""
Проанализируй существующий код проекта и дай рекомендации для новой разработки.

ЗАДАЧА:
{task}

СТЕК:
{json.dumps(tech_stack, indent=2)}

СУЩЕСТВУЮЩИЙ КОД:
{json.dumps(existing_code, indent=2, ensure_ascii=False)[:10000]}

Определи:

Какие паттерны используются в проекте
Стиль именования (camelCase, snake_case, etc.)
Структура импортов
Как обрабатываются ошибки
Как организованы тесты
Какие conventions нужно соблюдать
Верни JSON:
{{
"coding_style": {{
"naming_convention": "snake_case/camelCase",
"import_style": "описание",
"error_handling": "описание",
"docstring_style": "Google/NumPy/etc"
}},
"patterns_used": ["список паттернов"],
"must_follow": ["обязательные правила"],
"avoid": ["чего избегать"],
"integration_points": ["где интегрировать новый код"]
}}
"""

    response = call_llm(prompt)

    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except:
        pass

    return {
        "coding_style": {},
        "patterns_used": [],
        "must_follow": [],
        "avoid": [],
        "integration_points": []
}

@app.post("/process")
async def process_code_review(request: CodeReviewRequest):
    task_id = str(uuid.uuid4())

    try:
        data = request.data
        tech_stack = data.get("tech_stack", {"primary_language": request.language})
        repo_context = data.get("repo_context", {})
        task_context = data.get("context", request.task)
        
        # Определяем что анализировать
        code_to_analyze = request.code or ""
        
        # Если передан контекст с ключевыми файлами, добавляем их
        if not code_to_analyze and repo_context.get("key_files"):
            code_to_analyze = json.dumps(repo_context["key_files"], indent=2)
        
        if not code_to_analyze:
            return JSONResponse(content={
                "task_id": task_id,
                "status": "completed",
                "issues": [],
                "summary": {"message": "Код для анализа не предоставлен"},
                "recommendations": ["Предоставьте код для анализа"],
                "compatibility_notes": [],
                "structured_output": {}
            })
        
        # Анализируем
        result = analyze_code_with_context(
            code=code_to_analyze,
            language=request.language,
            tech_stack=tech_stack,
            task_context=task_context,
            repo_context=repo_context
        )
        
        # Формируем ответ
        issues = []
        for issue_data in result.get("issues", []):
            try:
                issues.append(CodeIssue(**issue_data))
            except Exception as e:
                logger.warning(f"Issue parse error: {e}")
        
        response = CodeReviewResponse(
            task_id=task_id,
            status="completed",
            issues=issues,
            summary=result.get("summary", {}),
            recommendations=result.get("recommendations", []),
            compatibility_notes=result.get("compatibility_notes", []),
            structured_output={
                "overall_score": result.get("overall_score", 0),
                "analysis": result,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return JSONResponse(content=response.dict())
        
    except Exception as e:
        logger.error(f"Review error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/style")
async def analyze_project_style(request: Dict[str, Any]):

    task = request.get("task", "")
    tech_stack = request.get("tech_stack", {})
    existing_code = request.get("existing_code", {})

    result = analyze_for_new_code_generation(task, tech_stack, existing_code)

    return result

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "code_reviewer", "version": "2.0.0"}

@app.get("/metrics")
async def metrics():
    return generate_latest()

if __name__ == "main":
    uvicorn.run(app, host="0.0.0.0", port=8000)