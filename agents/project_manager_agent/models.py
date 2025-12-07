"""
Pydantic модели для Project Manager Agent
ИСПРАВЛЕНО: Унифицированы контракты с другими агентами
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field
import uuid


# ============================================================================
# ENUMS
# ============================================================================

class TaskState(str, Enum):
    """Состояния выполнения задачи"""
    PENDING = "pending"
    PLANNING = "planning"
    ARCHITECTURE = "architecture"
    CODING = "coding"
    REVIEWING = "reviewing"
    REVISION = "revision"
    DOCUMENTING = "documenting"
    AGGREGATING = "aggregating"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentType(str, Enum):
    """Типы агентов"""
    ARCHITECT = "architect"
    CODE_WRITER = "code_writer"
    CODE_REVIEWER = "code_reviewer"
    DOCUMENTATION = "documentation"


class TaskPriority(str, Enum):
    """Приоритет задачи"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FileAction(str, Enum):
    """Действие с файлом"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


# ============================================================================
# TECH STACK
# ============================================================================

class TechStack(BaseModel):
    """Технологический стек проекта"""
    primary_language: str = "unknown"
    languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    databases: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    package_managers: List[str] = Field(default_factory=list)
    testing_frameworks: List[str] = Field(default_factory=list)
    ci_cd: List[str] = Field(default_factory=list)
    architecture_patterns: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "allow"


# ============================================================================
# FILE MODELS (унифицированные)
# ============================================================================

class FileToCreate(BaseModel):
    """
    Унифицированная модель файла
    Совместима с CodeFile от Code Writer и DocFile от Documentation
    """
    path: str
    content: str
    language: str = "text"
    description: str = ""
    action: FileAction = FileAction.CREATE
    source_agent: str = "unknown"
    
    # Дополнительные метаданные (опционально)
    doc_type: Optional[str] = None  # Для документации
    
    class Config:
        extra = "allow"


# ============================================================================
# PIPELINE MODELS
# ============================================================================

class PipelineStep(BaseModel):
    """Шаг в пайплайне выполнения"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent: AgentType
    action: str
    description: str = ""
    depends_on: List[str] = Field(default_factory=list)
    input_from: List[AgentType] = Field(default_factory=list)
    priority: TaskPriority = TaskPriority.MEDIUM
    timeout_seconds: int = 180
    retry_count: int = 0
    max_retries: int = 2


class Pipeline(BaseModel):
    """Пайплайн выполнения задачи"""
    steps: List[PipelineStep]
    reasoning: str = ""
    estimated_time_seconds: int = 0
    
    def get_step_by_agent(self, agent: AgentType) -> Optional[PipelineStep]:
        for step in self.steps:
            if step.agent == agent:
                return step
        return None


# ============================================================================
# AGENT RESULT MODELS
# ============================================================================

class ArchitectureResult(BaseModel):
    """
    Результат работы Architect Agent
    Хранит как структурированные данные, так и плоские для передачи
    """
    # Плоская структура (для передачи другим агентам)
    components: List[Dict[str, Any]] = Field(default_factory=list)
    patterns: List[str] = Field(default_factory=list)
    file_structure: List[Dict[str, Any]] = Field(default_factory=list)
    interfaces: List[Dict[str, Any]] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    integration_points: List[Dict[str, Any]] = Field(default_factory=list)
    diagrams: Dict[str, str] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "allow"


class CodeResult(BaseModel):
    """
    Результат работы Code Writer Agent
    """
    files: List[Dict[str, Any]] = Field(default_factory=list)  # Сырые данные файлов
    implementation_notes: List[str] = Field(default_factory=list)
    changes_made: List[Dict[str, Any]] = Field(default_factory=list)
    addressed_issues: List[str] = Field(default_factory=list)
    unaddressed_issues: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        extra = "allow"
    
    def get_files_for_github(self) -> List[FileToCreate]:
        """Конвертирует файлы в формат для GitHub"""
        result = []
        for f in self.files:
            try:
                action = FileAction(f.get("action", "create"))
            except ValueError:
                action = FileAction.CREATE
            
            result.append(FileToCreate(
                path=f.get("path", ""),
                content=f.get("content", ""),
                language=f.get("language", "text"),
                description=f.get("description", ""),
                action=action,
                source_agent="code_writer"
            ))
        return result


class ReviewIssue(BaseModel):
    """Замечание от Code Reviewer"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: str
    severity: str
    title: str = ""
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None
    
    class Config:
        extra = "allow"


class ReviewResult(BaseModel):
    """
    Результат работы Code Reviewer Agent
    """
    approved: bool = False
    needs_revision: bool = True
    quality_score: float = 0.0
    issues: List[ReviewIssue] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    summary: str = ""
    
    # Дополнительные метрики
    metrics: Dict[str, Any] = Field(default_factory=dict)
    blocking_issues: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "allow"
    
    @property
    def critical_issues(self) -> List[ReviewIssue]:
        return [i for i in self.issues if i.severity == "critical"]
    
    @property
    def high_issues(self) -> List[ReviewIssue]:
        return [i for i in self.issues if i.severity == "high"]


class DocumentationResult(BaseModel):
    """
    Результат работы Documentation Agent
    """
    files: List[Dict[str, Any]] = Field(default_factory=list)
    sections_created: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "allow"
    
    def get_files_for_github(self) -> List[FileToCreate]:
        """Конвертирует файлы в формат для GitHub"""
        result = []
        for f in self.files:
            if not f:
                continue
            try:
                action = FileAction(f.get("action", "create"))
            except ValueError:
                action = FileAction.CREATE
            
            result.append(FileToCreate(
                path=f.get("path", ""),
                content=f.get("content", ""),
                language="markdown",
                description=f.get("description", ""),
                action=action,
                source_agent="documentation",
                doc_type=f.get("doc_type")
            ))
        return result


# ============================================================================
# TASK CONTEXT
# ============================================================================

class TaskContext(BaseModel):
    """
    Контекст задачи - передаётся между агентами
    Содержит все данные и результаты
    """
    # Идентификация
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Входные данные
    task_description: str
    repo_owner: str
    repo_name: str
    base_branch: str = "main"
    repo_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Анализ
    tech_stack: Optional[TechStack] = None
    
    # Pipeline
    pipeline: Optional[Pipeline] = None
    current_state: TaskState = TaskState.PENDING
    current_step_index: int = 0
    
    # Результаты агентов
    architecture_result: Optional[ArchitectureResult] = None
    code_result: Optional[CodeResult] = None
    review_result: Optional[ReviewResult] = None
    documentation_result: Optional[DocumentationResult] = None
    
    # Review loop
    review_iterations: int = 0
    max_review_iterations: int = 3
    revision_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Финальные данные
    branch_name: Optional[str] = None
    commit_message: Optional[str] = None
    pr_title: Optional[str] = None
    pr_description: Optional[str] = None
    
    # Логирование
    reasoning_log: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        extra = "allow"
    
    def log_step(self, step: str, message: str, data: Optional[Dict] = None):
        """Добавляет запись в лог"""
        self.reasoning_log.append({
            "step": step,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        })
    
    def log_error(self, step: str, error: str, details: Optional[Dict] = None):
        """Добавляет ошибку в лог"""
        self.errors.append({
            "step": step,
            "error": error,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        })
    
    def get_all_files(self) -> List[FileToCreate]:
        """Собирает все файлы от всех агентов"""
        files = []
        
        # Файлы от Code Writer
        if self.code_result:
            files.extend(self.code_result.get_files_for_github())
        
        # Файлы от Documentation
        if self.documentation_result:
            files.extend(self.documentation_result.get_files_for_github())
        
        # Диаграммы от Architect
        if self.architecture_result and self.architecture_result.diagrams:
            for diagram_type, content in self.architecture_result.diagrams.items():
                files.append(FileToCreate(
                    path=f"docs/diagrams/{diagram_type}.puml",
                    content=content,
                    language="plantuml",
                    description=f"{diagram_type} diagram",
                    source_agent="architect"
                ))
        
        return files


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AgentCallResult(BaseModel):
    """Результат вызова агента"""
    agent: AgentType
    status: str  # success, error, timeout
    duration_seconds: float
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class WorkflowRequest(BaseModel):
    """Запрос на выполнение workflow"""
    task_description: str
    repo_owner: str
    repo_name: str
    base_branch: str = "main"
    repo_context: Optional[Dict[str, Any]] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    max_review_iterations: int = 3


class WorkflowResponse(BaseModel):
    """Ответ workflow"""
    task_id: str
    status: str
    tech_stack: Optional[TechStack] = None
    branch_name: str
    files_to_create: List[Dict[str, Any]]
    commit_message: str
    pr_title: str
    pr_description: str
    summary: str
    
    # Детали выполнения
    pipeline_executed: List[Dict[str, Any]] = Field(default_factory=list)
    agent_results: Dict[str, Any] = Field(default_factory=dict)
    review_iterations: int = 0
    
    # Логи
    reasoning_log: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Метрики
    total_duration_seconds: float = 0.0