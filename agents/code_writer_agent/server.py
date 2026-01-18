"""
Code Writer Agent
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
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
import httpx
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from logging_config import setup_logging

from models import (
    FileAction, CodeLanguage,
    NamingConvention, ImportStyle, CodingStyle,
    CodeFile, CodeChange,
    CodeWriteRequest, CodeWriteResponse,
    TechStack
)

# ============================================================================
# CONFIGURATION
# ============================================================================

logger = setup_logging("code_writer")

OPENROUTER_MCP_URL = os.getenv("OPENROUTER_MCP_URL", "http://openrouter-proxy:8000")
LLM_TIMEOUT = 1000
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL")

# ============================================================================
# METRICS
# ============================================================================

# Стандартизированные метрики для всех агентов
AGENT_REQUESTS_TOTAL = Counter('agent_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
AGENT_RESPONSE_TIME_SECONDS_BUCKET = Histogram('agent_response_time_seconds_bucket', 'Request duration',
                            buckets=[0.5, 1, 2, 5, 10, 30, 60, 120, 300], labelnames=['method', 'endpoint'])
AGENT_ACTIVE_REQUESTS = Gauge('agent_active_requests', 'Number of active requests', ['method', 'endpoint'])

# Общие метрики для всех агентов

# Стандартизированные метрики для всех агентов
PM_AGENT_CALLS = Counter('pm_agent_calls_total', 'Agent calls', ['agent_name', 'status'])
PM_AGENT_RESPONSE_TIME_SECONDS_BUCKET = Histogram('pm_agent_response_time_seconds_bucket', 'Agent response time', ['agent_name'], buckets=[0.5, 1, 2, 5, 10, 30, 60, 120, 300])
PM_ACTIVE_TASKS = Gauge('pm_active_tasks', 'Currently processing tasks', ['method', 'endpoint'])
PM_TASKS_TOTAL = Counter('pm_tasks_total', 'Total tasks processed', ['status', 'method', 'endpoint'])
PM_TASK_DURATION = Histogram('pm_task_duration_seconds_bucket', 'Task duration', buckets=[30, 60, 120, 300, 600, 1200])

EXTENSION_TO_LANGUAGE = {
    "py": "python",
    "js": "javascript", "jsx": "javascript",
    "ts": "typescript", "tsx": "typescript",
    "go": "go", "rs": "rust", "java": "java",
    "html": "html", "css": "css", "sql": "sql",
    "sh": "shell", "yaml": "yaml", "yml": "yaml",
    "json": "json", "md": "markdown",
}

# ============================================================================
# HTTP CLIENT
# ============================================================================

http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(LLM_TIMEOUT))
    
    logger.info("Code Writer Agent started")
    yield
    
    await http_client.aclose()
    logger.info("Code Writer Agent stopped")


app = FastAPI(
    title="Code Writer Agent",
    description="Агент для написания кода по архитектуре",
    version="2.3.0",  # Обновлена версия
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
    
    agent_name = "code_writer_agent"
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
    temperature: float = 0.2,
    max_tokens: int = 100000,
    step: str = "code_writer_llm_request"
) -> str:
    """Вызов LLM через OpenRouter MCP"""

    if not system_prompt:
        system_prompt = """Ты опытный программист. Пишешь чистый, рабочий, production-ready код.

ПРАВИЛА:
1. Пиши ПОЛНЫЙ код, не заглушки и не TODO
2. Добавляй все необходимые импорты
3. Добавляй docstrings и комментарии
4. Обрабатывай ошибки
5. Следуй архитектуре и стилю проекта
6. Отвечай ТОЛЬКО в формате JSON когда просят"""

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
    """
    Парсит JSON из ответа LLM.
    Пробует несколько стратегий.
    """
    
    if not response:
        logger.error("Empty response")
        return None
    
    # Стратегия 1: весь ответ - JSON
    try:
        result = json.loads(response.strip())
        logger.info("Parsed JSON: strategy 1 (direct)")
        return result
    except json.JSONDecodeError:
        pass
    
    # Стратегия 2: JSON в блоке ```json...```
    match = re.search(r'```json\s*\n?([\s\S]*?)\n?```', response)
    if match:
        try:
            result = json.loads(match.group(1).strip())
            logger.info("Parsed JSON: strategy 2 (```json block)")
            return result
        except json.JSONDecodeError:
            pass
    
    # Стратегия 3: JSON в блоке ```...```
    match = re.search(r'```\s*\n?([\s\S]*?)\n?```', response)
    if match:
        try:
            content = match.group(1).strip()
            # Убираем возможный язык в начале (python, javascript, etc)
            content = re.sub(r'^[a-zA-Z]+\s*\n', '', content)
            result = json.loads(content)
            logger.info("Parsed JSON: strategy 3 (``` block)")
            return result
        except json.JSONDecodeError:
            pass
    
    # Стратегия 4: найти первый { и последний }
    first_brace = response.find('{')
    last_brace = response.rfind('}')
    
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            json_str = response[first_brace:last_brace + 1]
            result = json.loads(json_str)
            logger.info("Parsed JSON: strategy 4 (brace extraction)")
            return result
        except json.JSONDecodeError:
            pass
    
    # Стратегия 5: исправить типичные ошибки
    try:
        # Убираем trailing commas
        fixed = re.sub(r',(\s*[}\]])', r'\1', response)
        first_brace = fixed.find('{')
        last_brace = fixed.rfind('}')
        if first_brace != -1 and last_brace != -1:
            result = json.loads(fixed[first_brace:last_brace + 1])
            logger.info("Parsed JSON: strategy 5 (fixed commas)")
            return result
    except json.JSONDecodeError:
        pass
    
    logger.error(f"Failed to parse JSON. Response preview:\n{response[:1000]}")
    return None


def detect_language(file_path: str) -> CodeLanguage:
    """Определяет язык по расширению"""
    if "." in file_path:
        ext = file_path.rsplit(".", 1)[-1].lower()
        return EXTENSION_TO_LANGUAGE.get(ext, CodeLanguage.UNKNOWN)
    return CodeLanguage.UNKNOWN


# ============================================================================
# CODING STYLE
# ============================================================================

def get_default_style(language: str) -> CodingStyle:
    """Стиль по умолчанию для языка"""
    
    lang = language.lower()
    
    if lang == "python":
        return CodingStyle(
            naming=NamingConvention(
                variables="snake_case",
                functions="snake_case",
                classes="PascalCase",
                constants="UPPER_SNAKE_CASE"
            ),
            docstring_format="Google",
            indent_size=4,
            max_line_length=88,
            use_type_hints=True
        )
    
    elif lang in ["javascript", "typescript"]:
        return CodingStyle(
            naming=NamingConvention(
                variables="camelCase",
                functions="camelCase",
                classes="PascalCase",
                constants="UPPER_SNAKE_CASE"
            ),
            docstring_format="JSDoc",
            indent_size=2,
            max_line_length=100,
            quote_style="single"
        )
    
    elif lang == "go":
        return CodingStyle(
            naming=NamingConvention(
                variables="camelCase",
                functions="camelCase",
                classes="PascalCase"
            ),
            indent_size=4,
            use_type_hints=True
        )
    
    return CodingStyle()


async def analyze_coding_style(
    repo_context: Dict[str, Any],
    tech_stack: TechStack
) -> CodingStyle:
    """Анализирует стиль из существующего кода"""
    
    key_files = repo_context.get("key_files", {})
    
    # Находим файлы с кодом
    code_samples = {}
    for path, content in key_files.items():
        lang = detect_language(path)
        if lang not in [CodeLanguage.UNKNOWN, CodeLanguage.MARKDOWN, 
                        CodeLanguage.YAML, CodeLanguage.JSON]:
            code_samples[path] = content[:15000]
    
    if not code_samples:
        return get_default_style(tech_stack.primary_language)
    
    # Быстрый анализ без LLM для скорости
    # Можно расширить с LLM если нужен более точный анализ
    return get_default_style(tech_stack.primary_language)


# ============================================================================
# CONTEXT MANAGER
# ============================================================================

class CodeContextManager:
    """Управление контекстом между генерируемыми файлами"""
    
    def __init__(self):
        self.generated_files: List[Dict[str, Any]] = []
        self.file_contents: Dict[str, str] = {}
        self.imports_map: Dict[str, List[str]] = {}
        self.classes_map: Dict[str, List[str]] = {}
        self.functions_map: Dict[str, List[str]] = {}
        self.dependencies_map: Dict[str, List[str]] = {}
    
    def add_file(self, file_data: Dict[str, Any]):
        """Добавляет файл в контекст"""
        path = file_data.get("path", "")
        if not path:
            return
        
        self.generated_files.append(file_data)
        
        # Сохраняем содержимое
        content = file_data.get("content", "")
        if content:
            self.file_contents[path] = content[:10000]  # Ограничиваем для контекста
        
        # Извлекаем структуру файла
        self._analyze_file_structure(file_data)
    
    def _analyze_file_structure(self, file_data: Dict[str, Any]):
        """Анализирует структуру файла для контекста"""
        path = file_data.get("path", "")
        content = file_data.get("content", "")
        
        if not path or not content:
            return
        
        lang = detect_language(path)
        
        # Извлекаем импорты
        imports = self._extract_imports(content, lang)
        if imports:
            self.imports_map[path] = imports
        
        # Извлекаем классы
        classes = self._extract_classes(content, lang)
        if classes:
            self.classes_map[path] = classes
        
        # Извлекаем функции
        functions = self._extract_functions(content, lang)
        if functions:
            self.functions_map[path] = functions
    
    def _extract_imports(self, content: str, lang: CodeLanguage) -> List[str]:
        """Извлекает импорты из кода"""
        imports = []
        
        if lang == CodeLanguage.PYTHON:
            # Паттерны для Python импортов
            patterns = [
                r'^import\s+(\w+(\.\w+)*)(\s+as\s+\w+)?',
                r'^from\s+(\w+(\.\w+)*)\s+import\s+',
            ]
            for line in content.split('\n'):
                line = line.strip()
                for pattern in patterns:
                    if re.match(pattern, line):
                        imports.append(line)
                        break
        
        elif lang in [CodeLanguage.JAVASCRIPT, CodeLanguage.TYPESCRIPT]:
            # Паттерны для JS/TS импортов
            patterns = [
                r'^import\s+.*from\s+[\'"](.+)[\'"]',
                r'^const\s+\w+\s*=\s*require\([\'"](.+)[\'"]\)',
            ]
            for line in content.split('\n'):
                line = line.strip()
                for pattern in patterns:
                    if re.search(pattern, line):
                        imports.append(line)
                        break
        
        return imports
    
    def _extract_classes(self, content: str, lang: CodeLanguage) -> List[str]:
        """Извлекает объявления классов"""
        classes = []
        
        if lang == CodeLanguage.PYTHON:
            pattern = r'^class\s+(\w+)'
            for line in content.split('\n'):
                match = re.match(pattern, line.strip())
                if match:
                    classes.append(match.group(1))
        
        elif lang in [CodeLanguage.JAVASCRIPT, CodeLanguage.TYPESCRIPT, CodeLanguage.JAVA]:
            pattern = r'^(?:export\s+)?(?:abstract\s+)?(?:public\s+)?class\s+(\w+)'
            for line in content.split('\n'):
                match = re.search(pattern, line.strip())
                if match:
                    classes.append(match.group(1))
        
        return classes
    
    def _extract_functions(self, content: str, lang: CodeLanguage) -> List[str]:
        """Извлекает объявления функций"""
        functions = []
        
        if lang == CodeLanguage.PYTHON:
            pattern = r'^def\s+(\w+)'
            for line in content.split('\n'):
                match = re.match(pattern, line.strip())
                if match:
                    functions.append(match.group(1))
        
        elif lang in [CodeLanguage.JAVASCRIPT, CodeLanguage.TYPESCRIPT]:
            patterns = [
                r'^(?:export\s+)?(?:async\s+)?function\s+(\w+)',
                r'^(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(?.*\)?\s*=>',
                r'^(?:export\s+)?let\s+(\w+)\s*=\s*(?:async\s+)?\(?.*\)?\s*=>',
            ]
            for line in content.split('\n'):
                line = line.strip()
                for pattern in patterns:
                    match = re.search(pattern, line)
                    if match:
                        functions.append(match.group(1))
                        break
        
        return functions
    
    def get_context_summary(self, max_files: int = 5) -> Dict[str, Any]:
        """Возвращает сводку контекста для промпта"""
        summary = {
            "total_files": len(self.generated_files),
            "recent_files": [],
            "imports_by_file": {},
            "classes_by_file": {},
            "functions_by_file": {},
            "file_relationships": []
        }
        
        # Берем последние файлы
        recent_files = self.generated_files[-max_files:] if self.generated_files else []
        
        for file_data in recent_files:
            path = file_data.get("path", "")
            description = file_data.get("description", "")
            lang = file_data.get("language", "")
            
            file_summary = {
                "path": path,
                "description": description,
                "language": lang,
                "has_content": path in self.file_contents
            }
            
            summary["recent_files"].append(file_summary)
            
            # Добавляем структуру если есть
            if path in self.imports_map:
                summary["imports_by_file"][path] = self.imports_map[path][:5]  # Ограничиваем
            
            if path in self.classes_map:
                summary["classes_by_file"][path] = self.classes_map[path]
            
            if path in self.functions_map:
                summary["functions_by_file"][path] = self.functions_map[path][:10]  # Ограничиваем
        
        # Анализируем связи между файлами
        summary["file_relationships"] = self._analyze_relationships()
        
        return summary
    
    def _analyze_relationships(self) -> List[Dict[str, Any]]:
        """Анализирует связи между файлами"""
        relationships = []
        
        for file_path, imports in self.imports_map.items():
            for imp in imports:
                # Пытаемся определить, на какой файл ссылается импорт
                target_file = self._find_import_target(imp, file_path)
                if target_file:
                    relationships.append({
                        "source": file_path,
                        "target": target_file,
                        "type": "import",
                        "detail": imp[:50]
                    })
        
        return relationships
    
    def _find_import_target(self, import_stmt: str, source_file: str) -> Optional[str]:
        """Находит файл, на который ссылается импорт"""
        # Простая эвристика: ищем файлы с похожими именами
        import_name = ""
        
        if "from" in import_stmt and "import" in import_stmt:
            # Python: from module import something
            match = re.search(r'from\s+([\w\.]+)\s+import', import_stmt)
            if match:
                import_name = match.group(1).replace('.', '/')
        elif "import" in import_stmt and "from" in import_stmt:
            # JS/TS: import something from 'module'
            match = re.search(r'from\s+[\'"](.+?)[\'"]', import_stmt)
            if match:
                import_name = match.group(1)
        
        if import_name:
            # Ищем файлы, содержащие import_name в пути
            for file_path in self.file_contents.keys():
                if import_name in file_path or \
                   any(part in file_path for part in import_name.split('/')):
                    return file_path
        
        return None
    
    def get_file_content_preview(self, file_path: str, max_lines: int = 50) -> str:
        """Возвращает превью содержимого файла"""
        if file_path in self.file_contents:
            content = self.file_contents[file_path]
            lines = content.split('\n')
            return '\n'.join(lines[:max_lines])
        return ""
    
    def get_related_files_context(self, current_file_path: str) -> Dict[str, Any]:
        """Возвращает контекст связанных файлов для текущего файла"""
        related = {
            "imports_from": [],
            "imports_to": [],
            "similar_files": []
        }
        
        current_dir = os.path.dirname(current_file_path)
        current_name = os.path.basename(current_file_path)
        
        # Ищем файлы в той же директории
        for file_path in self.file_contents.keys():
            if file_path == current_file_path:
                continue
                
            file_dir = os.path.dirname(file_path)
            file_name = os.path.basename(file_path)
            
            # Файлы в той же директории
            if file_dir == current_dir:
                related["similar_files"].append({
                    "path": file_path,
                    "name": file_name,
                    "preview": self.get_file_content_preview(file_path, 20)
                })
            
            # Импорты из текущего файла в другие
            if current_file_path in self.imports_map:
                for imp in self.imports_map.get(current_file_path, []):
                    if self._find_import_target(imp, current_file_path) == file_path:
                        related["imports_to"].append({
                            "target": file_path,
                            "import": imp
                        })
            
            # Импорты из других файлов в текущий
            if file_path in self.imports_map:
                for imp in self.imports_map.get(file_path, []):
                    if self._find_import_target(imp, file_path) == current_file_path:
                        related["imports_from"].append({
                            "source": file_path,
                            "import": imp
                        })
        
        return related


# ============================================================================
# CODE GENERATION
# ============================================================================

async def generate_code(
    task: str,
    architecture: Optional[Dict[str, Any]],
    tech_stack: TechStack,
    repo_context: Dict[str, Any],
    coding_style: CodingStyle,
    file_to_generate: Dict[str, Any],
    context_manager: CodeContextManager
) -> Dict[str, Any]:
    """
    Генерирует код на основе архитектуры с учетом контекста
    """
    
    components = architecture.get("components", []) if architecture else []
    file_structure = architecture.get("file_structure", []) if architecture else []
    interfaces = architecture.get("interfaces", []) if architecture else []
    patterns = architecture.get("patterns", []) if architecture else []
    integration_points = architecture.get("integration_points", []) if architecture else []

    # Получаем контекст из менеджера
    context_summary = context_manager.get_context_summary()
    related_context = context_manager.get_related_files_context(file_to_generate.get("path", ""))
    
    # Форматируем компоненты для промпта
    components_desc = []
    if components:
        for comp in components:
            desc = f"- **{comp.get('name', 'Unknown')}** ({comp.get('type', 'class')}): {comp.get('responsibility', '')}"
            methods = comp.get('methods', [])
            if methods:
                method_names = [m.get('name', '') for m in methods[:5]]
                desc += f"\n  Методы: {', '.join(method_names)}"
            components_desc.append(desc)

    # Форматируем структуру файлов
    files_desc = []
    if file_structure:
        for fs in file_structure:
            path = fs.get('path', '')
            contains = fs.get('contains', [])
            if path:
                files_desc.append(f"- {path}: содержит {', '.join(contains) if contains else 'модуль'}")

    # Форматируем контекст уже сгенерированных файлов
    context_files_desc = []
    for file_summary in context_summary.get("recent_files", []):
        path = file_summary.get("path", "")
        description = file_summary.get("description", "")
        language = file_summary.get("language", "")
        
        # Получаем превью содержимого
        content_preview = context_manager.get_file_content_preview(path, 30)
        
        context_entry = f"""
### Файл: {path}
**Описание:** {description}
**Язык:** {language}

**Содержимое (первые 30 строк):**
{content_preview}

"""
        
        # Добавляем информацию о структуре
        if path in context_summary.get("classes_by_file", {}):
            classes = context_summary["classes_by_file"][path]
            if classes:
                context_entry += f"\n**Классы:** {', '.join(classes)}"
        
        if path in context_summary.get("functions_by_file", {}):
            functions = context_summary["functions_by_file"][path]
            if functions:
                context_entry += f"\n**Функции:** {', '.join(functions[:5])}" + ("..." if len(functions) > 5 else "")
        
        context_files_desc.append(context_entry)
    
    # Форматируем связи с текущим файлом
    related_context_desc = []
    if related_context.get("imports_to"):
        related_context_desc.append("### Импорты ИЗ этого файла:")
        for imp in related_context["imports_to"][:3]:
            related_context_desc.append(f"- → {imp['target']} ({imp['import'][:50]})")
    
    if related_context.get("imports_from"):
        related_context_desc.append("### Импорты В этот файл:")
        for imp in related_context["imports_from"][:3]:
            related_context_desc.append(f"- ← {imp['source']} ({imp['import'][:50]})")
    
    if related_context.get("similar_files"):
        related_context_desc.append("### Файлы в той же директории:")
        for file_info in related_context["similar_files"][:3]:
            related_context_desc.append(f"- {file_info['name']}: {file_info['preview'][:100]}...")

    # Получаем путь к файлу для генерации
    file_path = file_to_generate.get('path', '')

    # Определяем, есть ли архитектурная информация
    has_architecture = bool(components or file_structure or interfaces or patterns)

    if has_architecture:
        prompt = f"""Напиши полный рабочий код для одного файла: {file_path}

## ЗАДАЧА
{task}

## ТЕКУЩИЙ ФАЙЛ (для генерации)
- Путь: {file_path}
- Содержит: {file_to_generate.get('contains', 'компоненты архитектуры')}

## КОНТЕКСТ УЖЕ СГЕНЕРИРОВАННЫХ ФАЙЛОВ ({context_summary.get('total_files', 0)} файлов всего)
{chr(10).join(context_files_desc) if context_files_desc else 'Это первый файл в проекте'}

## СВЯЗИ С ДРУГИМИ ФАЙЛАМИ
{chr(10).join(related_context_desc) if related_context_desc else 'Связей с другими файлами пока не обнаружено'}

## КОМПОНЕНТЫ ДЛЯ РЕАЛИЗАЦИИ
{chr(10).join(components_desc) if components_desc else 'Определи компоненты самостоятельно на основе задачи'}

## СТРУКТУРА ФАЙЛОВ (из архитектуры)
{chr(10).join(files_desc[:100]) if files_desc else 'Определи структуру самостоятельно'}

## ИНТЕРФЕЙСЫ
{json.dumps(interfaces, indent=2, ensure_ascii=False) if interfaces else 'Определи интерфейсы самостоятельно'}

## ПАТТЕРНЫ
{', '.join(patterns) if patterns else 'Используй подходящие паттерны'}

## ТЕХНОЛОГИИ
- Язык: {tech_stack.primary_language}
- Фреймворки: {', '.join(tech_stack.frameworks) if tech_stack.frameworks else 'стандартная библиотека'}

## СТИЛЬ КОДА
- Именование переменных: {coding_style.naming.variables}
- Именование функций: {coding_style.naming.functions}
- Именование классов: {coding_style.naming.classes}
- Docstrings: {coding_style.docstring_format}
- Отступы: {coding_style.indent_size} пробела

## КОНТЕКСТ РЕПОЗИТОРИЯ (если есть)
"""
        # Добавляем контекст из репозитория
        key_files = repo_context.get("key_files", {})
        if key_files:
            prompt += "\nСуществующие файлы в репозитории:\n"
            for path, content in list(key_files.items())[:2]:  # Ограничиваем
                prompt += f"\n{path}:\n```\n{content[:500]}...\n```\n"

        prompt += f"""
## ВАЖНЫЕ ТРЕБОВАНИЯ
1. Пиши ПОЛНЫЙ РАБОЧИЙ код - НЕ заглушки, НЕ TODO, НЕ pass
2. Файл должен быть законченным и работающим
3. Добавляй все необходимые импорты в начале файла
4. Добавляй docstrings к классам и функциям
5. Обрабатывай возможные ошибки
6. Код должен соответствовать указанному стилю
7. Учитывай уже сгенерированные файлы при написании кода
8. Согласуй импорты с существующими файлами
9. Используй классы и функции из уже сгенерированных файлов где это уместно
10. Следи за согласованностью API между файлами

## ФОРМАТ ОТВЕТА
Верни JSON объект (без markdown блоков):

{{
    "file": {{
        "path": "{file_path}",
        "content": "полный код файла",
        "language": "язык программирования",
        "description": "описание назначения файла",
        "dependencies": ["список зависимостей от других файлов"],
        "exports": ["что экспортирует этот файл"]
    }},
    "implementation_notes": [
        "заметка о реализации 1",
        "заметка о реализации 2"
    ],
    "integration_points": [
        {{"type": "import", "from": "файл", "what": "что импортируется"}},
        {{"type": "export", "to": "файл", "what": "что экспортируется"}}
    ]
}}

ВАЖНО: Верни только JSON, без ```json``` блоков!"""
    else:
        # Промпт без архитектуры - упрощённый
        prompt = f"""Напиши полный рабочий код для файла: {file_path}

## ЗАДАЧА
{task}

## КОНТЕКСТ УЖЕ СГЕНЕРИРОВАННЫХ ФАЙЛОВ ({context_summary.get('total_files', 0)} файлов всего)
{chr(10).join(context_files_desc) if context_files_desc else 'Это первый файл в проекте'}

## СВЯЗИ С ДРУГИМИ ФАЙЛАМИ
{chr(10).join(related_context_desc) if related_context_desc else 'Связей с другими файлами пока не обнаружено'}

## КОНТЕКСТ РЕПОЗИТОРИЯ
"""
        key_files = repo_context.get("key_files", {})
        if key_files:
            for path, content in list(key_files.items())[:2]:
                prompt += f"\n{path}:\n```\n{content[:500]}...\n```\n"

        prompt += f"""
## ТЕХНОЛОГИИ
- Язык: {tech_stack.primary_language}
- Фреймворки: {', '.join(tech_stack.frameworks) if tech_stack.frameworks else 'стандартная библиотека'}

## СТИЛЬ КОДА
- Именование переменных: {coding_style.naming.variables}
- Именование функций: {coding_style.naming.functions}
- Именование классов: {coding_style.naming.classes}
- Docstrings: {coding_style.docstring_format}
- Отступы: {coding_style.indent_size} пробела

## ТРЕБОВАНИЯ
1. Пиши ПОЛНЫЙ РАБОЧИЙ код - НЕ заглушки, НЕ TODO, НЕ pass
2. Файл должен быть законченным и работающим
3. Добавляй все необходимые импорты в начале файла
4. Добавляй docstrings к классам и функциям
5. Обрабатывай возможные ошибки
6. Код должен соответствовать указанному стилю
7. Учитывай уже сгенерированные файлы при написании кода
8. Согласуй импорты с существующими файлами

## ФОРМАТ ОТВЕТА
Верни JSON объект (без markdown блоков):

{{
    "file": {{
        "path": "{file_path}",
        "content": "полный код файла",
        "language": "язык программирования",
        "description": "описание назначения файла",
        "dependencies": ["список зависимостей от других файлов"]
    }},
    "implementation_notes": [
        "заметка о реализации 1",
        "заметка о реализации 2"
    ]
}}

ВАЖНО: Верни только JSON, без ```json``` блоков!"""

    logger.info(f"Generating code for {file_path} with context of {context_summary.get('total_files', 0)} files")
    response = await call_llm(prompt, max_tokens=100000, temperature=0.3, step="code_writer_code_generation_with_context")
    
    if not response:
        logger.error("Empty LLM response")
        return {"files": [], "implementation_notes": ["LLM returned empty response"]}
    
    result = parse_json_response(response)

    if not result:
        logger.error("Failed to parse response")
        return {"files": [], "implementation_notes": ["Failed to parse LLM response"]}

    file_data = result.get("file")
    if not file_data:
        logger.warning("No file in parsed response")
        # Попробуем ещё раз с более простым промптом
        return await generate_code_simple(task, tech_stack, coding_style, context_manager)

    # Возвращаем в формате массива для совместимости
    files = [file_data]
    result["files"] = files

    logger.info(f"Generated 1 file: {file_data.get('path', 'unknown')} with context awareness")
    return result


async def generate_code_simple(
    task: str,
    tech_stack: TechStack,
    coding_style: CodingStyle,
    context_manager: CodeContextManager
) -> Dict[str, Any]:
    """
    Упрощённая генерация когда основной метод не сработал
    """
    
    logger.info("Trying simple code generation...")

    # Получаем контекст
    context_summary = context_manager.get_context_summary()

    prompt = f"""Напиши код для следующей задачи.

ЗАДАЧА: {task}

## КОНТЕКСТ ({context_summary.get('total_files', 0)} файлов уже сгенерировано)
"""
    
    if context_summary.get("recent_files"):
        prompt += "Последние сгенерированные файлы:\n"
        for file_info in context_summary["recent_files"][:3]:
            prompt += f"- {file_info['path']}: {file_info['description']}\n"
    
    prompt += f"""
ЯЗЫК: {tech_stack.primary_language}

Создай все необходимые файлы с полным рабочим кодом.

Учитывай уже существующие файлы при генерации.

Верни ответ в формате JSON:
{{
    "files": [
        {{
            "path": "путь/к/файлу",
            "content": "полный код",
            "language": "{tech_stack.primary_language.lower()}",
            "description": "описание",
            "dependencies": ["другие_файлы"]
        }}
    ],
    "implementation_notes": ["как запустить"]
}}

Только JSON, без markdown!"""

    response = await call_llm(prompt, max_tokens=100000, temperature=0.4, step="code_writer_code_generation_simple_with_context")
    
    if not response:
        return {"files": [], "implementation_notes": ["Simple generation also failed"]}
    
    result = parse_json_response(response)
    
    if result and result.get("files"):
        logger.info(f"Simple generation succeeded: {len(result['files'])} files")
        return result
    
    return {"files": [], "implementation_notes": ["Could not generate code"]}


async def revise_code(
    original_code: Dict[str, Any],
    review_issues: List[Dict[str, Any]],
    suggestions: List[str],
    architecture: Dict[str, Any],
    tech_stack: TechStack,
    coding_style: CodingStyle,
    context_manager: CodeContextManager,
    iteration: int = 1
) -> Dict[str, Any]:
    """
    Исправляет код по замечаниям ревьюера с учетом контекста
    """

    original_files = original_code.get("files", [])

    if not original_files:
        logger.warning("No original files to revise")
        return original_code

    # Получаем контекст для всех файлов
    context_summary = context_manager.get_context_summary()

    results = {
        "files": [],
        "addressed_issues": [],
        "implementation_notes": [],
        "unaddressed_issues": []
    }

    for file in original_files:
        file_path = file.get("path", "")
        file_issues = [issue for issue in review_issues if issue.get("file_path") == file_path]

        if not file_issues:
            # No issues for this file, keep as is
            results["files"].append(file)
            continue

        # Получаем контекст связанных файлов
        related_context = context_manager.get_related_files_context(file_path)

        # Sort issues by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_issues = sorted(
            file_issues,
            key=lambda x: severity_order.get(x.get("severity", "low"), 3)
        )

        # Format file for prompt
        file_for_prompt = {
            "path": file.get("path", ""),
            "content": file.get("content", "")[:50000],  # Limit
            "language": file.get("language", "")
        }

        # Format issues
        issues_for_prompt = []
        for issue in sorted_issues[:50]:  # Top 50, but since per file, probably less
            issues_for_prompt.append({
                "id": issue.get("id", ""),
                "type": issue.get("type", ""),
                "severity": issue.get("severity", ""),
                "description": issue.get("description", ""),
                "file_path": issue.get("file_path", ""),
                "suggestion": issue.get("suggestion", "")
            })

        # Форматируем контекст связанных файлов
        context_desc = []
        if related_context.get("imports_to"):
            context_desc.append("### Этот файл импортирует из:")
            for imp in related_context["imports_to"][:3]:
                context_desc.append(f"- {imp['target']}: {imp['import'][:50]}")
        
        if related_context.get("imports_from"):
            context_desc.append("### Этот файл импортируется в:")
            for imp in related_context["imports_from"][:3]:
                context_desc.append(f"- {imp['source']}: {imp['import'][:50]}")

        prompt = f"""Исправь код одного файла по замечаниям код-ревьюера.

## ОРИГИНАЛЬНЫЙ ФАЙЛ
{json.dumps(file_for_prompt, indent=2, ensure_ascii=False)}

## КОНТЕКСТ СВЯЗАННЫХ ФАЙЛОВ
{chr(10).join(context_desc) if context_desc else 'Нет информации о связанных файлах'}

## ЗАМЕЧАНИЯ (отсортированы по важности)
{json.dumps(issues_for_prompt, indent=2, ensure_ascii=False)}

## ПРЕДЛОЖЕНИЯ ПО УЛУЧШЕНИЮ
{json.dumps(suggestions[:10], indent=2, ensure_ascii=False)}

## ТРЕБОВАНИЯ
1. Исправь ВСЕ critical и high замечания
2. По возможности исправь medium замечания
3. Сохрани общую структуру кода
4. Не удаляй существующий функционал
5. Учитывай связанные файлы при исправлении
6. Не ломай импорты/экспорты с другими файлами

## ФОРМАТ ОТВЕТА
Верни JSON (без markdown блоков):

{{
    "file": {{
        "path": "{file_path}",
        "content": "исправленный полный код",
        "language": "язык",
        "description": "что исправлено",
        "dependencies": ["обновленные зависимости"]
    }},
    "addressed_issues": ["id1", "id2"],
    "implementation_notes": ["что было изменено"],
    "integration_changes": ["изменения в интеграции с другими файлами"]
}}

Только JSON!"""

        response = await call_llm(prompt, max_tokens=100000, temperature=0.2, step="code_writer_code_revision_with_context")
        result = parse_json_response(response)

        if not result or not result.get("file"):
            logger.warning(f"Revision failed for {file_path}, keeping original")
            results["files"].append(file)
            # Add issues to unaddressed
            for issue in file_issues:
                results["unaddressed_issues"].append({
                    "id": issue.get("id", ""),
                    "reason": "Revision failed"
                })
            continue

        revised_file = result["file"]
        results["files"].append(revised_file)
        results["addressed_issues"].extend(result.get("addressed_issues", []))
        results["implementation_notes"].extend(result.get("implementation_notes", []))

    logger.info(f"Revision complete: {len(results['files'])} files, "
                f"addressed: {len(results['addressed_issues'])} issues")

    return results


# ============================================================================
# POST-PROCESSING
# ============================================================================

def clean_code_content(content: str, language: CodeLanguage) -> str:
    """Очищает код от артефактов"""
    
    if not content:
        return ""
    
    # Убираем markdown code blocks
    content = re.sub(r'^```[a-zA-Z]*\s*\n?', '', content)
    content = re.sub(r'\n?```\s*$', '', content)
    
    # Убираем trailing whitespace
    lines = [line.rstrip() for line in content.split('\n')]
    
    # Убираем множественные пустые строки подряд (оставляем максимум 2)
    cleaned = []
    empty_count = 0
    for line in lines:
        if line == "":
            empty_count += 1
            if empty_count <= 2:
                cleaned.append(line)
        else:
            empty_count = 0
            cleaned.append(line)
    
    # Убираем пустые строки в начале
    while cleaned and cleaned[0] == "":
        cleaned.pop(0)
    
    # Убираем пустые строки в конце (оставляем одну)
    while len(cleaned) > 1 and cleaned[-1] == "" and cleaned[-2] == "":
        cleaned.pop()
    
    result = '\n'.join(cleaned)
    
    # Добавляем финальный newline если нет
    if result and not result.endswith('\n'):
        result += '\n'
    
    return result


def post_process_files(
    files: List[Dict[str, Any]],
    tech_stack: TechStack
) -> List[CodeFile]:
    """Пост-обработка файлов"""
    
    processed = []
    
    for file_data in files:
        path = file_data.get("path", "")
        content = file_data.get("content", "")
        
        if not path:
            logger.warning("Skipping file without path")
            continue
        
        if not content:
            logger.warning(f"Skipping file without content: {path}")
            continue
        
        # Определяем язык
        language = detect_language(path)
        if file_data.get("language"):
            try:
                language = CodeLanguage(file_data["language"].lower())
            except ValueError:
                pass
        
        # Определяем действие
        action = FileAction.CREATE
        if file_data.get("action"):
            try:
                action = FileAction(file_data["action"].lower())
            except ValueError:
                pass
        
        # Очищаем контент
        content = clean_code_content(content, language)
        
        processed.append(CodeFile(
            path=path,
            content=content,
            language=language,
            description=file_data.get("description", ""),
            action=action,
            imports=file_data.get("imports", []),
            exports=file_data.get("exports", []),
            classes=file_data.get("classes", []),
            functions=file_data.get("functions", []),
            dependencies=file_data.get("dependencies", []),
            changes_description=file_data.get("changes_description")
        ))
    
    return processed


# ============================================================================
# MAIN ENDPOINT
# ============================================================================

@app.post("/process", response_model=CodeWriteResponse)
async def process_code_write(request: CodeWriteRequest):
    """Основной endpoint для написания кода"""

    AGENT_ACTIVE_REQUESTS.labels(method="POST", endpoint="/process").inc()
    start_time = time.time()
    task_id = str(uuid.uuid4())

    try:
        # Валидация входных данных
        if not request.task or not request.task.strip():
            raise HTTPException(
                status_code=400,
                detail="Task description is required and cannot be empty"
            )

        if request.action not in ["write_code", "revise_code"]:
            raise HTTPException(
                status_code=400,
                detail="Action must be either 'write_code' or 'revise_code'"
            )

        data = request.data
        action = request.action

        logger.info(f"[{task_id[:8]}] Action: {action}, Task: {request.task[:80]}...")

        # Извлекаем данные
        tech_stack_data = data.get("tech_stack", {})
        tech_stack = TechStack(**tech_stack_data) if tech_stack_data else TechStack()

        repo_context = data.get("repo_context", {})
        architecture = data.get("architecture", {})

        # Анализируем стиль
        coding_style = await analyze_coding_style(repo_context, tech_stack)

        # Определяем язык
        primary_language = CodeLanguage.UNKNOWN
        if tech_stack.primary_language:
            try:
                primary_language = CodeLanguage(tech_stack.primary_language.lower())
            except ValueError:
                pass

        # Инициализируем менеджер контекста
        context_manager = CodeContextManager()
        
        # Загружаем существующие файлы в контекст
        key_files = repo_context.get("key_files", {})
        for path, content in key_files.items():
            context_manager.add_file({
                "path": path,
                "content": content,
                "description": f"Existing file from repository",
            })

        # Выполняем действие
        if action == "write_code":
            result = {}
            result["files"] = []
            result["implementation_notes"] = []

            # Проверяем, есть ли архитектурная информация
            file_structure = architecture.get("file_structure", []) if architecture else []

            if file_structure:
                # Есть структура файлов - генерируем по архитектуре
                for fs in file_structure:
                    result_fs = await generate_code(
                        task=request.task,
                        architecture=architecture,
                        tech_stack=tech_stack,
                        repo_context=repo_context,
                        coding_style=coding_style,
                        file_to_generate=fs,
                        context_manager=context_manager
                    )

                    # Добавляем сгенерированный файл в контекст
                    if result_fs.get("file"):
                        context_manager.add_file(result_fs["file"])

                    if result_fs.get("files"):
                        result["files"].extend(result_fs["files"])
                    result["implementation_notes"].extend(result_fs["implementation_notes"])
                    
                    logger.info(f"[{task_id[:8]}] Generated file {fs.get('path', 'unknown')}, context now has {len(context_manager.generated_files)} files")
            else:
                # Нет архитектуры - генерируем простой файл
                logger.info("No architecture provided, generating simple file")
                result = await generate_code_simple(
                    task=request.task,
                    tech_stack=tech_stack,
                    coding_style=coding_style,
                    context_manager=context_manager
                )
                
                # Добавляем сгенерированные файлы в контекст
                if result.get("files"):
                    for file_data in result["files"]:
                        context_manager.add_file(file_data)

        elif action == "revise_code":
            original_code = data.get("original_code", {})
            review_comments = data.get("review_comments", [])
            suggestions = data.get("suggestions", [])
            iteration = data.get("iteration", 1)

            # Добавляем оригинальные файлы в контекст
            if original_code.get("files"):
                for file_data in original_code["files"]:
                    context_manager.add_file(file_data)

            result = await revise_code(
                original_code=original_code,
                review_issues=review_comments,
                suggestions=suggestions,
                architecture=architecture,
                tech_stack=tech_stack,
                coding_style=coding_style,
                context_manager=context_manager,
                iteration=iteration
            )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown action: {action}. Use 'write_code' or 'revise_code'"
            )

        # Пост-обработка файлов
        files = post_process_files(result.get("files", []), tech_stack)

        duration = time.time() - start_time
        status = "success" if files else "error"

        # Обновляем метрики
        AGENT_REQUESTS_TOTAL.labels(method="POST", endpoint="/process", status=status).inc()
        AGENT_RESPONSE_TIME_SECONDS_BUCKET.labels(method="POST", endpoint="/process").observe(duration)

        logger.info(f"[{task_id[:8]}] {status}: {len(files)} files in {duration:.1f}s, context had {len(context_manager.generated_files)} files")

        # Если нет файлов - логируем детали для диагностики
        if not files:
            logger.error(f"[{task_id[:8]}] No files generated!")
            logger.error(f"[{task_id[:8]}] implementation_notes: {result.get('implementation_notes', [])}")

        response = CodeWriteResponse(
            task_id=task_id,
            status=status,
            files=[f.dict() for f in files],
            implementation_notes=result.get("implementation_notes", []),
            changes_made=[],
            addressed_issues=result.get("addressed_issues", []),
            unaddressed_issues=result.get("unaddressed_issues", []),
            language=primary_language,
            coding_style_used=coding_style,
            duration_seconds=duration,
            context_info={
                "total_files_in_context": len(context_manager.generated_files),
                "files_analyzed": len(context_manager.file_contents)
            }
        )

        AGENT_ACTIVE_REQUESTS.labels(method="POST", endpoint="/process").dec()
        return response

    except HTTPException:
        AGENT_ACTIVE_REQUESTS.labels(method="POST", endpoint="/process").dec()
        raise
    except Exception as e:
        logger.exception(f"[{task_id[:8]}] Error: {e}")
        AGENT_ACTIVE_REQUESTS.labels(method="POST", endpoint="/process").dec()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ADDITIONAL ENDPOINTS
# ============================================================================

@app.post("/generate-single")
async def generate_single_file(request: Dict[str, Any]):
    """Генерация одного файла (для тестирования)"""

    AGENT_ACTIVE_REQUESTS.labels(method="POST", endpoint="/generate-single").inc()
    start_time = time.time()
    task = request.get("task", "")
    file_path = request.get("file_path", "main.py")
    language = request.get("language", "python")

    try:
        prompt = f"""Напиши код для файла {file_path}

Задача: {task}

Верни только код, без JSON обёртки, без ```."""

        content = await call_llm(prompt, max_tokens=100000, step="code_writer_single_file_generation")
        content = clean_code_content(content, detect_language(file_path))

        duration = time.time() - start_time
        AGENT_REQUESTS_TOTAL.labels(method="POST", endpoint="/generate-single", status="success").inc()
        AGENT_RESPONSE_TIME_SECONDS_BUCKET.labels(method="POST", endpoint="/generate-single").observe(duration)

        AGENT_ACTIVE_REQUESTS.labels(method="POST", endpoint="/generate-single").dec()
        return {
            "path": file_path,
            "content": content,
            "language": language
        }
    except Exception as e:
        AGENT_ACTIVE_REQUESTS.labels(method="POST", endpoint="/generate-single").dec()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint - не экспортирует метрики"""
    return {
        "status": "healthy",
        "service": "code_writer",
        "version": "2.3.0",  # Обновлена версия
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
        "service": "Code Writer Agent",
        "version": "2.3.0",  # Обновлена версия
        "description": "Writes code based on architecture specifications with context awareness",
        "endpoints": {
            "process": "POST /process - main endpoint",
            "generate_single": "POST /generate-single - single file generation",
            "health": "GET /health",
            "metrics": "GET /metrics - Prometheus metrics"
        },
        "actions": ["write_code", "revise_code"],
        "features": [
            "Context-aware code generation",
            "Inter-file dependency tracking",
            "Import/export relationship analysis",
            "Coding style consistency"
        ]
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