"""
Pydantic модели для Code Reviewer Agent
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid


# ============================================================================
# ENUMS
# ============================================================================

class IssueSeverity(str, Enum):
    """Серьёзность проблемы"""
    CRITICAL = "critical"  # Блокирует релиз, нужно исправить обязательно
    HIGH = "high"          # Серьёзная проблема, нужно исправить
    MEDIUM = "medium"      # Желательно исправить
    LOW = "low"            # Можно исправить позже / косметика


class IssueType(str, Enum):
    """Тип проблемы"""
    BUG = "bug"                                  # Логическая ошибка
    SECURITY = "security"                        # Уязвимость безопасности
    PERFORMANCE = "performance"                  # Проблема производительности
    ARCHITECTURE_VIOLATION = "architecture_violation"  # Нарушение архитектуры
    STYLE = "style"                              # Нарушение стиля кода
    MAINTAINABILITY = "maintainability"          # Проблема поддерживаемости
    DOCUMENTATION = "documentation"              # Отсутствие/плохая документация
    TYPE_ERROR = "type_error"                    # Ошибка типизации
    ERROR_HANDLING = "error_handling"            # Плохая обработка ошибок
    DUPLICATION = "duplication"                  # Дублирование кода
    COMPLEXITY = "complexity"                    # Излишняя сложность
    NAMING = "naming"                            # Плохое именование
    TESTING = "testing"                          # Проблемы с тестируемостью
    COMPATIBILITY = "compatibility"              # Проблемы совместимости


class ReviewDecision(str, Enum):
    """Решение по ревью"""
    APPROVED = "approved"           # Код готов к merge
    NEEDS_REVISION = "needs_revision"  # Требуется доработка
    REJECTED = "rejected"           # Код отклонён (серьёзные проблемы)


# ============================================================================
# ISSUE MODELS
# ============================================================================

class CodeLocation(BaseModel):
    """Расположение проблемы в коде"""
    file_path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    column_start: Optional[int] = None
    column_end: Optional[int] = None
    
    def __str__(self) -> str:
        loc = self.file_path
        if self.line_start:
            loc += f":{self.line_start}"
            if self.line_end and self.line_end != self.line_start:
                loc += f"-{self.line_end}"
        return loc


class ReviewIssue(BaseModel):
    """Замечание по коду"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: IssueType
    severity: IssueSeverity
    title: str
    description: str
    
    # Расположение
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    line_end: Optional[int] = None
    
    # Контекст
    code_snippet: Optional[str] = None
    
    # Решение
    suggestion: Optional[str] = None
    suggested_code: Optional[str] = None
    
    # Дополнительно
    references: List[str] = Field(default_factory=list)  # Ссылки на документацию
    effort_to_fix: str = "low"  # low, medium, high
    
    class Config:
        extra = "allow"
    
    @property
    def location(self) -> str:
        if self.file_path:
            loc = self.file_path
            if self.line_number:
                loc += f":{self.line_number}"
            return loc
        return "general"


class FileSummary(BaseModel):
    """Сводка по файлу"""
    file_path: str
    language: str = "unknown"
    lines_of_code: int = 0
    issues_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    quality_score: float = 10.0
    recommendations: List[str] = Field(default_factory=list)


# ============================================================================
# ARCHITECTURE COMPLIANCE
# ============================================================================

class ArchitectureCheck(BaseModel):
    """Проверка соответствия архитектуре"""
    component_name: str
    expected: str
    actual: str
    compliant: bool
    issue: Optional[str] = None


class ArchitectureCompliance(BaseModel):
    """Результат проверки соответствия архитектуре"""
    overall_compliant: bool = True
    checks: List[ArchitectureCheck] = Field(default_factory=list)
    missing_components: List[str] = Field(default_factory=list)
    extra_components: List[str] = Field(default_factory=list)
    interface_violations: List[str] = Field(default_factory=list)
    dependency_violations: List[str] = Field(default_factory=list)


# ============================================================================
# SECURITY CHECK
# ============================================================================

class SecurityFinding(BaseModel):
    """Находка безопасности"""
    vulnerability_type: str  # sql_injection, xss, hardcoded_secret, etc.
    severity: IssueSeverity
    file_path: str
    line_number: Optional[int] = None
    description: str
    cwe_id: Optional[str] = None  # Common Weakness Enumeration
    remediation: str


class SecurityReport(BaseModel):
    """Отчёт по безопасности"""
    passed: bool = True
    findings: List[SecurityFinding] = Field(default_factory=list)
    checked_patterns: List[str] = Field(default_factory=list)


# ============================================================================
# REVIEW RESULT
# ============================================================================

class ReviewMetrics(BaseModel):
    """Метрики ревью"""
    total_files: int = 0
    total_lines: int = 0
    total_issues: int = 0
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0
    
    # Breakdown по типам
    bugs: int = 0
    security_issues: int = 0
    performance_issues: int = 0
    style_issues: int = 0
    
    # Качество
    overall_quality_score: float = 0.0
    maintainability_score: float = 0.0
    security_score: float = 0.0
    performance_score: float = 0.0


class ReviewResult(BaseModel):
    """Полный результат ревью"""
    decision: ReviewDecision
    approved: bool = False
    needs_revision: bool = True
    
    # Качество
    quality_score: float = 0.0  # 0-10
    
    # Проблемы
    issues: List[ReviewIssue] = Field(default_factory=list)
    
    # Рекомендации
    suggestions: List[str] = Field(default_factory=list)
    
    # Сводка
    summary: str = ""
    
    # Детальные отчёты
    metrics: ReviewMetrics = Field(default_factory=ReviewMetrics)
    file_summaries: List[FileSummary] = Field(default_factory=list)
    architecture_compliance: Optional[ArchitectureCompliance] = None
    security_report: Optional[SecurityReport] = None
    
    # Для итерации
    blocking_issues: List[str] = Field(default_factory=list)  # ID issues которые блокируют
    
    class Config:
        extra = "allow"
    
    @property
    def critical_issues(self) -> List[ReviewIssue]:
        return [i for i in self.issues if i.severity == IssueSeverity.CRITICAL]
    
    @property
    def high_issues(self) -> List[ReviewIssue]:
        return [i for i in self.issues if i.severity == IssueSeverity.HIGH]
    
    def get_issues_for_file(self, file_path: str) -> List[ReviewIssue]:
        return [i for i in self.issues if i.file_path == file_path]


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CodeFile(BaseModel):
    """Файл с кодом для ревью"""
    path: str
    content: str
    language: str = "unknown"
    description: str = ""
    action: str = "create"
    
    class Config:
        extra = "allow"


class CodeReviewRequest(BaseModel):
    """Запрос на ревью кода"""
    task: str
    action: str = "review_code"
    data: Dict[str, Any] = Field(default_factory=dict)
    priority: str = "medium"


class CodeReviewResponse(BaseModel):
    """Ответ с результатами ревью"""
    task_id: str
    status: str  # success, error
    result: ReviewResult
    
    # Метаданные
    reviewed_files: int = 0
    duration_seconds: float = 0.0
    
    class Config:
        extra = "allow"


# ============================================================================
# TECH STACK (копия для совместимости)
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