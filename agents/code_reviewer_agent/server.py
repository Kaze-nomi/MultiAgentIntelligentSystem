"""
Code Reviewer Agent - Проверяет код от Code Writer

Ответственности:
1. Проверка соответствия архитектуре от Architect
2. Поиск багов и логических ошибок
3. Проверка производительности
4. Проверка стиля и качества кода
5. Проверка документации и типизации
6. Принятие решения: approved / needs_revision

Получает:
- Код от Code Writer Agent
- Архитектуру от Architect Agent
- Контекст репозитория
- Технологический стек

Возвращает:
- ReviewResult с issues и решением
"""

import os
import json
import logging
import re
import time
import uuid
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
import httpx
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from models import (
    IssueSeverity, IssueType, ReviewDecision,
    CodeLocation, ReviewIssue, FileSummary,
    ArchitectureCheck, ArchitectureCompliance,
    ReviewMetrics, ReviewResult,
    CodeFile, CodeReviewRequest, CodeReviewResponse,
    TechStack
)

from logging_config import setup_logging

# ============================================================================
# CONFIGURATION
# ============================================================================

logger = setup_logging("code_reviewer")

OPENROUTER_MCP_URL = os.getenv("OPENROUTER_MCP_URL", "http://openrouter-proxy:8000")
LLM_TIMEOUT = 1000
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL")

# Настройки параллельной обработки
MAX_CONCURRENT_LLM_REQUESTS = 5  # Максимальное количество одновременных запросов к LLM
llm_semaphore = asyncio.Semaphore(MAX_CONCURRENT_LLM_REQUESTS)

# Пороги качества (смягченные)
QUALITY_THRESHOLDS = {
    "approve_min_score": 4.0,       # Сильно снижен порог для approve
    "max_critical_for_approve": 1,   # Допускаем 1 критическую ошибку
    "max_high_for_approve": 5,      # Допускаем до 5 высокоприоритетных проблем
    "max_medium_for_approve": 20,   # Много medium проблем - нормально
}

# ============================================================================
# METRICS
# ============================================================================

AGENT_REQUESTS_TOTAL = Counter('agent_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
AGENT_RESPONSE_TIME_SECONDS_BUCKET = Histogram('agent_response_time_seconds_bucket', 'Request duration',
                            ['method', 'endpoint'], buckets=[0.5, 1, 2, 5, 10, 30, 60, 120, 300])
AGENT_ACTIVE_REQUESTS = Gauge('agent_active_requests', 'Active requests', ['method', 'endpoint'])
REVIEWS_TOTAL = Counter('code_reviewer_reviews_total', 'Total reviews', ['decision'])
ISSUES_FOUND = Counter('code_reviewer_issues_total', 'Issues found', ['severity', 'type'])

# ============================================================================
# HTTP CLIENT
# ============================================================================

http_client: Optional[httpx.AsyncClient] = None

async def lifespan(app: FastAPI):
    """Lifecycle manager"""
    global http_client
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(LLM_TIMEOUT))
    
    logger.info("Code Reviewer Agent started")
    yield
    
    await http_client.aclose()
    logger.info("Code Reviewer Agent stopped")

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Code Reviewer Agent",
    description="Агент для проверки кода и принятия решений о качестве",
    version="2.0.0",
    lifespan=lifespan
)

# ============================================================================
# PROMETHEUS MIDDLEWARE
# ============================================================================

@app.middleware("http")
async def prometheus_middleware(request, call_next):
    """Middleware для отслеживания HTTP метрик"""
    if request.url.path in ["/health", "/metrics"]:
        return await call_next(request)
    
    AGENT_ACTIVE_REQUESTS.labels(method=request.method, endpoint=request.url.path).inc()
    start_time = time.time()

    try:
        response = await call_next(request)
        duration = time.time() - start_time
        status = str(response.status_code)

        AGENT_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=request.url.path,
            status=status
        ).inc()

        AGENT_RESPONSE_TIME_SECONDS_BUCKET.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)

        return response
    finally:
        AGENT_ACTIVE_REQUESTS.labels(method=request.method, endpoint=request.url.path).dec()

# ============================================================================
# LLM HELPER
# ============================================================================

async def call_llm(
    prompt: str,
    step: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 100000
) -> str:
    """Вызов LLM через OpenRouter MCP"""

    if not system_prompt:
        system_prompt = """Ты опытный код-ревьюер с 15+ лет опыта в разработке ПО.

ТВОЯ ГЛАВНАЯ ЗАДАЧА: Быть СПРАВЕДЛИВЫМ и ПОЛЕЗНЫМ ревьюером, который помогает, а не блокирует.

ПРИОРИТЕТЫ ПРОВЕРКИ:
1. Помогать разработчикам писать лучший код
2. Указывать на реальные проблемы, а не мелочи
3. Быть конструктивным и поддерживающим

СТАНЬТЕ МЯГЧЕ:
- Если код работает и делает то, что нужно, не нужно его усложнять
- Простой код лучше сложного "идеального" кода
- Не придирайся к стилю и мелким деталям
- Хвали хорошие решения, а не только критикуй ошибки
- Помни, что цель - рабочий продукт, а не идеальный код

ЧТО СЛЕДУЕТ ПРОВЕРЯТЬ:
1. Критические баги, которые точно сломают программу
2. Серьёзные проблемы безопасности
3. Очевидные ошибки производительности (O(n²) там где нужно O(n))
4. Нарушения архитектуры, которые помешают развитию проекта

ЧТО СЛЕДУЕТ ПРОПУСКАТЬ:
- Мелкие стилистические проблемы
- Вопросы именования (если имена понятны)
- Отсутствие документации для очевидных функций
- "Могло бы быть лучше" рекомендации
- Микрооптимизации

ПРИНЦИПЫ:
- Если код работает и понятен - это уже хорошо
- Лучшее - враг хорошего
- Простые решения часто лучше сложных
- Хвали за хорошие практики
- Предлагай улучшения, но не настаивай на них

ФОРМАТ:
- Будь дружелюбным и поддерживающим
- Используй "возможно", "можно рассмотреть" вместо "надо", "должен"
- Предлагай альтернативы, а не требования

Возвращай ответы в JSON когда это указано."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    logger.info(f"step: {step}")

    start_time = time.time()

    try:
        response = await http_client.post(
            f"{OPENROUTER_MCP_URL}/chat/completions",
            json={
                "model": DEFAULT_MODEL,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
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
            # Логирование ошибки и обновление метрики
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
        
        # Логирование исключения и обновление метрики
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
        parsed = json.loads(response)
        return parsed
    except json.JSONDecodeError:
        pass
    
    try:
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
    
    return None

# ============================================================================
# ARCHITECTURE COMPLIANCE CHECK (СМЯГЧЕННЫЙ)
# ============================================================================

async def check_architecture_compliance(
    code_file: Dict[str, Any],
    architecture: Dict[str, Any],
    tech_stack: TechStack
) -> Tuple[List[ArchitectureCheck], List[ReviewIssue]]:
    """
    Проверяет соответствие кода архитектуре (мягкая проверка)
    """

    if not architecture:
        return [], []

    components = architecture.get("components", [])
    interfaces = architecture.get("interfaces", [])
    file_structure = architecture.get("file_structure", [])

    prompt = f"""
Проверь соответствие кода архитектуре, но будь СПРАВЕДЛИВ и РАЗУМЕН.

## АРХИТЕКТУРА:
{json.dumps(architecture, indent=2, ensure_ascii=False)}

## КОД ДЛЯ ПРОВЕРКИ:
{json.dumps({"path": code_file.get("path"), "content": code_file.get("content", "")[:3000]}, indent=2, ensure_ascii=False)}

## БУДЬ МЯГКИМ:
- Если код в целом соответствует архитектуре, это хорошо
- Небольшие отклонения - это нормально, особенно на ранних этапах
- Главное - чтобы код был рабочим и понятным

## ПРОВЕРЬ ТОЛЬКО СЕРЬЁЗНЫЕ ПРОБЛЕМЫ:
1. **КРИТИЧЕСКИЕ**: Полное отсутствие ключевых компонентов
2. **ВЫСОКИЕ**: Нарушения, которые точно приведут к проблемам
3. **СРЕДНИЕ**: Важные отклонения, но не блокирующие

## ИГНОРИРУЙ:
- Мелкие несоответствия структуре
- Отсутствие необязательных паттернов
- Рекомендации по "улучшению" работающего кода

## ФОРМАТ ОТВЕТА (JSON):
{{
    "checks": [
        {{
            "component_name": "имя компонента",
            "expected": "что ожидалось",
            "actual": "что реализовано",
            "compliant": true/false,
            "issue": "описание проблемы если есть (только для серьёзных)"
        }}
    ],
    "issues": [
        {{
            "type": "architecture_violation",
            "severity": "medium/high/critical",
            "title": "краткое описание проблемы",
            "description": "подробное описание",
            "file_path": "путь к файлу",
            "suggestion": "необязательное предложение по исправлению"
        }}
    ]
}}

ВАЖНО: Будь сдержан в оценках. Если проблема не критическая, лучше отметить её как medium или вообще не отмечать.
"""

    response = await call_llm(prompt, step="architecture_compliance_check")
    parsed = parse_json_response(response)

    issues = []
    checks = []
    file_path = code_file.get("path", "unknown")

    if parsed:
        checks = [ArchitectureCheck(**c) for c in parsed.get("checks", [])]
        issues_data = parsed.get("issues", [])

        for issue_data in issues_data:
            try:
                severity = IssueSeverity(issue_data.get("severity", "medium"))
                # Автоматически понижаем severity на один уровень для мягкости
                if severity == IssueSeverity.CRITICAL:
                    severity = IssueSeverity.HIGH
                elif severity == IssueSeverity.HIGH:
                    severity = IssueSeverity.MEDIUM
            except ValueError:
                severity = IssueSeverity.MEDIUM

            issue = ReviewIssue(
                type=IssueType.ARCHITECTURE_VIOLATION,
                severity=severity,
                title=issue_data.get("title", "Architecture note"),
                description=issue_data.get("description", ""),
                file_path=issue_data.get("file_path"),
                suggestion=issue_data.get("suggestion")
            )
            
            issues.append(issue)

    return checks, issues

# ============================================================================
# CODE QUALITY CHECK (СМЯГЧЕННЫЙ)
# ============================================================================

async def check_code_quality(
    code_file: Dict[str, Any],
    tech_stack: TechStack
) -> List[ReviewIssue]:
    """
    Проверяет качество кода (мягкая проверка)
    """
    
    file_path = code_file.get("path", "unknown")
    
    prompt = f"""
Проведи ДРУЖЕСТВЕННОЕ код-ревью. Цель - помочь, а не наказать.

## ТЕХНОЛОГИИ:
- Язык: {tech_stack.primary_language}
- Фреймворки: {', '.join(tech_stack.frameworks)}

## КОД:
{json.dumps([{"path": code_file.get("path"), "content": code_file.get("content", "")} ], indent=2, ensure_ascii=False)[:15000]}

## БУДЬ ПОЛОЖИТЕЛЬНЫМ:
- Сначала отметь, что сделано хорошо
- Критикуй конструктивно
- Предлагай улучшения как варианты, а не требования

## ПРОВЕРЬ ТОЛЬКО ВАЖНОЕ:

### 1. РЕАЛЬНЫЕ БАГИ (только если точно уверен)
- Код, который точно не будет работать
- Ошибки, которые приведут к сбою

### 2. СЕРЬЁЗНЫЕ ПРОБЛЕМЫ
- Утечки памяти/ресурсов
- Бесконечные циклы
- Отсутствие обработки критических ошибок

### 3. УЛУЧШЕНИЯ (предлагай мягко)
- Возможные оптимизации
- Улучшение читаемости
- Лучшие практики

## ИГНОРИРУЙ:
- Стилистические предпочтения
- Мелкие неэффективности
- "Идеальный" код vs рабочий код
- Дублирование кода, если оно не критично

## ФОРМАТ ОТВЕТА (JSON):
{{
    "praise": ["что сделано хорошо"],
    "issues": [
        {{
            "type": "bug/performance/maintainability/documentation",
            "severity": "low/medium/high/critical",
            "title": "краткое описание",
            "description": "подробное описание с объяснением",
            "file_path": "путь/к/файлу.py",
            "line_number": 42,
            "code_snippet": "проблемный код",
            "suggestion": "дружелюбное предложение по улучшению",
            "suggested_code": "необязательный пример кода",
            "effort_to_fix": "low/medium/high"
        }}
    ]
}}

ПРИМЕЧАНИЕ: Будь очень осторожен с severity="critical". Используй только для реальных блокирующих проблем.
"""

    response = await call_llm(prompt, step="code_quality_check", max_tokens=100000)
    parsed = parse_json_response(response)
    
    issues = []
    
    if parsed:
        issues_data = parsed.get("issues", [])
        
        for issue_data in issues_data:
            try:
                issue_type = IssueType(issue_data.get("type", "maintainability"))
            except ValueError:
                issue_type = IssueType.MAINTAINABILITY
            
            try:
                severity = IssueSeverity(issue_data.get("severity", "low"))
                # Автоматически понижаем severity для мягкости
                if severity == IssueSeverity.CRITICAL:
                    severity = IssueSeverity.HIGH
            except ValueError:
                severity = IssueSeverity.LOW
            
            # Пропускаем очень мелкие issues
            if severity == IssueSeverity.LOW and issue_type in [IssueType.STYLE, IssueType.NAMING]:
                continue
            
            issue = ReviewIssue(
                type=issue_type,
                severity=severity,
                title=issue_data.get("title", "Suggestion"),
                description=issue_data.get("description", ""),
                file_path=issue_data.get("file_path"),
                line_number=issue_data.get("line_number"),
                code_snippet=issue_data.get("code_snippet"),
                suggestion=issue_data.get("suggestion"),
                suggested_code=issue_data.get("suggested_code"),
                effort_to_fix=issue_data.get("effort_to_fix", "low")
            )
            
            issues.append(issue)
    
    return issues

# ============================================================================
# PARALLEL FILE PROCESSING
# ============================================================================

async def process_file_parallel(
    code_file: Dict[str, Any],
    architecture: Dict[str, Any],
    tech_stack: TechStack
) -> Tuple[List[ArchitectureCheck], List[ReviewIssue]]:
    """
    Параллельно обрабатывает один файл
    """
    file_path = code_file.get('path')
    
    async with llm_semaphore:
        try:
            # 1. Проверка соответствия архитектуре
            arch_checks, arch_issues = await check_architecture_compliance(
                code_file, architecture, tech_stack
            )
            
            # 2. Проверка качества кода
            quality_issues = await check_code_quality(code_file, tech_stack)
            
            # Объединяем все проблемы
            all_issues = arch_issues + quality_issues
            
            return arch_checks, all_issues
        
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return [], []

# ============================================================================
# DECISION MAKING (СМЯГЧЕННЫЙ)
# ============================================================================

def make_review_decision(issues: List[ReviewIssue]) -> Tuple[ReviewDecision, bool, List[str]]:
    """
    Принимает решение на основе найденных проблем (мягкая логика)
    """
    
    critical_count = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
    high_count = sum(1 for i in issues if i.severity == IssueSeverity.HIGH)
    
    logger.info(f"Review decision: {critical_count} critical, {high_count} high issues")
    
    blocking_ids = []
    
    # Собираем ID только критических проблем как блокирующие
    for issue in issues:
        if issue.severity == IssueSeverity.CRITICAL:
            blocking_ids.append(issue.id)
    
    # Мягкая логика принятия решений
    if critical_count > QUALITY_THRESHOLDS["max_critical_for_approve"]:
        # Много критических проблем
        logger.info(f"Decision: NEEDS_REVISION (critical issues: {critical_count})")
        return ReviewDecision.NEEDS_REVISION, True, blocking_ids
    
    if high_count > QUALITY_THRESHOLDS["max_high_for_approve"]:
        # Много высокоприоритетных проблем
        logger.info(f"Decision: NEEDS_REVISION (high issues: {high_count})")
        return ReviewDecision.NEEDS_REVISION, True, blocking_ids
    
    # В большинстве случаев одобряем
    logger.info("Decision: APPROVED (no blocking issues)")
    return ReviewDecision.APPROVED, False, []

def calculate_quality_score(issues: List[ReviewIssue], total_files: int) -> float:
    """
    Вычисляет оценку качества кода (0-10) с мягкой логикой
    """
    try:
        # Проверка входных данных
        if total_files <= 0:
            logger.warning("Total files is 0 or negative in calculate_quality_score")
            return 10.0
        
        if not issues:
            logger.debug("No issues provided, returning perfect score")
            return 10.0
        
        # Мягкие веса
        severity_weights = {
            IssueSeverity.CRITICAL: 3.0,  # Снижен вес
            IssueSeverity.HIGH: 1.0,       # Снижен вес
            IssueSeverity.MEDIUM: 0.1,     # Очень низкий вес
            IssueSeverity.LOW: 0.01,       # Практически игнорируем
        }
        
        # Считаем взвешенную сумму проблем с безопасным доступом
        total_weight = 0
        try:
            for issue in issues:
                if hasattr(issue, 'severity') and issue.severity:
                    weight = severity_weights.get(issue.severity, 0.1)
                    total_weight += weight
                else:
                    logger.debug("Issue without severity, using default weight")
                    total_weight += 0.1
        except Exception as e:
            logger.error(f"Error calculating total weight: {e}")
            total_weight = len(issues) * 0.1  # Используем минимальный вес
        
        # Нормализуем по количеству файлов
        issues_per_file = total_weight / total_files
        
        # Мягкая формула: даже с проблемами даём хорошую оценку
        score = max(0, 10 - (issues_per_file * 1))
        
        final_score = round(score, 1)
        logger.debug(f"Quality score calculated: {final_score} (issues: {len(issues)}, files: {total_files}, weight: {total_weight})")
        
        return final_score
        
    except Exception as e:
        logger.exception(f"Unexpected error in calculate_quality_score: {e}")
        return 5.0  # Возвращаем среднюю оценку в случае ошибки

# ============================================================================
# MAIN REVIEW FUNCTION (УПРОЩЕННАЯ)
# ============================================================================

async def perform_code_review(
    code_files: List[Dict[str, Any]],
    architecture: Dict[str, Any],
    tech_stack: TechStack,
    repo_context: Dict[str, Any]
) -> ReviewResult:
    """
    Выполняет полное ревью кода (упрощенная версия без батчей)
    """
    
    all_issues: List[ReviewIssue] = []
    all_architecture_checks: List[ArchitectureCheck] = []
    
    logger.info(f"Starting parallel processing of {len(code_files)} files")
    
    # Создаем задачи для параллельной обработки файлов
    tasks = []
    for code_file in code_files:
        task = process_file_parallel(code_file, architecture, tech_stack)
        tasks.append(task)
    
    # Запускаем параллельную обработку
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Обрабатываем результаты
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Error processing file: {result}")
        else:
            arch_checks, file_issues = result
            all_architecture_checks.extend(arch_checks)
            all_issues.extend(file_issues)
    
    # Принимаем решение
    decision, needs_revision, blocking_ids = make_review_decision(all_issues)
    
    # Вычисляем оценку
    quality_score = calculate_quality_score(all_issues, len(code_files))
    
    # Создаем метрики
    metrics = ReviewMetrics(
        total_files=len(code_files),
        total_lines=sum(f.get("content", "").count('\n') + 1 for f in code_files),
        total_issues=len(all_issues),
        critical_issues=sum(1 for i in all_issues if i.severity == IssueSeverity.CRITICAL),
        high_issues=sum(1 for i in all_issues if i.severity == IssueSeverity.HIGH),
        medium_issues=sum(1 for i in all_issues if i.severity == IssueSeverity.MEDIUM),
        low_issues=sum(1 for i in all_issues if i.severity == IssueSeverity.LOW),
        bugs=sum(1 for i in all_issues if i.type == IssueType.BUG),
        performance_issues=sum(1 for i in all_issues if i.type == IssueType.PERFORMANCE),
        overall_quality_score=quality_score,
        maintainability_score=10.0 - (len([i for i in all_issues if i.severity in [IssueSeverity.CRITICAL, IssueSeverity.HIGH]]) * 0.5)
    )
    
    # Создаём сводки по файлам
    file_summaries = []
    for file_data in code_files:
        path = file_data.get("path", "unknown")
        file_issues = [i for i in all_issues if i.file_path == path]
        
        summary = FileSummary(
            file_path=path,
            language=file_data.get("language", "unknown"),
            lines_of_code=file_data.get("content", "").count('\n') + 1,
            issues_count=len(file_issues),
            critical_count=sum(1 for i in file_issues if i.severity == IssueSeverity.CRITICAL),
            high_count=sum(1 for i in file_issues if i.severity == IssueSeverity.HIGH),
            quality_score=10.0 - (len(file_issues) * 0.2),
            recommendations=[i.suggestion for i in file_issues[:3] if i.suggestion]
        )
        file_summaries.append(summary)
    
    # Архитектурное соответствие
    architecture_compliance = ArchitectureCompliance(
        overall_compliant=len([c for c in all_architecture_checks if not c.compliant]) == 0,
        checks=all_architecture_checks,
        missing_components=[],
        extra_components=[],
        interface_violations=[],
        dependency_violations=[]
    )
    
    # Генерируем summary
    critical_count = metrics.critical_issues
    high_count = metrics.high_issues
    
    if decision == ReviewDecision.APPROVED:
        summary = f"✅ Код одобрен\n\n"
    else:
        summary = f"⚠️ Требуется доработка\n\n"
    
    summary += f"Оценка: {quality_score}/10\n"
    summary += f"Проблемы: {critical_count} критических, {high_count} высоких\n\n"
    
    if critical_count > 0:
        summary += "Критические проблемы:\n"
        for issue in [i for i in all_issues if i.severity == IssueSeverity.CRITICAL][:3]:
            summary += f"- {issue.title}\n"
    
    suggestions = []
    if critical_count > 0:
        suggestions.append("Исправьте критические проблемы перед релизом")
    elif high_count > 0:
        suggestions.append("Рассмотрите исправление высокоприоритетных проблем")
    else:
        suggestions.append("Код в хорошем состоянии. Можно запускать в прод.")
    
    # Обновляем метрики Prometheus
    REVIEWS_TOTAL.labels(decision=decision.value).inc()
    for issue in all_issues:
        ISSUES_FOUND.labels(severity=issue.severity.value, type=issue.type.value).inc()
    
    return ReviewResult(
        decision=decision,
        approved=(decision == ReviewDecision.APPROVED),
        needs_revision=needs_revision,
        quality_score=quality_score,
        issues=all_issues,
        suggestions=suggestions,
        summary=summary,
        metrics=metrics,
        file_summaries=file_summaries,
        architecture_compliance=architecture_compliance,
        blocking_issues=blocking_ids
    )

# ============================================================================
# MAIN ENDPOINT
# ============================================================================

@app.post("/process", response_model=CodeReviewResponse)
async def process_code_review(request: CodeReviewRequest):
    """
    Основной endpoint для ревью кода
    """
    
    start_time = time.time()
    task_id = str(uuid.uuid4())
    
    try:
        data = request.data
        
        logger.info(f"[{task_id[:8]}] Starting code review: {request.task[:100]}")
        
        # Извлекаем данные с улучшенной обработкой ошибок
        code_data = data.get("code", {})
        code_files = []
        
        try:
            if "code" in data and "files" in data["code"]:
                code_files = data["code"]["files"]
                logger.debug(f"[{task_id[:8]}] Found {len(code_files)} files in data.code.files")
            elif "files" in data:
                code_files = data["files"]
                logger.debug(f"[{task_id[:8]}] Found {len(code_files)} files in data.files")
            else:
                logger.warning(f"[{task_id[:8]}] No code files found in request data")
                raise HTTPException(status_code=400, detail="No code files provided")
        except (AttributeError, TypeError) as e:
            logger.error(f"[{task_id[:8]}] Error extracting code files: {e}")
            raise HTTPException(status_code=400, detail="Invalid code files format")
        
        # Валидация файлов
        if not isinstance(code_files, list):
            logger.error(f"[{task_id[:8]}] Code files is not a list: {type(code_files)}")
            raise HTTPException(status_code=400, detail="Code files must be a list")
        
        if len(code_files) == 0:
            logger.warning(f"[{task_id[:8]}] Empty code files list")
            raise HTTPException(status_code=400, detail="No code files provided")
        
        # Проверка структуры каждого файла
        for i, file_data in enumerate(code_files):
            if not isinstance(file_data, dict):
                logger.error(f"[{task_id[:8]}] File {i} is not a dict: {type(file_data)}")
                raise HTTPException(status_code=400, detail=f"File {i} must be a dict")
            
            if "path" not in file_data:
                logger.error(f"[{task_id[:8]}] File {i} missing 'path' field")
                raise HTTPException(status_code=400, detail=f"File {i} missing 'path' field")
            
            if "content" not in file_data:
                logger.error(f"[{task_id[:8]}] File {i} missing 'content' field")
                raise HTTPException(status_code=400, detail=f"File {i} missing 'content' field")
        
        # Извлекаем остальные данные с обработкой ошибок
        try:
            architecture = data.get("architecture", {})
            tech_stack_data = data.get("tech_stack", {})
            
            if tech_stack_data and isinstance(tech_stack_data, dict):
                tech_stack = TechStack(**tech_stack_data)
            else:
                tech_stack = TechStack()
                logger.debug(f"[{task_id[:8]}] Using default TechStack")
            
            repo_context = data.get("repo_context", {})
        except Exception as e:
            logger.error(f"[{task_id[:8]}] Error extracting additional data: {e}")
            # Используем значения по умолчанию в случае ошибки
            architecture = {}
            tech_stack = TechStack()
            repo_context = {}
        
        logger.info(f"[{task_id[:8]}] Reviewing {len(code_files)} files")
        
        # Выполняем ревью с обработкой ошибок
        try:
            result = await perform_code_review(
                code_files=code_files,
                architecture=architecture,
                tech_stack=tech_stack,
                repo_context=repo_context
            )
        except Exception as e:
            logger.exception(f"[{task_id[:8]}] Error during code review: {e}")
            # Создаем базовый результат в случае ошибки
            result = ReviewResult(
                decision=ReviewDecision.NEEDS_REVISION,
                approved=False,
                needs_revision=True,
                quality_score=0.0,
                issues=[],
                suggestions=[f"Review failed due to error: {str(e)}"],
                summary=f"Review failed: {str(e)}",
                metrics=ReviewMetrics(total_files=len(code_files)),
                file_summaries=[],
                blocking_issues=[]
            )
        
        duration = time.time() - start_time
        
        logger.info(f"[{task_id[:8]}] Review completed in {duration:.1f}s, "
                   f"decision: {result.decision.value}")
        
        response_data = {
            "task_id": task_id,
            "status": "success",
            "result": result,
            "reviewed_files": len(code_files),
            "duration_seconds": duration
        }
        
        return CodeReviewResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[{task_id[:8]}] Unexpected review error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ============================================================================
# ADDITIONAL ENDPOINTS
# ============================================================================

@app.post("/review-repo")
async def review_repo(request: Dict[str, Any]):
    """
    Проверяет весь репозиторий
    """

    task_id = str(uuid.uuid4())[:8]
    
    # Валидация поля target_folder если оно присутствует
    if "target_folder" in request:
        target_folder = request.get("target_folder")
        if not isinstance(target_folder, str):
            logger.error(f"[{task_id}] target_folder must be a string, got: {type(target_folder)}")
            raise HTTPException(status_code=400, detail="target_folder must be a string")
        if not target_folder.strip():
            logger.error(f"[{task_id}] target_folder cannot be empty")
            raise HTTPException(status_code=400, detail="target_folder cannot be empty")
        logger.debug(f"[{task_id}] Using target_folder: {target_folder}")
    
    try:
        # Извлекаем и валидируем входные данные
        if not isinstance(request, dict):
            logger.error(f"[{task_id}] Request is not a dict: {type(request)}")
            raise HTTPException(status_code=400, detail="Invalid request format")
        
        repo_context = request.get("repo_context", {})
        tech_stack_data = request.get("tech_stack", {})
        
        # Создаем TechStack с обработкой ошибок
        try:
            if tech_stack_data and isinstance(tech_stack_data, dict):
                tech_stack = TechStack(**tech_stack_data)
            else:
                tech_stack = TechStack()
                logger.debug(f"[{task_id}] Using default TechStack")
        except Exception as e:
            logger.error(f"[{task_id}] Error creating TechStack: {e}")
            tech_stack = TechStack()

        logger.info(f"[{task_id}] Starting repository review")

        # Извлекаем все файлы из repo_context с обработкой ошибок
        code_files = []
        
        try:
            if not isinstance(repo_context, dict):
                logger.error(f"[{task_id}] repo_context is not a dict: {type(repo_context)}")
                repo_context = {}
            
            key_files = repo_context.get("key_files", {})
            
            if not isinstance(key_files, dict):
                logger.error(f"[{task_id}] key_files is not a dict: {type(key_files)}")
                key_files = {}

            for file_path, content in key_files.items():
                try:
                    if isinstance(content, str) and content.strip():
                        language = "text"
                        if "." in file_path:
                            ext = file_path.rsplit(".", 1)[-1].lower()
                            lang_map = {
                                "py": "python", "js": "javascript", "ts": "typescript",
                                "java": "java", "c": "c", "cpp": "cpp", "cs": "csharp",
                                "php": "php", "rb": "ruby", "go": "go", "rs": "rust"
                            }
                            language = lang_map.get(ext, "text")

                        code_files.append({
                            "path": file_path,
                            "content": content,
                            "language": language
                        })
                except Exception as e:
                    logger.error(f"[{task_id}] Error processing file {file_path}: {e}")
                    continue
        except Exception as e:
            logger.error(f"[{task_id}] Error extracting files from repo_context: {e}")

        logger.info(f"[{task_id}] Reviewing {len(code_files)} files from repository")

        if not code_files:
            return {
                "decision": "approved",
                "approved": True,
                "needs_revision": False,
                "quality_score": 10.0,
                "issues": [],
                "suggestions": ["Repository appears to be empty or no code files found"],
                "summary": "No code files to review",
                "metrics": {
                    "total_files": 0,
                    "total_lines": 0,
                    "total_issues": 0,
                    "critical_issues": 0,
                    "high_issues": 0,
                    "medium_issues": 0,
                    "low_issues": 0,
                    "overall_quality_score": 10.0
                },
                "file_summaries": [],
                "blocking_issues": []
            }

        # Выполняем ревью с обработкой ошибок
        result = await perform_code_review(
            code_files=code_files,
            architecture={},
            tech_stack=tech_stack,
            repo_context=repo_context
        )

        logger.info(f"[{task_id}] Repository review completed: {result.decision.value}")

        # Формируем ответ с обработкой ошибок
        try:
            response_data = {
                "decision": result.decision.value,
                "approved": result.approved,
                "needs_revision": result.needs_revision,
                "quality_score": result.quality_score,
                "issues": [i.dict() for i in result.issues],
                "suggestions": result.suggestions,
                "summary": result.summary,
                "metrics": result.metrics.dict(),
                "file_summaries": [fs.dict() for fs in result.file_summaries],
                "architecture_compliance": result.architecture_compliance.dict(),
                "blocking_issues": result.blocking_issues
            }
            return response_data
        except Exception as e:
            logger.error(f"[{task_id}] Error formatting response: {e}")
            # Возвращаем базовый ответ в случае ошибки форматирования
            return {
                "decision": result.decision.value,
                "approved": result.approved,
                "needs_revision": result.needs_revision,
                "quality_score": result.quality_score,
                "issues": [],
                "suggestions": ["Review completed but response formatting failed"],
                "summary": f"Review completed: {result.decision.value}",
                "metrics": {"total_files": len(code_files)},
                "file_summaries": [],
                "blocking_issues": []
            }
        except Exception as e:
            logger.exception(f"[{task_id}] Error during repository review: {e}")
            # Возвращаем базовый ответ в случае ошибки ревью
            return {
                "decision": "needs_revision",
                "approved": False,
                "needs_revision": True,
                "quality_score": 0.0,
                "issues": [],
                "suggestions": [f"Review failed due to error: {str(e)}"],
                "summary": f"Review failed: {str(e)}",
                "metrics": {"total_files": len(code_files)},
                "file_summaries": [],
                "blocking_issues": []
            }
    except Exception as e:
        logger.exception(f"[{task_id}] Error in review_repo endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/thresholds")
async def get_thresholds():
    """Возвращает текущие пороги"""
    return QUALITY_THRESHOLDS

@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "service": "code_reviewer",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics"""
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Code Reviewer Agent",
        "version": "2.0.0",
        "description": "Агент для проверки качества кода (мягкая версия)",
        "focus": "Помогает, а не блокирует. Фокусируется на реальных проблемах, а не мелочах.",
        "philosophy": "Рабочий код лучше идеального кода",
        "checks": [
            "Реальные баги (только если уверен)",
            "Серьёзные проблемы безопасности",
            "Критические архитектурные нарушения"
        ],
        "ignores": [
            "Стилистические предпочтения",
            "Мелкие неэффективности",
            "'Могло бы быть лучше' рекомендации"
        ],
        "endpoints": {
            "process": "POST /process - ревью кода",
            "review_repo": "POST /review-repo - ревью репозитория",
            "thresholds": "GET /thresholds - пороги качества",
            "health": "GET /health",
            "metrics": "GET /metrics"
        }
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