import os
import json
import logging
import uuid
import re
import base64
import zlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DesignType(str, Enum):
    ARCHITECTURE = "architecture"
    FLOWCHART = "flowchart"
    ER_DIAGRAM = "er_diagram"
    SEQUENCE = "sequence"
    CLASS_DIAGRAM = "class_diagram"
    COMPONENT = "component"
    DEPLOYMENT = "deployment"


class DesignRequest(BaseModel):
    task: str
    data: Dict[str, Any] = {}
    design_type: DesignType = DesignType.ARCHITECTURE
    style: str = "simple"


class DesignResponse(BaseModel):
    task_id: str
    status: str
    plantuml_code: str
    diagram_url: str
    architecture_advice: List[str]
    files_generated: List[Dict[str, Any]]
    structured_output: Dict[str, Any]


app = FastAPI(title="Design Assistant Agent", version="2.0.0")

OPENROUTER_MCP_URL = os.getenv("OPENROUTER_MCP_URL", "http://openrouter-mcp:8000")


def call_llm(prompt: str, system_prompt: str = None) -> str:
    if not system_prompt:
        system_prompt = """Ты опытный архитектор ПО.
Создаёшь понятные PlantUML диаграммы.
Даёшь практичные советы по архитектуре.
Учитываешь существующую структуру проекта."""

    try:
        response = requests.post(
            f"{OPENROUTER_MCP_URL}/chat/completions",
            json={
                "model": "deepseek/deepseek-chat-v3-0324",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2
            },
            timeout=90
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return ""
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return ""


def generate_plantuml_url(plantuml_code: str) -> str:
    plantuml_code = plantuml_code.strip()
    utf8_bytes = plantuml_code.encode('utf-8')
    compressed = zlib.compress(utf8_bytes, 9)[2:-4]
    encoded = base64.b64encode(compressed).decode('ascii')
    encoded = encoded.translate(str.maketrans({'+': '-', '/': '_'}))
    return f"http://www.plantuml.com/plantuml/png/{encoded}"


def analyze_existing_architecture(repo_context: Dict[str, Any], tech_stack: Dict[str, Any]) -> Dict[str, Any]:
    
    structure = repo_context.get("structure", [])
    key_files = repo_context.get("key_files", {})
    
    prompt = f"""
Проанализируй архитектуру проекта:

## Технологический стек:
{json.dumps(tech_stack, indent=2)}

## Структура файлов:
{json.dumps(structure[:50], indent=2)}

## Ключевые файлы:
{json.dumps(list(key_files.keys()), indent=2)}

Определи:
1. Архитектурный паттерн (monolith, microservices, etc.)
2. Слои приложения
3. Основные компоненты
4. Внешние зависимости
5. Точки интеграции

Верни JSON:
{{
    "pattern": "название паттерна",
    "layers": ["список слоёв"],
    "components": [
        {{"name": "имя", "type": "тип", "responsibility": "ответственность"}}
    ],
    "external_services": ["внешние сервисы"],
    "integration_points": ["точки интеграции"]
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
        "pattern": "unknown",
        "layers": [],
        "components": [],
        "external_services": [],
        "integration_points": []
    }


def generate_diagram_from_context(
    task: str,
    design_type: DesignType,
    tech_stack: Dict[str, Any],
    repo_context: Dict[str, Any],
    architecture_analysis: Dict[str, Any]
) -> str:
    
    type_templates = {
        DesignType.ARCHITECTURE: """
Создай архитектурную диаграмму компонентов.
Используй:
- package для группировки
- component для компонентов  
- interface для интерфейсов
- database для БД
- cloud для внешних сервисов
""",
        DesignType.CLASS_DIAGRAM: """
Создай диаграмму классов.
Используй:
- class для классов
- interface для интерфейсов
- abstract для абстрактных классов
- Покажи наследование и композицию
""",
        DesignType.SEQUENCE: """
Создай диаграмму последовательности.
Используй:
- participant/actor для участников
- -> для синхронных вызовов
- --> для асинхронных
- activate/deactivate для активации
""",
        DesignType.ER_DIAGRAM: """
Создай ER диаграмму.
Используй:
- entity для сущностей
- Покажи связи: one-to-many, many-to-many
- Укажи ключевые поля
""",
        DesignType.FLOWCHART: """
Создай блок-схему процесса.
Используй:
- start/stop
- :действие: для процессов
- if/else для условий
- fork/merge для параллельности
""",
        DesignType.COMPONENT: """
Создай диаграмму компонентов.
Покажи:
- Основные компоненты
- Их интерфейсы
- Зависимости между ними
""",
        DesignType.DEPLOYMENT: """
Создай диаграмму развёртывания.
Покажи:
- Серверы/контейнеры
- Компоненты на них
- Сетевые соединения
"""
    }
    
    prompt = f"""
Создай PlantUML диаграмму типа {design_type.value} для проекта.

## ЗАДАЧА:
{task}

## АНАЛИЗ АРХИТЕКТУРЫ:
{json.dumps(architecture_analysis, indent=2, ensure_ascii=False)}

## ТЕХНОЛОГИЧЕСКИЙ СТЕК:
- Язык: {tech_stack.get('primary_language', 'unknown')}
- Фреймворки: {', '.join(tech_stack.get('frameworks', []))}
- Паттерны: {', '.join(tech_stack.get('architecture_patterns', []))}

## ТРЕБОВАНИЯ К ДИАГРАММЕ:
{type_templates.get(design_type, "Создай подходящую диаграмму")}

## ПРАВИЛА:
1. Диаграмма должна отражать РЕАЛЬНУЮ структуру проекта
2. Используй понятные названия компонентов
3. Добавь title с описанием
4. Используй цвета для группировки (#LightBlue, #LightGreen, etc.)
5. Добавь legend если нужно

Верни только PlantUML код, начиная с @startuml и заканчивая @enduml.
"""
    
    response = call_llm(prompt)
    
    # Извлекаем PlantUML код
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
    
    # Fallback диаграмма
    components = architecture_analysis.get("components", [])
    comp_str = "\n".join([f'  component "{c.get("name", "Component")}"' for c in components[:10]])
    
    return f"""@startuml
title {design_type.value.replace("_", " ").title()} Diagram

package "System" {{
{comp_str if comp_str else '  component "Main Component"'}
}}

@enduml"""


def generate_architecture_advice(
    task: str,
    tech_stack: Dict[str, Any],
    architecture_analysis: Dict[str, Any]
) -> List[str]:
    
    prompt = f"""
На основе анализа проекта дай 5 практичных советов по архитектуре.

## ЗАДАЧА:
{task}

## ТЕКУЩАЯ АРХИТЕКТУРА:
{json.dumps(architecture_analysis, indent=2, ensure_ascii=False)}

## СТЕК:
{json.dumps(tech_stack, indent=2)}

Дай советы по:
1. Улучшению текущей архитектуры
2. Масштабированию
3. Безопасности
4. Производительности
5. Поддерживаемости

Верни JSON:
{{"advice": ["совет1", "совет2", "совет3", "совет4", "совет5"]}}
"""
    
    response = call_llm(prompt)
    
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return result.get("advice", [])
    except:
        pass
    
    return [
        "Рассмотрите разделение на слои для лучшей поддерживаемости",
        "Добавьте интеграционные тесты для критических путей",
        "Документируйте архитектурные решения (ADR)"
    ]


@app.post("/process")
async def process_design(request: DesignRequest):
    task_id = str(uuid.uuid4())
    
    try:
        data = request.data
        tech_stack = data.get("tech_stack", {})
        repo_context = data.get("repo_context", {})
        
        # Анализируем существующую архитектуру
        architecture_analysis = analyze_existing_architecture(repo_context, tech_stack)
        
        # Генерируем диаграмму
        plantuml_code = generate_diagram_from_context(
            task=request.task,
            design_type=request.design_type,
            tech_stack=tech_stack,
            repo_context=repo_context,
            architecture_analysis=architecture_analysis
        )
        
        # Генерируем URL
        diagram_url = generate_plantuml_url(plantuml_code)
        
        # Генерируем советы
        advice = generate_architecture_advice(request.task, tech_stack, architecture_analysis)
        
        # Файлы для создания
        files_generated = [
            {
                "path": f"docs/diagrams/{request.design_type.value}.puml",
                "content": plantuml_code,
                "description": f"{request.design_type.value} diagram"
            }
        ]
        
        response = DesignResponse(
            task_id=task_id,
            status="completed",
            plantuml_code=plantuml_code,
            diagram_url=diagram_url,
            architecture_advice=advice,
            files_generated=files_generated,
            structured_output={
                "design_type": request.design_type.value,
                "architecture_analysis": architecture_analysis,
                "diagram_url": diagram_url,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return JSONResponse(content=response.dict())
        
    except Exception as e:
        logger.error(f"Design error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "design_assistant", "version": "2.0.0"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)