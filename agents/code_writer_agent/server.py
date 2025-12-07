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
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
import httpx

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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

OPENROUTER_MCP_URL = os.getenv("OPENROUTER_MCP_URL", "http://openrouter-mcp:8000")
LLM_TIMEOUT = 180
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL")

EXTENSION_TO_LANGUAGE = {
    "py": CodeLanguage.PYTHON,
    "js": CodeLanguage.JAVASCRIPT,
    "jsx": CodeLanguage.JAVASCRIPT,
    "ts": CodeLanguage.TYPESCRIPT,
    "tsx": CodeLanguage.TYPESCRIPT,
    "go": CodeLanguage.GO,
    "rs": CodeLanguage.RUST,
    "java": CodeLanguage.JAVA,
    "html": CodeLanguage.HTML,
    "css": CodeLanguage.CSS,
    "sql": CodeLanguage.SQL,
    "sh": CodeLanguage.SHELL,
    "yaml": CodeLanguage.YAML,
    "yml": CodeLanguage.YAML,
    "json": CodeLanguage.JSON,
    "md": CodeLanguage.MARKDOWN,
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
    version="2.2.0",
    lifespan=lifespan
)


# ============================================================================
# LLM HELPER
# ============================================================================

async def call_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 100000
) -> str:
    """Вызов LLM"""
    
    if not system_prompt:
        system_prompt = """Ты опытный программист. Пишешь чистый, рабочий, production-ready код.

ПРАВИЛА:
1. Пиши ПОЛНЫЙ код, не заглушки и не TODO
2. Добавляй все необходимые импорты
3. Добавляй docstrings и комментарии
4. Обрабатывай ошибки
5. Следуй архитектуре и стилю проекта
6. Отвечай ТОЛЬКО в формате JSON когда просят"""
    
    try:
        logger.info(f"Calling LLM, prompt length: {len(prompt)}")
        
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
            content = response.json()["choices"][0]["message"]["content"]
            logger.info(f"LLM response length: {len(content)}")
            return content
        else:
            logger.error(f"LLM error {response.status_code}: {response.text[:500]}")
            return ""
            
    except httpx.TimeoutException:
        logger.error("LLM timeout")
        return ""
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
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
            code_samples[path] = content[:1500]
    
    if not code_samples:
        return get_default_style(tech_stack.primary_language)
    
    # Быстрый анализ без LLM для скорости
    # Можно расширить с LLM если нужен более точный анализ
    return get_default_style(tech_stack.primary_language)


# ============================================================================
# CODE GENERATION
# ============================================================================

async def generate_code(
    task: str,
    architecture: Dict[str, Any],
    tech_stack: TechStack,
    repo_context: Dict[str, Any],
    coding_style: CodingStyle
) -> Dict[str, Any]:
    """
    Генерирует код на основе архитектуры
    """
    
    components = architecture.get("components", [])
    file_structure = architecture.get("file_structure", [])
    interfaces = architecture.get("interfaces", [])
    patterns = architecture.get("patterns", [])
    integration_points = architecture.get("integration_points", [])
    
    # Форматируем компоненты для промпта
    components_desc = []
    for comp in components:
        desc = f"- **{comp.get('name', 'Unknown')}** ({comp.get('type', 'class')}): {comp.get('responsibility', '')}"
        methods = comp.get('methods', [])
        if methods:
            method_names = [m.get('name', '') for m in methods[:5]]
            desc += f"\n  Методы: {', '.join(method_names)}"
        components_desc.append(desc)
    
    # Форматируем структуру файлов
    files_desc = []
    for fs in file_structure:
        path = fs.get('path', '')
        contains = fs.get('contains', [])
        if path and fs.get('type') != 'test':  # Пропускаем тесты
            files_desc.append(f"- {path}: содержит {', '.join(contains) if contains else 'модуль'}")
    
    prompt = f"""Напиши полный рабочий код для реализации задачи.

## ЗАДАЧА
{task}

## КОМПОНЕНТЫ ДЛЯ РЕАЛИЗАЦИИ
{chr(10).join(components_desc) if components_desc else 'Определи компоненты самостоятельно на основе задачи'}

## СТРУКТУРА ФАЙЛОВ
{chr(10).join(files_desc[:15]) if files_desc else 'Определи структуру самостоятельно'}

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

## ТРЕБОВАНИЯ
1. Пиши ПОЛНЫЙ РАБОЧИЙ код - НЕ заглушки, НЕ TODO, НЕ pass
2. Каждый файл должен быть законченным и работающим
3. Добавляй все необходимые импорты в начале файла
4. Добавляй docstrings к классам и функциям
5. Обрабатывай возможные ошибки
6. Код должен соответствовать указанному стилю

## ФОРМАТ ОТВЕТА
Верни JSON объект (без markdown блоков):

{{
    "files": [
        {{
            "path": "путь/к/файлу.расширение",
            "content": "полный код файла",
            "language": "язык программирования",
            "description": "описание назначения файла"
        }}
    ],
    "implementation_notes": [
        "заметка о реализации 1",
        "заметка о реализации 2"
    ]
}}

ВАЖНО: Верни только JSON, без ```json``` блоков!"""

    logger.info("Generating code...")
    response = await call_llm(prompt, max_tokens=100000, temperature=0.3)
    
    if not response:
        logger.error("Empty LLM response")
        return {"files": [], "implementation_notes": ["LLM returned empty response"]}
    
    result = parse_json_response(response)
    
    if not result:
        logger.error("Failed to parse response")
        return {"files": [], "implementation_notes": ["Failed to parse LLM response"]}
    
    files = result.get("files", [])
    
    if not files:
        logger.warning("No files in parsed response")
        # Попробуем ещё раз с более простым промптом
        return await generate_code_simple(task, tech_stack, coding_style)
    
    logger.info(f"Generated {len(files)} files")
    return result


async def generate_code_simple(
    task: str,
    tech_stack: TechStack,
    coding_style: CodingStyle
) -> Dict[str, Any]:
    """
    Упрощённая генерация когда основной метод не сработал
    """
    
    logger.info("Trying simple code generation...")
    
    prompt = f"""Напиши код для следующей задачи.

ЗАДАЧА: {task}

ЯЗЫК: {tech_stack.primary_language}

Создай все необходимые файлы с полным рабочим кодом.

Верни ответ в формате JSON:
{{
    "files": [
        {{
            "path": "путь/к/файлу",
            "content": "полный код",
            "language": "{tech_stack.primary_language.lower()}",
            "description": "описание"
        }}
    ],
    "implementation_notes": ["как запустить"]
}}

Только JSON, без markdown!"""

    response = await call_llm(prompt, max_tokens=100000, temperature=0.4)
    
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
    iteration: int = 1
) -> Dict[str, Any]:
    """
    Исправляет код по замечаниям ревьюера
    """
    
    original_files = original_code.get("files", [])
    
    if not original_files:
        logger.warning("No original files to revise")
        return original_code
    
    # Сортируем issues по severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_issues = sorted(
        review_issues,
        key=lambda x: severity_order.get(x.get("severity", "low"), 3)
    )
    
    # Форматируем файлы (ограничиваем размер контента)
    files_for_prompt = []
    for f in original_files:
        files_for_prompt.append({
            "path": f.get("path", ""),
            "content": f.get("content", "")[:5000],  # Ограничиваем
            "language": f.get("language", "")
        })
    
    # Форматируем issues
    issues_for_prompt = []
    for issue in sorted_issues[:15]:  # Берём топ-15
        issues_for_prompt.append({
            "id": issue.get("id", ""),
            "type": issue.get("type", ""),
            "severity": issue.get("severity", ""),
            "description": issue.get("description", ""),
            "file_path": issue.get("file_path", ""),
            "suggestion": issue.get("suggestion", "")
        })
    
    prompt = f"""Исправь код по замечаниям код-ревьюера.

## ОРИГИНАЛЬНЫЙ КОД
{json.dumps(files_for_prompt, indent=2, ensure_ascii=False)}

## ЗАМЕЧАНИЯ (отсортированы по важности)
{json.dumps(issues_for_prompt, indent=2, ensure_ascii=False)}

## ПРЕДЛОЖЕНИЯ ПО УЛУЧШЕНИЮ
{json.dumps(suggestions[:10], indent=2, ensure_ascii=False)}

## ТРЕБОВАНИЯ
1. Исправь ВСЕ critical и high замечания
2. По возможности исправь medium замечания
3. Сохрани общую структуру кода
4. Не удаляй существующий функционал

## ФОРМАТ ОТВЕТА
Верни JSON (без markdown блоков):

{{
    "files": [
        {{
            "path": "путь/к/файлу",
            "content": "исправленный полный код",
            "language": "язык",
            "description": "что исправлено"
        }}
    ],
    "addressed_issues": ["id1", "id2"],
    "implementation_notes": ["что было изменено"]
}}

Только JSON!"""

    response = await call_llm(prompt, max_tokens=100000, temperature=0.2)
    result = parse_json_response(response)
    
    if not result or not result.get("files"):
        logger.warning("Revision failed, returning original")
        return {
            "files": original_files,
            "implementation_notes": ["Revision parsing failed"],
            "addressed_issues": [],
            "unaddressed_issues": [{"id": "all", "reason": "Parse error"}]
        }
    
    logger.info(f"Revision complete: {len(result.get('files', []))} files, "
                f"addressed: {len(result.get('addressed_issues', []))} issues")
    
    return result


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
    
    start_time = time.time()
    task_id = str(uuid.uuid4())
    
    try:
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
        
        # Выполняем действие
        if action == "write_code":
            result = await generate_code(
                task=request.task,
                architecture=architecture,
                tech_stack=tech_stack,
                repo_context=repo_context,
                coding_style=coding_style
            )
            
        elif action == "revise_code":
            original_code = data.get("original_code", {})
            review_comments = data.get("review_comments", [])
            suggestions = data.get("suggestions", [])
            iteration = data.get("iteration", 1)
            
            result = await revise_code(
                original_code=original_code,
                review_issues=review_comments,
                suggestions=suggestions,
                architecture=architecture,
                tech_stack=tech_stack,
                coding_style=coding_style,
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
        
        logger.info(f"[{task_id[:8]}] {status}: {len(files)} files in {duration:.1f}s")
        
        # Если нет файлов - логируем детали для диагностики
        if not files:
            logger.error(f"[{task_id[:8]}] No files generated!")
            logger.error(f"[{task_id[:8]}] implementation_notes: {result.get('implementation_notes', [])}")
        
        return CodeWriteResponse(
            task_id=task_id,
            status=status,
            files=files,
            implementation_notes=result.get("implementation_notes", []),
            changes_made=[],
            addressed_issues=result.get("addressed_issues", []),
            unaddressed_issues=result.get("unaddressed_issues", []),
            language=primary_language,
            coding_style_used=coding_style,
            duration_seconds=duration
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[{task_id[:8]}] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ADDITIONAL ENDPOINTS
# ============================================================================

@app.post("/generate-single")
async def generate_single_file(request: Dict[str, Any]):
    """Генерация одного файла (для тестирования)"""
    
    task = request.get("task", "")
    file_path = request.get("file_path", "main.py")
    language = request.get("language", "python")
    
    prompt = f"""Напиши код для файла {file_path}

Задача: {task}

Верни только код, без JSON обёртки, без ```."""
    
    content = await call_llm(prompt, max_tokens=100000)
    content = clean_code_content(content, detect_language(file_path))
    
    return {
        "path": file_path,
        "content": content,
        "language": language
    }


@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "service": "code_writer",
        "version": "2.2.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Code Writer Agent",
        "version": "2.2.0",
        "description": "Writes code based on architecture specifications",
        "endpoints": {
            "process": "POST /process - main endpoint",
            "generate_single": "POST /generate-single - single file generation",
            "health": "GET /health"
        },
        "actions": ["write_code", "revise_code"]
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