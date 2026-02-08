"""Ultra Librarian extractor (DigiKey, ultralibrarian.com).

ZIP structure (KiCad v6+):
    LQFP-64_STM.step
    KiCADv6/2026-02-08_08-16-27.kicad_sym
    KiCADv6/footprints.pretty/LQFP-64_STM.kicad_mod
    KiCADv6/footprints.pretty/LQFP-64_STM-M.kicad_mod
    KiCADv6/footprints.pretty/LQFP-64_STM-L.kicad_mod

Notes:
- The KiCAD directory may be KiCAD/, KiCADv6/, or KiCADv5/.
- Symbol filename is a timestamp, NOT the MPN.
- MPN is best extracted from the symbol file content (symbol name).
- May contain legacy .lib files (KiCad v5 format).
"""

import os

from models import ComponentFiles, Provider
from extractors.base import BaseExtractor


class UltraLibrarianExtractor(BaseExtractor):

    def extract(self, zip_path: str, extract_dir: str,
                source_url: str | None = None,
                referrer_url: str | None = None) -> ComponentFiles:
        self._unzip(zip_path, extract_dir)

        # Find the KiCAD directory (KiCAD/, KiCADv5/, KiCADv6/)
        kicad_dir = None
        for entry in os.listdir(extract_dir):
            if entry.upper().startswith('KICAD') and os.path.isdir(os.path.join(extract_dir, entry)):
                kicad_dir = os.path.join(extract_dir, entry)
                break

        # Find symbol file
        symbol_file = None
        symbol_format = "kicad_sym"
        if kicad_dir:
            sym_files = self._find_files(kicad_dir, ('.kicad_sym',))
            lib_files = self._find_files(kicad_dir, ('.lib',))
            if sym_files:
                symbol_file = sym_files[0]
            elif lib_files:
                symbol_file = lib_files[0]
                symbol_format = "legacy_lib"

        # Find footprint files
        footprint_files = []
        footprint_file = None
        if kicad_dir:
            footprint_files = self._find_files(kicad_dir, ('.kicad_mod',))
            if footprint_files:
                # Prefer the base footprint (shortest name, no -L or -M suffix)
                footprint_files.sort(key=lambda p: len(os.path.basename(p)))
                footprint_file = footprint_files[0]

        # Find 3D model files (may be at root level or nested)
        step_files = self._find_files(extract_dir, ('.step', '.stp'))
        wrl_files = self._find_files(extract_dir, ('.wrl',))

        # Guess MPN from symbol content (the symbol name inside the file)
        mpn = self._extract_mpn_from_symbol(symbol_file) if symbol_file else None

        # Fallback: try to get MPN from the source URL
        if not mpn and source_url:
            mpn = self._mpn_from_url(source_url)

        # Last resort: use footprint filename
        if not mpn and footprint_file:
            mpn = self._guess_mpn_from_filename(footprint_file)

        if not mpn:
            mpn = "UNKNOWN"

        return ComponentFiles(
            mpn=mpn,
            symbol_file=symbol_file,
            footprint_file=footprint_file,
            footprint_files=footprint_files,
            model_step=step_files[0] if step_files else None,
            model_wrl=wrl_files[0] if wrl_files else None,
            symbol_format=symbol_format,
            source_provider=Provider.ULTRA_LIBRARIAN,
            source_url=source_url,
            referrer_url=referrer_url,
            extract_dir=extract_dir,
        )

    def _extract_mpn_from_symbol(self, symbol_path: str) -> str | None:
        """Read the symbol name from a .kicad_sym file.

        The symbol name is the MPN in Ultra Librarian downloads.
        Looks for: (symbol "STM32C071RBT6" ...)
        """
        if not symbol_path or not os.path.exists(symbol_path):
            return None
        try:
            with open(symbol_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('(symbol "') and 'pin_names' in line:
                        # Extract name between first pair of quotes
                        start = line.index('"') + 1
                        end = line.index('"', start)
                        return line[start:end]
        except (OSError, ValueError):
            pass
        return None

    def _mpn_from_url(self, url: str) -> str | None:
        """Try to extract MPN from Ultra Librarian URL path."""
        # URLs like: .../STMicroelectronics/STM32C071RBT6
        parts = url.rstrip('/').split('/')
        if len(parts) >= 2:
            return parts[-1].split('?')[0]
        return None
