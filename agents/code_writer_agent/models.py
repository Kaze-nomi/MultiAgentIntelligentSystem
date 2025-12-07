"""
Pydantic модели для Code Writer Agent
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field
import uuid


# ============================================================================
# ENUMS
# ============================================================================

class FileAction(str, Enum):
    """Действие с файлом"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class CodeLanguage(str, Enum):
    """Поддерживаемые языки программирования"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    CSHARP = "csharp"
    CPP = "cpp"
    RUBY = "ruby"
    PHP = "php"
    SWIFT = "swift"
    KOTLIN = "kotlin"
    SCALA = "scala"
    HTML = "html"
    CSS = "css"
    SQL = "sql"
    SHELL = "shell"
    YAML = "yaml"
    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"
    UNKNOWN = "unknown"


# ============================================================================
# CODING STYLE MODELS
# ============================================================================

class NamingConvention(BaseModel):
    """Соглашения об именовании"""
    variables: str = "snake_case"  # snake_case, camelCase, PascalCase
    functions: str = "snake_case"
    classes: str = "PascalCase"
    constants: str = "UPPER_SNAKE_CASE"
    files: str = "snake_case"
    
    class Config:
        extra = "allow"


class ImportStyle(BaseModel):
    """Стиль импортов"""
    style: str = "absolute"  # absolute, relative
    grouping: str = "stdlib, third_party, local"
    sorting: str = "alphabetical"
    
    class Config:
        extra = "allow"


class CodingStyle(BaseModel):
    """Полный стиль кодирования проекта"""
    naming: NamingConvention = Field(default_factory=NamingConvention)
    imports: ImportStyle = Field(default_factory=ImportStyle)
    docstring_format: str = "Google"  # Google, NumPy, Sphinx, JSDoc
    indent_size: int = 4
    max_line_length: int = 88
    use_type_hints: bool = True
    error_handling_style: str = "try-except with logging"
    quote_style: str = "double"  # single, double
    trailing_comma: bool = True
    
    # Специфичные для языка
    python_version: Optional[str] = None
    node_version: Optional[str] = None
    
    class Config:
        extra = "allow"


# ============================================================================
# CODE FILE MODELS
# ============================================================================

class CodeFile(BaseModel):
    """Файл с кодом"""
    path: str
    content: str
    language: CodeLanguage = CodeLanguage.UNKNOWN
    description: str = ""
    action: FileAction = FileAction.CREATE
    
    # Метаданные
    imports: List[str] = Field(default_factory=list)
    exports: List[str] = Field(default_factory=list)
    classes: List[str] = Field(default_factory=list)
    functions: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    
    # Для обновления существующих файлов
    original_sha: Optional[str] = None
    changes_description: Optional[str] = None
    
    class Config:
        extra = "allow"
    
    @property
    def extension(self) -> str:
        """Получает расширение файла"""
        if "." in self.path:
            return self.path.rsplit(".", 1)[-1].lower()
        return ""


class CodeChange(BaseModel):
    """Описание изменения в коде"""
    file_path: str
    change_type: str  # add, modify, delete, refactor
    description: str
    before: Optional[str] = None
    after: Optional[str] = None
    line_numbers: Optional[List[int]] = None


# ============================================================================
# ARCHITECTURE INPUT MODELS
# ============================================================================

class ComponentSpec(BaseModel):
    """Спецификация компонента от архитектора"""
    name: str
    type: str  # class, module, function, service
    responsibility: str
    methods: List[Dict[str, Any]] = Field(default_factory=list)
    properties: List[Dict[str, Any]] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    interfaces: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "allow"


class FileStructureSpec(BaseModel):
    """Спецификация структуры файла от архитектора"""
    path: str
    type: str  # module, package, config, test
    contains: List[str] = Field(default_factory=list)  # что должен содержать
    imports_from: List[str] = Field(default_factory=list)
    exports: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "allow"


class ArchitectureInput(BaseModel):
    """Входные данные от Architect Agent"""
    components: List[ComponentSpec] = Field(default_factory=list)
    patterns: List[str] = Field(default_factory=list)
    file_structure: List[FileStructureSpec] = Field(default_factory=list)
    interfaces: List[Dict[str, Any]] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    integration_points: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "allow"


# ============================================================================
# REVIEW INPUT MODELS
# ============================================================================

class ReviewIssue(BaseModel):
    """Замечание от Code Reviewer"""
    id: str
    type: str  # bug, security, performance, style, architecture_violation
    severity: str  # critical, high, medium, low
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    description: str
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None
    
    class Config:
        extra = "allow"


class ReviewInput(BaseModel):
    """Входные данные от Code Reviewer для ревизии"""
    issues: List[ReviewIssue] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "allow"


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CodeWriteRequest(BaseModel):
    """Запрос на написание кода"""
    task: str
    action: str = "write_code"  # write_code, revise_code
    data: Dict[str, Any] = Field(default_factory=dict)
    priority: str = "medium"


class CodeWriteResponse(BaseModel):
    """Ответ с написанным кодом"""
    task_id: str
    status: str  # success, partial, error
    files: List[CodeFile]
    implementation_notes: List[str] = Field(default_factory=list)
    changes_made: List[CodeChange] = Field(default_factory=list)
    
    # При ревизии
    addressed_issues: List[str] = Field(default_factory=list)  # ID исправленных issues
    unaddressed_issues: List[Dict[str, str]] = Field(default_factory=list)  # Что не удалось исправить
    
    # Метаданные
    language: CodeLanguage = CodeLanguage.UNKNOWN
    coding_style_used: Optional[CodingStyle] = None
    duration_seconds: float = 0.0
    
    class Config:
        extra = "allow"


# ============================================================================
# TECH STACK (копия из project manager для совместимости)
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