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
    structured_output: Dict[str, Any]

app = FastAPI(title="Design Assistant Agent", version="1.0.0")

OPENROUTER_MCP_URL = os.getenv("OPENROUTER_MCP_URL", "http://openrouter-mcp:8000")

def call_llm(prompt: str, model: str = "deepseek/deepseek-chat-v3-0324") -> str:
    try:
        response = requests.post(
            f"{OPENROUTER_MCP_URL}/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "Ты архитектор ПО. Создавай PlantUML диаграммы и давай советы по архитектуре."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return ""
    except Exception as e:
        logger.error(f"Error calling LLM: {str(e)}")
        return ""

def generate_plantuml_url(plantuml_code: str) -> str:
    """Генерация URL для PlantUML диаграммы"""
    # Убираем лишние пробелы
    plantuml_code = plantuml_code.strip()
    
    # Кодируем в UTF-8
    utf8_bytes = plantuml_code.encode('utf-8')
    
    # Сжимаем с помощью DEFLATE
    compressed = zlib.compress(utf8_bytes, 9)[2:-4]
    
    # Кодируем в base64
    encoded = base64.b64encode(compressed).decode('ascii')
    
    # Заменяем символы для URL
    encoded = encoded.translate(str.maketrans({
        '+': '-',
        '/': '_'
    }))
    
    return f"http://www.plantuml.com/plantuml/png/{encoded}"

def generate_architecture_advice(description: str) -> List[str]:
    """Генерация советов по архитектуре"""
    prompt = f"""
    На основе следующего описания системы дай 3-5 советов по архитектуре:
    
    {description}
    
    Советы должны быть конкретными и полезными. Верни список советов в JSON формате:
    {{"advice": ["совет1", "совет2", "совет3"]}}
    """
    
    response = call_llm(prompt)
    
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return result.get("advice", ["Проверь соблюдение принципов SOLID", "Добавь больше тестов", "Документируй API"])
        else:
            return ["Проверь соблюдение принципов SOLID", "Добавь больше тестов", "Документируй API"]
    except:
        return ["Проверь соблюдение принципов SOLID", "Добавь больше тестов", "Документируй API"]

def generate_plantuml_diagram(description: str, diagram_type: DesignType) -> str:
    """Генерация PlantUML кода"""
    
    type_prompts = {
        DesignType.ARCHITECTURE: """
        Создай PlantUML код для архитектурной диаграммы на основе описания:
        
        {description}
        
        Диаграмма должна показывать компоненты системы и их взаимодействие.
        Используй:
        - component для компонентов
        - interface для интерфейсов
        - arrow для связей
        - package для группировки
        
        Верни только PlantUML код без дополнительных объяснений.
        """,
        
        DesignType.FLOWCHART: """
        Создай PlantUML код для блок-схемы на основе описания:
        
        {description}
        
        Используй:
        - start и stop для начала и конца
        - :действие: для процессов
        - if для условий
        - -> для связей
        
        Верни только PlantUML код без дополнительных объяснений.
        """,
        
        DesignType.ER_DIAGRAM: """
        Создай PlantUML код для ER-диаграммы на основе описания:
        
        {description}
        
        Используй:
        - entity для сущностей
        - field для полей
        - relationship для связей
        
        Верни только PlantUML код без дополнительных объяснений.
        """,
        
        DesignType.SEQUENCE: """
        Создай PlantUML код для диаграммы последовательности на основе описания:
        
        {description}
        
        Используй:
        - participant для участников
        - -> для сообщений
        - activate для активации
        - deactivate для деактивации
        
        Верни только PlantUML код без дополнительных объяснений.
        """
    }
    
    prompt = type_prompts.get(diagram_type, type_prompts[DesignType.ARCHITECTURE])
    prompt = prompt.format(description=description)
    
    response = call_llm(prompt)
    
    # Очищаем ответ, оставляем только PlantUML код
    lines = response.split('\n')
    plantuml_lines = []
    in_plantuml = False
    
    for line in lines:
        line = line.strip()
        if line.startswith('@startuml'):
            in_plantuml = True
        if in_plantuml:
            plantuml_lines.append(line)
        if line.startswith('@enduml'):
            break
    
    if plantuml_lines:
        return '\n'.join(plantuml_lines)
    else:
        # Если не нашли PlantUML, создаем простую диаграмму
        return f"""@startuml
title {diagram_type.value.capitalize()} Diagram

package "System" {{
  component Component1
  component Component2
}}

Component1 --> Component2 : Interacts
@enduml"""

@app.post("/process")
async def process_design(request: DesignRequest):
    """Обработка запроса на создание диаграммы"""
    task_id = str(uuid.uuid4())
    
    try:
        # Генерируем PlantUML код
        plantuml_code = generate_plantuml_diagram(request.task, request.design_type)
        
        # Генерируем URL для диаграммы
        diagram_url = generate_plantuml_url(plantuml_code)
        
        # Генерируем советы по архитектуре
        advice = generate_architecture_advice(request.task)
        
        response_data = DesignResponse(
            task_id=task_id,
            status="completed",
            plantuml_code=plantuml_code,
            diagram_url=diagram_url,
            architecture_advice=advice,
            structured_output={
                "diagram_type": request.design_type.value,
                "plantuml_code": plantuml_code,
                "diagram_url": diagram_url,
                "advice": advice,
                "timestamp": datetime.now().isoformat(),
                "agent": "design_assistant"
            }
        )
        
        return JSONResponse(content=response_data.dict())
        
    except Exception as e:
        logger.error(f"Error in design process: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate/diagram")
async def generate_diagram(request: Dict[str, Any]):
    """Генерация диаграммы по описанию"""
    description = request.get("description", "")
    diagram_type = request.get("type", "architecture")
    
    if not description:
        raise HTTPException(status_code=400, detail="Description is required")
    
    try:
        design_type = DesignType(diagram_type)
    except:
        design_type = DesignType.ARCHITECTURE
    
    plantuml_code = generate_plantuml_diagram(description, design_type)
    diagram_url = generate_plantuml_url(plantuml_code)
    
    return {
        "plantuml_code": plantuml_code,
        "diagram_url": diagram_url,
        "type": diagram_type
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "design_assistant"}

@app.get("/")
async def root():
    return {
        "service": "Design Assistant Agent",
        "version": "1.0.0",
        "endpoints": {
            "process": "POST /process - Create diagram from task",
            "generate_diagram": "POST /generate/diagram - Generate diagram from description"
        },
        "supported_diagram_types": ["architecture", "flowchart", "er_diagram", "sequence"]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)