"""
Documentation Agent - Создаёт документацию на основе финального кода

Ответственности:
1. АВТОМАТИЧЕСКИ определяет какую документацию нужно создать
2. Анализ существующей документации и стиля
3. Генерация/обновление README
4. Создание API документации
5. Генерация документации кода (docstrings reference)
6. Создание CHANGELOG entries
7. Генерация architecture documentation
8. Создание user/developer guides

Получает:
- Финальный код от Code Writer
- Архитектуру от Architect
- Результаты ревью от Code Reviewer
- Контекст репозитория
- Технологический стек

Возвращает:
- Файлы документации (README, API docs, etc.)
- CHANGELOG entries
- Module documentation
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

from models import (
    DocType, DocFormat, DocLanguage, ChangeType,
    DocStyle, DocFile,
    ChangelogEntry, ChangelogVersion,
    ApiParameter, ApiResponse, ApiEndpoint, ApiDocumentation,
    FunctionDoc, ClassDoc, ModuleDoc,
    CodeFileInput, ArchitectureInput, ReviewInput,
    DocumentationRequest, DocumentationResponse,
    TechStack
)

from logging_config import setup_logging

# ============================================================================
# CONFIGURATION
# ============================================================================

logger = setup_logging("documentation")

OPENROUTER_MCP_URL = os.getenv("OPENROUTER_MCP_URL", "http://openrouter-mcp:8000")
LLM_TIMEOUT = 1000
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL")

# ============================================================================
# HTTP CLIENT
# ============================================================================

http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager"""
    global http_client
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(LLM_TIMEOUT))
    logger.info("Documentation Agent started")
    yield
    await http_client.aclose()
    logger.info("Documentation Agent stopped")


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Documentation Agent",
    description="Агент для создания документации на основе кода и архитектуры",
    version="2.1.0",
    lifespan=lifespan
)


# ============================================================================
# LLM HELPER
# ============================================================================

async def call_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 100000,
    step: str = "documentation_llm_request"
) -> str:
    """Вызов LLM через OpenRouter MCP"""

    if not system_prompt:
        system_prompt = """Ты опытный технический писатель с 15+ лет опыта.
Ты создаёшь:
- Понятную, структурированную документацию
- Полезные примеры кода
- Чёткие инструкции
- Профессиональные API reference

Ты учитываешь:
- Существующий стиль документации проекта
- Целевую аудиторию
- Лучшие практики документирования

ВАЖНО:
- Ты никогда не придумываешь, то чего не было коде или в архитектуре
- Всегда пишешь только о том, что действительно реализовано
- Никогда не ври

Возвращаешь ответы в Markdown или JSON когда это указано."""

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
                "step": step,
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
            "step": step,
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
        return json.loads(response)
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


def count_words(text: str) -> int:
    """Считает слова в тексте"""
    return len(text.split())


# ============================================================================
# AUTO-DETERMINE DOC TYPES
# ============================================================================

async def determine_doc_types(
    task: str,
    code_files: List[Dict[str, Any]],
    architecture: Dict[str, Any],
    review_result: Dict[str, Any],
    repo_context: Dict[str, Any],
    tech_stack: TechStack
) -> List[DocType]:
    """
    Автоматически определяет какие типы документации нужно создать
    на основе входных данных и контекста.
    
    Returns:
        List[DocType]: Список типов документации для генерации
    """
    
    doc_types = []
    key_files = repo_context.get("key_files", {})
    
    # 1. README - ВСЕГДА генерируем/обновляем
    doc_types.append(DocType.README)
    logger.info("  → README: ВКЛЮЧЁН (всегда)")
    
    # 2. API Documentation - если есть API endpoints в коде
    has_api = False
    api_indicators = ["@app.", "@router.", "def get", "def post", "def put", "def delete",
                      "async def", "route", "endpoint", "api", "controller", "FastAPI", "Flask", "Express"]
    
    for f in code_files:
        content = f.get("content", "").lower()
        path = f.get("path", "").lower()
        
        if any(indicator.lower() in content or indicator.lower() in path for indicator in api_indicators):
            has_api = True
            break
    
    if has_api:
        doc_types.append(DocType.API)
        logger.info("  → API docs: ВКЛЮЧЁН (обнаружены API endpoints)")
    else:
        logger.info("  → API docs: ПРОПУЩЕН (нет API endpoints)")
    
    # 3. Architecture Documentation - если есть данные от архитектора
    if architecture and (architecture.get("components") or architecture.get("patterns")):
        doc_types.append(DocType.ARCHITECTURE)
        logger.info(f"  → Architecture: ВКЛЮЧЁН (компонентов: {len(architecture.get('components', []))})")
    else:
        logger.info("  → Architecture: ПРОПУЩЕН (нет данных архитектуры)")
    
    # 4. CHANGELOG - если есть ревью или это новая фича
    task_lower = task.lower()
    is_feature = any(word in task_lower for word in ["добавить", "создать", "реализовать", "add", "create", "implement", "feature"])
    is_fix = any(word in task_lower for word in ["исправить", "fix", "bug", "ошибка", "баг"])
    
    if review_result or is_feature or is_fix:
        doc_types.append(DocType.CHANGELOG)
        logger.info(f"  → CHANGELOG: ВКЛЮЧЁН (feature={is_feature}, fix={is_fix}, has_review={bool(review_result)})")
    else:
        logger.info("  → CHANGELOG: ПРОПУЩЕН")
    
    # 5. Code Reference - если много кода (более 3 файлов) или есть классы
    has_classes = False
    for f in code_files:
        content = f.get("content", "")
        if "class " in content:
            has_classes = True
            break
    
    if len(code_files) >= 3 or has_classes:
        doc_types.append(DocType.CODE)
        logger.info(f"  → Code Reference: ВКЛЮЧЁН (файлов: {len(code_files)}, классы: {has_classes})")
    else:
        logger.info(f"  → Code Reference: ПРОПУЩЕН (файлов: {len(code_files)}, мало для reference)")
    
    # 6. CONTRIBUTING - только если это новый проект (нет существующего CONTRIBUTING)
    has_contributing = any("contributing" in k.lower() for k in key_files.keys())
    
    if not has_contributing and len(code_files) >= 5:
        doc_types.append(DocType.CONTRIBUTING)
        logger.info("  → CONTRIBUTING: ВКЛЮЧЁН (нет существующего, проект достаточно большой)")
    else:
        logger.info(f"  → CONTRIBUTING: ПРОПУЩЕН (exists={has_contributing})")
    
    logger.info(f"Итого типов документации: {len(doc_types)} - {[dt.value for dt in doc_types]}")
    
    return doc_types


# ============================================================================
# DOCUMENTATION STYLE ANALYSIS
# ============================================================================

async def analyze_doc_style(repo_context: Dict[str, Any]) -> DocStyle:
    """
    Анализирует существующий стиль документации проекта
    """
    
    key_files = repo_context.get("key_files", {})
    
    # Ищем существующую документацию
    doc_files = {}
    for path, content in key_files.items():
        lower_path = path.lower()
        if any(x in lower_path for x in ["readme", "doc", "guide", "changelog", "contributing"]):
            doc_files[path] = content[:3000] if content else ""
    
    if not doc_files:
        # Возвращаем стиль по умолчанию
        return DocStyle()
    
    prompt = f"""
Проанализируй стиль документации в проекте.

## СУЩЕСТВУЮЩАЯ ДОКУМЕНТАЦИЯ:
{json.dumps(doc_files, indent=2, ensure_ascii=False)}

## ОПРЕДЕЛИ:

1. Формат: markdown, rst, asciidoc
2. Язык: ru, en
3. Стиль заголовков: atx (#) или setext
4. Используются ли badges
5. Есть ли Table of Contents
6. Используются ли emoji
7. Какие секции есть в README

## ФОРМАТ ОТВЕТА (JSON):
{{
    "format": "markdown",
    "language": "ru",
    "heading_style": "atx",
    "code_fence": "```",
    "list_marker": "-",
    "use_badges": true,
    "use_toc": true,
    "use_emojis": true,
    "readme_sections": ["description", "installation", "usage", "api", "license"]
}}
"""
    
    response = await call_llm(prompt, step="doc_style_analysis")
    parsed = parse_json_response(response)
    
    if parsed:
        try:
            doc_format = DocFormat(parsed.get("format", "markdown"))
        except ValueError:
            doc_format = DocFormat.MARKDOWN
        
        try:
            doc_lang = DocLanguage(parsed.get("language", "ru"))
        except ValueError:
            doc_lang = DocLanguage.RUSSIAN
        
        return DocStyle(
            format=doc_format,
            language=doc_lang,
            heading_style=parsed.get("heading_style", "atx"),
            code_fence=parsed.get("code_fence", "```"),
            list_marker=parsed.get("list_marker", "-"),
            use_badges=parsed.get("use_badges", True),
            use_toc=parsed.get("use_toc", True),
            use_emojis=parsed.get("use_emojis", True),
            readme_sections=parsed.get("readme_sections", [])
        )
    
    return DocStyle()


# ============================================================================
# README GENERATION
# ============================================================================

async def generate_readme(
    task: str,
    code_files: List[Dict[str, Any]],
    architecture: Dict[str, Any],
    tech_stack: TechStack,
    doc_style: DocStyle,
    existing_readme: Optional[str] = None
) -> DocFile:
    """
    Генерирует или обновляет README
    """
    
    # Собираем информацию о коде
    code_summary = []
    for f in code_files[:10]:
        code_summary.append({
            "path": f.get("path", ""),
            "description": f.get("description", ""),
            "language": f.get("language", "")
        })
    
    # Информация об архитектуре
    components = architecture.get("components", [])[:10] if architecture else []
    patterns = architecture.get("patterns", []) if architecture else []
    
    # Формируем список секций
    sections = doc_style.readme_sections or [
        "description", "features", "installation", 
        "quick_start", "usage", "api", "configuration",
        "testing", "contributing", "license"
    ]
    
    existing_section = ""
    if existing_readme:
        existing_section = f"""
## СУЩЕСТВУЮЩИЙ README (обнови его):
{existing_readme[:5000]}
"""
    
    emoji_note = "Используй emoji для секций (📦, 🚀, ⚙️, etc.)" if doc_style.use_emojis else "Не используй emoji"
    toc_note = "Добавь Table of Contents в начало" if doc_style.use_toc else ""
    badge_note = "Добавь badges (build status, version, license)" if doc_style.use_badges else ""
    
    prompt = f"""
Создай профессиональный README.md для проекта.

## ЗАДАЧА (что было добавлено):
{task}

## НОВЫЙ КОД:
{json.dumps(code_summary, indent=2, ensure_ascii=False)}

## АРХИТЕКТУРА:
- Компоненты: {json.dumps([c.get("name") if isinstance(c, dict) else c for c in components], ensure_ascii=False)}
- Паттерны: {', '.join(patterns) if patterns else 'N/A'}

## ТЕХНОЛОГИИ:
- Язык: {tech_stack.primary_language}
- Фреймворки: {', '.join(tech_stack.frameworks) if tech_stack.frameworks else 'N/A'}
- Тестирование: {', '.join(tech_stack.testing_frameworks) if tech_stack.testing_frameworks else 'N/A'}
- Инструменты: {', '.join(tech_stack.tools) if tech_stack.tools else 'N/A'}

## СТИЛЬ ДОКУМЕНТАЦИИ:
- Язык: {'Русский' if doc_style.language == DocLanguage.RUSSIAN else 'English'}
- {emoji_note}
- {toc_note}
- {badge_note}

## СЕКЦИИ ДЛЯ ВКЛЮЧЕНИЯ:
{', '.join(sections)}
{existing_section}

## ТРЕБОВАНИЯ:
1. Профессиональный, понятный стиль
2. Примеры кода с подсветкой синтаксиса
3. Чёткие инструкции по установке
4. Примеры использования
5. Если обновляешь существующий - сохрани структуру, добавь новое

Верни только Markdown контент, без ```markdown блоков.
"""
    
    content = await call_llm(prompt, max_tokens=100000, step="readme_generation")
    
    # Очищаем от markdown блоков
    content = re.sub(r'^```(?:markdown)?\n?', '', content)
    content = re.sub(r'\n?```$', '', content)
    content = content.strip()
    
    # Определяем действие
    action = "update" if existing_readme else "create"
    
    return DocFile(
        path="README.md",
        content=content,
        doc_type=DocType.README,
        format=doc_style.format,
        description="Project README",
        action=action,
        word_count=count_words(content)
    )


# ============================================================================
# API DOCUMENTATION
# ============================================================================

async def extract_api_endpoints(
    code_files: List[Dict[str, Any]],
    tech_stack: TechStack
) -> List[ApiEndpoint]:
    """
    Извлекает API endpoints из кода
    """
    
    # Собираем код с API
    api_code = []
    for f in code_files:
        path = f.get("path", "").lower()
        content = f.get("content", "")
        
        # Ищем файлы с API
        if any(x in path for x in ["route", "api", "endpoint", "controller", "view"]):
            api_code.append({"path": f.get("path"), "content": content[:4000]})
        elif any(x in content.lower() for x in ["@app.", "@router.", "def get", "def post", "async def", "route", "endpoint", "api", "controller", "FastAPI", "Flask", "Express"]):
            api_code.append({"path": f.get("path"), "content": content[:4000]})
    
    if not api_code:
        return []
    
    prompt = f"""
Извлеки API endpoints из кода.

## ФРЕЙМВОРКИ:
{', '.join(tech_stack.frameworks) if tech_stack.frameworks else 'Unknown'}

## КОД:
{json.dumps(api_code, indent=2, ensure_ascii=False)}

## ФОРМАТ ОТВЕТА (JSON):
{{
    "endpoints": [
        {{
            "method": "POST",
            "path": "/api/auth/login",
            "summary": "Авторизация пользователя",
            "description": "Авторизует пользователя и возвращает JWT токен",
            "tags": ["auth"],
            "parameters": [
                {{
                    "name": "username",
                    "type": "string",
                    "required": true,
                    "description": "Имя пользователя",
                    "location": "body"
                }}
            ],
            "request_body": {{
                "content_type": "application/json",
                "example": {{"username": "user", "password": "pass"}}
            }},
            "responses": [
                {{
                    "status_code": 200,
                    "description": "Успешная авторизация",
                    "example": {{"access_token": "...", "token_type": "bearer"}}
                }},
                {{
                    "status_code": 401,
                    "description": "Неверные credentials"
                }}
            ],
            "authentication": "None"
        }}
    ]
}}
"""
    
    response = await call_llm(prompt, step="api_endpoints_extraction")
    parsed = parse_json_response(response)
    
    endpoints = []
    
    if parsed:
        for ep_data in parsed.get("endpoints", []):
            parameters = []
            for param in ep_data.get("parameters", []):
                parameters.append(ApiParameter(**param))
            
            responses = []
            for resp in ep_data.get("responses", []):
                responses.append(ApiResponse(**resp))
            
            endpoints.append(ApiEndpoint(
                method=ep_data.get("method", "GET"),
                path=ep_data.get("path", ""),
                summary=ep_data.get("summary", ""),
                description=ep_data.get("description", ""),
                tags=ep_data.get("tags", []),
                parameters=parameters,
                request_body=ep_data.get("request_body"),
                responses=responses,
                authentication=ep_data.get("authentication")
            ))
    
    return endpoints


async def generate_api_documentation(
    endpoints: List[ApiEndpoint],
    tech_stack: TechStack,
    doc_style: DocStyle
) -> Optional[DocFile]:
    """
    Генерирует API документацию
    """
    
    if not endpoints:
        logger.info("No API endpoints found, skipping API documentation")
        return None
    
    endpoints_info = [ep.dict() for ep in endpoints]
    
    lang_note = "Пиши на русском языке" if doc_style.language == DocLanguage.RUSSIAN else "Write in English"
    
    prompt = f"""
Создай полную API документацию в Markdown.

## ENDPOINTS:
{json.dumps(endpoints_info, indent=2, ensure_ascii=False)}

## ФРЕЙМВОРК:
{', '.join(tech_stack.frameworks) if tech_stack.frameworks else 'Unknown'}

## ТРЕБОВАНИЯ:
1. {lang_note}
2. Для каждого endpoint:
   - Описание
   - HTTP метод и путь
   - Параметры с типами
   - Request body (если есть)
   - Responses с примерами
   - Примеры curl/httpie
3. Группируй по тегам/ресурсам
4. Добавь Table of Contents
5. Добавь секцию Authentication если нужно

## ФОРМАТ:
Markdown с code blocks для примеров.

Верни только Markdown контент.
"""
    
    content = await call_llm(prompt, max_tokens=100000, step="api_docs_generation")
    
    content = re.sub(r'^```(?:markdown)?\n?', '', content)
    content = re.sub(r'\n?```$', '', content)
    content = content.strip()
    
    return DocFile(
        path="docs/api.md",
        content=content,
        doc_type=DocType.API,
        format=doc_style.format,
        description="API Documentation",
        action="create",
        word_count=count_words(content)
    )


# ============================================================================
# CODE DOCUMENTATION
# ============================================================================

async def generate_code_documentation(
    code_files: List[Dict[str, Any]],
    architecture: Dict[str, Any],
    tech_stack: TechStack,
    doc_style: DocStyle
) -> DocFile:
    """
    Генерирует документацию кода (module reference)
    """
    
    # Собираем информацию о компонентах
    components = architecture.get("components", []) if architecture else []
    interfaces = architecture.get("interfaces", []) if architecture else []
    
    # Собираем информацию из кода
    code_info = []
    for f in code_files[:50]:
        code_info.append({
            "path": f.get("path", ""),
            "description": f.get("description", ""),
            "classes": f.get("classes", []),
            "functions": f.get("functions", []),
            "content_preview": f.get("content", "")[:15000]
        })
    
    lang_note = "Пиши на русском языке" if doc_style.language == DocLanguage.RUSSIAN else "Write in English"
    
    prompt = f"""
Создай документацию кода (Code Reference) в Markdown.

## АРХИТЕКТУРА:
### Компоненты:
{json.dumps(components[:10], indent=2, ensure_ascii=False)}

### Интерфейсы:
{json.dumps(interfaces[:5], indent=2, ensure_ascii=False)}

## КОД:
{json.dumps(code_info, indent=2, ensure_ascii=False)}

## ТЕХНОЛОГИИ:
- Язык: {tech_stack.primary_language}

## ТРЕБОВАНИЯ:
1. {lang_note}
2. Документируй каждый модуль:
   - Описание модуля
   - Классы с описанием методов
   - Функции с параметрами
   - Примеры использования
3. Группируй по модулям/пакетам
4. Добавь Table of Contents
5. Используй code blocks для примеров

Верни только Markdown контент.
"""
    
    content = await call_llm(prompt, max_tokens=100000, step="code_docs_generation")
    
    content = re.sub(r'^```(?:markdown)?\n?', '', content)
    content = re.sub(r'\n?```$', '', content)
    content = content.strip()
    
    return DocFile(
        path="docs/code-reference.md",
        content=content,
        doc_type=DocType.CODE,
        format=doc_style.format,
        description="Code Reference Documentation",
        action="create",
        word_count=count_words(content)
    )


# ============================================================================
# ARCHITECTURE DOCUMENTATION
# ============================================================================

async def generate_architecture_documentation(
    architecture: Dict[str, Any],
    tech_stack: TechStack,
    doc_style: DocStyle
) -> Optional[DocFile]:
    """
    Генерирует документацию архитектуры
    """
    
    if not architecture:
        logger.info("No architecture data, skipping architecture documentation")
        return None
    
    components = architecture.get("components", [])
    patterns = architecture.get("patterns", [])
    file_structure = architecture.get("file_structure", [])
    diagrams = architecture.get("diagrams", {})
    recommendations = architecture.get("recommendations", [])
    integration_points = architecture.get("integration_points", [])
    
    # Формируем секцию диаграмм
    diagrams_section = ""
    if diagrams:
        for diagram_type, plantuml_code in diagrams.items():
            diagrams_section += f"""
        ### {diagram_type.replace('_', ' ').title()} Diagram

        ```plantuml
        {plantuml_code}
        """

        lang_note = "Пиши на русском языке" if doc_style.language == DocLanguage.RUSSIAN else "Write in English"

        prompt = f"""
        Создай документацию архитектуры в Markdown.

        КОМПОНЕНТЫ:
        {json.dumps(components[:50], indent=2, ensure_ascii=False)}

        ПАТТЕРНЫ:
        {json.dumps(patterns, indent=2, ensure_ascii=False)}

        СТРУКТУРА ФАЙЛОВ:
        {json.dumps(file_structure[:20], indent=2, ensure_ascii=False)}

        ТОЧКИ ИНТЕГРАЦИИ:
        {json.dumps(integration_points[:10], indent=2, ensure_ascii=False)}

        РЕКОМЕНДАЦИИ:
        {json.dumps(recommendations, indent=2, ensure_ascii=False)}

        ТЕХНОЛОГИИ:
        Язык: {tech_stack.primary_language}
        Фреймворки: {', '.join(tech_stack.frameworks) if tech_stack.frameworks else 'N/A'}
        Паттерны: {', '.join(tech_stack.architecture_patterns) if tech_stack.architecture_patterns else 'N/A'}
        ТРЕБОВАНИЯ:
        {lang_note}
        Секции:
        Обзор архитектуры
        Компоненты и их ответственности
        Слои приложения
        Паттерны проектирования
        Структура проекта
        Зависимости между компонентами
        Диаграммы
        Решения и обоснования (ADR)
        Добавь Table of Contents
        ДИАГРАММЫ (включи в документ):
        {diagrams_section if diagrams_section else "Диаграммы не предоставлены"}

        Верни только Markdown контент.
        """
    content = await call_llm(prompt, max_tokens=100000, step="architecture_docs_generation")

    content = re.sub(r'^```(?:markdown)?\n?', '', content)
    content = re.sub(r'\n?```$', '', content)
    content = content.strip()

    return DocFile(
        path="docs/architecture.md",
        content=content,
        doc_type=DocType.ARCHITECTURE,
        format=doc_style.format,
        description="Architecture Documentation",
        action="create",
        word_count=count_words(content)
    )

# ============================================================================
# CHANGELOG GENERATION
# ============================================================================
async def generate_changelog(
task: str,
code_files: List[Dict[str, Any]],
review_result: Dict[str, Any],
existing_changelog: Optional[str] = None
) -> Tuple[DocFile, ChangelogVersion]:
    """
    Генерирует CHANGELOG entry
    """

    # Собираем информацию об изменениях
    files_info = []
    for f in code_files[:20]:
        files_info.append({
            "path": f.get("path", ""),
            "action": f.get("action", "create"),
            "description": f.get("description", "")
        })

    quality_score = review_result.get("quality_score", 0) if review_result else 0

    prompt = f"""
Создай запись для CHANGELOG на основе изменений.

ЗАДАЧА:
{task}

ИЗМЕНЁННЫЕ ФАЙЛЫ:
{json.dumps(files_info, indent=2, ensure_ascii=False)}

КАЧЕСТВО КОДА:
{quality_score}/10

ФОРМАТ ОТВЕТА (JSON):
{{
"version": "X.Y.Z",
"entries": [
{{
"change_type": "added/changed/fixed/deprecated/removed/security",
"description": "Описание изменения",
"component": "опционально: какой компонент затронут"
}}
]
}}

ПРАВИЛА:
added: новая функциональность

changed: изменения в существующей функциональности

fixed: исправления багов

deprecated: скоро будет удалено

removed: удалённая функциональность

security: исправления безопасности
"""

    response = await call_llm(prompt, step="changelog_generation")
    parsed = parse_json_response(response)

    version = "0.1.0"
    entries = []

    if parsed:
        version = parsed.get("version", "0.1.0")
        for entry_data in parsed.get("entries", []):
            try:
                change_type = ChangeType(entry_data.get("change_type", "added"))
            except ValueError:
                change_type = ChangeType.ADDED
            entries.append(ChangelogEntry(
                change_type=change_type,
                description=entry_data.get("description", ""),
                component=entry_data.get("component")
            ))

    if not entries:
        entries.append(ChangelogEntry(
        change_type=ChangeType.ADDED,
        description=task[:100],
        component=None
    ))

    changelog_version = ChangelogVersion(
        version=version,
        entries=entries
    )

    content = format_changelog_markdown(changelog_version, existing_changelog)

    return DocFile(
        path="CHANGELOG.md",
        content=content,
        doc_type=DocType.CHANGELOG,
        format=DocFormat.MARKDOWN,
        description="Changelog",
        action="update" if existing_changelog else "create",
        word_count=count_words(content)
    ), changelog_version

def format_changelog_markdown(
version: ChangelogVersion,
existing_changelog: Optional[str] = None
) -> str:
    """
    Форматирует CHANGELOG в Markdown
    """
    # Группируем entries по типу
    by_type = {}
    for entry in version.entries:
        t = entry.change_type.value.capitalize()
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(entry)

    # Формируем новую секцию
    new_section = f"## [{version.version}] - {version.date}\n\n"

    type_order = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]

    for change_type in type_order:
        if change_type in by_type:
            new_section += f"### {change_type}\n\n"
            for entry in by_type[change_type]:
                component = f"**{entry.component}**: " if entry.component else ""
                new_section += f"- {component}{entry.description}\n"
            new_section += "\n"

    # Если есть существующий CHANGELOG - добавляем в начало
    if existing_changelog:
        # Ищем место после заголовка
        header_match = re.search(r'^#\s+Changelog.*?\n', existing_changelog, re.IGNORECASE)
        
        if header_match:
            header_end = header_match.end()
            content = (
                existing_changelog[:header_end] + 
                "\n" + new_section + 
                existing_changelog[header_end:]
            )
        else:
            content = f"# Changelog\n\n{new_section}\n{existing_changelog}"
    else:
        content = f"""# Changelog
    All notable changes to this project will be documented in this file.

    The format is based on Keep a Changelog,
    and this project adheres to Semantic Versioning.

    {new_section}"""

    return content

# ============================================================================
# CONTRIBUTING GUIDE
# ============================================================================

async def generate_contributing_guide(
tech_stack: TechStack,
doc_style: DocStyle
) -> DocFile:
    """
    Генерирует CONTRIBUTING.md
    """

    lang_note = "Пиши на русском языке" if doc_style.language == DocLanguage.RUSSIAN else "Write in English"

    prompt = f"""
    Создай CONTRIBUTING.md для проекта.

    ТЕХНОЛОГИИ:
    Язык: {tech_stack.primary_language}
    Фреймворки: {', '.join(tech_stack.frameworks) if tech_stack.frameworks else 'N/A'}
    Тестирование: {', '.join(tech_stack.testing_frameworks) if tech_stack.testing_frameworks else 'N/A'}
    Package Manager: {', '.join(tech_stack.package_managers) if tech_stack.package_managers else 'N/A'}
    ТРЕБОВАНИЯ:
    {lang_note}
    Секции:
    Как начать разработку
    Настройка окружения
    Code style guidelines
    Процесс создания PR
    Правила коммитов (Conventional Commits)
    Процесс ревью
    Тестирование
    Будь конкретным для стека технологий
    Верни только Markdown контент.
    """

    content = await call_llm(prompt, max_tokens=100000, step="contributing_guide_generation")

    content = re.sub(r'^```(?:markdown)?\n?', '', content)
    content = re.sub(r'\n?```$', '', content)
    content = content.strip()

    return DocFile(
        path="CONTRIBUTING.md",
        content=content,
        doc_type=DocType.CONTRIBUTING,
        format=doc_style.format,
        description="Contributing Guide",
        action="create",
        word_count=count_words(content)
    )

# ============================================================================
# MAIN DOCUMENTATION GENERATION
# ============================================================================
async def generate_documentation(
task: str,
code_files: List[Dict[str, Any]],
architecture: Dict[str, Any],
review_result: Dict[str, Any],
tech_stack: TechStack,
repo_context: Dict[str, Any],
doc_types: List[DocType]
) -> List[DocFile]:
    """
    Генерирует всю запрошенную документацию
    """

    files = []

    # 1. Анализируем стиль
    logger.info("Analyzing documentation style...")
    doc_style = await analyze_doc_style(repo_context)

    # Получаем существующие файлы
    key_files = repo_context.get("key_files", {})
    existing_readme = key_files.get("README.md")
    existing_changelog = key_files.get("CHANGELOG.md")

    # 2. README
    if DocType.README in doc_types:
        logger.info("Generating README...")
        readme = await generate_readme(
            task=task,
            code_files=code_files,
            architecture=architecture,
            tech_stack=tech_stack,
            doc_style=doc_style,
            existing_readme=existing_readme
        )
        files.append(readme)

    # 3. API Documentation
    if DocType.API in doc_types:
        logger.info("Generating API documentation...")
        endpoints = await extract_api_endpoints(code_files, tech_stack)
        api_doc = await generate_api_documentation(endpoints, tech_stack, doc_style)
        if api_doc:
            files.append(api_doc)

    # 4. Code Documentation
    if DocType.CODE in doc_types:
        logger.info("Generating code documentation...")
        code_doc = await generate_code_documentation(
            code_files, architecture, tech_stack, doc_style
        )
        files.append(code_doc)

    # 5. Architecture Documentation
    if DocType.ARCHITECTURE in doc_types:
        logger.info("Generating architecture documentation...")
        arch_doc = await generate_architecture_documentation(
            architecture, tech_stack, doc_style
        )
        if arch_doc:
            files.append(arch_doc)

    # 6. CHANGELOG
    if DocType.CHANGELOG in doc_types:
        logger.info("Generating CHANGELOG...")
        changelog_file, _ = await generate_changelog(
            task, code_files, review_result, existing_changelog
        )
        files.append(changelog_file)

    # 7. CONTRIBUTING
    if DocType.CONTRIBUTING in doc_types:
        logger.info("Generating CONTRIBUTING guide...")
        contributing = await generate_contributing_guide(tech_stack, doc_style)
        files.append(contributing)

    return files

# ============================================================================
# MAIN ENDPOINT
# ============================================================================
@app.post("/process", response_model=DocumentationResponse)
async def process_documentation(request: DocumentationRequest):
    """
    Основной endpoint для генерации документации.

    АВТОМАТИЧЕСКИ определяет какие типы документации нужно создать
    на основе входных данных.
    """

    start_time = time.time()
    task_id = str(uuid.uuid4())

    try:
        data = request.data
        
        logger.info(f"[{task_id[:8]}] Starting documentation generation: {request.task[:100]}")
        logger.info(f"[{task_id[:8]}] Received data keys: {list(data.keys())}")
        
        # Извлекаем данные с подробным логированием
        code_data = data.get("code", {})
        code_files = code_data.get("files", [])
        if not code_files and "files" in data:
            code_files = data["files"]
        
        logger.info(f"[{task_id[:8]}] Code files count: {len(code_files)}")
        
        architecture = data.get("architecture", {})
        logger.info(f"[{task_id[:8]}] Architecture: components={len(architecture.get('components', []))}, "
                f"patterns={len(architecture.get('patterns', []))}")
        
        review_result = data.get("review", {})
        logger.info(f"[{task_id[:8]}] Review: present={bool(review_result)}, "
                f"score={review_result.get('quality_score', 'N/A')}")
        
        tech_stack_data = data.get("tech_stack", {})
        tech_stack = TechStack(**tech_stack_data) if tech_stack_data else TechStack()
        logger.info(f"[{task_id[:8]}] Tech stack: {tech_stack.primary_language}, "
                f"frameworks={tech_stack.frameworks}")
        
        repo_context = data.get("repo_context", {})
        logger.info(f"[{task_id[:8]}] Repo context: key_files={len(repo_context.get('key_files', {}))}")
        
        # =======================================================================
        # АВТОМАТИЧЕСКОЕ ОПРЕДЕЛЕНИЕ ТИПОВ ДОКУМЕНТАЦИИ
        # =======================================================================
        logger.info(f"[{task_id[:8]}] Auto-determining documentation types...")
        
        doc_types = await determine_doc_types(
            task=request.task,
            code_files=code_files,
            architecture=architecture,
            review_result=review_result,
            repo_context=repo_context,
            tech_stack=tech_stack
        )
        
        logger.info(f"[{task_id[:8]}] Will generate: {[dt.value for dt in doc_types]}")
        
        # Генерируем документацию
        files = await generate_documentation(
            task=request.task,
            code_files=code_files,
            architecture=architecture,
            review_result=review_result,
            tech_stack=tech_stack,
            repo_context=repo_context,
            doc_types=doc_types
        )
        
        # Анализируем стиль для ответа
        doc_style = await analyze_doc_style(repo_context)
        
        duration = time.time() - start_time
        total_words = sum(f.word_count for f in files)
        
        logger.info(f"[{task_id[:8]}] Documentation generated in {duration:.1f}s, "
                f"files: {len(files)}, words: {total_words}")
        
        return DocumentationResponse(
            task_id=task_id,
            status="success" if files else "error",
            files=files,
            doc_style=doc_style,
            sections_created=[f.doc_type.value for f in files],
            total_files=len(files),
            total_words=total_words,
            duration_seconds=duration
        )

    except Exception as e:
        logger.exception(f"[{task_id[:8]}] Documentation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ADDITIONAL ENDPOINTS
# ============================================================================
@app.post("/readme")
async def generate_readme_only(request: Dict[str, Any]):
    """
    Генерация только README
    """

    task = request.get("task", "")
    code_files = request.get("code_files", [])
    architecture = request.get("architecture", {})
    tech_stack_data = request.get("tech_stack", {})
    tech_stack = TechStack(**tech_stack_data) if tech_stack_data else TechStack()
    existing_readme = request.get("existing_readme")

    doc_style = DocStyle()

    readme = await generate_readme(
        task=task,
        code_files=code_files,
        architecture=architecture,
        tech_stack=tech_stack,
        doc_style=doc_style,
        existing_readme=existing_readme
    )

    return readme.dict()

@app.post("/api-docs")
async def generate_api_docs_only(request: Dict[str, Any]):
    """
    Генерация только API документации
    """

    code_files = request.get("code_files", [])
    tech_stack_data = request.get("tech_stack", {})
    tech_stack = TechStack(**tech_stack_data) if tech_stack_data else TechStack()

    endpoints = await extract_api_endpoints(code_files, tech_stack)
    doc_style = DocStyle()

    api_doc = await generate_api_documentation(endpoints, tech_stack, doc_style)

    return {
        "file": api_doc.dict() if api_doc else None,
        "endpoints_found": len(endpoints)
    }

@app.post("/changelog")
async def generate_changelog_only(request: Dict[str, Any]):
    """
    Генерация только CHANGELOG entry
    """
    task = request.get("task", "")
    code_files = request.get("code_files", [])
    review_result = request.get("review_result", {})
    existing_changelog = request.get("existing_changelog")

    changelog_file, changelog_version = await generate_changelog(
        task, code_files, review_result, existing_changelog
    )

    return {
        "file": changelog_file.dict(),
        "version": changelog_version.dict()
    }

@app.get("/health")
async def health_check():
    """Health check"""
    return {
    "status": "healthy",
    "service": "documentation",
    "version": "2.1.0",
    "timestamp": datetime.now().isoformat(),
    "features": {
    "auto_doc_types": True,
    "supported_types": [dt.value for dt in DocType]
    }
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
    "service": "Documentation Agent",
    "version": "2.1.0",
    "description": "Агент для создания документации на основе кода и архитектуры",
    "auto_detection": "Автоматически определяет какие типы документации нужно создать",
    "doc_types": [dt.value for dt in DocType],
    "receives_from": ["code_writer", "architect", "code_reviewer"],
    "outputs": [
    "README.md",
    "docs/api.md",
    "docs/code-reference.md",
    "docs/architecture.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md"
    ],
    "endpoints": {
    "process": "POST /process - полная генерация (авто-определение типов)",
    "readme": "POST /readme - только README",
    "api_docs": "POST /api-docs - только API docs",
    "changelog": "POST /changelog - только CHANGELOG",
    "health": "GET /health"
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