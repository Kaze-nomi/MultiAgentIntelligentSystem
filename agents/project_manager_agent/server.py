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
from prometheus_client import Counter, generate_latest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Метрики
TASKS_PROCESSED = Counter('project_manager_tasks_total', 'Total tasks processed')
TASKS_FAILED = Counter('project_manager_tasks_failed', 'Failed tasks')

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TechStack(BaseModel):
    primary_language: str = "unknown"
    languages: List[str] = []
    frameworks: List[str] = []
    databases: List[str] = []
    tools: List[str] = []
    package_managers: List[str] = []
    testing_frameworks: List[str] = []
    ci_cd: List[str] = []
    architecture_patterns: List[str] = []

class RepoFile(BaseModel):
    path: str
    content: Optional[str] = None
    size: int = 0
    type: str = "file"  # file, dir
    sha: Optional[str] = None

class RepoContext(BaseModel):
    owner: str
    name: str
    default_branch: str = "main"
    structure: List[RepoFile] = []
    key_files: Dict[str, str] = {}  # path -> content
    readme_content: Optional[str] = None
    tech_stack: Optional[TechStack] = None

class FileToCreate(BaseModel):
    path: str
    content: str
    description: str
    action: str = "create"  # create, update, delete
    original_sha: Optional[str] = None  # для обновления

class SubtaskResult(BaseModel):
    agent: str
    status: str
    output: Dict[str, Any] = {}
    files_generated: List[FileToCreate] = []
    recommendations: List[str] = []

class WorkflowRequest(BaseModel):
    task_description: str
    repo_owner: str
    repo_name: str
    base_branch: str = "main"
    repo_context: Optional[Dict[str, Any]] = None  # Контекст репозитория от n8n
    generate_files: bool = True

class WorkflowResponse(BaseModel):
    task_id: str
    status: str
    tech_stack: TechStack
    branch_name: str
    files_to_create: List[Dict[str, Any]]
    commit_message: str
    pr_title: str
    pr_description: str
    summary: str
    agent_results: List[Dict[str, Any]]
    reasoning_log: List[Dict[str, Any]]

app = FastAPI(title="Project Manager Agent", version="3.0.0")

# Конфигурация агентов
OPENROUTER_MCP_URL = os.getenv("OPENROUTER_MCP_URL", "http://openrouter-mcp:8000")
CODE_REVIEWER_URL = os.getenv("CODE_REVIEWER_URL", "http://code-reviewer:8000")
DOCUMENTATION_URL = os.getenv("DOCUMENTATION_URL", "http://documentation:8000")
DESIGN_ASSISTANT_URL = os.getenv("DESIGN_ASSISTANT_URL", "http://design-assistant:8000")

# Хранилище
tasks_db = {}
reasoning_logs = {}


def call_llm(prompt: str, system_prompt: str = None, model: str = "deepseek/deepseek-chat-v3-0324") -> str:
    if not system_prompt:
        system_prompt = """Ты опытный технический лидер и архитектор ПО с 15+ лет опыта.
Ты отлично понимаешь различные технологические стеки, паттерны проектирования и лучшие практики.
Всегда анализируешь существующий код перед предложением изменений.
Возвращай ответы в формате JSON когда это указано."""

    try:
        response = requests.post(
            f"{OPENROUTER_MCP_URL}/chat/completions",
            json={
                "model": model,
                "input": [
                    {"type": "message", "role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2
            },
            timeout=120
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            logger.error(f"LLM error: {response.status_code}")
            return ""
    except Exception as e:
        logger.error(f"Error calling LLM: {str(e)}")
        return ""


def analyze_tech_stack(repo_context: Dict[str, Any]) -> TechStack:
    
    structure = repo_context.get("structure", [])
    key_files = repo_context.get("key_files", {})
    
    # Собираем информацию о файлах
    file_extensions = {}
    config_files = []
    
    for file in structure:
        path = file.get("path", "")
        if "." in path:
            ext = path.split(".")[-1].lower()
            file_extensions[ext] = file_extensions.get(ext, 0) + 1
        
        # Ключевые конфигурационные файлы
        filename = path.split("/")[-1].lower()
        if filename in ["package.json", "requirements.txt", "pyproject.toml", "cargo.toml", 
                        "go.mod", "pom.xml", "build.gradle", "composer.json", "gemfile",
                        "dockerfile", "docker-compose.yml", "docker-compose.yaml",
                        ".github/workflows", "jenkinsfile", ".gitlab-ci.yml"]:
            config_files.append(path)
    
    # Формируем prompt для анализа
    prompt = f"""
Проанализируй технологический стек проекта на основе следующей информации:

## Структура файлов (расширения и количество):
{json.dumps(file_extensions, indent=2)}

## Конфигурационные файлы:
{json.dumps(config_files, indent=2)}

## Содержимое ключевых файлов:
{json.dumps(key_files, indent=2, ensure_ascii=False)[:10000]}

Определи и верни JSON:
{{
    "primary_language": "основной язык программирования",
    "languages": ["список всех языков"],
    "frameworks": ["используемые фреймворки"],
    "databases": ["базы данных если есть"],
    "tools": ["инструменты разработки"],
    "package_managers": ["менеджеры пакетов"],
    "testing_frameworks": ["фреймворки тестирования"],
    "ci_cd": ["CI/CD инструменты"],
    "architecture_patterns": ["архитектурные паттерны, например: microservices, monolith, MVC, etc"]
}}
"""
    
    response = call_llm(prompt)
    
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return TechStack(**data)
    except Exception as e:
        logger.error(f"Error parsing tech stack: {e}")
    
    # Fallback: определяем по расширениям
    primary_lang = "unknown"
    if file_extensions:
        # Определяем основной язык по количеству файлов
        lang_map = {
            "py": "Python", "js": "JavaScript", "ts": "TypeScript",
            "java": "Java", "go": "Go", "rs": "Rust", "rb": "Ruby",
            "php": "PHP", "cs": "C#", "cpp": "C++", "c": "C"
        }
        for ext, count in sorted(file_extensions.items(), key=lambda x: -x[1]):
            if ext in lang_map:
                primary_lang = lang_map[ext]
                break
    
    return TechStack(primary_language=primary_lang, languages=[primary_lang])


def generate_branch_name(task_description: str, tech_stack: TechStack) -> str:
    prompt = f"""
Создай короткое имя git ветки для задачи.
Стек проекта: {tech_stack.primary_language}, {', '.join(tech_stack.frameworks[:3])}
Задача: {task_description[:200]}

Требования:
- Только латинские буквы, цифры и дефисы
- Максимум 50 символов
- Формат: feature/описание или fix/описание

Верни только имя ветки без кавычек.
"""
    response = call_llm(prompt)
    branch = re.sub(r'[^a-zA-Z0-9\-/]', '-', response.strip()[:50])
    branch = re.sub(r'-+', '-', branch).strip('-')
    
    if not branch or len(branch) < 5:
        branch = f"feature/task-{uuid.uuid4().hex[:8]}"
    
    return branch


def plan_task_with_context(
    task_description: str, 
    tech_stack: TechStack, 
    repo_context: Dict[str, Any]
) -> Dict[str, Any]:
    
    structure = repo_context.get("structure", [])
    key_files = repo_context.get("key_files", {})
    
    # Формируем список существующих файлов
    existing_files = [f.get("path") for f in structure if f.get("type") == "file"][:100]
    
    prompt = f"""
Ты - технический лидер. Проанализируй задачу и создай план выполнения.

## ЗАДАЧА:
{task_description}

## ТЕХНОЛОГИЧЕСКИЙ СТЕК ПРОЕКТА:
- Основной язык: {tech_stack.primary_language}
- Фреймворки: {', '.join(tech_stack.frameworks) or 'не определены'}
- Паттерны: {', '.join(tech_stack.architecture_patterns) or 'не определены'}
- Тестирование: {', '.join(tech_stack.testing_frameworks) or 'не определено'}

## СУЩЕСТВУЮЩАЯ СТРУКТУРА (первые 100 файлов):
{json.dumps(existing_files, indent=2)}

## СОДЕРЖИМОЕ КЛЮЧЕВЫХ ФАЙЛОВ:
{json.dumps(key_files, indent=2, ensure_ascii=False)[:15000]}

## ТВОЯ ЗАДАЧА:

1. Определи какие агенты нужны для выполнения задачи:
   - code_reviewer: анализ кода, поиск проблем, предложения улучшений
   - documentation: создание/обновление документации
   - design_assistant: создание диаграмм архитектуры

2. Определи какие НОВЫЕ файлы нужно создать и какие СУЩЕСТВУЮЩИЕ обновить

3. Для каждого файла сгенерируй ПОЛНЫЙ рабочий код, соответствующий стеку проекта

4. Учитывай существующие паттерны и стиль кода проекта

Верни СТРОГО JSON:
{{
    "reasoning": "Подробное обоснование плана (2-3 предложения)",
    "analysis": {{
        "affected_areas": ["список затрагиваемых областей кода"],
        "risks": ["потенциальные риски"],
        "dependencies": ["зависимости между изменениями"]
    }},
    "subtasks": [
        {{
            "id": "subtask-1",
            "description": "Что нужно сделать",
            "assigned_agent": "code_reviewer/documentation/design_assistant",
            "priority": "high/medium/low",
            "context": "Какой контекст передать агенту",
            "expected_output": "Что ожидается от агента"
        }}
    ],
    "files_to_create": [
        {{
            "path": "путь/к/новому/файлу.py",
            "content": "ПОЛНЫЙ КОД ФАЙЛА - НЕ ЗАГЛУШКА",
            "description": "Описание файла",
            "action": "create"
        }}
    ],
    "files_to_update": [
        {{
            "path": "путь/к/существующему/файлу.py",
            "content": "ПОЛНЫЙ ОБНОВЛЁННЫЙ КОД",
            "description": "Что изменено и почему",
            "action": "update"
        }}
    ],
    "commit_message": "тип(область): краткое описание",
    "pr_title": "Заголовок PR",
    "pr_description": "Подробное описание изменений в markdown"
}}

ВАЖНО: 
- Генерируй ПОЛНЫЙ рабочий код, НЕ заглушки
- Код должен соответствовать стилю и паттернам проекта
- Учитывай существующие импорты и зависимости
"""
    
    response = call_llm(prompt)
    
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        logger.error(f"Error parsing plan: {e}")
    
    return create_default_plan(task_description, tech_stack)


def create_default_plan(task_description: str, tech_stack: TechStack) -> Dict[str, Any]:
    return {
        "reasoning": "Автоматический план на основе анализа задачи",
        "analysis": {
            "affected_areas": ["unknown"],
            "risks": ["Требуется ручная проверка"],
            "dependencies": []
        },
        "subtasks": [
            {
                "id": "subtask-1",
                "description": f"Анализ и реализация: {task_description}",
                "assigned_agent": "code_reviewer",
                "priority": "high",
                "context": task_description,
                "expected_output": "Анализ и рекомендации"
            }
        ],
        "files_to_create": [],
        "files_to_update": [],
        "commit_message": f"feat: implement task",
        "pr_title": f"Feature: {task_description[:50]}",
        "pr_description": f"## Описание\n\n{task_description}"
    }


def call_agent(agent_url: str, agent_name: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        logger.info(f"Calling agent {agent_name} at {agent_url}")
        response = requests.post(
            f"{agent_url}/process",
            json=task_data,
            timeout=180
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Agent {agent_name} error: {response.status_code}")
            return {"error": f"Status {response.status_code}", "status": "failed"}
            
    except Exception as e:
        logger.error(f"Error calling agent {agent_name}: {e}")
        return {"error": str(e), "status": "failed"}


def execute_subtasks(
    subtasks: List[Dict], 
    tech_stack: TechStack,
    repo_context: Dict[str, Any],
    task_id: str
) -> List[Dict[str, Any]]:
    
    results = []
    agent_urls = {
        "code_reviewer": CODE_REVIEWER_URL,
        "documentation": DOCUMENTATION_URL,
        "design_assistant": DESIGN_ASSISTANT_URL
    }
    
    for subtask in subtasks:
        agent_name = subtask.get("assigned_agent", "")
        agent_url = agent_urls.get(agent_name)
        
        if not agent_url:
            logger.warning(f"Unknown agent: {agent_name}")
            continue
        
        # Формируем запрос для агента с полным контекстом
        agent_request = {
            "task": subtask.get("description", ""),
            "data": {
                "parent_task_id": task_id,
                "subtask_id": subtask.get("id"),
                "context": subtask.get("context", ""),
                "expected_output": subtask.get("expected_output", ""),
                "tech_stack": tech_stack.dict(),
                "repo_context": {
                    "structure": repo_context.get("structure", [])[:50],
                    "key_files": repo_context.get("key_files", {})
                }
            },
            "priority": subtask.get("priority", "medium")
        }
        
        # Специфичные данные для разных агентов
        if agent_name == "code_reviewer":
            agent_request["language"] = tech_stack.primary_language
            agent_request["code"] = json.dumps(repo_context.get("key_files", {}), indent=2)[:20000]
            
        elif agent_name == "documentation":
            agent_request["doc_type"] = "code"
            agent_request["data"]["existing_docs"] = repo_context.get("key_files", {}).get("README.md", "")
            
        elif agent_name == "design_assistant":
            agent_request["design_type"] = "architecture"
            agent_request["data"]["existing_structure"] = repo_context.get("structure", [])
        
        # Вызываем агента
        result = call_agent(agent_url, agent_name, agent_request)
        
        results.append({
            "subtask_id": subtask.get("id"),
            "agent": agent_name,
            "description": subtask.get("description"),
            "status": result.get("status", "completed"),
            "output": result
        })
    
    return results


def merge_agent_results(
    plan: Dict[str, Any], 
    agent_results: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    
    all_files = []
    
    # Файлы из плана
    for file in plan.get("files_to_create", []):
        all_files.append({
            "path": file.get("path"),
            "content": file.get("content"),
            "description": file.get("description"),
            "action": "create",
            "source": "project_manager"
        })
    
    for file in plan.get("files_to_update", []):
        all_files.append({
            "path": file.get("path"),
            "content": file.get("content"),
            "description": file.get("description"),
            "action": "update",
            "source": "project_manager"
        })
    
    # Файлы от агентов
    for result in agent_results:
        output = result.get("output", {})
        agent = result.get("agent", "unknown")
        
        # Documentation agent
        if agent == "documentation":
            doc = output.get("documentation", {})
            if doc.get("markdown"):
                all_files.append({
                    "path": "docs/README.md",
                    "content": doc.get("markdown"),
                    "description": "Auto-generated documentation",
                    "action": "create",
                    "source": "documentation_agent"
                })
        
        # Design assistant
        elif agent == "design_assistant":
            if output.get("plantuml_code"):
                all_files.append({
                    "path": "docs/diagrams/architecture.puml",
                    "content": output.get("plantuml_code"),
                    "description": "Architecture diagram",
                    "action": "create",
                    "source": "design_assistant"
                })
        
        # Code reviewer - добавляем отчёт
        elif agent == "code_reviewer":
            issues = output.get("issues", [])
            if issues:
                review_content = "# Code Review Report\n\n"
                review_content += f"Generated: {datetime.now().isoformat()}\n\n"
                
                for issue in issues:
                    severity = issue.get("severity", "info")
                    review_content += f"## [{severity.upper()}] {issue.get('type', 'Issue')}\n\n"
                    review_content += f"{issue.get('description', '')}\n\n"
                    if issue.get("suggestion"):
                        review_content += f"**Suggestion:** {issue.get('suggestion')}\n\n"
                    review_content += "---\n\n"
                
                all_files.append({
                    "path": "docs/code-review-report.md",
                    "content": review_content,
                    "description": "Code review findings",
                    "action": "create",
                    "source": "code_reviewer"
                })
    
    return all_files


def generate_summary(
    task: str, 
    tech_stack: TechStack, 
    files: List[Dict], 
    agent_results: List[Dict],
    branch: str
) -> str:    
    summary = f"""Задача выполнена!

Задача: {task[:150]}{'...' if len(task) > 150 else ''}

Стек проекта: {tech_stack.primary_language}
Фреймворки: {', '.join(tech_stack.frameworks[:3]) or 'не определены'}

Ветка: {branch}

Агентов задействовано: {len(agent_results)}
Файлов создано/обновлено: {len(files)}

Файлы:"""
    
    for f in files[:7]:
        action = f.get("action", "create")
        icon = "+" if action == "create" else "~"
        summary += f"\n  {icon} {f.get('path', 'unknown')}"
    
    if len(files) > 7:
        summary += f"\n  ... и ещё {len(files) - 7}"
    
    summary += "\n\nПроверьте Pull Request и выполните merge."
    
    return summary


@app.post("/workflow/process", response_model=WorkflowResponse)
async def process_workflow_task(request: WorkflowRequest):
    TASKS_PROCESSED.inc()
    
    task_id = str(uuid.uuid4())
    reasoning_logs[task_id] = []
    
    try:
        # 1. Начало обработки
        log_step(task_id, "start", f"Начало обработки: {request.task_description[:100]}")
        
        # 2. Получаем контекст репозитория
        repo_context = request.repo_context or {}
        log_step(task_id, "context_received", 
                 f"Получен контекст: {len(repo_context.get('structure', []))} файлов")
        
        # 3. Анализируем технологический стек
        log_step(task_id, "analyzing_stack", "Анализ технологического стека...")
        tech_stack = analyze_tech_stack(repo_context)
        log_step(task_id, "stack_analyzed", 
                 f"Стек: {tech_stack.primary_language}, frameworks: {tech_stack.frameworks}")
        
        # 4. Генерируем имя ветки
        branch_name = generate_branch_name(request.task_description, tech_stack)
        log_step(task_id, "branch_generated", f"Ветка: {branch_name}")
        
        # 5. Планируем задачу с учётом контекста
        log_step(task_id, "planning", "Планирование задачи...")
        plan = plan_task_with_context(
            request.task_description,
            tech_stack,
            repo_context
        )
        log_step(task_id, "plan_created", 
                 f"План: {len(plan.get('subtasks', []))} подзадач, "
                 f"{len(plan.get('files_to_create', []))} новых файлов")
        
        # 6. Выполняем подзадачи через агентов
        agent_results = []
        if plan.get("subtasks"):
            log_step(task_id, "executing_subtasks", "Выполнение подзадач агентами...")
            agent_results = execute_subtasks(
                plan["subtasks"],
                tech_stack,
                repo_context,
                task_id
            )
            log_step(task_id, "subtasks_completed", 
                     f"Выполнено: {len(agent_results)} подзадач")
        
        # 7. Объединяем результаты
        all_files = merge_agent_results(plan, agent_results)
        log_step(task_id, "files_merged", f"Итого файлов: {len(all_files)}")
        
        # 8. Генерируем резюме
        summary = generate_summary(
            request.task_description,
            tech_stack,
            all_files,
            agent_results,
            branch_name
        )
        
        log_step(task_id, "completed", "Обработка завершена успешно")
        
        # 9. Сохраняем и возвращаем результат
        return WorkflowResponse(
            task_id=task_id,
            status="completed",
            tech_stack=tech_stack,
            branch_name=branch_name,
            files_to_create=all_files,
            commit_message=plan.get("commit_message", f"feat: {request.task_description[:50]}"),
            pr_title=plan.get("pr_title", f"Feature: {request.task_description[:50]}"),
            pr_description=plan.get("pr_description", f"## Описание\n\n{request.task_description}"),
            summary=summary,
            agent_results=agent_results,
            reasoning_log=reasoning_logs[task_id]
        )
        
    except Exception as e:
        TASKS_FAILED.inc()
        logger.error(f"Error: {str(e)}")
        log_step(task_id, "error", f"Ошибка: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def log_step(task_id: str, step: str, message: str):
    if task_id not in reasoning_logs:
        reasoning_logs[task_id] = []
    
    reasoning_logs[task_id].append({
        "step": step,
        "timestamp": datetime.now().isoformat(),
        "message": message
    })
    logger.info(f"[{task_id[:8]}] {step}: {message}")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "project_manager", "version": "3.0.0"}


@app.get("/metrics")
async def metrics():
    return generate_latest()


@app.get("/")
async def root():
    return {
        "service": "Project Manager Agent",
        "version": "3.0.0",
        "description": "Coordinates development tasks with repository context awareness",
        "endpoints": {
            "workflow_process": "POST /workflow/process - Main n8n endpoint with repo context"
        }
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)