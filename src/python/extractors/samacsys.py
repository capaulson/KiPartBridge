"""SamacSys / Component Search Engine extractor (Mouser).

ZIP structure:
    KiCad/symbol/<MPN>.kicad_sym    (or KiCad/<MPN>.kicad_sym)
    KiCad/footprint/<MPN>.kicad_mod (or KiCad/<MPN>.pretty/<MPN>.kicad_mod)
    KiCad/3dmodel/<MPN>.step
"""

import os

from models import ComponentFiles, Provider
from extractors.base import BaseExtractor


class SamacSysExtractor(BaseExtractor):

    def extract(self, zip_path: str, extract_dir: str,
                source_url: str | None = None,
                referrer_url: str | None = None) -> ComponentFiles:
        self._unzip(zip_path, extract_dir)

        # Look for KiCad directory
        kicad_dir = None
        for entry in os.listdir(extract_dir):
            if entry == 'KiCad' and os.path.isdir(os.path.join(extract_dir, entry)):
                kicad_dir = os.path.join(extract_dir, entry)
                break

        search_dir = kicad_dir or extract_dir
        sym_files = self._find_files(search_dir, ('.kicad_sym',))
        mod_files = self._find_files(search_dir, ('.kicad_mod',))
        step_files = self._find_files(search_dir, ('.step', '.stp'))
        wrl_files = self._find_files(search_dir, ('.wrl',))

        # Also check root for 3D models
        if not step_files:
            step_files = self._find_files(extract_dir, ('.step', '.stp'))
        if not wrl_files:
            wrl_files = self._find_files(extract_dir, ('.wrl',))

        symbol_file = sym_files[0] if sym_files else None
        footprint_file = mod_files[0] if mod_files else None

        mpn = self._guess_mpn_from_filename(symbol_file) if symbol_file else None
        if not mpn and footprint_file:
            mpn = self._guess_mpn_from_filename(footprint_file)
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
            source_provider=Provider.SAMACSYS,
            source_url=source_url,
            referrer_url=referrer_url,
            extract_dir=extract_dir,
        )
