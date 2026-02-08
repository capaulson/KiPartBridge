"""Generic extractor — recursive scan for any KiCad files."""

import os

from models import ComponentFiles, Provider
from extractors.base import BaseExtractor


class GenericExtractor(BaseExtractor):

    def extract(self, zip_path: str, extract_dir: str,
                source_url: str | None = None,
                referrer_url: str | None = None) -> ComponentFiles:
        self._unzip(zip_path, extract_dir)

        sym_files = self._find_files(extract_dir, ('.kicad_sym',))
        lib_files = self._find_files(extract_dir, ('.lib',))
        mod_files = self._find_files(extract_dir, ('.kicad_mod',))
        step_files = self._find_files(extract_dir, ('.step', '.stp'))
        wrl_files = self._find_files(extract_dir, ('.wrl',))

        symbol_file = None
        symbol_format = "kicad_sym"
        if sym_files:
            symbol_file = sym_files[0]
        elif lib_files:
            symbol_file = lib_files[0]
            symbol_format = "legacy_lib"

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
            symbol_format=symbol_format,
            source_provider=Provider.GENERIC,
            source_url=source_url,
            referrer_url=referrer_url,
            extract_dir=extract_dir,
        )
