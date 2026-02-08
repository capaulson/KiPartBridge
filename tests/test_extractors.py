"""Tests for provider extractors."""

import os
import pytest
from models import Provider
from extractors import get_extractor
from extractors.ultra_librarian import UltraLibrarianExtractor


class TestUltraLibrarianExtractor:
    def test_extract_fixture(self, ul_fixture_path, tmp_path):
        extractor = UltraLibrarianExtractor()
        result = extractor.extract(
            ul_fixture_path,
            str(tmp_path),
            source_url="https://app.ultralibrarian.com/details/a8ac03c5/STMicroelectronics/STM32C071RBT6",
            referrer_url="https://www.digikey.com/en/models/24770021"
        )

        assert result.mpn == "STM32C071RBT6"
        assert result.symbol_file is not None
        assert os.path.exists(result.symbol_file)
        assert result.symbol_file.endswith('.kicad_sym')
        assert result.symbol_format == "kicad_sym"

        assert result.footprint_file is not None
        assert os.path.exists(result.footprint_file)
        assert result.footprint_file.endswith('.kicad_mod')

        assert len(result.footprint_files) == 3  # base, -M, -L variants

        assert result.model_step is not None
        assert os.path.exists(result.model_step)
        assert result.model_step.endswith('.step')

        assert result.source_provider == Provider.ULTRA_LIBRARIAN

    def test_mpn_from_symbol_content(self, ul_fixture_path, tmp_path):
        """MPN should be extracted from the symbol name in the .kicad_sym file."""
        extractor = UltraLibrarianExtractor()
        result = extractor.extract(ul_fixture_path, str(tmp_path))
        assert result.mpn == "STM32C071RBT6"


class TestExtractorFactory:
    def test_get_ultra_librarian(self):
        ext = get_extractor(Provider.ULTRA_LIBRARIAN)
        assert isinstance(ext, UltraLibrarianExtractor)

    def test_easyeda_raises(self, tmp_path):
        ext = get_extractor(Provider.EASYEDA)
        fake_zip = tmp_path / "test.zip"
        import zipfile
        with zipfile.ZipFile(str(fake_zip), 'w') as zf:
            zf.writestr("test.json", "{}")
        with pytest.raises(NotImplementedError):
            ext.extract(str(fake_zip), str(tmp_path / "out"))
