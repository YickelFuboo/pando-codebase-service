from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Protocol


class TypeKind(Enum):
    Class = auto()
    Interface = auto()
    Struct = auto()
    Enum = auto()
    Delegate = auto()
    Record = auto()


class AccessModifier(Enum):
    Public = auto()
    Private = auto()
    Protected = auto()
    Internal = auto()
    ProtectedInternal = auto()
    PrivateProtected = auto()


@dataclass
class ParameterInfo:
    name: str = ""
    type: str = ""
    is_optional: bool = False
    default_value: str = ""


@dataclass
class FunctionCallInfo:
    name: str = ""
    full_name: str = ""
    line_number: int = 0
    target_type: str = ""
    is_static: bool = False


@dataclass
class FunctionInfo:
    name: str = ""
    full_name: str = ""
    file_path: str = ""
    line_number: int = 0
    end_line_number: int = 0
    return_type: str = ""
    parameters: List[ParameterInfo] = field(default_factory=list)
    generic_parameters: List[str] = field(default_factory=list)
    calls: List[FunctionCallInfo] = field(default_factory=list)
    access_modifier: AccessModifier = AccessModifier.Public
    is_static: bool = False
    is_async: bool = False
    is_abstract: bool = False
    is_virtual: bool = False
    is_override: bool = False
    parent_type: str = ""


@dataclass
class VariableInfo:
    name: str = ""
    type: str = ""
    line_number: int = 0
    access_modifier: AccessModifier = AccessModifier.Public
    is_static: bool = False
    is_readonly: bool = False
    is_const: bool = False


@dataclass
class ImportInfo:
    name: str = ""
    alias: str = ""
    file_path: str = ""
    is_wildcard: bool = False
    imported_members: List[str] = field(default_factory=list)


@dataclass
class TypeInfo:
    name: str = ""
    full_name: str = ""
    kind: TypeKind = TypeKind.Class
    file_path: str = ""
    line_number: int = 0
    end_line_number: int = 0
    base_types: List[str] = field(default_factory=list)
    interfaces: List[str] = field(default_factory=list)
    methods: List[FunctionInfo] = field(default_factory=list)
    fields: List[VariableInfo] = field(default_factory=list)
    generic_parameters: List[str] = field(default_factory=list)
    access_modifier: AccessModifier = AccessModifier.Public
    is_abstract: bool = False
    is_sealed: bool = False
    is_static: bool = False


@dataclass
class SemanticModel:
    file_path: str = ""
    namespace: str = ""
    types: List[TypeInfo] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)
    imports: List[ImportInfo] = field(default_factory=list)
    variables: List[VariableInfo] = field(default_factory=list)


@dataclass
class ProjectSemanticModel:
    files: Dict[str, SemanticModel] = field(default_factory=dict)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    all_types: Dict[str, TypeInfo] = field(default_factory=dict)
    all_functions: Dict[str, FunctionInfo] = field(default_factory=dict)


class BaseSemanticAnalyzer(Protocol):
    @property
    def supported_extensions(self) -> List[str]: ...
    async def analyze_file_async(self, file_path: str, content: str) -> SemanticModel: ...
    async def analyze_project_async(self, file_paths: List[str]) -> ProjectSemanticModel: ... 