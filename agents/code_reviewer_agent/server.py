"""
Code Reviewer Agent - Проверяет код от Code Writer

Ответственности:
1. Проверка соответствия архитектуре от Architect
2. Поиск багов и логических ошибок
3. Анализ безопасности (SQL injection, XSS, secrets, etc.)
4. Проверка производительности
5. Проверка стиля и качества кода
6. Проверка документации и типизации
7. Принятие решения: approved / needs_revision

Получает:
- Код от Code Writer Agent
- Архитектуру от Architect Agent
- Контекст репозитория
- Технологический стек

Возвращает:
- ReviewResult с issues и решением
- Может вернуть needs_revision для review loop
"""

import os
import json
import logging
import re
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import httpx
from prometheus_client import Counter, Histogram, generate_latest

from models import (
    IssueSeverity, IssueType, ReviewDecision,
    CodeLocation, ReviewIssue, FileSummary,
    ArchitectureCheck, ArchitectureCompliance,
    SecurityFinding, SecurityReport,
    ReviewMetrics, ReviewResult,
    CodeFile, CodeReviewRequest, CodeReviewResponse,
    TechStack
)

# ============================================================================
# CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

OPENROUTER_MCP_URL = os.getenv("OPENROUTER_MCP_URL", "http://openrouter-mcp:8000")
LLM_TIMEOUT = 240
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL")

# Пороги качества
QUALITY_THRESHOLDS = {
    "approve_min_score": 7.0,       # Минимум для approve
    "max_critical_for_approve": 0,   # Максимум critical issues для approve
    "max_high_for_approve": 0,       # Максимум high issues для approve
    "max_medium_for_approve": 5,     # Максимум medium issues для approve
}

# ============================================================================
# METRICS
# ============================================================================

REVIEWS_TOTAL = Counter('code_reviewer_reviews_total', 'Total reviews', ['decision'])
ISSUES_FOUND = Counter('code_reviewer_issues_total', 'Issues found', ['severity', 'type'])
REVIEW_DURATION = Histogram('code_reviewer_duration_seconds', 'Review duration',
                            buckets=[10, 30, 60, 120, 300])

# ============================================================================
# HTTP CLIENT
# ============================================================================

http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
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
# LLM HELPER
# ============================================================================

async def call_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.1,  # Низкая температура для консистентности
    max_tokens: int = 100000
) -> str:
    """Вызов LLM через OpenRouter MCP"""
    
    if not system_prompt:
        system_prompt = """Ты опытный код-ревьюер с 15+ лет опыта в разработке ПО.
Ты тщательно проверяешь код на:
- Баги и логические ошибки
- Уязвимости безопасности
- Проблемы производительности
- Соответствие архитектуре и паттернам
- Качество кода и поддерживаемость
- Документацию и типизацию

Ты даёшь конкретные, actionable замечания с примерами исправлений.
Ты справедлив и объективен в оценках.
Возвращаешь ответы в JSON когда это указано."""
    
    try:
        response = await http_client.post(
            f"{OPENROUTER_MCP_URL}/chat/completions",
            json={
                "model": DEFAULT_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            timeout=LLM_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            logger.error(f"LLM error: {response.status_code} - {response.text}")
            return ""
            
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return ""


def parse_json_response(response: str) -> Optional[Dict]:
    """Извлекает JSON из ответа LLM"""
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    try:
        # Ищем JSON в markdown блоке
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        # Ищем JSON объект
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
    
    return None


# ============================================================================
# ARCHITECTURE COMPLIANCE CHECK
# ============================================================================

async def check_architecture_compliance(
    code_files: List[Dict[str, Any]],
    architecture: Dict[str, Any],
    tech_stack: TechStack
) -> Tuple[ArchitectureCompliance, List[ReviewIssue]]:
    """
    Проверяет соответствие кода архитектуре от Architect Agent
    """
    
    if not architecture:
        return ArchitectureCompliance(overall_compliant=True), []
    
    components = architecture.get("components", [])
    interfaces = architecture.get("interfaces", [])
    file_structure = architecture.get("file_structure", [])
    patterns = architecture.get("patterns", [])
    
    prompt = f"""
Проверь соответствие кода спроектированной архитектуре.

## АРХИТЕКТУРА (от Architect Agent):

### Компоненты:
{json.dumps(components, indent=2, ensure_ascii=False)}

### Интерфейсы:
{json.dumps(interfaces, indent=2, ensure_ascii=False)}

### Структура файлов:
{json.dumps(file_structure, indent=2, ensure_ascii=False)}

### Паттерны:
{json.dumps(patterns, indent=2, ensure_ascii=False)}

## КОД ДЛЯ ПРОВЕРКИ:
{json.dumps([{"path": f.get("path"), "content": f.get("content", "")[:3000]} for f in code_files], indent=2, ensure_ascii=False)}

## ПРОВЕРЬ:

1. **Компоненты**: Все ли компоненты реализованы? Соответствуют ли спецификации?
2. **Интерфейсы**: Соответствуют ли сигнатуры методов? Правильные ли типы?
3. **Структура файлов**: Правильно ли расположены файлы?
4. **Паттерны**: Применены ли указанные паттерны проектирования?
5. **Зависимости**: Соблюдены ли зависимости между компонентами?

## ФОРМАТ ОТВЕТА (JSON):
{{
    "overall_compliant": true/false,
    "checks": [
        {{
            "component_name": "имя компонента",
            "expected": "что ожидалось",
            "actual": "что реализовано",
            "compliant": true/false,
            "issue": "описание проблемы если есть"
        }}
    ],
    "missing_components": ["список нереализованных компонентов"],
    "extra_components": ["лишние компоненты не из архитектуры"],
    "interface_violations": ["нарушения интерфейсов"],
    "dependency_violations": ["нарушения зависимостей"],
    "issues": [
        {{
            "type": "architecture_violation",
            "severity": "high/medium/low",
            "title": "краткое описание",
            "description": "подробное описание",
            "file_path": "путь к файлу",
            "suggestion": "как исправить"
        }}
    ]
}}
"""
    
    response = await call_llm(prompt)
    parsed = parse_json_response(response)
    
    issues = []
    compliance = ArchitectureCompliance(overall_compliant=True)
    
    if parsed:
        compliance = ArchitectureCompliance(
            overall_compliant=parsed.get("overall_compliant", True),
            checks=[ArchitectureCheck(**c) for c in parsed.get("checks", [])],
            missing_components=parsed.get("missing_components", []),
            extra_components=parsed.get("extra_components", []),
            interface_violations=parsed.get("interface_violations", []),
            dependency_violations=parsed.get("dependency_violations", [])
        )
        
        # Создаём issues
        for issue_data in parsed.get("issues", []):
            try:
                severity = IssueSeverity(issue_data.get("severity", "medium"))
            except ValueError:
                severity = IssueSeverity.MEDIUM
            
            issues.append(ReviewIssue(
                type=IssueType.ARCHITECTURE_VIOLATION,
                severity=severity,
                title=issue_data.get("title", "Architecture violation"),
                description=issue_data.get("description", ""),
                file_path=issue_data.get("file_path"),
                suggestion=issue_data.get("suggestion")
            ))
        
        # Добавляем issues для missing components
        for comp in compliance.missing_components:
            issues.append(ReviewIssue(
                type=IssueType.ARCHITECTURE_VIOLATION,
                severity=IssueSeverity.HIGH,
                title=f"Missing component: {comp}",
                description=f"Component '{comp}' was specified in architecture but not implemented",
                suggestion=f"Implement the '{comp}' component according to architecture specification"
            ))
    
    return compliance, issues


# ============================================================================
# SECURITY CHECK
# ============================================================================

async def check_security(
    code_files: List[Dict[str, Any]],
    tech_stack: TechStack
) -> Tuple[SecurityReport, List[ReviewIssue]]:
    """
    Проверяет код на уязвимости безопасности
    """
    
    prompt = f"""
Проведи аудит безопасности кода.

## ТЕХНОЛОГИИ:
- Язык: {tech_stack.primary_language}
- Фреймворки: {', '.join(tech_stack.frameworks)}
- Базы данных: {', '.join(tech_stack.databases)}

## КОД:
{json.dumps([{"path": f.get("path"), "content": f.get("content", "")} for f in code_files], indent=2, ensure_ascii=False)[:15000]}

## ПРОВЕРЬ НА:

1. **Инъекции**: SQL injection, Command injection, LDAP injection
2. **XSS**: Cross-site scripting
3. **Секреты**: Hardcoded passwords, API keys, tokens
4. **Аутентификация**: Слабая аутентификация, отсутствие проверок
5. **Авторизация**: Отсутствие проверок доступа, IDOR
6. **Криптография**: Слабые алгоритмы, небезопасное хранение
7. **Данные**: Логирование sensitive data, небезопасная сериализация
8. **Зависимости**: Известные уязвимые версии
9. **Конфигурация**: Debug mode, небезопасные настройки
10. **Валидация**: Отсутствие валидации входных данных

## ФОРМАТ ОТВЕТА (JSON):
{{
    "passed": true/false,
    "findings": [
        {{
            "vulnerability_type": "sql_injection/xss/hardcoded_secret/...",
            "severity": "critical/high/medium/low",
            "file_path": "путь к файлу",
            "line_number": 42,
            "description": "описание уязвимости",
            "cwe_id": "CWE-89",
            "remediation": "как исправить"
        }}
    ],
    "checked_patterns": ["что было проверено"]
}}
"""
    
    response = await call_llm(prompt)
    parsed = parse_json_response(response)
    
    issues = []
    report = SecurityReport(passed=True)
    
    if parsed:
        findings = []
        for f in parsed.get("findings", []):
            try:
                severity = IssueSeverity(f.get("severity", "medium"))
            except ValueError:
                severity = IssueSeverity.MEDIUM
            
            findings.append(SecurityFinding(
                vulnerability_type=f.get("vulnerability_type", "unknown"),
                severity=severity,
                file_path=f.get("file_path", ""),
                line_number=f.get("line_number"),
                description=f.get("description", ""),
                cwe_id=f.get("cwe_id"),
                remediation=f.get("remediation", "")
            ))
            
            # Создаём issue
            issues.append(ReviewIssue(
                type=IssueType.SECURITY,
                severity=severity,
                title=f"Security: {f.get('vulnerability_type', 'vulnerability')}",
                description=f.get("description", ""),
                file_path=f.get("file_path"),
                line_number=f.get("line_number"),
                suggestion=f.get("remediation"),
                references=[f.get("cwe_id")] if f.get("cwe_id") else []
            ))
        
        report = SecurityReport(
            passed=parsed.get("passed", len(findings) == 0),
            findings=findings,
            checked_patterns=parsed.get("checked_patterns", [])
        )
    
    return report, issues


# ============================================================================
# CODE QUALITY CHECK
# ============================================================================

async def check_code_quality(
    code_files: List[Dict[str, Any]],
    tech_stack: TechStack
) -> List[ReviewIssue]:
    """
    Проверяет качество кода: баги, производительность, стиль, документация
    """
    
    prompt = f"""
Проведи детальный код-ревью.

## ТЕХНОЛОГИИ:
- Язык: {tech_stack.primary_language}
- Фреймворки: {', '.join(tech_stack.frameworks)}
- Тестирование: {', '.join(tech_stack.testing_frameworks)}

## КОД:
{json.dumps([{"path": f.get("path"), "content": f.get("content", "")} for f in code_files], indent=2, ensure_ascii=False)[:15000]}

## ПРОВЕРЬ:

### 1. БАГИ И ОШИБКИ (bug)
- Логические ошибки
- Off-by-one errors
- Null/undefined reference
- Race conditions
- Edge cases

### 2. ПРОИЗВОДИТЕЛЬНОСТЬ (performance)
- N+1 queries
- Неоптимальные алгоритмы (O(n²) где можно O(n))
- Утечки памяти
- Лишние вычисления в циклах
- Большие объекты в памяти

### 3. СТИЛЬ И ЧИТАЕМОСТЬ (style, naming)
- Консистентность именования
- Длинные методы (>50 строк)
- Глубокая вложенность (>4 уровней)
- Magic numbers
- Dead code

### 4. ДОКУМЕНТАЦИЯ (documentation)
- Отсутствие docstrings
- Устаревшие комментарии
- Отсутствие type hints

### 5. ОБРАБОТКА ОШИБОК (error_handling)
- Пустые catch блоки
- Проглатывание исключений
- Отсутствие обработки ошибок

### 6. ПОДДЕРЖИВАЕМОСТЬ (maintainability)
- Нарушение SOLID
- Высокая связанность
- Дублирование кода
- Тестируемость

## ФОРМАТ ОТВЕТА (JSON):
{{
    "issues": [
        {{
            "type": "bug/security/performance/style/documentation/error_handling/maintainability/naming",
            "severity": "critical/high/medium/low",
            "title": "краткое описание проблемы",
            "description": "подробное описание",
            "file_path": "путь/к/файлу.py",
            "line_number": 42,
            "code_snippet": "проблемный код",
            "suggestion": "как исправить",
            "suggested_code": "исправленный код",
            "effort_to_fix": "low/medium/high"
        }}
    ],
    "positive_aspects": [
        "что хорошо в коде"
    ]
}}

ВАЖНО: 
- Будь конкретен - указывай точные места проблем
- Давай конкретные решения с примерами кода
- Не придирайся к мелочам в critical/high
"""
    
    response = await call_llm(prompt, max_tokens=100000)
    parsed = parse_json_response(response)
    
    issues = []
    
    if parsed:
        for issue_data in parsed.get("issues", []):
            try:
                issue_type = IssueType(issue_data.get("type", "maintainability"))
            except ValueError:
                issue_type = IssueType.MAINTAINABILITY
            
            try:
                severity = IssueSeverity(issue_data.get("severity", "medium"))
            except ValueError:
                severity = IssueSeverity.MEDIUM
            
            issues.append(ReviewIssue(
                type=issue_type,
                severity=severity,
                title=issue_data.get("title", "Issue"),
                description=issue_data.get("description", ""),
                file_path=issue_data.get("file_path"),
                line_number=issue_data.get("line_number"),
                code_snippet=issue_data.get("code_snippet"),
                suggestion=issue_data.get("suggestion"),
                suggested_code=issue_data.get("suggested_code"),
                effort_to_fix=issue_data.get("effort_to_fix", "low")
            ))
    
    return issues


# ============================================================================
# DECISION MAKING
# ============================================================================

def make_review_decision(issues: List[ReviewIssue]) -> Tuple[ReviewDecision, bool, List[str]]:
    """
    Принимает решение на основе найденных проблем
    Возвращает: (decision, needs_revision, blocking_issue_ids)
    """
    
    critical_count = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
    high_count = sum(1 for i in issues if i.severity == IssueSeverity.HIGH)
    medium_count = sum(1 for i in issues if i.severity == IssueSeverity.MEDIUM)
    
    blocking_ids = []
    
    # Собираем ID блокирующих issues
    for issue in issues:
        if issue.severity in [IssueSeverity.CRITICAL, IssueSeverity.HIGH]:
            blocking_ids.append(issue.id)
    
    # Решение
    if critical_count > QUALITY_THRESHOLDS["max_critical_for_approve"]:
        return ReviewDecision.NEEDS_REVISION, True, blocking_ids
    
    if high_count > QUALITY_THRESHOLDS["max_high_for_approve"]:
        return ReviewDecision.NEEDS_REVISION, True, blocking_ids
    
    if medium_count > QUALITY_THRESHOLDS["max_medium_for_approve"]:
        return ReviewDecision.NEEDS_REVISION, True, blocking_ids[:5]  # Топ-5 для исправления
    
    return ReviewDecision.APPROVED, False, []


def calculate_quality_score(issues: List[ReviewIssue], total_files: int) -> float:
    """
    Вычисляет общую оценку качества кода (0-10)
    """
    
    if total_files == 0:
        return 10.0
    
    # Веса для разных severity
    severity_weights = {
        IssueSeverity.CRITICAL: 3.0,
        IssueSeverity.HIGH: 1.5,
        IssueSeverity.MEDIUM: 0.5,
        IssueSeverity.LOW: 0.1,
    }
    
    # Считаем взвешенную сумму проблем
    total_weight = sum(severity_weights.get(i.severity, 0.5) for i in issues)
    
    # Нормализуем по количеству файлов
    issues_per_file = total_weight / total_files
    
    # Преобразуем в оценку (10 - идеально, 0 - много проблем)
    # Примерно: 0 issues = 10, 5 weighted issues/file = 0
    score = max(0, 10 - (issues_per_file * 2))
    
    return round(score, 1)


def calculate_detailed_scores(issues: List[ReviewIssue]) -> Dict[str, float]:
    """
    Вычисляет детальные оценки по категориям
    """
    
    categories = {
        "security": [IssueType.SECURITY],
        "performance": [IssueType.PERFORMANCE],
        "maintainability": [IssueType.MAINTAINABILITY, IssueType.COMPLEXITY, 
                          IssueType.DUPLICATION, IssueType.NAMING],
        "documentation": [IssueType.DOCUMENTATION],
    }
    
    scores = {}
    
    for category, types in categories.items():
        category_issues = [i for i in issues if i.type in types]
        
        if not category_issues:
            scores[category] = 10.0
        else:
            # Простая формула: 10 - (кол-во * вес)
            weight_sum = sum(
                2.0 if i.severity == IssueSeverity.CRITICAL else
                1.0 if i.severity == IssueSeverity.HIGH else
                0.3 if i.severity == IssueSeverity.MEDIUM else 0.1
                for i in category_issues
            )
            scores[category] = max(0, round(10 - weight_sum, 1))
    
    return scores


# ============================================================================
# SUMMARY GENERATION
# ============================================================================

async def generate_review_summary(
    issues: List[ReviewIssue],
    decision: ReviewDecision,
    quality_score: float,
    architecture_compliance: ArchitectureCompliance,
    security_report: SecurityReport
) -> str:
    """
    Генерирует человекочитаемое резюме ревью
    """
    
    critical = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
    high = [i for i in issues if i.severity == IssueSeverity.HIGH]
    medium = [i for i in issues if i.severity == IssueSeverity.MEDIUM]
    low = [i for i in issues if i.severity == IssueSeverity.LOW]
    
    # Группируем по типам
    by_type = {}
    for issue in issues:
        t = issue.type.value
        by_type[t] = by_type.get(t, 0) + 1
    
    summary_parts = []
    
    # Заголовок с решением
    if decision == ReviewDecision.APPROVED:
        summary_parts.append("✅ **КОД ОДОБРЕН**")
    else:
        summary_parts.append("⚠️ **ТРЕБУЕТСЯ ДОРАБОТКА**")
    
    summary_parts.append(f"\n📊 **Оценка качества: {quality_score}/10**\n")
    
    # Статистика issues
    summary_parts.append("### Найденные проблемы:\n")
    if critical:
        summary_parts.append(f"- 🔴 Критических: {len(critical)}")
    if high:
        summary_parts.append(f"- 🟠 Высокий приоритет: {len(high)}")
    if medium:
        summary_parts.append(f"- 🟡 Средний приоритет: {len(medium)}")
    if low:
        summary_parts.append(f"- 🟢 Низкий приоритет: {len(low)}")
    
    # По типам
    if by_type:
        summary_parts.append("\n### По категориям:")
        for t, count in sorted(by_type.items(), key=lambda x: -x[1]):
            summary_parts.append(f"- {t}: {count}")
    
    # Архитектура
    if not architecture_compliance.overall_compliant:
        summary_parts.append("\n### ⚠️ Нарушения архитектуры:")
        for comp in architecture_compliance.missing_components[:3]:
            summary_parts.append(f"- Не реализован: {comp}")
        for violation in architecture_compliance.interface_violations[:3]:
            summary_parts.append(f"- {violation}")
    
    # Безопасность
    if not security_report.passed:
        summary_parts.append("\n### 🔒 Проблемы безопасности:")
        for finding in security_report.findings[:3]:
            summary_parts.append(f"- [{finding.severity.value}] {finding.vulnerability_type}")
    
    # Что нужно исправить
    if decision == ReviewDecision.NEEDS_REVISION:
        summary_parts.append("\n### 📝 Необходимо исправить:")
        for issue in (critical + high)[:5]:
            summary_parts.append(f"- [{issue.severity.value}] {issue.title}")
    
    return "\n".join(summary_parts)


def generate_suggestions(issues: List[ReviewIssue]) -> List[str]:
    """
    Генерирует общие рекомендации на основе найденных проблем
    """
    
    suggestions = []
    
    # Группируем по типам
    by_type = {}
    for issue in issues:
        t = issue.type
        by_type[t] = by_type.get(t, 0) + 1
    
    # Рекомендации по типам
    if by_type.get(IssueType.DOCUMENTATION, 0) > 2:
        suggestions.append("Добавьте docstrings ко всем публичным функциям и классам")
    
    if by_type.get(IssueType.TYPE_ERROR, 0) > 2:
        suggestions.append("Используйте type hints для улучшения читаемости и IDE поддержки")
    
    if by_type.get(IssueType.ERROR_HANDLING, 0) > 1:
        suggestions.append("Улучшите обработку ошибок - избегайте пустых except блоков")
    
    if by_type.get(IssueType.COMPLEXITY, 0) > 1:
        suggestions.append("Разбейте сложные функции на более мелкие и понятные")
    
    if by_type.get(IssueType.DUPLICATION, 0) > 0:
        suggestions.append("Вынесите повторяющийся код в отдельные функции/классы")
    
    if by_type.get(IssueType.SECURITY, 0) > 0:
        suggestions.append("Проведите дополнительный аудит безопасности перед релизом")
    
    if by_type.get(IssueType.PERFORMANCE, 0) > 1:
        suggestions.append("Рассмотрите профилирование кода для выявления узких мест")
    
    if by_type.get(IssueType.TESTING, 0) > 0:
        suggestions.append("Добавьте unit-тесты для критической бизнес-логики")
    
    # Общие рекомендации
    if not suggestions:
        if issues:
            suggestions.append("Исправьте найденные замечания и запросите повторное ревью")
        else:
            suggestions.append("Код выглядит хорошо! Можно добавить тесты для большей уверенности")
    
    return suggestions


# ============================================================================
# FILE ANALYSIS
# ============================================================================

def create_file_summaries(
    code_files: List[Dict[str, Any]],
    issues: List[ReviewIssue]
) -> List[FileSummary]:
    """
    Создаёт сводку по каждому файлу
    """
    
    summaries = []
    
    for file_data in code_files:
        path = file_data.get("path", "unknown")
        content = file_data.get("content", "")
        language = file_data.get("language", "unknown")
        
        # Считаем строки
        lines = content.count('\n') + 1 if content else 0
        
        # Проблемы в этом файле
        file_issues = [i for i in issues if i.file_path == path]
        critical = sum(1 for i in file_issues if i.severity == IssueSeverity.CRITICAL)
        high = sum(1 for i in file_issues if i.severity == IssueSeverity.HIGH)
        
        # Оценка файла
        if not file_issues:
            score = 10.0
        else:
            score = calculate_quality_score(file_issues, 1)
        
        # Рекомендации для файла
        recommendations = []
        for issue in file_issues[:3]:
            if issue.suggestion:
                recommendations.append(issue.suggestion)
        
        summaries.append(FileSummary(
            file_path=path,
            language=language,
            lines_of_code=lines,
            issues_count=len(file_issues),
            critical_count=critical,
            high_count=high,
            quality_score=score,
            recommendations=recommendations
        ))
    
    return summaries


# ============================================================================
# MAIN REVIEW FUNCTION
# ============================================================================

async def perform_code_review(
    code_files: List[Dict[str, Any]],
    architecture: Dict[str, Any],
    tech_stack: TechStack,
    repo_context: Dict[str, Any]
) -> ReviewResult:
    """
    Выполняет полное ревью кода
    """
    
    all_issues: List[ReviewIssue] = []
    
    # 1. Проверка соответствия архитектуре
    logger.info("Checking architecture compliance...")
    architecture_compliance, arch_issues = await check_architecture_compliance(
        code_files, architecture, tech_stack
    )
    all_issues.extend(arch_issues)
    
    # 2. Проверка безопасности
    logger.info("Checking security...")
    security_report, security_issues = await check_security(code_files, tech_stack)
    all_issues.extend(security_issues)
    
    # 3. Проверка качества кода
    logger.info("Checking code quality...")
    quality_issues = await check_code_quality(code_files, tech_stack)
    all_issues.extend(quality_issues)
    
    # 4. Принимаем решение
    decision, needs_revision, blocking_ids = make_review_decision(all_issues)
    
    # 5. Вычисляем метрики
    quality_score = calculate_quality_score(all_issues, len(code_files))
    detailed_scores = calculate_detailed_scores(all_issues)
    
    metrics = ReviewMetrics(
        total_files=len(code_files),
        total_lines=sum(f.get("content", "").count('\n') + 1 for f in code_files),
        total_issues=len(all_issues),
        critical_issues=sum(1 for i in all_issues if i.severity == IssueSeverity.CRITICAL),
        high_issues=sum(1 for i in all_issues if i.severity == IssueSeverity.HIGH),
        medium_issues=sum(1 for i in all_issues if i.severity == IssueSeverity.MEDIUM),
        low_issues=sum(1 for i in all_issues if i.severity == IssueSeverity.LOW),
        bugs=sum(1 for i in all_issues if i.type == IssueType.BUG),
        security_issues=sum(1 for i in all_issues if i.type == IssueType.SECURITY),
        performance_issues=sum(1 for i in all_issues if i.type == IssueType.PERFORMANCE),
        style_issues=sum(1 for i in all_issues if i.type == IssueType.STYLE),
        overall_quality_score=quality_score,
        maintainability_score=detailed_scores.get("maintainability", 10.0),
        security_score=detailed_scores.get("security", 10.0),
        performance_score=detailed_scores.get("performance", 10.0)
    )
    
    # 6. Создаём сводки по файлам
    file_summaries = create_file_summaries(code_files, all_issues)
    
    # 7. Генерируем рекомендации
    suggestions = generate_suggestions(all_issues)
    
    # 8. Генерируем summary
    summary = await generate_review_summary(
        all_issues, decision, quality_score,
        architecture_compliance, security_report
    )
    
    # 9. Обновляем метрики Prometheus
    REVIEWS_TOTAL.labels(decision=decision.value).inc()
    for issue in all_issues:
        ISSUES_FOUND.labels(
            severity=issue.severity.value,
            type=issue.type.value
        ).inc()
    
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
        security_report=security_report,
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
        
        # Извлекаем данные
        code_data = data.get("code", {})
        code_files = []
        if "code" in data and "files" in data["code"]:
            code_files = data["code"]["files"]
        elif "files" in data:
            code_files = data["files"]
        else:
            raise HTTPException(status_code=400, detail="No code files provided")
        
        architecture = data.get("architecture", {})
        tech_stack_data = data.get("tech_stack", {})
        tech_stack = TechStack(**tech_stack_data) if tech_stack_data else TechStack()
        repo_context = data.get("repo_context", {})
        
        logger.info(f"[{task_id[:8]}] Reviewing {len(code_files)} files, "
                   f"language: {tech_stack.primary_language}")
        
        # Выполняем ревью
        result = await perform_code_review(
            code_files=code_files,
            architecture=architecture,
            tech_stack=tech_stack,
            repo_context=repo_context
        )
        
        duration = time.time() - start_time
        REVIEW_DURATION.observe(duration)
        
        logger.info(f"[{task_id[:8]}] Review completed in {duration:.1f}s, "
                   f"decision: {result.decision.value}, "
                   f"issues: {len(result.issues)}, "
                   f"score: {result.quality_score}")
        
        return CodeReviewResponse(
            task_id=task_id,
            status="success",
            result=result,
            reviewed_files=len(code_files),
            duration_seconds=duration
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[{task_id[:8]}] Review error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ADDITIONAL ENDPOINTS
# ============================================================================

@app.post("/quick-check")
async def quick_security_check(request: Dict[str, Any]):
    """
    Быстрая проверка только на безопасность
    """
    
    code_files = request.get("files", [])
    tech_stack_data = request.get("tech_stack", {})
    tech_stack = TechStack(**tech_stack_data) if tech_stack_data else TechStack()
    
    security_report, issues = await check_security(code_files, tech_stack)
    
    return {
        "passed": security_report.passed,
        "findings_count": len(security_report.findings),
        "findings": [f.dict() for f in security_report.findings],
        "issues": [i.dict() for i in issues]
    }


@app.get("/thresholds")
async def get_thresholds():
    """
    Возвращает текущие пороги для approve
    """
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
    return generate_latest()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Code Reviewer Agent",
        "version": "2.0.0",
        "description": "Агент для проверки качества кода",
        "checks": [
            "Architecture compliance",
            "Security vulnerabilities",
            "Bugs and logic errors",
            "Performance issues",
            "Code style and readability",
            "Documentation coverage",
            "Error handling",
            "Type safety"
        ],
        "receives_from": ["code_writer", "architect"],
        "decisions": ["approved", "needs_revision", "rejected"],
        "endpoints": {
            "process": "POST /process - полное ревью",
            "quick_check": "POST /quick-check - быстрая проверка безопасности",
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