"""Provider extractors — each returns standardized ComponentFiles."""

from models import Provider
from extractors.base import BaseExtractor
from extractors.ultra_librarian import UltraLibrarianExtractor
from extractors.snapeda import SnapEDAExtractor
from extractors.samacsys import SamacSysExtractor
from extractors.easyeda import EasyEDAExtractor
from extractors.generic import GenericExtractor

EXTRACTOR_MAP: dict[Provider, type[BaseExtractor]] = {
    Provider.ULTRA_LIBRARIAN: UltraLibrarianExtractor,
    Provider.SNAPEDA: SnapEDAExtractor,
    Provider.SAMACSYS: SamacSysExtractor,
    Provider.EASYEDA: EasyEDAExtractor,
    Provider.GENERIC: GenericExtractor,
}


def get_extractor(provider: Provider) -> BaseExtractor:
    """Factory to get the appropriate extractor for a provider."""
    cls = EXTRACTOR_MAP.get(provider, GenericExtractor)
    return cls()
