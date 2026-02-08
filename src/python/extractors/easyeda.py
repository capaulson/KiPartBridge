"""EasyEDA/JLCPCB extractor — stub for Phase 4."""

from models import ComponentFiles
from extractors.base import BaseExtractor


class EasyEDAExtractor(BaseExtractor):

    def extract(self, zip_path: str, extract_dir: str,
                source_url: str | None = None,
                referrer_url: str | None = None) -> ComponentFiles:
        raise NotImplementedError(
            "EasyEDA conversion requires easyeda2kicad (Phase 4). "
            "Install with: pip install easyeda2kicad"
        )
