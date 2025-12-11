"""
Project Manager Agent - Координатор мультиагентной системы

Ответственности:
- Анализ технологического стека репозитория
- Планирование pipeline агентов
- Координация выполнения агентов
- Передача контекста между агентами
- Управление review loop (Code Writer ↔ Code Reviewer)
- Агрегация результатов
- Генерация метаданных для PR
- Анализ ошибок и retry с перепланированием
"""
import os
import json
import logging
import uuid
import re
import time
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from contextlib import asynccontextmanager
from enum import Enum
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import httpx
from prometheus_client import Counter, Histogram, Gauge, generate_latest

from logging_config import setup_logging

from models import (
    TaskState, AgentType, TaskPriority, FileAction,
    TechStack, FileToCreate, PipelineStep, Pipeline,
    ArchitectureResult, CodeResult, ReviewResult, ReviewIssue,
    DocumentationResult, TaskContext, AgentCallResult,
    WorkflowRequest, WorkflowResponse
)

# ============================================================================
# CONFIGURATION
# ============================================================================

logger = setup_logging("project_manager")

# URLs агентов
OPENROUTER_MCP_URL = os.getenv("OPENROUTER_MCP_URL", "http://openrouter-mcp:8000")
ARCHITECT_URL = os.getenv("ARCHITECT_URL", "http://architect:8000")
CODE_WRITER_URL = os.getenv("CODE_WRITER_URL", "http://code-writer:8000")
CODE_REVIEWER_URL = os.getenv("CODE_REVIEWER_URL", "http://code-reviewer:8000")
DOCUMENTATION_URL = os.getenv("DOCUMENTATION_URL", "http://documentation:8000")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL")

# Маппинг агентов на URLs
AGENT_URLS = {
    AgentType.ARCHITECT: ARCHITECT_URL,
    AgentType.CODE_WRITER: CODE_WRITER_URL,
    AgentType.CODE_REVIEWER: CODE_REVIEWER_URL,
    AgentType.DOCUMENTATION: DOCUMENTATION_URL,
}

# Timeouts
DEFAULT_TIMEOUT = 1000
LLM_TIMEOUT = 1000

# Retry configuration
MAX_PIPELINE_RETRIES = 1  # Максимум одна попытка retry после ошибки

# ============================================================================
# WORKFLOW STATUS ENUM
# ============================================================================

class WorkflowStatus(str, Enum):
    """Статусы выполнения workflow"""
    COMPLETED = "completed"  # Всё успешно
    PARTIAL = "partial"      # Частично выполнено (есть файлы, но были ошибки)
    FAILED = "failed"        # Полный провал (нет файлов или критическая ошибка)
    ERROR = "error"          # Системная ошибка (исключение)

# ============================================================================
# METRICS
# ============================================================================

TASKS_TOTAL = Counter('pm_tasks_total', 'Total tasks processed', ['status'])
AGENT_CALLS = Counter('pm_agent_calls_total', 'Agent calls', ['agent', 'status'])
REVIEW_ITERATIONS = Histogram('pm_review_iterations', 'Review iterations per task')
TASK_DURATION = Histogram('pm_task_duration_seconds', 'Task duration',
                          buckets=[30, 60, 120, 300, 600, 1200])
ACTIVE_TASKS = Gauge('pm_active_tasks', 'Currently processing tasks')
PIPELINE_RETRIES = Counter('pm_pipeline_retries_total', 'Pipeline retry attempts', ['success'])

# ============================================================================
# HTTP CLIENT
# ============================================================================

http_client: Optional[httpx.AsyncClient] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager для FastAPI"""
    global http_client
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(DEFAULT_TIMEOUT))
    logger.info("HTTP client initialized")
    yield
    await http_client.aclose()
    logger.info("HTTP client closed")

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Project Manager Agent",
    description="Координатор мультиагентной системы разработки",
    version="2.1.0",
    lifespan=lifespan
)

# ============================================================================
# LLM HELPER
# ============================================================================

async def call_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.2,
    step: str = "project_manager_llm_request"
) -> str:
    """Вызов LLM через OpenRouter MCP"""

    if not system_prompt:
        system_prompt = """Ты опытный технический лидер и архитектор ПО.
Анализируешь задачи, планируешь работу команды, координируешь разработку.
Всегда возвращаешь ответы в формате JSON когда это указано.
Принимаешь решения на основе анализа контекста и лучших практик."""

    # Подготовка сообщений для запроса
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    # Логирование начала запроса - только шаг
    logger.info(f"step: {step}")

    start_time = time.time()

    try:
        response = await http_client.post(
            f"{OPENROUTER_MCP_URL}/chat/completions",
            json={
                "model": DEFAULT_MODEL,
                "messages": messages,
                "temperature": temperature
            },
            timeout=LLM_TIMEOUT
        )

        duration = time.time() - start_time

        if response.status_code == 200:
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"]

            # Извлечение информации о токенах
            usage = response_data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)

            # Извлечение reasoning (если присутствует)
            reasoning = None
            if "reasoning" in response_data["choices"][0]["message"]:
                reasoning = response_data["choices"][0]["message"]["reasoning"]
            elif "reasoning_content" in response_data["choices"][0]["message"]:
                reasoning = response_data["choices"][0]["message"]["reasoning_content"]

            # Логирование успешного ответа
            response_log = {
                "event": "llm_request_success",
                "model": DEFAULT_MODEL,
                "duration_seconds": round(duration, 3),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "content": content,
                "reasoning": reasoning,
                "timestamp": datetime.now().isoformat()
            }
            logger.info(json.dumps(response_log, ensure_ascii=False))

            return content
        else:
            # Логирование ошибки
            error_log = {
                "event": "llm_request_error",
                "model": DEFAULT_MODEL,
                "duration_seconds": round(duration, 3),
                "status_code": response.status_code,
                "error_response": response.text,
                "timestamp": datetime.now().isoformat()
            }
            logger.error(json.dumps(error_log, ensure_ascii=False))
            return ""

    except Exception as e:
        duration = time.time() - start_time
        # Логирование исключения
        exception_log = {
            "event": "llm_request_exception",
            "model": DEFAULT_MODEL,
            "duration_seconds": round(duration, 3),
            "exception": str(e),
            "timestamp": datetime.now().isoformat()
        }
        logger.error(json.dumps(exception_log, ensure_ascii=False))
        return ""


def parse_json_response(response: str) -> Optional[Dict]:
    """Извлекает JSON из ответа LLM"""
    try:
        # Пробуем найти JSON в ответе
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
    return None

# ============================================================================
# ERROR ANALYSIS AND RETRY FUNCTIONS
# ============================================================================

async def analyze_error_with_llm(
    context: TaskContext,
    failed_step: PipelineStep,
    error_details: str
) -> str:
    """
    Анализирует ошибку через LLM и возвращает объяснение
    """
    
    # Собираем информацию о контексте
    executed_agents = []
    if context.architecture_result:
        executed_agents.append("architect (успешно)")
    if context.code_result:
        executed_agents.append(f"code_writer ({len(context.code_result.files)} файлов)")
    if context.review_result:
        executed_agents.append(f"code_reviewer (score: {context.review_result.quality_score})")
    
    prompt = f"""
Произошла ошибка при выполнении pipeline мультиагентной системы разработки.

ЗАДАЧА:
{context.task_description}

ТЕХНОЛОГИЧЕСКИЙ СТЕК:
- Язык: {context.tech_stack.primary_language if context.tech_stack else 'unknown'}
- Фреймворки: {', '.join(context.tech_stack.frameworks) if context.tech_stack else 'unknown'}
- Паттерны: {', '.join(context.tech_stack.architecture_patterns) if context.tech_stack else 'unknown'}

УПАВШИЙ ШАГ:
- Агент: {failed_step.agent.value}
- Действие: {failed_step.action}
- Описание: {failed_step.description}
- Зависимости от: {[a.value for a in failed_step.input_from]}

ДЕТАЛИ ОШИБКИ:
{error_details[:3000]}

КОНТЕКСТ ВЫПОЛНЕНИЯ:
- Текущий шаг: {context.current_step_index + 1}
- Выполненные агенты: {', '.join(executed_agents) if executed_agents else 'нет'}
- Итераций ревью: {context.review_iterations}

ПРЕДЫДУЩИЕ ОШИБКИ:
{json.dumps(context.errors[-5:], indent=2, ensure_ascii=False) if context.errors else 'нет'}

Проанализируй ошибку и объясни:
1. ЧТО ПРОИЗОШЛО: Конкретная причина ошибки
2. ПОЧЕМУ: Корневая причина проблемы
3. КАК ИСПРАВИТЬ: Конкретные шаги для решения
4. РЕКОМЕНДАЦИИ ДЛЯ PIPELINE: Какие изменения нужны в pipeline

Будь конкретен и практичен.
"""
    
    system_prompt = """Ты опытный DevOps инженер и архитектор систем.
Специализируешься на анализе ошибок в мультиагентных системах.
Даёшь чёткие, практичные рекомендации.
Понимаешь как работают LLM-агенты и их ограничения."""
    
    response = await call_llm(prompt, system_prompt, temperature=0.3, step="error_analysis")

    if response:
        context.log_step(
            "error_analysis",
            "LLM analysis completed",
            {"analysis_preview": response[:200]}
        )
        logger.info(f"[{context.task_id[:8]}] Error analysis completed")
        return response
    
    return "Не удалось проанализировать ошибку через LLM"


async def replan_pipeline_after_error(
    context: TaskContext,
    failed_step: PipelineStep,
    error_analysis: str
) -> Pipeline:
    """
    Перепланирует pipeline с учётом произошедшей ошибки
    """
    
    # Информация о уже выполненных шагах
    executed_steps_info = []
    if context.pipeline:
        for i, step in enumerate(context.pipeline.steps):
            if i < context.current_step_index:
                executed_steps_info.append({
                    "agent": step.agent.value,
                    "action": step.action,
                    "status": "completed"
                })
            elif i == context.current_step_index:
                executed_steps_info.append({
                    "agent": step.agent.value,
                    "action": step.action,
                    "status": "FAILED"
                })
    
    # Информация о доступных результатах
    available_results = {}
    if context.architecture_result:
        available_results["architecture"] = {
            "components": len(context.architecture_result.components),
            "patterns": context.architecture_result.patterns[:3]
        }
    if context.code_result and context.code_result.files:
        available_results["code"] = {
            "files_count": len(context.code_result.files),
            "files": [f.get("path", "unknown") for f in context.code_result.files[:5]]
        }
    if context.review_result:
        available_results["review"] = {
            "approved": context.review_result.approved,
            "score": context.review_result.quality_score,
            "issues_count": len(context.review_result.issues)
        }
    
    prompt = f"""
Pipeline выполнения упал. Нужно создать НОВЫЙ pipeline с учётом ошибки.

ЗАДАЧА:
{context.task_description}

ТЕХНОЛОГИЧЕСКИЙ СТЕК:
- Язык: {context.tech_stack.primary_language if context.tech_stack else 'unknown'}
- Фреймворки: {', '.join(context.tech_stack.frameworks) if context.tech_stack else 'unknown'}

ИСТОРИЯ ВЫПОЛНЕНИЯ:
{json.dumps(executed_steps_info, indent=2, ensure_ascii=False)}

ДОСТУПНЫЕ РЕЗУЛЬТАТЫ ОТ ПРЕДЫДУЩИХ АГЕНТОВ:
{json.dumps(available_results, indent=2, ensure_ascii=False)}

УПАВШИЙ ШАГ:
- Агент: {failed_step.agent.value}
- Действие: {failed_step.action}
- Описание: {failed_step.description}

АНАЛИЗ ОШИБКИ:
{error_analysis[:2500]}

ДОСТУПНЫЕ АГЕНТЫ:
- architect - Проектирование архитектуры (анализ, компоненты, интерфейсы)
- code_writer - Написание кода (создание файлов, реализация)
- code_reviewer - Проверка кода (баги, качество, безопасность)
- documentation - Документация (README, API docs)

ВАЖНЫЕ ПРАВИЛА ДЛЯ НОВОГО PIPELINE:
1. НЕ повторяй успешно выполненные шаги (используй их результаты)
2. Если упал code_writer - возможно нужно:
   - Упростить задачу
   - Добавить architect если его не было
   - Разбить на более мелкие шаги
3. Если упал architect - попробуй более простой подход
4. ОБЯЗАТЕЛЬНО включи code_writer и code_reviewer
5. Учитывай КОНКРЕТНУЮ причину ошибки из анализа

Верни JSON нового pipeline:
{{
    "pipeline": [
        {{
            "agent": "имя_агента",
            "action": "действие",
            "description": "описание с учётом ошибки и как её избежать",
            "input_from": ["зависимости"],
            "priority": "high"
        }}
    ],
    "reasoning": "Почему выбран такой pipeline и как он решает проблему",
    "error_mitigation": "Как новый pipeline избегает предыдущей ошибки"
}}
"""
    
    system_prompt = """Ты опытный технический лидер.
Умеешь адаптировать планы после неудач.
Создаёшь практичные и надёжные pipeline.
Всегда отвечаешь валидным JSON."""
    
    response = await call_llm(prompt, system_prompt, temperature=0.3, step="replan_pipeline")
    parsed = parse_json_response(response)
    
    if parsed and "pipeline" in parsed:
        steps = []
        for step_data in parsed["pipeline"]:
            try:
                agent_type = AgentType(step_data["agent"])
                input_from = [AgentType(a) for a in step_data.get("input_from", [])]
                priority = TaskPriority(step_data.get("priority", "high"))
                
                steps.append(PipelineStep(
                    agent=agent_type,
                    action=step_data.get("action", "process"),
                    description=step_data.get("description", ""),
                    input_from=input_from,
                    priority=priority
                ))
            except (ValueError, KeyError) as e:
                logger.warning(f"Error parsing replanned step: {e}")
                continue
        
        if steps:
            context.log_step(
                "replan_pipeline",
                f"Новый pipeline: {' -> '.join([s.agent.value for s in steps])}",
                {
                    "reasoning": parsed.get("reasoning", ""),
                    "error_mitigation": parsed.get("error_mitigation", "")
                }
            )
            
            logger.info(f"[{context.task_id[:8]}] Replanned pipeline with {len(steps)} steps")
            logger.info(f"Replanned pipeline: {steps}")
            
            return Pipeline(
                steps=steps,
                reasoning=parsed.get("reasoning", "Replanned after error"),
                estimated_time_seconds=len(steps) * 60
            )
    
    # Fallback: минимальный pipeline
    context.log_step(
        "replan_pipeline",
        "Используется fallback minimal pipeline"
    )
    
    logger.warning(f"[{context.task_id[:8]}] Using fallback pipeline")
    
    fallback_steps = []
    
    # Если нет архитектуры, добавляем architect
    if not context.architecture_result:
        fallback_steps.append(PipelineStep(
            agent=AgentType.ARCHITECT,
            action="design_architecture",
            description="Проектирование архитектуры (retry)",
            input_from=[],
            priority=TaskPriority.HIGH
        ))
    
    # Всегда добавляем code_writer
    fallback_steps.append(PipelineStep(
        agent=AgentType.CODE_WRITER,
        action="write_code",
        description="Написание кода (retry после ошибки)",
        input_from=[AgentType.ARCHITECT] if context.architecture_result or not context.architecture_result else [],
        priority=TaskPriority.HIGH
    ))
    
    # Всегда добавляем code_reviewer
    fallback_steps.append(PipelineStep(
        agent=AgentType.CODE_REVIEWER,
        action="review_code",
        description="Проверка кода",
        input_from=[AgentType.CODE_WRITER],
        priority=TaskPriority.HIGH
    ))
    
    return Pipeline(
        steps=fallback_steps,
        reasoning="Fallback pipeline after error analysis"
    )

# ============================================================================
# TECH STACK ANALYSIS
# ============================================================================

async def analyze_tech_stack(repo_context: Dict[str, Any]) -> TechStack:
    """
    Анализирует технологический стек репозитория
    """
    
    structure = repo_context.get("structure", [])
    key_files = repo_context.get("key_files", {})
    
    # Собираем статистику по расширениям файлов
    extensions = {}
    config_files = []
    
    for item in structure:
        path = item.get("path", "")
        if item.get("type") == "file" and "." in path:
            ext = path.rsplit(".", 1)[-1].lower()
            extensions[ext] = extensions.get(ext, 0) + 1
            
            # Конфигурационные файлы
            filename = path.split("/")[-1].lower()
            if filename in [
                "package.json", "requirements.txt", "pyproject.toml", "setup.py",
                "cargo.toml", "go.mod", "pom.xml", "build.gradle",
                "composer.json", "gemfile", "mix.exs",
                "dockerfile", "docker-compose.yml", "docker-compose.yaml",
                "tsconfig.json", "webpack.config.js", "vite.config.ts",
                ".eslintrc.js", ".prettierrc", "jest.config.js",
                "makefile", "cmakelists.txt"
            ]:
                config_files.append(path)
    
    prompt = f"""
Проанализируй технологический стек проекта.

Статистика файлов по расширениям:
{json.dumps(extensions, indent=2)}

Конфигурационные файлы:
{json.dumps(config_files, indent=2)}

Содержимое ключевых файлов:
{json.dumps(key_files, indent=2, ensure_ascii=False)[:12000]}

Определи технологии проекта и верни JSON:
{{
    "primary_language": "основной язык (Python/JavaScript/TypeScript/Go/etc)",
    "languages": ["все используемые языки"],
    "frameworks": ["фреймворки (FastAPI/React/Django/Express/etc)"],
    "databases": ["базы данных если есть"],
    "tools": ["инструменты (Docker/Kubernetes/etc)"],
    "package_managers": ["npm/pip/cargo/etc"],
    "testing_frameworks": ["pytest/jest/etc"],
    "ci_cd": ["GitHub Actions/GitLab CI/etc"],
    "architecture_patterns": ["microservices/monolith/MVC/etc"]
}}
"""
    
    response = await call_llm(prompt, step="tech_analysis")
    parsed = parse_json_response(response)
    
    if parsed:
        return TechStack(**parsed)
    
    # Fallback: определяем по расширениям
    lang_map = {
        "py": "Python", "js": "JavaScript", "ts": "TypeScript",
        "go": "Go", "rs": "Rust", "java": "Java", "rb": "Ruby",
        "php": "PHP", "cs": "C#", "cpp": "C++", "c": "C"
    }
    
    primary = "unknown"
    for ext, count in sorted(extensions.items(), key=lambda x: -x[1]):
        if ext in lang_map:
            primary = lang_map[ext]
            break
    
    return TechStack(primary_language=primary, languages=[primary] if primary != "unknown" else [])

# ============================================================================
# PIPELINE PLANNING
# ============================================================================

async def plan_pipeline(context: TaskContext) -> Pipeline:
    """
    Планирует pipeline выполнения на основе задачи
    Определяет какие агенты нужны и в каком порядке
    """

    prompt = f"""
    Проанализируй задачу и определи какие агенты нужны для её выполнения.

    ЗАДАЧА:
    {context.task_description}

    ТЕХНОЛОГИЧЕСКИЙ СТЕК:
    - Язык: {context.tech_stack.primary_language if context.tech_stack else 'unknown'}
    - Фреймворки: {', '.join(context.tech_stack.frameworks) if context.tech_stack else 'unknown'}
    - Паттерны: {', '.join(context.tech_stack.architecture_patterns) if context.tech_stack else 'unknown'}

    СТРУКТУРА РЕПОЗИТОРИЯ:
    - {len(context.repo_context.get('structure', []))} файлов
    - Ключевые файлы: {list(context.repo_context.get('key_files', {}).keys())[:20]}

    ДОСТУПНЫЕ АГЕНТЫ:

    1. architect - Проектирование архитектуры
       - Анализирует существующую архитектуру
       - Проектирует новые компоненты
       - Определяет интерфейсы
       - Создаёт диаграммы
       НУЖЕН если: новая фича, рефакторинг, изменение структуры

    2. code_writer - Написание кода
       - Пишет код по архитектуре
       - Следует стилю проекта
       - Добавляет типизацию и docstrings
       НУЖЕН для: любых изменений кода

    3. code_reviewer - Проверка кода
       - Находит баги и уязвимости
       - Проверяет соответствие архитектуре
       - Может вернуть код на доработку
       НУЖЕН: всегда после code_writer

    4. documentation - Документация
       - Создаёт документацию
       - Обновляет README
       - Создаёт API документацию
       - Пишет CHANGELOG
       НУЖЕН: после финализации кода

    ПРАВИЛА PIPELINE:
    - architect -> code_writer (если нужна архитектура)
    - code_writer -> code_reviewer (всегда)
    - code_reviewer может вернуть на code_writer (review loop)
    - documentation идёт последним

    ВАЖНО:
    - ВСЕГДА НУЖНО СОЗДАТЬ КАК МИНИМУМ ОДИН ФАЙЛ!

    Верни JSON:
    {{
        "pipeline": [
            {{
                "agent": "architect",
                "action": "design_architecture",
                "description": "Проектирование архитектуры JWT аутентификации",
                "input_from": [],
                "priority": "high"
            }},
            {{
                "agent": "code_writer",
                "action": "write_code",
                "description": "Написание кода аутентификации",
                "input_from": ["architect"],
                "priority": "high"
            }},
            {{
                "agent": "code_reviewer",
                "action": "review_code",
                "description": "Проверка кода",
                "input_from": ["code_writer", "architect"],
                "priority": "high"
            }},
            {{
                "agent": "documentation",
                "action": "write_docs",
                "description": "Создание документации",
                "input_from": ["code_writer", "code_reviewer", "architect"],
                "priority": "medium"
            }}
        ],
        "reasoning": "Объяснение почему выбран такой pipeline",
        "skip_agents": ["список агентов которые не нужны и почему"]
    }}
    """
    
    response = await call_llm(prompt, step="plan_pipeline")
    parsed = parse_json_response(response)
    
    if parsed and "pipeline" in parsed:
        steps = []
        for i, step_data in enumerate(parsed["pipeline"]):
            try:
                agent_type = AgentType(step_data["agent"])
                input_from = [AgentType(a) for a in step_data.get("input_from", [])]
                priority = TaskPriority(step_data.get("priority", "medium"))
                
                steps.append(PipelineStep(
                    agent=agent_type,
                    action=step_data.get("action", "process"),
                    description=step_data.get("description", ""),
                    input_from=input_from,
                    priority=priority
                ))
            except (ValueError, KeyError) as e:
                logger.warning(f"Error parsing pipeline step: {e}")
                continue

        logger.info(f"Generated pipeline: {steps}")
        
        return Pipeline(
            steps=steps,
            reasoning=parsed.get("reasoning", ""),
            estimated_time_seconds=len(steps) * 60  # ~1 min per step
        )
    
    # Default pipeline
    return Pipeline(
        steps=[
            PipelineStep(
                agent=AgentType.ARCHITECT,
                action="design_architecture",
                description="Проектирование архитектуры",
                input_from=[],
                priority=TaskPriority.HIGH
            ),
            PipelineStep(
                agent=AgentType.CODE_WRITER,
                action="write_code",
                description="Написание кода",
                input_from=[AgentType.ARCHITECT],
                priority=TaskPriority.HIGH
            ),
            PipelineStep(
                agent=AgentType.CODE_REVIEWER,
                action="review_code",
                description="Проверка кода",
                input_from=[AgentType.CODE_WRITER, AgentType.ARCHITECT],
                priority=TaskPriority.HIGH
            ),
            PipelineStep(
                agent=AgentType.DOCUMENTATION,
                action="write_docs",
                description="Создание документации",
                input_from=[AgentType.CODE_WRITER, AgentType.CODE_REVIEWER, AgentType.ARCHITECT],
                priority=TaskPriority.MEDIUM
            )
        ],
        reasoning="Default pipeline for code generation task"
    )

# ============================================================================
# AGENT COMMUNICATION
# ============================================================================

def build_agent_request(
    step: PipelineStep,
    context: TaskContext
) -> Dict[str, Any]:
    """
    Собирает запрос для агента с учётом результатов предыдущих агентов
    ИСПРАВЛЕНО: Правильные форматы данных для каждого агента
    """

    # Базовые данные
    request = {
        "task": context.task_description,
        "action": step.action,
        "data": {
            "task_id": context.task_id,
            "tech_stack": context.tech_stack.dict() if context.tech_stack else {},
            "repo_context": {
                "structure": context.repo_context.get("structure", [])[:100],
                "key_files": context.repo_context.get("key_files", {})
            }
        },
        "priority": step.priority.value
    }

    # Добавляем результаты от указанных агентов
    for source_agent in step.input_from:
        if source_agent == AgentType.ARCHITECT and context.architecture_result and step.agent != AgentType.ARCHITECT:
            # Architect -> передаём dict структуру (стандартизировано)
            request["data"]["architecture"] = {
                "components": [c.dict() if hasattr(c, 'dict') else c for c in context.architecture_result.components],
                "patterns": context.architecture_result.patterns,
                "file_structure": [f.dict() if hasattr(f, 'dict') else f for f in context.architecture_result.file_structure],
                "interfaces": [i.dict() if hasattr(i, 'dict') else i for i in context.architecture_result.interfaces],
                "dependencies": context.architecture_result.dependencies,
                "integration_points": [ip.dict() if hasattr(ip, 'dict') else ip for ip in context.architecture_result.integration_points],
                "diagrams": context.architecture_result.diagrams,
                "recommendations": context.architecture_result.recommendations
            }

        elif source_agent == AgentType.CODE_WRITER and context.code_result:
            # Code Writer -> передаём files в правильном формате
            request["data"]["code"] = {
                "files": context.code_result.files,
                "implementation_notes": context.code_result.implementation_notes
            }

        elif source_agent == AgentType.CODE_REVIEWER and context.review_result:
            # Code Reviewer -> передаём результат ревью
            request["data"]["review"] = {
                "approved": context.review_result.approved,
                "needs_revision": context.review_result.needs_revision,
                "quality_score": context.review_result.quality_score,
                "issues": [i.dict() for i in context.review_result.issues],
                "suggestions": context.review_result.suggestions,
                "summary": context.review_result.summary
            }

    # Специфичные данные для revise_code
    if step.agent == AgentType.CODE_WRITER and step.action == "revise_code":
        if context.review_result:
            request["data"]["review_comments"] = [i.dict() for i in context.review_result.issues]
            request["data"]["suggestions"] = context.review_result.suggestions
        if context.code_result:
            request["data"]["original_code"] = {
                "files": context.code_result.files
            }

    return request


async def call_agent(
    agent: AgentType,
    request: Dict[str, Any],
    timeout: int = DEFAULT_TIMEOUT
) -> AgentCallResult:
    """
    Вызывает агента и возвращает результат
    """
    
    url = AGENT_URLS.get(agent)
    if not url:
        return AgentCallResult(
            agent=agent,
            status="error",
            duration_seconds=0,
            error=f"Unknown agent: {agent}"
        )
    
    start_time = time.time()
    
    try:
        logger.info(f"Calling {agent.value} at {url}/process")
        
        response = await http_client.post(
            f"{url}/process",
            json=request,
            timeout=timeout
        )
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            AGENT_CALLS.labels(agent=agent.value, status="success").inc()
            
            return AgentCallResult(
                agent=agent,
                status="success",
                duration_seconds=duration,
                result=result
            )
        else:
            error_msg = f"HTTP {response.status_code}: {response.text[:500]}"
            AGENT_CALLS.labels(agent=agent.value, status="error").inc()
            
            return AgentCallResult(
                agent=agent,
                status="error",
                duration_seconds=duration,
                error=error_msg
            )
            
    except httpx.TimeoutException:
        duration = time.time() - start_time
        AGENT_CALLS.labels(agent=agent.value, status="timeout").inc()
        
        return AgentCallResult(
            agent=agent,
            status="timeout",
            duration_seconds=duration,
            error=f"Timeout after {timeout}s"
        )
        
    except Exception as e:
        duration = time.time() - start_time
        AGENT_CALLS.labels(agent=agent.value, status="error").inc()
        
        return AgentCallResult(
            agent=agent,
            status="error",
            duration_seconds=duration,
            error=str(e)
        )


def update_context_with_result(
    context: TaskContext,
    agent: AgentType,
    result: Dict[str, Any]
) -> TaskContext:
    """
    Обновляет контекст результатом от агента
    ИСПРАВЛЕНО: Корректный парсинг ответов от каждого агента
    """
    
    if agent == AgentType.ARCHITECT:
        # Architect возвращает плоскую структуру
        context.architecture_result = ArchitectureResult(
            components=result.get("components", []),
            patterns=result.get("patterns", []),
            file_structure=result.get("file_structure", []),
            interfaces=result.get("interfaces", []),
            dependencies=result.get("dependencies", []),
            integration_points=result.get("integration_points", []),
            diagrams=result.get("diagrams", {}),
            recommendations=result.get("recommendations", [])
        )
        
    if agent == AgentType.CODE_WRITER:
        files = result.get("files", [])
        processed_files = []
        for f in files:
            if isinstance(f, dict):
                processed_files.append(f)
            elif hasattr(f, 'dict'):  # Pydantic объект
                processed_files.append(f.dict())
            else:
                logger.warning(f"Unknown file format: {type(f)}")
        
        context.code_result = CodeResult(
            files=processed_files,
            implementation_notes=result.get("implementation_notes", []),
            changes_made=result.get("changes_made", []),
            addressed_issues=result.get("addressed_issues", []),
            unaddressed_issues=result.get("unaddressed_issues", [])
        )
        
    elif agent == AgentType.CODE_REVIEWER:
        # Code Reviewer возвращает result с вложенной структурой
        review_data = result.get("result", result)
        
        issues = []
        for i in review_data.get("issues", []):
            issues.append(ReviewIssue(
                id=i.get("id", str(uuid.uuid4())[:8]),
                type=i.get("type", "unknown"),
                severity=i.get("severity", "medium"),
                title=i.get("title", ""),
                description=i.get("description", ""),
                file_path=i.get("file_path"),
                line_number=i.get("line_number"),
                suggestion=i.get("suggestion"),
                code_snippet=i.get("code_snippet")
            ))
        
        context.review_result = ReviewResult(
            approved=review_data.get("approved", False),
            needs_revision=review_data.get("needs_revision", True),
            quality_score=review_data.get("quality_score", 0),
            issues=issues,
            suggestions=review_data.get("suggestions", []),
            summary=review_data.get("summary", ""),
            metrics=review_data.get("metrics", {}),
            blocking_issues=review_data.get("blocking_issues", [])
        )
        
    elif agent == AgentType.DOCUMENTATION:
        # Documentation возвращает files
        files_raw = result.get("files", [])
        
        files = []
        for f in files_raw:
            if f:  # Пропускаем None
                if hasattr(f, 'dict'):
                    files.append(f.dict())
                elif isinstance(f, dict):
                    files.append(f)
        
        context.documentation_result = DocumentationResult(
            files=files,
            sections_created=result.get("sections_created", [])
        )
    
    return context

# ============================================================================
# REVIEW LOOP
# ============================================================================

async def handle_review_loop(context: TaskContext) -> TaskContext:
    """
    Обрабатывает цикл ревью: Code Writer <-> Code Reviewer
    Максимум max_review_iterations итераций
    """
    
    while (context.review_result and
           context.review_result.needs_revision and
           context.review_iterations < context.max_review_iterations):
        
        context.review_iterations += 1
        context.current_state = TaskState.REVISION
        
        context.log_step(
            "review_loop",
            f"Iteration {context.review_iterations}: sending code back to Code Writer",
            {
                "issues_count": len(context.review_result.issues),
                "critical": len(context.review_result.critical_issues),
                "high": len(context.review_result.high_issues)
            }
        )
        
        # Сохраняем историю ревизий
        context.revision_history.append({
            "iteration": context.review_iterations,
            "issues": [i.dict() for i in context.review_result.issues],
            "quality_score": context.review_result.quality_score
        })
        
        # Отправляем на доработку Code Writer'у
        revision_step = PipelineStep(
            agent=AgentType.CODE_WRITER,
            action="revise_code",
            description=f"Revision iteration {context.review_iterations}",
            input_from=[AgentType.CODE_REVIEWER, AgentType.ARCHITECT]
        )
        
        revision_request = build_agent_request(revision_step, context)
        revision_result = await call_agent(AgentType.CODE_WRITER, revision_request)
        
        if revision_result.status != "success":
            context.log_error(
                "review_loop",
                f"Code Writer revision failed: {revision_result.error}"
            )
            break
        
        # Обновляем контекст новым кодом
        context = update_context_with_result(
            context, 
            AgentType.CODE_WRITER, 
            revision_result.result
        )
        
        # Повторное ревью
        context.current_state = TaskState.REVIEWING
        
        review_step = PipelineStep(
            agent=AgentType.CODE_REVIEWER,
            action="review_code",
            description=f"Review after revision {context.review_iterations}",
            input_from=[AgentType.CODE_WRITER, AgentType.ARCHITECT]
        )
        
        review_request = build_agent_request(review_step, context)
        review_result = await call_agent(AgentType.CODE_REVIEWER, review_request)
        
        if review_result.status != "success":
            context.log_error(
                "review_loop",
                f"Code Reviewer failed: {review_result.error}"
            )
            break
        
        # Обновляем контекст результатом ревью
        context = update_context_with_result(
            context,
            AgentType.CODE_REVIEWER,
            review_result.result
        )
        
        context.log_step(
            "review_loop",
            f"Iteration {context.review_iterations} complete",
            {
                "approved": context.review_result.approved,
                "quality_score": context.review_result.quality_score
            }
        )
    
    REVIEW_ITERATIONS.observe(context.review_iterations)
    
    return context

# ============================================================================
# PIPELINE EXECUTION
# ============================================================================

async def execute_pipeline(
    context: TaskContext,
    is_retry: bool = False
) -> Tuple[TaskContext, bool, Optional[PipelineStep], Optional[str]]:
    """
    Выполняет pipeline с проверкой критических ошибок
    
    Returns:
        Tuple[TaskContext, bool, Optional[PipelineStep], Optional[str]]:
            (обновленный контекст, успешность, упавший шаг, детали ошибки)
    """
    
    if not context.pipeline:
        context.log_error("execute_pipeline", "No pipeline defined")
        context.current_state = TaskState.FAILED
        return context, False, None, "No pipeline defined"
    
    executed_steps = []
    critical_failure = False
    successful_steps = 0
    failed_steps = 0
    failed_step: Optional[PipelineStep] = None
    error_details: Optional[str] = None
    
    retry_prefix = "[RETRY] " if is_retry else ""
    
    for i, step in enumerate(context.pipeline.steps):
        context.current_step_index = i
        context.log_step(
            "execute_step",
            f"{retry_prefix}Starting step {i+1}/{len(context.pipeline.steps)}: {step.agent.value}.{step.action}",
            {"description": step.description}
        )
        
        # Обновляем состояние
        state_map = {
            AgentType.ARCHITECT: TaskState.ARCHITECTURE,
            AgentType.CODE_WRITER: TaskState.CODING,
            AgentType.CODE_REVIEWER: TaskState.REVIEWING,
            AgentType.DOCUMENTATION: TaskState.DOCUMENTING
        }
        context.current_state = state_map.get(step.agent, TaskState.PENDING)
        
        # Собираем запрос
        request = build_agent_request(step, context)
        
        # Вызываем агента
        result = await call_agent(step.agent, request, step.timeout_seconds)
        
        executed_steps.append({
            "step": i + 1,
            "agent": step.agent.value,
            "action": step.action,
            "status": result.status,
            "duration": result.duration_seconds,
            "error": result.error
        })
        
        if result.status != "success":
            # Пробуем retry
            if step.retry_count < step.max_retries:
                step.retry_count += 1
                context.log_step("retry", f"Retrying {step.agent.value} (attempt {step.retry_count})")
                result = await call_agent(step.agent, request, step.timeout_seconds)
                executed_steps[-1]["status"] = result.status
                executed_steps[-1]["error"] = result.error
            
            if result.status != "success":
                failed_steps += 1
                failed_step = step
                error_details = result.error
                
                context.log_error(
                    "execute_step",
                    f"Step failed: {step.agent.value}",
                    {"error": result.error}
                )
                
                # КРИТИЧЕСКАЯ ПРОВЕРКА: Code Writer должен создать файлы (только если он в pipeline)
                if step.agent == AgentType.CODE_WRITER:
                    critical_failure = True
                    context.log_error(
                        "critical_failure",
                        "Code Writer failed to generate code - stopping pipeline"
                    )
                    break
                
                continue
        
        # Обновляем контекст результатом
        context = update_context_with_result(context, step.agent, result.result)
        
        # КРИТИЧЕСКАЯ ПРОВЕРКА: Code Writer вернул 0 файлов
        if step.agent == AgentType.CODE_WRITER:
            if not context.code_result or not context.code_result.files:
                critical_failure = True
                failed_step = step
                error_details = "Code Writer returned 0 files"
                context.log_error(
                    "critical_failure",
                    "Code Writer returned 0 files - stopping pipeline",
                    {"implementation_notes": context.code_result.implementation_notes if context.code_result else []}
                )
                break
            else:
                context.log_step(
                    "execute_step",
                    f"Code Writer created {len(context.code_result.files)} files"
                )
        
        successful_steps += 1
        context.log_step(
            "execute_step",
            f"Step completed: {step.agent.value}",
            {"duration": result.duration_seconds}
        )
        
        # После Code Reviewer проверяем нужен ли review loop (только если есть Code Writer в pipeline)
        if step.agent == AgentType.CODE_REVIEWER:
            has_code_writer = any(s.agent == AgentType.CODE_WRITER for s in context.pipeline.steps)
            if has_code_writer and context.review_result and context.review_result.needs_revision:
                context = await handle_review_loop(context)
    
    # Определяем итоговый статус
    if critical_failure:
        context.current_state = TaskState.FAILED
        context.log_step("execute_pipeline", f"{retry_prefix}Pipeline FAILED due to critical error")
        return context, False, failed_step, error_details
    elif failed_steps > 0:
        # Есть ошибки, но не критические
        if successful_steps > 0:
            context.current_state = TaskState.COMPLETED  # Частично выполнено
            context.log_step(
                "execute_pipeline",
                f"{retry_prefix}Pipeline completed with errors: {successful_steps} succeeded, {failed_steps} failed"
            )
            return context, True, failed_step, error_details  # Частичный успех
        else:
            context.current_state = TaskState.FAILED
            context.log_step("execute_pipeline", f"{retry_prefix}Pipeline FAILED - all steps failed")
            return context, False, failed_step, error_details
    else:
        context.log_step("execute_pipeline", f"{retry_prefix}Pipeline completed successfully. Steps executed: {len(executed_steps)}")
        return context, True, None, None

# ============================================================================
# STATUS DETERMINATION
# ============================================================================

def determine_workflow_status(
    context: TaskContext,
    pipeline_success: bool,
    has_files: bool
) -> WorkflowStatus:
    """
    Определяет финальный статус workflow на основе результатов
    
    Args:
        context: Контекст задачи
        pipeline_success: Успешность выполнения pipeline
        has_files: Есть ли сгенерированные файлы
    
    Returns:
        WorkflowStatus: Статус выполнения
    """
    
    # Критерий 1: Если state = FAILED, то failed
    if context.current_state == TaskState.FAILED:
        return WorkflowStatus.FAILED
    
    # Критерий 2: Если нет файлов вообще - failed
    if not has_files:
        context.log_error("workflow_status", "No files generated")
        return WorkflowStatus.FAILED
    
    # Критерий 3: Если есть критические ошибки - failed
    has_critical_errors = any(
        "critical" in str(e).lower() or "critical_failure" in str(e.get("step", "")).lower()
        for e in context.errors
    )
    if has_critical_errors:
        return WorkflowStatus.FAILED
    
    # Критерий 4: Если pipeline не успешен, но есть файлы - partial
    if not pipeline_success and has_files:
        return WorkflowStatus.PARTIAL
    
    # Критерий 5: Если есть ошибки, но pipeline успешен - partial
    if context.errors and has_files:
        return WorkflowStatus.PARTIAL
    
    # Критерий 6: Если ревью не прошло - partial
    if context.review_result and not context.review_result.approved:
        # Но если есть файлы, всё равно partial, а не failed
        if has_files:
            return WorkflowStatus.PARTIAL
        return WorkflowStatus.FAILED
    
    # Всё хорошо
    return WorkflowStatus.COMPLETED

# ============================================================================
# METADATA GENERATION
# ============================================================================

async def generate_branch_name(context: TaskContext) -> str:
    """Генерирует имя ветки"""
    
    prompt = f"""
Создай имя git ветки для задачи.

Задача: {context.task_description[:200]}
Стек: {context.tech_stack.primary_language if context.tech_stack else 'unknown'}

Требования:
- Только латинские буквы, цифры и дефисы
- Максимум 50 символов
- Формат: feature/краткое-описание или fix/краткое-описание

Верни только имя ветки без кавычек и объяснений.
"""
    
    response = await call_llm(prompt, temperature=0.1, step="branch_generation")
    branch = re.sub(r'[^a-zA-Z0-9-/]', '-', response.strip()[:50])
    branch = re.sub(r'-+', '-', branch).strip('-')
    
    if not branch or len(branch) < 5:
        import uuid
        branch = f"feature/task-{uuid.uuid4().hex[:8]}"
    
    return branch


async def generate_commit_message(context: TaskContext) -> str:
    """Генерирует commit message"""
    
    files_info = []
    all_files = context.get_all_files()
    for f in all_files[:10]:
        files_info.append(f"{f.action.value}: {f.path}")
    
    prompt = f"""
Создай commit message для изменений.

Задача: {context.task_description[:200]}

Файлы:
{chr(10).join(files_info)}

Формат: type(scope): description

Типы: feat, fix, docs, refactor, test, chore

Верни только commit message без кавычек.
"""
    
    response = await call_llm(prompt, temperature=0.1, step="commit_message_generation")
    message = response.strip().strip('"').strip("'")
    
    if not message or len(message) < 10:
        message = f"feat: implement {context.task_description[:40]}"
    
    return message[:72]  # Git рекомендует до 72 символов


async def generate_pr_metadata(context: TaskContext) -> Tuple[str, str]:
    """Генерирует заголовок и описание PR"""
    
    # Собираем информацию о результатах
    files_created = len([f for f in context.get_all_files() if f.action == FileAction.CREATE])
    files_updated = len([f for f in context.get_all_files() if f.action == FileAction.UPDATE])
    
    arch_summary = ""
    if context.architecture_result:
        arch_summary = f"""
### Архитектура
- Компонентов: {len(context.architecture_result.components)}
- Паттерны: {', '.join(context.architecture_result.patterns[:5])}
"""
    
    review_summary = ""
    if context.review_result:
        review_summary = f"""
### Результат ревью
- Качество кода: {context.review_result.quality_score}/10
- Итераций ревью: {context.review_iterations}
- Статус: {'Approved' if context.review_result.approved else 'Needs attention'}
"""
    
    prompt = f"""
Создай заголовок и описание Pull Request.

Задача:
{context.task_description} (измени так, чтобы выглядело красиво и логично)

Статистика:
- Файлов создано: {files_created}
- Файлов обновлено: {files_updated}
- Итераций ревью: {context.review_iterations}

Файлы:
{chr(10).join([f.path for f in context.get_all_files()[:50]])}

Верни JSON:
{{
    "title": "Краткий заголовок (до 72 символов)",
    "description": "Полное описание в Markdown с секциями: Описание, Изменения, Тестирование"
}}
"""
    
    response = await call_llm(prompt, step="pr_metadata_generation")
    parsed = parse_json_response(response)
    
    if parsed:
        title = parsed.get("title", f"Feature: {context.task_description[:50]}")
        description = parsed.get("description", "")
    else:
        title = f"Feature: {context.task_description[:50]}"
        description = f"## Описание\n\n{context.task_description}"
    
    # Добавляем автоматические секции
    description += f"""

---
## Автоматически сгенерировано

- Task ID: `{context.task_id}`
- Технологии: {context.tech_stack.primary_language if context.tech_stack else 'N/A'}
- Файлов: {files_created} создано, {files_updated} обновлено
{arch_summary}
{review_summary}

### Pipeline выполнения
"""
    
    for log in context.reasoning_log[-100:]:
        description += f"- {log['step']}: {log['message']}\n"
    
    return title, description


async def generate_summary(context: TaskContext, status: WorkflowStatus, total_duration_seconds: float) -> str:
    """Генерирует краткое резюме для Telegram"""
    
    all_files = context.get_all_files()
    
    # Эмодзи в зависимости от статуса
    status_emoji_map = {
        WorkflowStatus.COMPLETED: "✅",
        WorkflowStatus.PARTIAL: "⚠️",
        WorkflowStatus.FAILED: "❌",
        WorkflowStatus.ERROR: "💥"
    }
    status_emoji = status_emoji_map.get(status, "❓")
    
    status_text_map = {
        WorkflowStatus.COMPLETED: "Задача выполнена!",
        WorkflowStatus.PARTIAL: "Задача выполнена частично",
        WorkflowStatus.FAILED: "Задача не выполнена",
        WorkflowStatus.ERROR: "Ошибка выполнения"
    }
    status_text = status_text_map.get(status, "Неизвестный статус")
    
    summary = f"""{status_emoji} {status_text}

{context.task_description[:100]}{'...' if len(context.task_description) > 100 else ''}

Стек: {context.tech_stack.primary_language if context.tech_stack else 'N/A'}
Фреймворки: {', '.join((context.tech_stack.frameworks or [])[:3]) if context.tech_stack else 'N/A'}

Ветка: {context.branch_name or 'N/A'}
Файлов: {len(all_files)}
Ревью итераций: {context.review_iterations}
"""
    
    if context.review_result:
        summary += f"Качество кода: {context.review_result.quality_score}/10\n"

    if total_duration_seconds > 0:
        minutes = int(total_duration_seconds // 60)
        seconds = int(total_duration_seconds % 60)
        if minutes > 0:
            summary += f"Время выполнения: {minutes} мин {seconds} сек\n"
        else:
            summary += f"Время выполнения: {seconds} сек\n"
    
    # Показываем ошибки если есть
    if context.errors:
        summary += f"\nОшибок: {len(context.errors)}\n"
        for err in context.errors[:50]:
            summary += f"  - {err.get('step', 'unknown')}: {err.get('error', 'unknown error')[:100]}\n"
    
    if all_files:
        summary += "\nФайлы:"
        for f in all_files[:5]:
            icon = "+" if f.action == FileAction.CREATE else "~"
            summary += f"\n  {icon} {f.path}"
        
        if len(all_files) > 5:
            summary += f"\n  ... и ещё {len(all_files) - 5}"
    else:
        summary += "\nФайлов не создано"
    
    return summary

# ============================================================================
# MAIN WORKFLOW ENDPOINT
# ============================================================================

@app.post("/workflow/process", response_model=WorkflowResponse)
async def process_workflow(request: WorkflowRequest):
    """
    Основной endpoint для обработки задачи
    Координирует работу всех агентов
    С поддержкой retry при ошибках
    """
    
    start_time = time.time()
    ACTIVE_TASKS.inc()
    
    # Инициализация контекста - выносим наружу для доступа в except
    context = None
    pipeline_success = False
    pipeline_retry_count = 0
    
    try:
        # 1. Инициализация контекста
        context = TaskContext(
            task_description=request.task_description,
            repo_owner=request.repo_owner,
            repo_name=request.repo_name,
            base_branch=request.base_branch,
            repo_context=request.repo_context or {},
            max_review_iterations=request.max_review_iterations
        )
        
        context.current_state = TaskState.PLANNING
        context.log_step("init", f"Task received: {request.task_description[:100]}")
        
        logger.info(f"[{context.task_id[:8]}] Starting workflow")
        
        # 2. Анализ технологического стека
        context.log_step("analyze_stack", "Analyzing tech stack...")
        try:
            context.tech_stack = await analyze_tech_stack(context.repo_context)
            context.log_step(
                "analyze_stack",
                f"Stack: {context.tech_stack.primary_language}, "
                f"frameworks: {context.tech_stack.frameworks}"
            )
        except Exception as e:
            context.log_error("analyze_stack", f"Failed to analyze tech stack: {e}")
            # Продолжаем с дефолтным стеком
            context.tech_stack = TechStack(primary_language="unknown")
        
        # 3. Планирование pipeline
        context.log_step("plan_pipeline", "Planning execution pipeline...")
        try:
            context.pipeline = await plan_pipeline(context)
            context.log_step(
                "plan_pipeline",
                f"Pipeline: {' -> '.join([s.agent.value for s in context.pipeline.steps])}",
                {"reasoning": context.pipeline.reasoning}
            )
        except Exception as e:
            context.log_error("plan_pipeline", f"Failed to plan pipeline: {e}")
            raise  # Без pipeline продолжать нельзя
        
        # 4. Генерация имени ветки
        try:
            context.branch_name = await generate_branch_name(context)
            context.log_step("generate_branch", f"Branch: {context.branch_name}")
        except Exception as e:
            context.log_error("generate_branch", f"Failed to generate branch name: {e}")
            context.branch_name = f"feature/task-{context.task_id[:8]}"
        
        # 5. Выполнение pipeline с возможностью retry
        context.log_step("execute_pipeline", "Starting pipeline execution...")
        context, pipeline_success, failed_step, error_details = await execute_pipeline(context)
        
        # 5.1. Проверка наличия файлов после выполнения pipeline
        all_files = context.get_all_files()
        has_files = len(all_files) > 0
        
        # Если pipeline успешен, но файлов нет - это ошибка
        if pipeline_success and not has_files:
            pipeline_success = False
            failed_step = context.pipeline.steps[-1] if context.pipeline and context.pipeline.steps else None
            error_details = "Pipeline completed successfully but no files were generated. This is considered a fatal error."
            context.log_error("no_files", error_details)
        
        # 6. RETRY LOGIC: Если pipeline упал ИЛИ нет файлов, пробуем перепланировать
        while not pipeline_success and pipeline_retry_count < MAX_PIPELINE_RETRIES:
            pipeline_retry_count += 1
            PIPELINE_RETRIES.labels(success="attempt").inc()
            
            context.log_step(
                "retry_pipeline",
                f"Pipeline failed or no files generated, attempting retry {pipeline_retry_count}/{MAX_PIPELINE_RETRIES}",
                {
                    "failed_agent": failed_step.agent.value if failed_step else "unknown",
                    "error": error_details[:200] if error_details else "unknown",
                    "has_files": has_files
                }
            )

            logger.info(f"[{context.task_id[:8]}] Pipeline failed or no files generated, attempting retry {pipeline_retry_count}/{MAX_PIPELINE_RETRIES}")
            logger.info(f"Failed agent: {failed_step.agent.value if failed_step else 'unknown'}, error details: {error_details[:200] if error_details else 'unknown'}")
            
            # 6.1. Анализируем ошибку через LLM
            context.log_step("error_analysis", "Analyzing error with LLM...")
            
            # Формируем сообщение об ошибке для анализа
            error_message = ""
            if error_details:
                error_message = error_details
            elif not has_files:
                error_message = "Pipeline completed but no files were generated. This indicates the agents did not produce any output files."
            
            error_analysis = await analyze_error_with_llm(
                context,
                failed_step,
                error_message or "Unknown error"
            )
            
            context.log_step(
                "error_analysis",
                "Error analysis completed",
                {"analysis_preview": error_analysis[:300]}
            )
            
            # 6.2. Перепланируем pipeline с учётом ошибки
            context.log_step("replan_pipeline", "Replanning pipeline based on error analysis...")
            new_pipeline = await replan_pipeline_after_error(
                context,
                failed_step,
                error_analysis
            )
            
            context.pipeline = new_pipeline
            context.log_step(
                "replan_pipeline",
                f"New pipeline: {' -> '.join([s.agent.value for s in new_pipeline.steps])}",
                {"reasoning": new_pipeline.reasoning}
            )
            
            # 6.3. Сбрасываем индекс шага для нового выполнения
            context.current_step_index = 0
            
            # 6.4. Выполняем новый pipeline
            context.log_step("execute_pipeline", "Executing replanned pipeline...")
            context, pipeline_success, retry_failed_step, retry_error = await execute_pipeline(
                context,
                is_retry=True
            )
            
            # 6.5. Проверяем наличие файлов после retry
            all_files = context.get_all_files()
            has_files = len(all_files) > 0
            
            # Если после retry pipeline успешен, но файлов всё ещё нет - это снова ошибка
            if pipeline_success and not has_files:
                pipeline_success = False
                error_details = "Retry pipeline completed but still no files were generated. This is considered a fatal error."
                context.log_error("no_files_after_retry", error_details)
            
            if pipeline_success and has_files:
                PIPELINE_RETRIES.labels(success="success").inc()
                context.log_step("retry_pipeline", "Retry succeeded with files generated!")
                logger.info(f"[{context.task_id[:8]}] Pipeline retry succeeded with {len(all_files)} files")
                context.errors = []
                context.log_step(
                    "cleanup_errors",
                    f"Cleaned old errors after successful retry (kept {len(context.errors)} recent errors)"
                )

            else:
                PIPELINE_RETRIES.labels(success="failed").inc()
                context.log_step(
                    "retry_pipeline",
                    "Retry failed or no files generated",
                    {
                        "failed_agent": retry_failed_step.agent.value if retry_failed_step else "unknown",
                        "has_files": has_files
                    }
                )
                logger.warning(f"[{context.task_id[:8]}] Pipeline retry failed or no files generated")
        
        # 7. Финальная проверка успешности выполнения
        # Проверяем только после всех retry попыток
        all_files = context.get_all_files()

        # 8. Определение статуса
        workflow_status = determine_workflow_status(context, pipeline_success, has_files)
        
        # 9. Генерация метаданных
        if workflow_status != WorkflowStatus.FAILED:
            context.current_state = TaskState.AGGREGATING
            
            try:
                context.commit_message = await generate_commit_message(context)
            except Exception as e:
                context.log_error("generate_commit", f"Failed: {e}")
                context.commit_message = f"feat: implement task {context.task_id[:8]}"
            
            try:
                context.pr_title, context.pr_description = await generate_pr_metadata(context)
            except Exception as e:
                context.log_error("generate_pr", f"Failed: {e}")
                context.pr_title = f"Task: {context.task_description[:50]}"
                context.pr_description = context.task_description
        else:
            context.commit_message = ""
            context.pr_title = ""
            context.pr_description = ""
        
        # 10. Обновляем финальный state
        if workflow_status == WorkflowStatus.COMPLETED:
            context.current_state = TaskState.COMPLETED
        elif workflow_status == WorkflowStatus.PARTIAL:
            context.current_state = TaskState.COMPLETED  # Partial тоже considered "done"
        else:
            context.current_state = TaskState.FAILED
        
        duration = time.time() - start_time

        # 11. Генерация summary
        summary = await generate_summary(context, workflow_status, duration)
        
        TASK_DURATION.observe(duration)
        TASKS_TOTAL.labels(status=workflow_status.value).inc()
        
        context.log_step(
            "completed",
            f"Workflow finished with status: {workflow_status.value} in {duration:.1f}s",
            {
                "files_count": len(all_files),
                "errors_count": len(context.errors),
                "retry_count": pipeline_retry_count
            }
        )
        
        logger.info(f"[{context.task_id[:8]}] Workflow {workflow_status.value} in {duration:.1f}s (retries: {pipeline_retry_count}, files: {len(all_files)})")
        
        # 12. Формирование ответа
        return WorkflowResponse(
            task_id=context.task_id,
            status=workflow_status.value,
            tech_stack=context.tech_stack,
            branch_name=context.branch_name,
            files_to_create=[f.dict() for f in all_files],
            commit_message=context.commit_message,
            pr_title=context.pr_title,
            pr_description=context.pr_description,
            summary=summary,
            pipeline_executed=[
                {"agent": s.agent.value, "action": s.action}
                for s in context.pipeline.steps
            ] if context.pipeline else [],
            agent_results={
                "architect": context.architecture_result.dict() if context.architecture_result else None,
                "code_writer": context.code_result.dict() if context.code_result else None,
                "code_reviewer": context.review_result.dict() if context.review_result else None,
                "documentation": context.documentation_result.dict() if context.documentation_result else None
            },
            review_iterations=context.review_iterations,
            reasoning_log=context.reasoning_log,
            errors=context.errors,
            total_duration_seconds=duration
        )
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.exception(f"Workflow error: {e}")
        
        duration = time.time() - start_time
        TASKS_TOTAL.labels(status="error").inc()
        
        # Если контекст был создан, возвращаем частичную информацию
        if context:
            context.log_error("fatal", f"Unhandled exception: {str(e)}")
            context.current_state = TaskState.FAILED
            
            return WorkflowResponse(
                task_id=context.task_id,
                status=WorkflowStatus.ERROR.value,
                tech_stack=context.tech_stack,
                branch_name=context.branch_name or "",
                files_to_create=[],
                commit_message="",
                pr_title="",
                pr_description="",
                summary=f"Критическая ошибка: {str(e)[:200]}",
                pipeline_executed=[],
                agent_results={},
                review_iterations=0,
                reasoning_log=context.reasoning_log,
                errors=context.errors + [{"step": "fatal", "message": str(e)}],
                total_duration_seconds=duration
            )
        
        # Контекст не создан - возвращаем минимальный ответ
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "status": "error"
            }
        )
        
    finally:
        ACTIVE_TASKS.dec()

# ============================================================================
# ADDITIONAL ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    
    # Проверяем доступность агентов
    agents_status = {}
    for agent, url in AGENT_URLS.items():
        try:
            response = await http_client.get(f"{url}/health", timeout=5)
            agents_status[agent.value] = response.status_code == 200
        except:
            agents_status[agent.value] = False
    
    return {
        "status": "healthy",
        "service": "project_manager",
        "version": "2.1.0",
        "timestamp": datetime.now().isoformat(),
        "agents": agents_status,
        "features": {
            "error_analysis": True,
            "pipeline_retry": True,
            "max_retries": MAX_PIPELINE_RETRIES
        }
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()


@app.get("/")
async def root():
    """Root endpoint с информацией о сервисе"""
    return {
        "service": "Project Manager Agent",
        "version": "2.1.0",
        "description": "Координатор мультиагентной системы разработки",
        "responsibilities": [
            "Анализ технологического стека",
            "Планирование pipeline агентов",
            "Координация выполнения",
            "Передача контекста между агентами",
            "Управление review loop",
            "Агрегация результатов",
            "Анализ ошибок через LLM",
            "Retry pipeline с перепланированием"
        ],
        "does_not": [
            "Писать код",
            "Делать ревью кода",
            "Создавать документацию",
            "Проектировать архитектуру"
        ],
        "statuses": {
            "completed": "Всё успешно выполнено",
            "partial": "Частично выполнено (есть файлы, но были ошибки)",
            "failed": "Провал (нет файлов или критическая ошибка)",
            "error": "Системная ошибка (исключение)"
        },
        "retry_features": {
            "max_pipeline_retries": MAX_PIPELINE_RETRIES,
            "error_analysis": "LLM анализирует причину ошибки",
            "replan_pipeline": "Pipeline перестраивается с учётом ошибки"
        },
        "endpoints": {
            "workflow": "POST /workflow/process",
            "health": "GET /health",
            "metrics": "GET /metrics"
        },
        "connected_agents": list(AGENT_URLS.keys())
    }

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )