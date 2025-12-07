"""
Pydantic модели для Documentation Agent
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field
import uuid


# ============================================================================
# ENUMS
# ============================================================================

class DocType(str, Enum):
    """Типы документации"""
    README = "readme"
    API = "api"
    CODE = "code"
    ARCHITECTURE = "architecture"
    USER_GUIDE = "user_guide"
    DEVELOPER_GUIDE = "developer_guide"
    CHANGELOG = "changelog"
    CONTRIBUTING = "contributing"
    INSTALLATION = "installation"
    CONFIGURATION = "configuration"
    TROUBLESHOOTING = "troubleshooting"
    FAQ = "faq"


class DocFormat(str, Enum):
    """Форматы документации"""
    MARKDOWN = "markdown"
    RST = "rst"
    HTML = "html"
    ASCIIDOC = "asciidoc"


class DocLanguage(str, Enum):
    """Язык документации"""
    ENGLISH = "en"
    RUSSIAN = "ru"
    CHINESE = "zh"
    SPANISH = "es"
    GERMAN = "de"


class ChangeType(str, Enum):
    """Типы изменений для CHANGELOG"""
    ADDED = "added"
    CHANGED = "changed"
    DEPRECATED = "deprecated"
    REMOVED = "removed"
    FIXED = "fixed"
    SECURITY = "security"


# ============================================================================
# DOCUMENTATION STYLE
# ============================================================================

class DocStyle(BaseModel):
    """Стиль документации проекта"""
    format: DocFormat = DocFormat.MARKDOWN
    language: DocLanguage = DocLanguage.RUSSIAN
    
    # Стиль заголовков
    heading_style: str = "atx"  # atx (#) или setext (underline)
    
    # Стиль кода
    code_fence: str = "```"  # ``` или ~~~
    
    # Стиль списков
    list_marker: str = "-"  # -, *, +
    
    # Особенности
    use_badges: bool = True
    use_toc: bool = True  # Table of Contents
    use_emojis: bool = True
    
    # Секции README
    readme_sections: List[str] = Field(default_factory=lambda: [
        "description", "features", "installation", 
        "usage", "configuration", "api", "contributing", "license"
    ])
    
    class Config:
        extra = "allow"


# ============================================================================
# FILE MODELS
# ============================================================================

class DocFile(BaseModel):
    """Файл документации"""
    path: str
    content: str
    doc_type: DocType
    format: DocFormat = DocFormat.MARKDOWN
    description: str = ""
    action: str = "create"  # create, update, prepend, append
    
    # Метаданные
    sections: List[str] = Field(default_factory=list)
    word_count: int = 0
    
    class Config:
        extra = "allow"


# ============================================================================
# CHANGELOG MODELS
# ============================================================================

class ChangelogEntry(BaseModel):
    """Запись в CHANGELOG"""
    change_type: ChangeType
    description: str
    component: Optional[str] = None
    issue_ref: Optional[str] = None  # #123
    
    class Config:
        extra = "allow"


class ChangelogVersion(BaseModel):
    """Версия в CHANGELOG"""
    version: str
    date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    entries: List[ChangelogEntry] = Field(default_factory=list)
    
    class Config:
        extra = "allow"


# ============================================================================
# API DOCUMENTATION MODELS
# ============================================================================

class ApiParameter(BaseModel):
    """Параметр API endpoint"""
    name: str
    type: str
    required: bool = True
    description: str = ""
    default: Optional[str] = None
    example: Optional[str] = None
    location: str = "body"  # body, query, path, header
    
    class Config:
        extra = "allow"


class ApiResponse(BaseModel):
    """Ответ API endpoint"""
    status_code: int
    description: str
    content_type: str = "application/json"
    schema: Optional[Dict[str, Any]] = None
    example: Optional[Any] = None
    
    class Config:
        extra = "allow"


class ApiEndpoint(BaseModel):
    """API endpoint"""
    method: str  # GET, POST, PUT, DELETE, PATCH
    path: str
    summary: str
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    parameters: List[ApiParameter] = Field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    responses: List[ApiResponse] = Field(default_factory=list)
    authentication: Optional[str] = None
    examples: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        extra = "allow"


class ApiDocumentation(BaseModel):
    """Полная API документация"""
    title: str
    version: str = "1.0.0"
    description: str = ""
    base_url: str = ""
    authentication: Optional[str] = None
    endpoints: List[ApiEndpoint] = Field(default_factory=list)
    models: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        extra = "allow"


# ============================================================================
# CODE DOCUMENTATION MODELS
# ============================================================================

class FunctionDoc(BaseModel):
    """Документация функции"""
    name: str
    description: str
    parameters: List[Dict[str, str]] = Field(default_factory=list)
    returns: Optional[str] = None
    raises: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "allow"


class ClassDoc(BaseModel):
    """Документация класса"""
    name: str
    description: str
    attributes: List[Dict[str, str]] = Field(default_factory=list)
    methods: List[FunctionDoc] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "allow"


class ModuleDoc(BaseModel):
    """Документация модуля"""
    name: str
    path: str
    description: str
    classes: List[ClassDoc] = Field(default_factory=list)
    functions: List[FunctionDoc] = Field(default_factory=list)
    constants: List[Dict[str, str]] = Field(default_factory=list)
    
    class Config:
        extra = "allow"


# ============================================================================
# INPUT MODELS (от других агентов)
# ============================================================================

class CodeFileInput(BaseModel):
    """Файл кода от Code Writer"""
    path: str
    content: str
    language: str = "unknown"
    description: str = ""
    classes: List[str] = Field(default_factory=list)
    functions: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "allow"


class ArchitectureInput(BaseModel):
    """Архитектура от Architect"""
    components: List[Dict[str, Any]] = Field(default_factory=list)
    patterns: List[str] = Field(default_factory=list)
    file_structure: List[Dict[str, Any]] = Field(default_factory=list)
    interfaces: List[Dict[str, Any]] = Field(default_factory=list)
    diagrams: Dict[str, str] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "allow"


class ReviewInput(BaseModel):
    """Результаты ревью от Code Reviewer"""
    approved: bool = False
    quality_score: float = 0.0
    issues_count: int = 0
    summary: str = ""
    
    class Config:
        extra = "allow"


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class DocumentationRequest(BaseModel):
    """Запрос на создание документации"""
    task: str
    action: str = "write_docs"
    data: Dict[str, Any] = Field(default_factory=dict)
    priority: str = "medium"
    
    # Какие типы документации генерировать
    doc_types: List[DocType] = Field(default_factory=lambda: [
        DocType.README, DocType.API, DocType.CHANGELOG
    ])


class DocumentationResponse(BaseModel):
    """Ответ с документацией"""
    task_id: str
    status: str  # success, partial, error
    
    files: List[DocFile] = Field(default_factory=list)
    
    # Детали
    doc_style: Optional[DocStyle] = None
    api_documentation: Optional[ApiDocumentation] = None
    changelog: Optional[ChangelogVersion] = None
    module_docs: List[ModuleDoc] = Field(default_factory=list)
    
    # Метаданные
    sections_created: List[str] = Field(default_factory=list)
    total_files: int = 0
    total_words: int = 0
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