"""
Architect Agent - Проектирует архитектуру ДО написания кода

Ответственности:
1. Анализ существующей архитектуры репозитория
2. Проектирование новых компонентов
3. Определение интерфейсов и контрактов
4. Планирование структуры файлов
5. Выбор паттернов проектирования
6. Определение зависимостей
7. Создание архитектурных диаграмм
8. Планирование интеграции с существующим кодом

Получает:
- Описание задачи
- Контекст репозитория
- Технологический стек

Возвращает:
- Спецификации компонентов
- Интерфейсы
- Структуру файлов
- Паттерны
- Диаграммы (PlantUML)
- Рекомендации
"""

import os
import json
import logging
import re
import time
import uuid
import base64
import zlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
import httpx
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from logging_config import setup_logging

from models import (
    ComponentType, RelationType, DiagramType, PatternCategory,
    MethodParameter, MethodSpec, PropertySpec, ComponentSpec,
    ComponentRelation, InterfaceSpec, FileSpec, DirectorySpec,
    PatternRecommendation, DiagramSpec, IntegrationPoint, ExternalDependency,
    ExistingArchitecture, ArchitectureDesign,
    ArchitectRequest, ArchitectResponse, TechStack
)

# ============================================================================
# CONFIGURATION
# ============================================================================

OPENROUTER_MCP_URL = os.getenv("OPENROUTER_MCP_URL", "http://openrouter-proxy:8000")
LLM_TIMEOUT = 1000
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL")

logger = setup_logging("architect")

# ============================================================================
# PROMETHEUS METRICS
# ============================================================================

# Стандартизированные метрики для всех агентов
AGENT_REQUESTS_TOTAL = Counter('agent_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
AGENT_RESPONSE_TIME_SECONDS_BUCKET = Histogram('agent_response_time_seconds_bucket', 'Request duration',
                            buckets=[0.5, 1, 2, 5, 10, 30, 60, 120, 300], labelnames=['method', 'endpoint'])
AGENT_ACTIVE_REQUESTS = Gauge('agent_active_requests', 'Number of active requests', ['method', 'endpoint'])

# Общие метрики для всех агентов
PM_AGENT_STATUS = Gauge('pm_agent_status', 'Agent status', ['agent_name'])
PM_SYSTEM_ERRORS_TOTAL = Counter('pm_system_errors_total', 'Total system errors', ['agent_name', 'error_type'])

# Стандартизированные метрики для всех агентов
PM_AGENT_CALLS = Counter('pm_agent_calls_total', 'Agent calls', ['agent_name', 'status'])
PM_AGENT_RESPONSE_TIME_SECONDS_BUCKET = Histogram('pm_agent_response_time_seconds_bucket', 'Agent response time', ['agent_name'], buckets=[0.5, 1, 2, 5, 10, 30, 60, 120, 300])
PM_ACTIVE_TASKS = Gauge('pm_active_tasks', 'Currently processing tasks', ['method', 'endpoint'])
PM_TASKS_TOTAL = Counter('pm_tasks_total', 'Total tasks processed', ['status', 'method', 'endpoint'])
PM_TASK_DURATION = Histogram('pm_task_duration_seconds_bucket', 'Task duration', buckets=[30, 60, 120, 300, 600, 1200])

# ============================================================================
# HTTP CLIENT
# ============================================================================

http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager"""
    global http_client
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(LLM_TIMEOUT))
    
    # Устанавливаем статус агента при запуске
    PM_AGENT_STATUS.labels(agent_name="architect").set(1)  # 1 = online
    
    logger.info("Architect Agent started")
    yield
    
    # Устанавливаем статус агента при остановке
    PM_AGENT_STATUS.labels(agent_name="architect").set(0)  # 0 = offline
    
    await http_client.aclose()
    logger.info("Architect Agent stopped")


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Architect Agent",
    description="Агент для проектирования архитектуры ПО",
    version="2.0.0",
    lifespan=lifespan
)


# ============================================================================
# PROMETHEUS MIDDLEWARE
# ============================================================================

@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    """Middleware для отслеживания HTTP метрик"""
    # Исключаем эндпоинты /health и /metrics из метрик
    if request.url.path in ["/health", "/metrics"]:
        return await call_next(request)
    
    agent_name = "architect_agent"
    AGENT_ACTIVE_REQUESTS.labels(method=request.method, endpoint=request.url.path).inc()
    PM_ACTIVE_TASKS.labels(method=request.method, endpoint=request.url.path).inc()
    start_time = time.time()
    try:
        response = await call_next(request)
        status = str(response.status_code)
    except Exception:
        status = "500"
        raise
    else:
        duration = time.time() - start_time
        AGENT_RESPONSE_TIME_SECONDS_BUCKET.labels(method=request.method, endpoint=request.url.path).observe(duration)
        AGENT_REQUESTS_TOTAL.labels(method=request.method, endpoint=request.url.path, status=status).inc()
        
        # Обновляем стандартизированные метрики
        PM_AGENT_CALLS.labels(agent_name=agent_name, status=status).inc()
        PM_AGENT_RESPONSE_TIME_SECONDS_BUCKET.labels(agent_name=agent_name).observe(duration)
        PM_TASKS_TOTAL.labels(status=status, method=request.method, endpoint=request.url.path).inc()
        PM_TASK_DURATION.observe(duration)
        
        return response
    finally:
        AGENT_ACTIVE_REQUESTS.labels(method=request.method, endpoint=request.url.path).dec()
        PM_ACTIVE_TASKS.labels(method=request.method, endpoint=request.url.path).dec()


# ============================================================================
# LLM HELPER
# ============================================================================

async def call_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 100000,
    step_name: str = "llm_request"
) -> str:
    """Вызов LLM через OpenRouter MCP"""

    if not system_prompt:
        system_prompt = """Ты опытный архитектор ПО с 20+ лет опыта проектирования систем.
Ты отлично знаешь:
- Паттерны проектирования (GoF, Enterprise, DDD)
- Архитектурные стили (Clean Architecture, Hexagonal, Microservices)
- SOLID принципы и лучшие практики
- Различные технологические стеки

Ты проектируешь:
- Понятные, расширяемые компоненты
- Чистые интерфейсы
- Правильные зависимости
- Тестируемую архитектуру

Всегда учитываешь существующий код и стиль проекта.
Возвращаешь ответы в JSON когда это указано."""

    # Подготовка сообщений для запроса
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    # Логирование начала запроса - только шаг
    logger.info(f"step: {step_name}")

    start_time = time.time()

    try:
        # Метрики запросов к LLM теперь отслеживаются в OpenRouter MCP
        
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

            # Метрики токенов теперь отслеживаются в OpenRouter MCP

            # Извлечение reasoning (если присутствует)
            reasoning = None
            if "reasoning" in response_data["choices"][0]["message"]:
                reasoning = response_data["choices"][0]["message"]["reasoning"]
            elif "reasoning_content" in response_data["choices"][0]["message"]:
                reasoning = response_data["choices"][0]["message"]["reasoning_content"]

            # Логирование успешного ответа - полностью логируем ответы и reasoning
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
            
            # Обновляем метрику системных ошибок
            PM_SYSTEM_ERRORS_TOTAL.labels(agent_name="architect", error_type="llm_error").inc()
            
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
        
        # Обновляем метрику системных ошибок
        PM_SYSTEM_ERRORS_TOTAL.labels(agent_name="architect", error_type="exception").inc()
        
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
# PLANTUML HELPERS
# ============================================================================

def generate_plantuml_url(plantuml_code: str) -> str:
    """Генерирует URL для PlantUML диаграммы"""
    try:
        plantuml_code = plantuml_code.strip()
        utf8_bytes = plantuml_code.encode('utf-8')
        compressed = zlib.compress(utf8_bytes, 9)[2:-4]
        encoded = base64.b64encode(compressed).decode('ascii')
        encoded = encoded.translate(str.maketrans({'+': '-', '/': '_'}))
        return f"http://www.plantuml.com/plantuml/svg/{encoded}"
    except Exception as e:
        logger.error(f"PlantUML URL generation error: {e}")
        return ""


# ============================================================================
# EXISTING ARCHITECTURE ANALYSIS
# ============================================================================

async def analyze_existing_architecture(
    repo_context: Dict[str, Any],
    tech_stack: TechStack
) -> ExistingArchitecture:
    """
    Анализирует существующую архитектуру репозитория
    """
    
    structure = repo_context.get("structure", [])
    key_files = repo_context.get("key_files", {})
    
    # Группируем файлы по директориям
    directories = {}
    for item in structure:
        path = item.get("path", "")
        if "/" in path:
            dir_path = path.rsplit("/", 1)[0]
            directories[dir_path] = directories.get(dir_path, 0) + 1
    
    prompt = f"""
Проанализируй существующую архитектуру проекта.

## ТЕХНОЛОГИЧЕСКИЙ СТЕК:
- Язык: {tech_stack.primary_language}
- Фреймворки: {', '.join(tech_stack.frameworks)}
- Паттерны: {', '.join(tech_stack.architecture_patterns)}

## СТРУКТУРА ДИРЕКТОРИЙ:
{json.dumps(dict(sorted(directories.items(), key=lambda x: -x[1])[:30]), indent=2)}

## КЛЮЧЕВЫЕ ФАЙЛЫ:
{json.dumps(list(key_files.keys())[:40], indent=2)}

## СОДЕРЖИМОЕ КЛЮЧЕВЫХ ФАЙЛОВ:
{json.dumps(key_files, indent=2, ensure_ascii=False)[:150000]}

## ОПРЕДЕЛИ:

1. **Архитектурный паттерн**: monolith, modular_monolith, microservices, serverless, layered, hexagonal, clean_architecture
2. **Слои приложения**: какие слои есть (presentation, business/domain, data/infrastructure)
3. **Существующие компоненты**: основные классы, сервисы, модули
4. **Соглашения**: именование файлов, структура модулей
5. **Сильные стороны**: что хорошо в текущей архитектуре
6. **Слабые стороны**: что можно улучшить

## ФОРМАТ ОТВЕТА (JSON):
{{
    "pattern": "название архитектурного паттерна",
    "layers": ["presentation", "business", "data"],
    "existing_components": [
        {{
            "name": "имя компонента",
            "type": "class/service/module",
            "file_path": "путь к файлу",
            "responsibility": "за что отвечает"
        }}
    ],
    "conventions": {{
        "file_naming": "snake_case/kebab-case",
        "module_structure": "описание структуры",
        "import_style": "absolute/relative"
    }},
    "strengths": ["сильная сторона 1", "сильная сторона 2"],
    "weaknesses": ["слабая сторона 1", "слабая сторона 2"]
}}
"""
    
    response = await call_llm(prompt, step_name="analyze_existing_architecture")
    parsed = parse_json_response(response)

    if parsed:
        return ExistingArchitecture(
            pattern=parsed.get("pattern", "unknown"),
            layers=parsed.get("layers", []),
            existing_components=parsed.get("existing_components", []),
            conventions=parsed.get("conventions", {}),
            strengths=parsed.get("strengths", []),
            weaknesses=parsed.get("weaknesses", [])
        )

    return ExistingArchitecture()


# ============================================================================
# COMPONENT DESIGN
# ============================================================================

async def design_components(
    task: str,
    existing_arch: ExistingArchitecture,
    tech_stack: TechStack,
    repo_context: Dict[str, Any]
) -> Tuple[List[ComponentSpec], List[InterfaceSpec], List[ComponentRelation]]:
    """
    Проектирует новые компоненты для выполнения задачи
    """
    
    prompt = f"""
Спроектируй компоненты для реализации задачи.

## ЗАДАЧА:
{task}

## СУЩЕСТВУЮЩАЯ АРХИТЕКТУРА:
- Паттерн: {existing_arch.pattern}
- Слои: {', '.join(existing_arch.layers)}
- Соглашения: {json.dumps(existing_arch.conventions, ensure_ascii=False)}

## СУЩЕСТВУЮЩИЕ КОМПОНЕНТЫ:
{json.dumps(existing_arch.existing_components[:50], indent=2, ensure_ascii=False)}

## ТЕХНОЛОГИИ:
- Язык: {tech_stack.primary_language}
- Фреймворки: {', '.join(tech_stack.frameworks)}
- Тестирование: {', '.join(tech_stack.testing_frameworks)}

## ТРЕБОВАНИЯ:
1. Следуй существующей архитектуре и соглашениям
2. Проектируй по SOLID принципам
3. Минимизируй связанность (loose coupling)
4. Максимизируй связность (high cohesion)
5. Каждый компонент - одна ответственность

## САМОЕ ВАЖНОЕ:

НЕ усложняй архитектуру намеренно, если на это нет оснований

## ФОРМАТ ОТВЕТА (JSON):
{{
    "components": [
        {{
            "name": "JWTAuthenticator",
            "type": "service",
            "description": "Сервис для работы с JWT токенами",
            "responsibility": "Генерация, валидация и обновление JWT токенов",
            "layer": "business",
            "properties": [
                {{
                    "name": "secret_key",
                    "type": "str",
                    "description": "Секретный ключ для подписи",
                    "is_private": true
                }},
                {{
                    "name": "algorithm",
                    "type": "str",
                    "description": "Алгоритм шифрования",
                    "default": "HS256"
                }}
            ],
            "methods": [
                {{
                    "name": "create_access_token",
                    "description": "Создаёт access token",
                    "parameters": [
                        {{"name": "user_id", "type": "str", "required": true}},
                        {{"name": "expires_delta", "type": "timedelta", "required": false, "default": "None"}}
                    ],
                    "return_type": "str",
                    "is_async": false,
                    "raises": ["ValueError"]
                }},
                {{
                    "name": "verify_token",
                    "description": "Проверяет и декодирует токен",
                    "parameters": [
                        {{"name": "token", "type": "str", "required": true}}
                    ],
                    "return_type": "TokenPayload",
                    "is_async": false,
                    "raises": ["InvalidTokenError", "ExpiredTokenError"]
                }}
            ],
            "dependencies": ["ConfigService"],
            "extends": null,
            "implements": ["IAuthenticator"]
        }}
    ],
    "interfaces": [
        {{
            "name": "IAuthenticator",
            "description": "Интерфейс аутентификатора",
            "methods": [
                {{
                    "name": "create_access_token",
                    "parameters": [{{"name": "user_id", "type": "str", "required": true}}],
                    "return_type": "str"
                }},
                {{
                    "name": "verify_token",
                    "parameters": [{{"name": "token", "type": "str", "required": true}}],
                    "return_type": "TokenPayload"
                }}
            ]
        }}
    ],
    "relations": [
        {{
            "source": "JWTAuthenticator",
            "target": "ConfigService",
            "relation_type": "dependency",
            "description": "Получает конфигурацию"
        }},
        {{
            "source": "JWTAuthenticator",
            "target": "IAuthenticator",
            "relation_type": "implementation",
            "description": "Реализует интерфейс"
        }}
    ]
}}
"""
    
    response = await call_llm(prompt, max_tokens=100000, step_name="design_components")
    parsed = parse_json_response(response)

    components = []
    interfaces = []
    relations = []

    if parsed:
        # Парсим компоненты
        for comp_data in parsed.get("components", []):
            try:
                comp_type = ComponentType(comp_data.get("type", "class"))
            except ValueError:
                comp_type = ComponentType.CLASS

            properties = []
            for prop in comp_data.get("properties", []):
                properties.append(PropertySpec(**prop))

            methods = []
            for method in comp_data.get("methods", []):
                params = []
                for p in method.get("parameters", []):
                    # Handle default values that might be lists
                    default_val = p.get("default")
                    if isinstance(default_val, list):
                        # Convert list to string representation for storage
                        default_val = str(default_val)
                    params.append(MethodParameter(**{**p, "default": default_val}))
                methods.append(MethodSpec(
                    name=method.get("name", ""),
                    description=method.get("description", ""),
                    parameters=params,
                    return_type=method.get("return_type", "None"),
                    is_async=method.get("is_async", False),
                    is_static=method.get("is_static", False),
                    raises=method.get("raises", [])
                ))

            # ИСПРАВЛЕНИЕ: Гарантируем, что implements и dependencies - списки
            implements = comp_data.get("implements")
            if implements is None or not isinstance(implements, list):
                implements = []
                
            dependencies = comp_data.get("dependencies")
            if dependencies is None or not isinstance(dependencies, list):
                dependencies = []
            
            # ИСПРАВЛЕНИЕ: Гарантируем, что extends - строка или None
            extends = comp_data.get("extends")
            if extends is not None and not isinstance(extends, str):
                extends = None

            components.append(ComponentSpec(
                name=comp_data.get("name", ""),
                type=comp_type,
                description=comp_data.get("description", ""),
                responsibility=comp_data.get("responsibility", ""),
                properties=properties,
                methods=methods,
                dependencies=dependencies,
                extends=extends,
                implements=implements,
                layer=comp_data.get("layer", "")
            ))

            # Парсим интерфейсы
            for iface_data in parsed.get("interfaces", []):
                methods = []
                for method in iface_data.get("methods", []):
                    params = []
                    for p in method.get("parameters", []):
                        # ИСПРАВЛЕНИЕ: То же для параметров методов
                        if isinstance(p, dict):
                            params.append(MethodParameter(**p))
                        else:
                            logger.warning(f"Invalid parameter format: {p}")
                            continue
                    
                    methods.append(MethodSpec(
                        name=method.get("name", ""),
                        parameters=params,
                        return_type=method.get("return_type", "None")
                    ))

                interfaces.append(InterfaceSpec(
                    name=iface_data.get("name", ""),
                    description=iface_data.get("description", ""),
                    methods=methods
                ))

            # Парсим связи
            for rel_data in parsed.get("relations", []):
                try:
                    rel_type = RelationType(rel_data.get("relation_type", "dependency"))
                except ValueError:
                    rel_type = RelationType.DEPENDENCY

                relations.append(ComponentRelation(
                    source=rel_data.get("source", ""),
                    target=rel_data.get("target", ""),
                    relation_type=rel_type,
                    description=rel_data.get("description", "")
                ))

    return components, interfaces, relations


# ============================================================================
# FILE STRUCTURE PLANNING
# ============================================================================

async def plan_file_structure(
    components: List[ComponentSpec],
    interfaces: List[InterfaceSpec],
    existing_arch: ExistingArchitecture,
    tech_stack: TechStack
) -> List[FileSpec]:
    """
    Планирует структуру файлов для компонентов
    """
    
    components_info = [
        {"name": c.name, "type": c.type.value, "layer": c.layer}
        for c in components
    ]
    
    interfaces_info = [{"name": i.name} for i in interfaces]
    
    prompt = f"""
Спланируй структуру файлов для новых компонентов.

## КОМПОНЕНТЫ:
{json.dumps(components_info, indent=2)}

## ИНТЕРФЕЙСЫ:
{json.dumps(interfaces_info, indent=2)}

## СУЩЕСТВУЮЩАЯ СТРУКТУРА:
- Паттерн: {existing_arch.pattern}
- Слои: {', '.join(existing_arch.layers)}
- Соглашения: {json.dumps(existing_arch.conventions, ensure_ascii=False)}

## ТЕХНОЛОГИИ:
- Язык: {tech_stack.primary_language}
- Фреймворки: {', '.join(tech_stack.frameworks)}

## ТРЕБОВАНИЯ:
1. Следуй существующим соглашениям по именованию
2. Группируй связанные компоненты
3. Учитывай слои архитектуры
4. Учитывай архитектуру текущего проекта и выбирай пути согласованные с ней
5. Выбирай расположения файлов в соответствии с архитектурой, не суй всё в корневую директорию, если этого не требуется

## ФОРМАТ ОТВЕТА (JSON):
{{
    "files": [
        {{
            "path": "путь/к/файлу.расширение",
            "type": "module | package | test | config | schema",
            "description": "Краткое описание назначения файла",
            "contains": ["Класс1", "Класс2", "функция1"],
            "imports_from": ["путь/к/зависимости1", "путь/к/зависимости2"],
            "exports": ["Класс1", "функция1"]
        }},
        {{
            "path": "путь/к/интерфейсам.расширение",
            "type": "module",
            "description": "Интерфейсы и абстрактные классы",
            "contains": ["IИнтерфейс1", "BaseКласс"],
            "exports": ["IИнтерфейс1", "BaseКласс"]
        }},
        {{
            "path": "путь/к/пакету/модулю.расширение",
            "type": "package",
            "description": "Инициализация пакета, реэкспорт публичного API",
            "exports": ["ГлавныйКласс", "вспомогательная_функция"]
        }},
        {{
            "path": "tests/test_модуль.расширение",
            "type": "test",
            "description": "Тесты для модуля",
            "contains": ["TestГлавныйКласс", "TestВспомогательныеФункции"]
        }}
    ]
}}
"""
    
    response = await call_llm(prompt, step_name="plan_file_structure")
    parsed = parse_json_response(response)

    files = []

    if parsed:
        for file_data in parsed.get("files", []):
            files.append(FileSpec(
                path=file_data.get("path", ""),
                type=file_data.get("type", "module"),
                description=file_data.get("description", ""),
                contains=file_data.get("contains", []),
                imports_from=file_data.get("imports_from", []),
                exports=file_data.get("exports", [])
            ))

    return files


# ============================================================================
# PATTERN SELECTION
# ============================================================================

async def select_patterns(
    task: str,
    components: List[ComponentSpec],
    tech_stack: TechStack
) -> List[PatternRecommendation]:
    """
    Выбирает подходящие паттерны проектирования
    """
    
    components_info = [
        {"name": c.name, "type": c.type.value, "responsibility": c.responsibility}
        for c in components
    ]
    
    prompt = f"""
Рекомендуй паттерны проектирования для задачи.

## ЗАДАЧА:
{task}

## КОМПОНЕНТЫ:
{json.dumps(components_info, indent=2, ensure_ascii=False)}

## ТЕХНОЛОГИИ:
{tech_stack.primary_language}, {', '.join(tech_stack.frameworks)}

## РАССМОТРИ ПАТТЕРНЫ:

### Creational (порождающие):
- Factory Method, Abstract Factory, Builder, Singleton, Prototype

### Structural (структурные):
- Adapter, Bridge, Composite, Decorator, Facade, Flyweight, Proxy

### Behavioral (поведенческие):
- Chain of Responsibility, Command, Iterator, Mediator, Memento, Observer, State, Strategy, Template Method, Visitor

### Architectural (архитектурные):
- Repository, Unit of Work, CQRS, Event Sourcing, DI Container

## ФОРМАТ ОТВЕТА (JSON):
{{
    "patterns": [
        {{
            "name": "Strategy",
            "category": "behavioral",
            "reason": "Позволяет менять алгоритм аутентификации без изменения клиентского кода",
            "how_to_apply": "Создать IAuthStrategy интерфейс, реализовать JWTStrategy, OAuth2Strategy",
            "components_affected": ["JWTAuthenticator", "AuthService"],
            "example": "class AuthService:\\n    def __init__(self, strategy: IAuthStrategy):\\n        self._strategy = strategy"
        }}
    ]
}}
"""
    
    response = await call_llm(prompt, step_name="select_patterns")
    parsed = parse_json_response(response)

    patterns = []

    if parsed:
        for pattern_data in parsed.get("patterns", []):
            try:
                category = PatternCategory(pattern_data.get("category", "behavioral"))
            except ValueError:
                category = PatternCategory.BEHAVIORAL

            patterns.append(PatternRecommendation(
                name=pattern_data.get("name", ""),
                category=category,
                reason=pattern_data.get("reason", ""),
                how_to_apply=pattern_data.get("how_to_apply", ""),
                components_affected=pattern_data.get("components_affected", []),
                example=pattern_data.get("example", "")
            ))

    return patterns


# ============================================================================
# INTEGRATION PLANNING
# ============================================================================

async def plan_integration(
    components: List[ComponentSpec],
    existing_arch: ExistingArchitecture,
    repo_context: Dict[str, Any]
) -> Tuple[List[IntegrationPoint], List[ExternalDependency]]:
    """
    Планирует интеграцию с существующим кодом
    """
    
    new_components = [{"name": c.name, "type": c.type.value} for c in components]
    existing_components = existing_arch.existing_components[:50]
    
    prompt = f"""
Спланируй интеграцию новых компонентов с существующим кодом.

## НОВЫЕ КОМПОНЕНТЫ:
{json.dumps(new_components, indent=2)}

## СУЩЕСТВУЮЩИЕ КОМПОНЕНТЫ:
{json.dumps(existing_components, indent=2, ensure_ascii=False)}

## СУЩЕСТВУЮЩИЕ ФАЙЛЫ:
{json.dumps(list(repo_context.get("key_files", {}).keys())[:20], indent=2)}

## ОПРЕДЕЛИ:

1. **Точки интеграции**: где новые компоненты подключаются к существующим
2. **Изменения**: какие существующие файлы нужно изменить
3. **Зависимости**: новые внешние библиотеки

## ФОРМАТ ОТВЕТА (JSON):
{{
    "integration_points": [
        {{
            "existing_component": "UserService",
            "new_component": "JWTAuthenticator",
            "integration_type": "dependency",
            "description": "UserService использует JWTAuthenticator для создания токенов",
            "changes_required": [
                "Добавить JWTAuthenticator в конструктор UserService",
                "Обновить метод login() для возврата токена"
            ]
        }}
    ],
    "external_dependencies": [
        {{
            "name": "pyjwt",
            "version": ">=2.8.0",
            "purpose": "JWT токены",
            "package_manager": "pip"
        }}
    ]
}}
"""
    
    response = await call_llm(prompt, step_name="plan_integration")
    parsed = parse_json_response(response)

    integration_points = []
    dependencies = []

    if parsed:
        for point_data in parsed.get("integration_points", []):
            integration_points.append(IntegrationPoint(
                existing_component=point_data.get("existing_component", ""),
                new_component=point_data.get("new_component", ""),
                integration_type=point_data.get("integration_type", "dependency"),
                description=point_data.get("description", ""),
                changes_required=point_data.get("changes_required", [])
            ))

        for dep_data in parsed.get("external_dependencies", []):
            dependencies.append(ExternalDependency(
                name=dep_data.get("name", ""),
                version=dep_data.get("version", ""),
                purpose=dep_data.get("purpose", ""),
                package_manager=dep_data.get("package_manager", "")
            ))

    return integration_points, dependencies


# ============================================================================
# DIAGRAM GENERATION
# ============================================================================

async def generate_diagrams(
    components: List[ComponentSpec],
    interfaces: List[InterfaceSpec],
    relations: List[ComponentRelation],
    file_structure: List[FileSpec],
    tech_stack: TechStack
) -> List[DiagramSpec]:
    """
    Генерирует архитектурные диаграммы
    """
    
    diagrams = []
    
    # 1. Component Diagram
    component_diagram = await generate_component_diagram(components, relations)
    if component_diagram:
        diagrams.append(component_diagram)
    
    # 2. Class Diagram
    class_diagram = await generate_class_diagram(components, interfaces, relations)
    if class_diagram:
        diagrams.append(class_diagram)
    
    return diagrams


async def generate_component_diagram(
    components: List[ComponentSpec],
    relations: List[ComponentRelation]
) -> Optional[DiagramSpec]:
    """Генерирует диаграмму компонентов"""
    
    components_info = [
        {"name": c.name, "type": c.type.value, "layer": c.layer}
        for c in components
    ]
    relations_info = [
        {"source": r.source, "target": r.target, "type": r.relation_type.value}
        for r in relations
    ]
    
    prompt = f"""
Создай PlantUML диаграмму компонентов.

## КОМПОНЕНТЫ:
{json.dumps(components_info, indent=2)}

## СВЯЗИ:
{json.dumps(relations_info, indent=2)}

## ТРЕБОВАНИЯ:
1. Группируй по слоям (packages)
2. Используй правильные стрелки для типов связей
3. Добавь цвета для разных типов компонентов
4. Добавь описательный title

Верни ТОЛЬКО PlantUML код, начиная с @startuml и заканчивая @enduml.
Без markdown блоков, без пояснений.
"""
    
    response = await call_llm(prompt, temperature=0.2, step_name="generate_component_diagram")

    # Извлекаем PlantUML код
    plantuml_code = extract_plantuml(response)

    if plantuml_code:
        return DiagramSpec(
            type=DiagramType.COMPONENT,
            title="Component Diagram",
            description="Architecture component diagram",
            plantuml_code=plantuml_code,
            svg_url=generate_plantuml_url(plantuml_code)
        )

    return None


async def generate_class_diagram(
    components: List[ComponentSpec],
    interfaces: List[InterfaceSpec],
    relations: List[ComponentRelation]
) -> Optional[DiagramSpec]:
    """Генерирует диаграмму классов"""
    
    # Формируем информацию о классах
    classes_info = []
    for comp in components:
        methods = [{"name": m.name, "params": [p.name for p in m.parameters], "return": m.return_type}
                   for m in comp.methods]
        props = [{"name": p.name, "type": p.type} for p in comp.properties]
        classes_info.append({
            "name": comp.name,
            "type": comp.type.value,
            "methods": methods,
            "properties": props,
            "extends": comp.extends,
            "implements": comp.implements
        })
    
    interfaces_info = []
    for iface in interfaces:
        methods = [{"name": m.name, "return": m.return_type} for m in iface.methods]
        interfaces_info.append({"name": iface.name, "methods": methods})
    
    prompt = f"""
Создай PlantUML диаграмму классов.

## КЛАССЫ:
{json.dumps(classes_info, indent=2, ensure_ascii=False)}

## ИНТЕРФЕЙСЫ:
{json.dumps(interfaces_info, indent=2, ensure_ascii=False)}

## ТРЕБОВАНИЯ:
1. Покажи все классы с методами и свойствами
2. Покажи интерфейсы
3. Покажи наследование и реализацию
4. Используй правильные модификаторы доступа (+, -, #)
5. Добавь описательный title

Верни ТОЛЬКО PlantUML код, начиная с @startuml и заканчивая @enduml.
"""
    
    response = await call_llm(prompt, temperature=0.2)
    plantuml_code = extract_plantuml(response)
    
    if plantuml_code:
        return DiagramSpec(
            type=DiagramType.CLASS,
            title="Class Diagram",
            description="Class diagram with interfaces",
            plantuml_code=plantuml_code,
            svg_url=generate_plantuml_url(plantuml_code)
        )
    
    return None


def extract_plantuml(response: str) -> str:
    """Извлекает PlantUML код из ответа"""
    
    # Удаляем markdown блоки
    response = re.sub(r'```(?:plantuml|puml)?\n?', '', response)
    response = re.sub(r'```', '', response)
    
    # Ищем @startuml ... @enduml
    lines = response.split('\n')
    plantuml_lines = []
    in_plantuml = False
    
    for line in lines:
        if '@startuml' in line:
            in_plantuml = True
        if in_plantuml:
            plantuml_lines.append(line)
        if '@enduml' in line:
            break
    
    if plantuml_lines:
        return '\n'.join(plantuml_lines)
    
    return ""


# ============================================================================
# RECOMMENDATIONS GENERATION
# ============================================================================

async def generate_recommendations(
    task: str,
    components: List[ComponentSpec],
    existing_arch: ExistingArchitecture,
    tech_stack: TechStack
) -> Tuple[List[str], List[str]]:
    """
    Генерирует рекомендации и риски
    """
    
    prompt = f"""
Дай архитектурные рекомендации и определи риски.

## ЗАДАЧА:
{task}

## НОВЫЕ КОМПОНЕНТЫ:
{json.dumps([c.name for c in components], indent=2)}

## СУЩЕСТВУЮЩАЯ АРХИТЕКТУРА:
- Паттерн: {existing_arch.pattern}
- Слабости: {existing_arch.weaknesses}

## ДАЙТЕ:

1. **Рекомендации** (5-7 штук):
   - По улучшению архитектуры
   - По тестированию
   - По производительности
   - По безопасности
   - По расширяемости

2. **Риски** (3-5 штук):
   - Технические риски
   - Риски интеграции
   - Риски производительности

## ФОРМАТ ОТВЕТА (JSON):
{{
    "recommendations": [
        "Рекомендация 1",
        "Рекомендация 2"
    ],
    "risks": [
        "Риск 1",
        "Риск 2"
    ]
}}
"""
    
    response = await call_llm(prompt, step_name="generate_recommendations")
    parsed = parse_json_response(response)

    if parsed:
        return parsed.get("recommendations", []), parsed.get("risks", [])

    return [], []


# ============================================================================
# MAIN ARCHITECTURE DESIGN
# ============================================================================

async def design_architecture(
    task: str,
    tech_stack: TechStack,
    repo_context: Dict[str, Any]
) -> Tuple[ExistingArchitecture, ArchitectureDesign]:
    """
    Выполняет полное проектирование архитектуры
    """
    
    # 1. Анализ существующей архитектуры
    logger.info("Analyzing existing architecture...")
    existing_arch = await analyze_existing_architecture(repo_context, tech_stack)
    
    # 2. Проектирование компонентов
    logger.info("Designing components...")
    components, interfaces, relations = await design_components(
        task, existing_arch, tech_stack, repo_context
    )
    
    # 3. Планирование структуры файлов
    logger.info("Planning file structure...")
    file_structure = await plan_file_structure(
        components, interfaces, existing_arch, tech_stack
    )
    
    # 4. Выбор паттернов
    logger.info("Selecting patterns...")
    patterns = await select_patterns(task, components, tech_stack)
    
    # 5. Планирование интеграции
    logger.info("Planning integration...")
    integration_points, dependencies = await plan_integration(
        components, existing_arch, repo_context
    )
    
    # 6. Генерация диаграмм
    logger.info("Generating diagrams...")
    diagrams = await generate_diagrams(
        components, interfaces, relations, file_structure, tech_stack
    )
    
    # 7. Рекомендации
    logger.info("Generating recommendations...")
    recommendations, risks = await generate_recommendations(
        task, components, existing_arch, tech_stack
    )
    
    # Собираем результат
    design = ArchitectureDesign(
        components=components,
        interfaces=interfaces,
        relations=relations,
        file_structure=file_structure,
        patterns=patterns,
        external_dependencies=dependencies,
        integration_points=integration_points,
        diagrams=diagrams,
        recommendations=recommendations,
        risks=risks
    )
    
    return existing_arch, design


# ============================================================================
# MAIN ENDPOINT
# ============================================================================

@app.post("/process", response_model=ArchitectResponse)
async def process_architecture(request: ArchitectRequest):
    """
    Основной endpoint для проектирования архитектуры
    """
    
    start_time = time.time()
    task_id = str(uuid.uuid4())
    
    try:
        data = request.data
        
        logger.info(f"[{task_id[:8]}] Starting architecture design: {request.task[:100]}")
        
        # Извлекаем данные
        tech_stack_data = data.get("tech_stack", {})
        tech_stack = TechStack(**tech_stack_data) if tech_stack_data else TechStack()
        repo_context = data.get("repo_context", {})
        
        # Выполняем проектирование
        existing_arch, design = await design_architecture(
            task=request.task,
            tech_stack=tech_stack,
            repo_context=repo_context
        )
        
        duration = time.time() - start_time
        
        logger.info(f"[{task_id[:8]}] Architecture design completed in {duration:.1f}s, "
                   f"components: {len(design.components)}, "
                   f"files: {len(design.file_structure)}")
        
        # Формируем плоскую структуру для совместимости
        components_flat = [c.dict() for c in design.components]
        patterns_flat = [p.name for p in design.patterns]
        file_structure_flat = [f.dict() for f in design.file_structure]
        interfaces_flat = [i.dict() for i in design.interfaces]
        dependencies_flat = [d.name for d in design.external_dependencies]
        integration_flat = [ip.dict() for ip in design.integration_points]
        diagrams_flat = {d.type.value: d.plantuml_code for d in design.diagrams}
        
        return ArchitectResponse(
            task_id=task_id,
            status="success",
            existing_architecture=existing_arch,
            architecture=design,
            # Плоская структура для Code Writer
            components=components_flat,
            patterns=patterns_flat,
            file_structure=file_structure_flat,
            interfaces=interfaces_flat,
            dependencies=dependencies_flat,
            integration_points=integration_flat,
            diagrams=diagrams_flat,
            recommendations=design.recommendations,
            duration_seconds=duration
        )
        
    except Exception as e:
        logger.exception(f"[{task_id[:8]}] Architecture design error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ADDITIONAL ENDPOINTS
# ============================================================================

@app.post("/analyze")
async def analyze_only(request: Dict[str, Any]):
    """
    Только анализ существующей архитектуры
    """

    AGENT_ACTIVE_REQUESTS.labels(method="POST", endpoint="/analyze").inc()
    start_time = time.time()

    try:
        tech_stack_data = request.get("tech_stack", {})
        tech_stack = TechStack(**tech_stack_data) if tech_stack_data else TechStack()
        repo_context = request.get("repo_context", {})

        existing_arch = await analyze_existing_architecture(repo_context, tech_stack)

        duration = time.time() - start_time

        # Метрики
        AGENT_REQUESTS_TOTAL.labels(method="POST", endpoint="/analyze", status="success").inc()
        AGENT_RESPONSE_TIME_SECONDS_BUCKET.labels(method="POST", endpoint="/analyze").observe(duration)

        return existing_arch.dict()

    except Exception as e:
        AGENT_REQUESTS_TOTAL.labels(method="POST", endpoint="/analyze", status="error").inc()
        AGENT_RESPONSE_TIME_SECONDS_BUCKET.labels(method="POST", endpoint="/analyze").observe(time.time() - start_time)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        AGENT_ACTIVE_REQUESTS.labels(method="POST", endpoint="/analyze").dec()


@app.post("/diagram")
async def generate_diagram_only(request: Dict[str, Any]):
    """
    Генерация отдельной диаграммы
    """

    AGENT_ACTIVE_REQUESTS.labels(method="POST", endpoint="/diagram").inc()
    start_time = time.time()

    try:
        diagram_type = request.get("type", "component")
        components = request.get("components", [])
        relations = request.get("relations", [])

        # Преобразуем в модели
        comp_specs = []
        for c in components:
            try:
                comp_specs.append(ComponentSpec(**c))
            except:
                pass

        rel_specs = []
        for r in relations:
            try:
                rel_specs.append(ComponentRelation(**r))
            except:
                pass

        if diagram_type == "component":
            diagram = await generate_component_diagram(comp_specs, rel_specs)
        else:
            diagram = await generate_class_diagram(comp_specs, [], rel_specs)

        duration = time.time() - start_time

        # Метрики
        AGENT_REQUESTS_TOTAL.labels(method="POST", endpoint="/diagram", status="success").inc()
        AGENT_RESPONSE_TIME_SECONDS_BUCKET.labels(method="POST", endpoint="/diagram").observe(duration)

        if diagram:
            return diagram.dict()

        return {"error": "Failed to generate diagram"}

    except Exception as e:
        AGENT_REQUESTS_TOTAL.labels(method="POST", endpoint="/diagram", status="error").inc()
        AGENT_RESPONSE_TIME_SECONDS_BUCKET.labels(method="POST", endpoint="/diagram").observe(time.time() - start_time)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        AGENT_ACTIVE_REQUESTS.labels(method="POST", endpoint="/diagram").dec()


@app.get("/health")
async def health_check():
    """Health check endpoint - не экспортирует метрики"""
    return {
        "status": "healthy",
        "service": "architect",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint - только метрики"""
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Architect Agent",
        "version": "2.0.0",
        "description": "Агент для проектирования архитектуры ПО",
        "capabilities": [
            "Analyze existing architecture",
            "Design new components",
            "Define interfaces and contracts",
            "Plan file structure",
            "Select design patterns",
            "Plan integration with existing code",
            "Generate PlantUML diagrams",
            "Provide recommendations"
        ],
        "outputs_to": ["code_writer", "code_reviewer"],
        "endpoints": {
            "process": "POST /process - полное проектирование",
            "analyze": "POST /analyze - только анализ",
            "diagram": "POST /diagram - генерация диаграммы",
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
