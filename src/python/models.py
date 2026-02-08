"""Data models for KiPartBridge pipeline."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Provider(Enum):
    ULTRA_LIBRARIAN = "ultra_librarian"
    SNAPEDA = "snapeda"
    SAMACSYS = "samacsys"
    EASYEDA = "easyeda"
    GENERIC = "generic"


@dataclass
class ComponentFiles:
    """Standardized result from a provider extractor."""
    mpn: str
    symbol_file: Optional[str] = None
    footprint_file: Optional[str] = None
    footprint_files: list[str] = field(default_factory=list)
    model_step: Optional[str] = None
    model_wrl: Optional[str] = None
    manufacturer: Optional[str] = None
    description: Optional[str] = None
    symbol_format: str = "kicad_sym"  # "kicad_sym" or "legacy_lib"
    source_provider: Optional[Provider] = None
    source_url: Optional[str] = None
    referrer_url: Optional[str] = None
    extract_dir: Optional[str] = None


@dataclass
class ProcessingResult:
    """Result of processing a component through the full pipeline."""
    status: str  # "success", "partial", "error"
    mpn: Optional[str] = None
    symbol_name: Optional[str] = None
    footprint_name: Optional[str] = None
    has_3d_model: bool = False
    error: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
