"""SnapEDA extractor.

ZIP structure: root-level .kicad_sym, .kicad_mod, .step files.

SnapEDA often uses UUID filenames (e.g. "a1b2c3d4-...-e5f6.kicad_sym"), so the
MPN must be extracted from inside the file content, not from the filename.
"""

import os
import re
from urllib.parse import unquote

from models import ComponentFiles, Provider
from extractors.base import BaseExtractor


class SnapEDAExtractor(BaseExtractor):

    def extract(self, zip_path: str, extract_dir: str,
                source_url: str | None = None,
                referrer_url: str | None = None) -> ComponentFiles:
        self._unzip(zip_path, extract_dir)

        sym_files = self._find_files(extract_dir, ('.kicad_sym',))
        mod_files = self._find_files(extract_dir, ('.kicad_mod',))
        step_files = self._find_files(extract_dir, ('.step', '.stp'))
        wrl_files = self._find_files(extract_dir, ('.wrl',))

        symbol_file = sym_files[0] if sym_files else None
        footprint_file = mod_files[0] if mod_files else None

        # 1. Try extracting MPN from symbol file content (most reliable)
        mpn = self._extract_mpn_from_symbol(symbol_file)

        # 2. Try extracting MPN from referrer URL (e.g. DigiKey product page)
        if not mpn and referrer_url:
            mpn = self._mpn_from_referrer_url(referrer_url)

        # 3. Try extracting MPN from footprint file content
        if not mpn and footprint_file:
            mpn = self._extract_mpn_from_footprint(footprint_file)

        # 4. Fallback to filename (only useful if not a UUID)
        if not mpn and symbol_file:
            candidate = self._guess_mpn_from_filename(symbol_file)
            if not self._looks_like_uuid(candidate):
                mpn = candidate
        if not mpn and footprint_file:
            candidate = self._guess_mpn_from_filename(footprint_file)
            if not self._looks_like_uuid(candidate):
                mpn = candidate

        if not mpn:
            mpn = "UNKNOWN"

        return ComponentFiles(
            mpn=mpn,
            symbol_file=symbol_file,
            footprint_file=footprint_file,
            footprint_files=mod_files,
            model_step=step_files[0] if step_files else None,
            model_wrl=wrl_files[0] if wrl_files else None,
            symbol_format="kicad_sym",
            source_provider=Provider.SNAPEDA,
            source_url=source_url,
            referrer_url=referrer_url,
            extract_dir=extract_dir,
        )

    def _extract_mpn_from_symbol(self, symbol_path: str | None) -> str | None:
        """Read the symbol entry name from a .kicad_sym file.

        Looks for the top-level: (symbol "PART_NAME" ...
        Skips sub-symbols (those containing _0_1, _1_1 suffixes).
        """
        if not symbol_path or not os.path.exists(symbol_path):
            return None
        try:
            with open(symbol_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Match top-level symbol declaration
                    if line.startswith('(symbol "'):
                        # Extract name between quotes
                        start = line.index('"') + 1
                        end = line.index('"', start)
                        name = line[start:end]
                        # Skip sub-symbols (e.g. "PartName_0_1")
                        if re.search(r'_\d+_\d+$', name):
                            continue
                        # Skip UUIDs
                        if self._looks_like_uuid(name):
                            continue
                        return name
        except (OSError, ValueError):
            pass
        return None

    def _extract_mpn_from_footprint(self, footprint_path: str | None) -> str | None:
        """Read the footprint name from a .kicad_mod file.

        Looks for: (footprint "PART_NAME" ...
        """
        if not footprint_path or not os.path.exists(footprint_path):
            return None
        try:
            with open(footprint_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('(footprint "'):
                        start = line.index('"') + 1
                        end = line.index('"', start)
                        name = line[start:end]
                        if not self._looks_like_uuid(name):
                            return name
                        break
        except (OSError, ValueError):
            pass
        return None

    def _mpn_from_referrer_url(self, url: str) -> str | None:
        """Try to extract MPN from a referrer URL.

        DigiKey: /en/products/detail/manufacturer/MPN/digikey-pn
        SnapEDA: /parts/MPN/Manufacturer/view-part/
        """
        url = unquote(url)
        # DigiKey product page: /en/products/detail/{mfr}/{MPN}/{dk-pn}
        m = re.search(r'/en/products/detail/[^/]+/([^/]+)/\d+', url)
        if m:
            return m.group(1)
        # SnapEDA part page: /parts/{MPN}/{Manufacturer}/view-part/
        m = re.search(r'/parts/([^/]+)/[^/]+/view-part', url)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def _looks_like_uuid(name: str) -> bool:
        """Check if a string looks like a UUID (8-4-4-4-12 hex pattern)."""
        return bool(re.match(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            name, re.IGNORECASE
        ))
