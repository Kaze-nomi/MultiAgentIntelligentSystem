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
CODE_REVIEWS_TOTAL = Counter('code_reviews_total', 'Total code reviews performed')
REVIEW_TIME = Histogram('code_review_duration_seconds', 'Time spent on code review')
ISSUES_FOUND = Counter('code_issues_found', 'Code issues found by type')

class IssueType(str, Enum):
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    MAINTAINABILITY = "maintainability"
    DOCUMENTATION = "documentation"

class CodeIssue(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: IssueType
    severity: str  # low, medium, high, critical
    description: str
    line_number: Optional[int] = None
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
    metrics: Dict[str, Any]
    structured_output: Dict[str, Any]

app = FastAPI(title="Code Reviewer Agent", version="1.0.0")

OPENROUTER_MCP_URL = os.getenv("OPENROUTER_MCP_URL", "http://openrouter-mcp:8000")

def call_llm(prompt: str, model: str = "deepseek/deepseek-chat-v3-0324") -> str:
    try:
        response = requests.post(
            f"{OPENROUTER_MCP_URL}/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "Ты опытный код-ревьюер. Анализируй код на ошибки, проблемы безопасности, стиль и качество. Возвращай структурированный JSON ответ."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return ""
    except Exception as e:
        logger.error(f"Error calling LLM: {str(e)}")
        return ""

def analyze_code(code: str, language: str = "python") -> Dict[str, Any]:
    """Анализ кода с помощью LLM"""
    
    prompt = f"""
    Проанализируй следующий код на языке {language}:
    
    ```{language}
    {code}
    ```
    
    Проверь:
    1. Синтаксические ошибки
    2. Проблемы безопасности
    3. Производительность
    4. Стиль кода (PEP8 для Python)
    5. Качество документации
    6. Потенциальные баги
    
    Для каждой найденной проблемы укажи:
    - Тип (bug, security, performance, style, maintainability, documentation)
    - Серьезность (low, medium, high, critical)
    - Описание
    - Номер строки (если применимо)
    - Предложение по исправлению
    
    Также предоставь общую оценку качества кода от 1 до 10.
    
    Верни ответ в JSON формате:
    {{
        "reasoning": "Твое обоснование анализа",
        "quality_score": 8.5,
        "issues": [
            {{
                "type": "bug/security/performance/style/maintainability/documentation",
                "severity": "low/medium/high/critical",
                "description": "Описание проблемы",
                "line_number": 10,
                "suggestion": "Как исправить",
                "code_snippet": "def bad_func():"
            }}
        ],
        "summary": {{
            "total_issues": 5,
            "critical_issues": 1,
            "high_issues": 2,
            "recommendations": ["рекомендация1", "рекомендация2"]
        }}
    }}
    """
    
    with REVIEW_TIME.time():
        response = call_llm(prompt)
    
    try:
        # Ищем JSON в ответе
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            
            # Обновляем метрики
            issues = result.get("issues", [])
            for issue in issues:
                ISSUES_FOUND.labels(type=issue.get("type", "unknown")).inc()
            
            CODE_REVIEWS_TOTAL.inc()
            return result
        else:
            return {
                "reasoning": "Не удалось проанализировать код",
                "quality_score": 0,
                "issues": [],
                "summary": {
                    "total_issues": 0,
                    "critical_issues": 0,
                    "high_issues": 0,
                    "recommendations": ["Требуется ручной анализ"]
                }
            }
    except Exception as e:
        logger.error(f"Error parsing analysis result: {str(e)}")
        return {
            "reasoning": f"Ошибка при анализе: {str(e)}",
            "quality_score": 0,
            "issues": [],
            "summary": {
                "total_issues": 0,
                "critical_issues": 0,
                "high_issues": 0,
                "recommendations": ["Ошибка анализатора"]
            }
        }

def analyze_commit(commit_data: Dict[str, Any]) -> Dict[str, Any]:
    """Анализ коммита"""
    prompt = f"""
    Проанализируй коммит:
    - Сообщение: {commit_data.get('message', '')}
    - Изменения: {json.dumps(commit_data.get('changes', {}), ensure_ascii=False)}
    - Автор: {commit_data.get('author', '')}
    
    Определи:
    1. Качество сообщения коммита
    2. Соответствие стандартам
    3. Потенциальные проблемы
    4. Рекомендации
    
    Верни JSON ответ.
    """
    
    response = call_llm(prompt)
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        return json.loads(json_match.group()) if json_match else {}
    except:
        return {}

@app.post("/process")
async def process_code_review(request: CodeReviewRequest):
    """Обработка запроса на код-ревью"""
    task_id = str(uuid.uuid4())
    
    try:
        # Логирование начала
        logger.info(f"Starting code review for task: {request.task}")
        
        result = None
        
        if request.code:
            # Анализ предоставленного кода
            result = analyze_code(request.code, request.language)
        elif "commit" in request.data:
            # Анализ коммита
            result = analyze_commit(request.data["commit"])
        else:
            # Общий анализ
            prompt = f"Проанализируй задачу: {request.task}\nКонтекст: {json.dumps(request.data, ensure_ascii=False)}"
            response = call_llm(prompt)
            result = {
                "reasoning": response,
                "issues": [],
                "summary": {"recommendations": ["Требуется предоставить код для анализа"]}
            }
        
        # Создаем структурированный ответ
        issues = []
        for issue_data in result.get("issues", []):
            try:
                issue = CodeIssue(**issue_data)
                issues.append(issue)
            except Exception as e:
                logger.warning(f"Error creating issue: {str(e)}")
        
        response_data = CodeReviewResponse(
            task_id=task_id,
            status="completed",
            issues=issues,
            summary=result.get("summary", {}),
            metrics={
                "total_issues": len(issues),
                "critical_issues": len([i for i in issues if i.severity == "critical"]),
                "review_duration": "measured"
            },
            structured_output={
                "analysis": result,
                "timestamp": datetime.now().isoformat(),
                "agent": "code_reviewer"
            }
        )
        
        return JSONResponse(content=response_data.dict())
        
    except Exception as e:
        logger.error(f"Error in code review: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/file")
async def analyze_code_file(request: Dict[str, Any]):
    """Анализ файла с кодом"""
    code = request.get("code", "")
    language = request.get("language", "python")
    
    if not code:
        raise HTTPException(status_code=400, detail="Code is required")
    
    result = analyze_code(code, language)
    return result

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "code_reviewer"}

@app.get("/metrics")
async def metrics():
    return generate_latest()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)