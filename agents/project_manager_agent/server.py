import os
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import requests
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus метрики
TASKS_PROCESSED = Counter('project_manager_tasks_total', 'Total tasks processed')
TASKS_FAILED = Counter('project_manager_tasks_failed', 'Failed tasks')
SUBTASKS_CREATED = Counter('project_manager_subtasks_total', 'Subtasks created')

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Subtask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    assigned_agent: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.now)
    deadline: Optional[datetime] = None

class ProjectTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: str = "pending"
    subtasks: List[Subtask] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = {}

class AgentRequest(BaseModel):
    task: str
    data: Dict[str, Any] = {}
    priority: TaskPriority = TaskPriority.MEDIUM
    require_response: bool = True

class TaskPlan(BaseModel):
    task_id: str
    plan_steps: List[str]
    reasoning: str
    estimated_time: str
    subtasks: List[Subtask]

app = FastAPI(title="Project Manager Agent", version="1.0.0")

# Конфигурация
OPENROUTER_MCP_URL = os.getenv("OPENROUTER_MCP_URL", "http://openrouter-mcp:8000")
CODE_REVIEWER_URL = os.getenv("CODE_REVIEWER_URL", "http://code-reviewer:8000")
DOCUMENTATION_URL = os.getenv("DOCUMENTATION_URL", "http://documentation:8000")
DESIGN_ASSISTANT_URL = os.getenv("DESIGN_ASSISTANT_URL", "http://design-assistant:8000")

# Хранилище задач
tasks_db = {}
reasoning_logs = {}

def call_llm(prompt: str, model: str = "deepseek/deepseek-chat-v3-0324") -> str:
    """Вызов LLM через OpenRouter MCP"""
    try:
        response = requests.post(
            f"{OPENROUTER_MCP_URL}/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "Ты опытный проектный менеджер. Твоя задача - планировать, разбивать задачи и координировать работу команды."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            logger.error(f"LLM error: {response.status_code} - {response.text}")
            return ""
    except Exception as e:
        logger.error(f"Error calling LLM: {str(e)}")
        return ""

def decompose_task(task_description: str) -> Dict[str, Any]:
    """Разбить задачу на подзадачи с reasoning"""
    prompt = f"""
    Проанализируй следующую задачу разработки и создай подробный план выполнения:
    
    Задача: {task_description}
    
    Требуется:
    1. Разбей задачу на подзадачи (3-5 штук)
    2. Для каждой подзадачи определи:
       - Какое действие нужно выполнить
       - Какой агент должен это сделать (code_reviewer, documentation, design_assistant)
       - Приоритет (low, medium, high, critical)
    3. Оцени общее время выполнения
    4. Предоставь reasoning (обоснование) своего плана
    
    Верни ответ в JSON формате:
    {{
        "reasoning": "Твое обоснование плана",
        "estimated_time": "2 дня",
        "subtasks": [
            {{
                "description": "Описание подзадачи",
                "assigned_agent": "code_reviewer/documentation/design_assistant",
                "priority": "medium"
            }}
        ]
    }}
    """
    
    response = call_llm(prompt)
    
    try:
        # Ищем JSON в ответе
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            # Если не нашли JSON, создаем базовую структуру
            return {
                "reasoning": "Автоматическое разбиение задачи",
                "estimated_time": "Не определено",
                "subtasks": [
                    {
                        "description": "Проанализировать задачу",
                        "assigned_agent": "code_reviewer",
                        "priority": "high"
                    }
                ]
            }
    except Exception as e:
        logger.error(f"Error parsing LLM response: {str(e)}")
        return {
            "reasoning": "Ошибка при разборе ответа",
            "estimated_time": "Не определено",
            "subtasks": []
        }

def delegate_to_agent(agent_url: str, task: Dict[str, Any]) -> Dict[str, Any]:
    """Делегировать задачу другому агенту"""
    try:
        response = requests.post(
            f"{agent_url}/process",
            json=task,
            timeout=60
        )
        return response.json()
    except Exception as e:
        logger.error(f"Error delegating to {agent_url}: {str(e)}")
        return {"error": str(e), "status": "failed"}

@app.post("/process")
async def process_task(request: AgentRequest):
    """Основной endpoint для обработки задач"""
    TASKS_PROCESSED.inc()
    
    task_id = str(uuid.uuid4())
    reasoning_logs[task_id] = []
    
    try:
        # Логируем начало обработки
        reasoning_logs[task_id].append({
            "step": "start",
            "timestamp": datetime.now().isoformat(),
            "message": f"Начало обработки задачи: {request.task}"
        })
        
        # 1. Разбиваем задачу на подзадачи с reasoning
        reasoning_logs[task_id].append({
            "step": "decomposition",
            "timestamp": datetime.now().isoformat(),
            "message": "Начинаю анализ и разбиение задачи"
        })
        
        plan = decompose_task(request.task)
        
        reasoning_logs[task_id].append({
            "step": "plan_created",
            "timestamp": datetime.now().isoformat(),
            "message": f"Создан план: {plan.get('reasoning', '')}",
            "plan": plan
        })
        
        # 2. Создаем объект задачи
        project_task = ProjectTask(
            id=task_id,
            title=request.task[:50] + ("..." if len(request.task) > 50 else ""),
            description=request.task,
            priority=request.priority,
            metadata=request.data
        )
        
        # 3. Создаем подзадачи
        subtasks_results = []
        for subtask_data in plan.get("subtasks", []):
            SUBTASKS_CREATED.inc()
            
            subtask = Subtask(**subtask_data)
            project_task.subtasks.append(subtask)
            
            # Определяем URL агента
            agent_url = {
                "code_reviewer": CODE_REVIEWER_URL,
                "documentation": DOCUMENTATION_URL,
                "design_assistant": DESIGN_ASSISTANT_URL
            }.get(subtask.assigned_agent)
            
            if agent_url:
                # Делегируем подзадачу
                agent_task = {
                    "task": subtask.description,
                    "data": {**request.data, "parent_task_id": task_id},
                    "priority": subtask.priority.value
                }
                
                reasoning_logs[task_id].append({
                    "step": "delegation",
                    "timestamp": datetime.now().isoformat(),
                    "message": f"Делегирую задачу агенту {subtask.assigned_agent}: {subtask.description}"
                })
                
                result = delegate_to_agent(agent_url, agent_task)
                subtasks_results.append({
                    "subtask": subtask.dict(),
                    "result": result,
                    "agent": subtask.assigned_agent
                })
                
                # Обновляем статус подзадачи
                subtask.status = "completed" if "error" not in result else "failed"
        
        # 4. Сохраняем задачу
        project_task.status = "completed"
        project_task.updated_at = datetime.now()
        tasks_db[task_id] = project_task
        
        # 5. Формируем итоговый ответ
        response_data = {
            "task_id": task_id,
            "status": "completed",
            "plan": plan,
            "subtasks_results": subtasks_results,
            "reasoning_log": reasoning_logs[task_id],
            "structured_output": {
                "task": project_task.dict(),
                "metrics": {
                    "total_subtasks": len(project_task.subtasks),
                    "completed_subtasks": len([s for s in project_task.subtasks if s.status == "completed"]),
                    "failed_subtasks": len([s for s in project_task.subtasks if s.status == "failed"])
                }
            }
        }
        
        reasoning_logs[task_id].append({
            "step": "completion",
            "timestamp": datetime.now().isoformat(),
            "message": "Задача успешно выполнена",
            "results": response_data
        })
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        TASKS_FAILED.inc()
        logger.error(f"Error processing task: {str(e)}")
        
        reasoning_logs[task_id].append({
            "step": "error",
            "timestamp": datetime.now().isoformat(),
            "message": f"Ошибка при обработке: {str(e)}"
        })
        
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/task/{task_id}")
async def get_task(task_id: str):
    """Получить информацию о задаче"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "task": tasks_db[task_id].dict(),
        "reasoning_log": reasoning_logs.get(task_id, [])
    }

@app.get("/tasks")
async def list_tasks(status: Optional[str] = None):
    """Список всех задач"""
    tasks = list(tasks_db.values())
    
    if status:
        tasks = [t for t in tasks if t.status == status]
    
    return {
        "tasks": [t.dict() for t in tasks],
        "total": len(tasks)
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "project_manager"}

@app.get("/metrics")
async def metrics():
    return generate_latest()

@app.get("/reasoning/{task_id}")
async def get_reasoning(task_id: str):
    """Получить логи reasoning для задачи"""
    if task_id not in reasoning_logs:
        raise HTTPException(status_code=404, detail="Reasoning log not found")
    
    return reasoning_logs[task_id]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)