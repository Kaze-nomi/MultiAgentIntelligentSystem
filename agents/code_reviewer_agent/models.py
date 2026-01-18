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
    
    @classmethod
    def from_string(cls, value: str, default: 'IssueSeverity' = None) -> 'IssueSeverity':
        """
        Безопасное преобразование строки в IssueSeverity
        
        Args:
            value: Строковое значение
            default: Значение по умолчанию в случае ошибки
            
        Returns:
            IssueSeverity или default
        """
        try:
            if not isinstance(value, str):
                return default or cls.MEDIUM
            
            value_upper = value.upper()
            if hasattr(cls, value_upper):
                return getattr(cls, value_upper)
            
            # Проверка по значениям
            for severity in cls:
                if severity.value.lower() == value.lower():
                    return severity
            
            return default or cls.MEDIUM
        except Exception:
            return default or cls.MEDIUM


class IssueType(str, Enum):
    """Тип проблемы"""
    BUG = "bug"                                  # Логическая ошибка
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
    
    @classmethod
    def from_string(cls, value: str, default: 'IssueType' = None) -> 'IssueType':
        """
        Безопасное преобразование строки в IssueType
        
        Args:
            value: Строковое значение
            default: Значение по умолчанию в случае ошибки
            
        Returns:
            IssueType или default
        """
        try:
            if not isinstance(value, str):
                return default or cls.MAINTAINABILITY
            
            value_upper = value.upper()
            if hasattr(cls, value_upper):
                return getattr(cls, value_upper)
            
            # Проверка по значениям
            for issue_type in cls:
                if issue_type.value.lower() == value.lower():
                    return issue_type
            
            return default or cls.MAINTAINABILITY
        except Exception:
            return default or cls.MAINTAINABILITY


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
    performance_issues: int = 0
    style_issues: int = 0
    
    # Качество
    overall_quality_score: float = 0.0
    maintainability_score: float = 0.0
    performance_score: float = 0.0
    
    def get_metric(self, metric_name: str, default=None):
        """
        Безопасный доступ к метрике с обработкой ошибок
        
        Args:
            metric_name: Имя метрики
            default: Значение по умолчанию если метрика не найдена
            
        Returns:
            Значение метрики или default
        """
        try:
            if hasattr(self, metric_name):
                value = getattr(self, metric_name)
                return value if value is not None else default
            return default
        except Exception:
            return default
    
    def calculate_quality_metrics(self, issues: List['ReviewIssue']) -> Dict[str, Any]:
        """
        Расчет дополнительных метрик качества на основе списка проблем
        
        Args:
            issues: Список проблем ревью
            
        Returns:
            Словарь с дополнительными метриками
        """
        try:
            if not issues:
                return {
                    "issues_per_file": 0.0,
                    "critical_ratio": 0.0,
                    "high_ratio": 0.0,
                    "medium_ratio": 0.0,
                    "low_ratio": 0.0
                }
            
            total_issues = len(issues)
            files_count = max(1, self.total_files)  # Предотвращаем деление на ноль
            
            # Расчет соотношений по серьезности
            critical_count = sum(1 for issue in issues if hasattr(issue, 'severity') and issue.severity == 'critical')
            high_count = sum(1 for issue in issues if hasattr(issue, 'severity') and issue.severity == 'high')
            medium_count = sum(1 for issue in issues if hasattr(issue, 'severity') and issue.severity == 'medium')
            low_count = sum(1 for issue in issues if hasattr(issue, 'severity') and issue.severity == 'low')
            
            return {
                "issues_per_file": total_issues / files_count,
                "critical_ratio": critical_count / total_issues if total_issues > 0 else 0.0,
                "high_ratio": high_count / total_issues if total_issues > 0 else 0.0,
                "medium_ratio": medium_count / total_issues if total_issues > 0 else 0.0,
                "low_ratio": low_count / total_issues if total_issues > 0 else 0.0
            }
        except Exception as e:
            # Возвращаем пустые метрики в случае ошибки
            return {
                "issues_per_file": 0.0,
                "critical_ratio": 0.0,
                "high_ratio": 0.0,
                "medium_ratio": 0.0,
                "low_ratio": 0.0,
                "error": str(e)
            }


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
    
    # Для итерации
    blocking_issues: List[str] = Field(default_factory=list)  # ID issues которые блокируют
    
    class Config:
        extra = "allow"
    
    @property
    def critical_issues(self) -> List[ReviewIssue]:
        """Безопасное получение критических проблем"""
        try:
            if not self.issues:
                return []
            return [i for i in self.issues if hasattr(i, 'severity') and i.severity == IssueSeverity.CRITICAL]
        except Exception:
            return []
    
    @property
    def high_issues(self) -> List[ReviewIssue]:
        """Безопасное получение высокоприоритетных проблем"""
        try:
            if not self.issues:
                return []
            return [i for i in self.issues if hasattr(i, 'severity') and i.severity == IssueSeverity.HIGH]
        except Exception:
            return []
    
    def get_issues_for_file(self, file_path: str) -> List[ReviewIssue]:
        """Безопасное получение проблем для конкретного файла"""
        try:
            if not self.issues or not file_path:
                return []
            return [i for i in self.issues if hasattr(i, 'file_path') and i.file_path == file_path]
        except Exception:
            return []
    
    def get_issues_by_severity(self, severity: IssueSeverity) -> List[ReviewIssue]:
        """
        Безопасное получение проблем по уровню серьезности
        
        Args:
            severity: Уровень серьезности
            
        Returns:
            Список проблем указанного уровня серьезности
        """
        try:
            if not self.issues:
                return []
            return [i for i in self.issues if hasattr(i, 'severity') and i.severity == severity]
        except Exception:
            return []
    
    def get_issues_by_type(self, issue_type: IssueType) -> List[ReviewIssue]:
        """
        Безопасное получение проблем по типу
        
        Args:
            issue_type: Тип проблемы
            
        Returns:
            Список проблем указанного типа
        """
        try:
            if not self.issues:
                return []
            return [i for i in self.issues if hasattr(i, 'type') and i.type == issue_type]
        except Exception:
            return []
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Получение сводной статистики по результатам ревью
        
        Returns:
            Словарь со статистикой
        """
        try:
            if not self.issues:
                return {
                    "total_issues": 0,
                    "by_severity": {
                        "critical": 0,
                        "high": 0,
                        "medium": 0,
                        "low": 0
                    },
                    "by_type": {},
                    "files_affected": 0
                }
            
            # Подсчет по серьезности
            severity_counts = {
                "critical": len(self.critical_issues),
                "high": len(self.high_issues),
                "medium": len([i for i in self.issues if hasattr(i, 'severity') and i.severity == IssueSeverity.MEDIUM]),
                "low": len([i for i in self.issues if hasattr(i, 'severity') and i.severity == IssueSeverity.LOW])
            }
            
            # Подсчет по типам
            type_counts = {}
            for issue in self.issues:
                if hasattr(issue, 'type') and issue.type:
                    type_name = issue.type.value if hasattr(issue.type, 'value') else str(issue.type)
                    type_counts[type_name] = type_counts.get(type_name, 0) + 1
            
            # Подсчет затронутых файлов
            files_affected = len(set(
                i.file_path for i in self.issues
                if hasattr(i, 'file_path') and i.file_path
            ))
            
            return {
                "total_issues": len(self.issues),
                "by_severity": severity_counts,
                "by_type": type_counts,
                "files_affected": files_affected
            }
        except Exception as e:
            return {
                "total_issues": 0,
                "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                "by_type": {},
                "files_affected": 0,
                "error": str(e)
            }


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
# REVIEW BATCH MODELS
# ============================================================================

class FileReviewHistory(BaseModel):
    """История ревью для конкретного файла"""
    file_path: str
    reviewed_in_attempts: List[int] = Field(default_factory=list)  # Номера попыток, в которых файл был проверен
    issues_by_attempt: Dict[int, List[str]] = Field(default_factory=dict)  # ID issues по попыткам
    last_review_attempt: int = 0  # Последняя попытка ревью
    is_fixed: bool = False  # Помечены ли все issues как исправленные
    
    class Config:
        extra = "allow"


class ReviewBatchState(BaseModel):
    """Состояние батча ревью"""
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: Optional[str] = None
    total_attempts: int = 0
    max_attempts: int = 3  # Максимальное количество попыток ревью
    current_attempt: int = 0
    files_history: Dict[str, FileReviewHistory] = Field(default_factory=dict)
    is_completed: bool = False
    final_decision: Optional[ReviewDecision] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def mark_file_reviewed(self, file_path: str, attempt: int, issue_ids: List[str]):
        """Отмечает файл как проверенный в указанной попытке"""
        if file_path not in self.files_history:
            self.files_history[file_path] = FileReviewHistory(file_path=file_path)
        
        history = self.files_history[file_path]
        if attempt not in history.reviewed_in_attempts:
            history.reviewed_in_attempts.append(attempt)
            history.last_review_attempt = attempt
            history.issues_by_attempt[attempt] = issue_ids
        
        self.updated_at = datetime.now()
    
    def is_file_reviewed_in_attempt(self, file_path: str, attempt: int) -> bool:
        """Проверяет, был ли файл уже проверен в указанной попытке"""
        if file_path not in self.files_history:
            return False
        return attempt in self.files_history[file_path].reviewed_in_attempts
    
    def get_files_to_review(self, all_files: List[str], attempt: int) -> List[str]:
        """Возвращает файлы, которые нужно проверить в указанной попытке"""
        return [
            file_path for file_path in all_files
            if not self.is_file_reviewed_in_attempt(file_path, attempt)
        ]
    
    def can_start_new_attempt(self) -> bool:
        """Проверяет, можно ли начать новую попытку ревью"""
        return self.current_attempt < self.max_attempts and not self.is_completed
    
    def start_new_attempt(self) -> int:
        """Начинает новую попытку ревью и возвращает её номер"""
        if not self.can_start_new_attempt():
            raise ValueError("Cannot start new attempt: max attempts reached or batch completed")
        
        self.current_attempt += 1
        self.total_attempts += 1
        self.updated_at = datetime.now()
        return self.current_attempt
    
    def complete_batch(self, final_decision: ReviewDecision):
        """Завершает батч ревью с указанным решением"""
        self.is_completed = True
        self.final_decision = final_decision
        self.updated_at = datetime.now()
    
    class Config:
        extra = "allow"


class ReviewBatchMetrics(BaseModel):
    """Метрики батча ревью"""
    batch_id: str
    total_files: int = 0
    reviewed_files: int = 0
    total_attempts: int = 0
    current_attempt: int = 0
    files_per_attempt: Dict[int, int] = Field(default_factory=dict)  # Количество файлов в каждой попытке
    issues_per_attempt: Dict[int, int] = Field(default_factory=dict)  # Количество проблем в каждой попытке
    new_issues_per_attempt: Dict[int, int] = Field(default_factory=dict)  # Новые проблемы в каждой попытке
    fixed_issues_per_attempt: Dict[int, int] = Field(default_factory=dict)  # Исправленные проблемы в каждой попытке
    quality_score_progression: List[float] = Field(default_factory=list)  # Прогресс оценки качества
    decision_by_attempt: Dict[int, ReviewDecision] = Field(default_factory=dict)  # Решения по попыткам
    
    # Метрики параллельной обработки
    parallel_processing_enabled: bool = True  # Включена ли параллельная обработка
    max_concurrent_files: int = 5  # Максимальное количество одновременно обрабатываемых файлов
    average_queue_wait_time: float = 0.0  # Среднее время ожидания в очереди
    processing_speedup: float = 1.0  # Ускорение обработки по сравнению с последовательной
    total_parallel_processing_time: float = 0.0  # Общее время параллельной обработки
    estimated_sequential_time: float = 0.0  # Оценочное время последовательной обработки
    
    def record_attempt_results(self, attempt: int, files_count: int, issues_count: int,
                              new_issues: int, fixed_issues: int, quality_score: float,
                              decision: ReviewDecision):
        """Записывает результаты попытки"""
        self.files_per_attempt[attempt] = files_count
        self.issues_per_attempt[attempt] = issues_count
        self.new_issues_per_attempt[attempt] = new_issues
        self.fixed_issues_per_attempt[attempt] = fixed_issues
        self.quality_score_progression.append(quality_score)
        self.decision_by_attempt[attempt] = decision
        self.current_attempt = attempt
        self.total_attempts = max(self.total_attempts, attempt)
    
    def record_parallel_metrics(self, queue_wait_time: float, processing_time: float,
                              estimated_sequential_time: float, speedup: float):
        """Записывает метрики параллельной обработки"""
        # Обновляем среднее время ожидания в очереди
        if self.average_queue_wait_time == 0.0:
            self.average_queue_wait_time = queue_wait_time
        else:
            # Скользящее среднее
            self.average_queue_wait_time = (self.average_queue_wait_time * 0.8 + queue_wait_time * 0.2)
        
        self.total_parallel_processing_time += processing_time
        self.estimated_sequential_time = estimated_sequential_time
        self.processing_speedup = speedup
    
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