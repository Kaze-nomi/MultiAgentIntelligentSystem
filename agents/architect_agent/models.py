"""
Pydantic модели для Architect Agent
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid


# ============================================================================
# ENUMS
# ============================================================================

class ComponentType(str, Enum):
    """Типы компонентов"""
    CLASS = "class"
    ABSTRACT_CLASS = "abstract_class"
    INTERFACE = "interface"
    MODULE = "module"
    SERVICE = "service"
    REPOSITORY = "repository"
    CONTROLLER = "controller"
    MIDDLEWARE = "middleware"
    UTILITY = "utility"
    FACTORY = "factory"
    SINGLETON = "singleton"
    DECORATOR = "decorator"
    ADAPTER = "adapter"
    FACADE = "facade"
    HANDLER = "handler"
    VALIDATOR = "validator"
    DTO = "dto"
    ENTITY = "entity"
    ENUM = "enum"
    CONFIG = "config"
    TEST = "test"


class RelationType(str, Enum):
    """Типы связей между компонентами"""
    INHERITANCE = "inheritance"         # extends
    IMPLEMENTATION = "implementation"   # implements
    COMPOSITION = "composition"         # contains (strong)
    AGGREGATION = "aggregation"         # has (weak)
    DEPENDENCY = "dependency"           # uses
    ASSOCIATION = "association"         # связан с


class DiagramType(str, Enum):
    """Типы диаграмм"""
    COMPONENT = "component"
    CLASS = "class"
    SEQUENCE = "sequence"
    ACTIVITY = "activity"
    ER = "er"
    DEPLOYMENT = "deployment"
    USE_CASE = "use_case"
    STATE = "state"


class PatternCategory(str, Enum):
    """Категории паттернов"""
    CREATIONAL = "creational"       # Factory, Singleton, Builder
    STRUCTURAL = "structural"        # Adapter, Facade, Decorator
    BEHAVIORAL = "behavioral"        # Strategy, Observer, Command
    ARCHITECTURAL = "architectural"  # MVC, MVVM, Clean Architecture


# ============================================================================
# COMPONENT MODELS
# ============================================================================

class MethodParameter(BaseModel):
    """Параметр метода"""
    name: str
    type: str
    required: bool = True
    default: Optional[Any] = None
    description: str = ""


class MethodSpec(BaseModel):
    """Спецификация метода"""
    name: str
    description: str = ""
    parameters: List[MethodParameter] = Field(default_factory=list)
    return_type: str = "None"
    is_async: bool = False
    is_static: bool = False
    is_classmethod: bool = False
    is_private: bool = False
    raises: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "allow"


class PropertySpec(BaseModel):
    """Спецификация свойства/атрибута"""
    name: str
    type: str
    description: str = ""
    required: bool = True
    default: Optional[Any] = None
    is_private: bool = False
    is_readonly: bool = False
    
    class Config:
        extra = "allow"


class ComponentSpec(BaseModel):
    """Полная спецификация компонента"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    type: ComponentType
    description: str = ""
    responsibility: str = ""
    
    # Содержимое
    properties: List[PropertySpec] = Field(default_factory=list)
    methods: List[MethodSpec] = Field(default_factory=list)
    
    # Связи
    extends: Optional[str] = None           # Наследуется от
    implements: List[str] = Field(default_factory=list)  # Реализует интерфейсы
    dependencies: List[str] = Field(default_factory=list)  # Зависит от
    
    # Метаданные
    file_path: Optional[str] = None
    layer: str = ""  # presentation, business, data, infrastructure
    module: str = ""
    
    class Config:
        extra = "allow"


class ComponentRelation(BaseModel):
    """Связь между компонентами"""
    source: str  # ID или имя компонента
    target: str
    relation_type: RelationType
    label: str = ""
    description: str = ""


# ============================================================================
# INTERFACE MODELS
# ============================================================================

class InterfaceSpec(BaseModel):
    """Спецификация интерфейса"""
    name: str
    description: str = ""
    methods: List[MethodSpec] = Field(default_factory=list)
    properties: List[PropertySpec] = Field(default_factory=list)
    extends: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "allow"


# ============================================================================
# FILE STRUCTURE MODELS
# ============================================================================

class FileSpec(BaseModel):
    """Спецификация файла"""
    path: str
    type: str = "module"  # module, package, config, test, resource
    description: str = ""
    contains: List[str] = Field(default_factory=list)  # Какие компоненты содержит
    imports_from: List[str] = Field(default_factory=list)  # Откуда импортирует
    exports: List[str] = Field(default_factory=list)  # Что экспортирует
    
    class Config:
        extra = "allow"


class DirectorySpec(BaseModel):
    """Спецификация директории"""
    path: str
    description: str = ""
    purpose: str = ""  # Назначение директории
    files: List[FileSpec] = Field(default_factory=list)
    
    class Config:
        extra = "allow"


# ============================================================================
# PATTERN MODELS
# ============================================================================

class PatternRecommendation(BaseModel):
    """Рекомендация по паттерну"""
    name: str
    category: PatternCategory
    reason: str
    how_to_apply: str
    components_affected: List[str] = Field(default_factory=list)
    example: str = ""
    
    class Config:
        extra = "allow"


# ============================================================================
# DIAGRAM MODELS
# ============================================================================

class DiagramSpec(BaseModel):
    """Спецификация диаграммы"""
    type: DiagramType
    title: str
    description: str = ""
    plantuml_code: str
    svg_url: Optional[str] = None
    
    class Config:
        extra = "allow"


# ============================================================================
# INTEGRATION MODELS
# ============================================================================

class IntegrationPoint(BaseModel):
    """Точка интеграции с существующим кодом"""
    existing_component: str  # Существующий компонент
    new_component: str       # Новый компонент
    integration_type: str    # composition, dependency, event, api
    description: str = ""
    changes_required: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "allow"


class ExternalDependency(BaseModel):
    """Внешняя зависимость"""
    name: str
    version: str = ""
    purpose: str = ""
    package_manager: str = ""  # pip, npm, cargo, etc.
    
    class Config:
        extra = "allow"


# ============================================================================
# ARCHITECTURE RESULT MODELS
# ============================================================================

class ExistingArchitecture(BaseModel):
    """Анализ существующей архитектуры"""
    pattern: str = "unknown"  # monolith, microservices, layered, etc.
    layers: List[str] = Field(default_factory=list)
    existing_components: List[Dict[str, Any]] = Field(default_factory=list)
    conventions: Dict[str, str] = Field(default_factory=dict)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "allow"


class ArchitectureDesign(BaseModel):
    """Полный дизайн архитектуры"""
    # Компоненты
    components: List[ComponentSpec] = Field(default_factory=list)
    interfaces: List[InterfaceSpec] = Field(default_factory=list)
    relations: List[ComponentRelation] = Field(default_factory=list)
    
    # Структура
    file_structure: List[FileSpec] = Field(default_factory=list)
    directories: List[DirectorySpec] = Field(default_factory=list)
    
    # Паттерны и зависимости
    patterns: List[PatternRecommendation] = Field(default_factory=list)
    external_dependencies: List[ExternalDependency] = Field(default_factory=list)
    
    # Интеграция
    integration_points: List[IntegrationPoint] = Field(default_factory=list)
    
    # Диаграммы
    diagrams: List[DiagramSpec] = Field(default_factory=list)
    
    # Рекомендации
    recommendations: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "allow"


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ArchitectRequest(BaseModel):
    """Запрос на проектирование архитектуры"""
    task: str
    action: str = "design_architecture"
    data: Dict[str, Any] = Field(default_factory=dict)
    priority: str = "medium"


class ArchitectResponse(BaseModel):
    """Ответ с архитектурным дизайном"""
    task_id: str
    status: str  # success, error
    
    # Анализ существующего
    existing_architecture: Optional[ExistingArchitecture] = None
    
    # Новый дизайн
    architecture: ArchitectureDesign
    
    # Для совместимости с другими агентами (плоская структура)
    components: List[Dict[str, Any]] = Field(default_factory=list)
    patterns: List[str] = Field(default_factory=list)
    file_structure: List[Dict[str, Any]] = Field(default_factory=list)
    interfaces: List[Dict[str, Any]] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    integration_points: List[Dict[str, Any]] = Field(default_factory=list)
    diagrams: Dict[str, str] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
    
    # Метаданные
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