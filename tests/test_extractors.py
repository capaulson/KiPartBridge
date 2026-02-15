"""Tests for provider extractors."""

import os
import zipfile
import pytest
from models import Provider
from extractors import get_extractor
from extractors.ultra_librarian import UltraLibrarianExtractor
from extractors.snapeda import SnapEDAExtractor


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


class TestSnapEDAExtractor:
    """Tests for SnapEDA extractor MPN extraction."""

    def _make_snapeda_zip(self, tmp_path, sym_name="KSC721J_LFS",
                          fp_name="KSC721J_LFS",
                          uuid_filenames=True):
        """Create a fake SnapEDA ZIP with optional UUID filenames."""
        zip_path = str(tmp_path / "snapeda_download.zip")
        if uuid_filenames:
            sym_filename = "a1b2c3d4-e5f6-7890-abcd-ef1234567890.kicad_sym"
            fp_filename = "b2c3d4e5-f6a7-8901-bcde-f12345678901.kicad_mod"
        else:
            sym_filename = f"{sym_name}.kicad_sym"
            fp_filename = f"{fp_name}.kicad_mod"

        sym_content = f'''(kicad_symbol_lib (version 20211014) (generator kicad_symbol_editor)
  (symbol "{sym_name}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)
    (property "Reference" "SW" (at 0 0 0) (effects (font (size 1.27 1.27))))
    (property "Value" "{sym_name}" (at 0 -2.54 0) (effects (font (size 1.27 1.27))))
    (symbol "{sym_name}_0_1"
      (rectangle (start -2.54 2.54) (end 2.54 -2.54) (stroke (width 0)) (fill (type background)))
    )
  )
)'''
        fp_content = f'''(footprint "{fp_name}" (version 20211014) (generator kicad_symbol_editor)
  (layer "F.Cu")
  (pad "1" smd rect (at 0 0) (size 1 1) (layers "F.Cu"))
)'''
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr(sym_filename, sym_content)
            zf.writestr(fp_filename, fp_content)
        return zip_path

    def test_mpn_from_symbol_content_uuid_filename(self, tmp_path):
        """MPN should be extracted from symbol content, not UUID filename."""
        zip_path = self._make_snapeda_zip(tmp_path, uuid_filenames=True)
        extractor = SnapEDAExtractor()
        result = extractor.extract(zip_path, str(tmp_path / "out"))
        assert result.mpn == "KSC721J_LFS"

    def test_mpn_from_symbol_content_normal_filename(self, tmp_path):
        """MPN extraction should work with normal filenames too."""
        zip_path = self._make_snapeda_zip(tmp_path, uuid_filenames=False)
        extractor = SnapEDAExtractor()
        result = extractor.extract(zip_path, str(tmp_path / "out"))
        assert result.mpn == "KSC721J_LFS"

    def test_mpn_from_referrer_url_digikey(self, tmp_path):
        """When symbol content fails, fall back to DigiKey referrer URL."""
        # Create ZIP with UUID in both filename and symbol content
        zip_path = str(tmp_path / "test.zip")
        uuid_name = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        sym_content = f'(kicad_symbol_lib (version 20211014)\n  (symbol "{uuid_name}"\n  )\n)'
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr(f"{uuid_name}.kicad_sym", sym_content)

        extractor = SnapEDAExtractor()
        result = extractor.extract(
            zip_path, str(tmp_path / "out"),
            referrer_url="https://www.digikey.com/en/products/detail/c-k/KSC721J-LFS/2414969"
        )
        assert result.mpn == "KSC721J-LFS"

    def test_mpn_from_referrer_url_snapeda(self, tmp_path):
        """Fall back to SnapEDA referrer URL."""
        zip_path = str(tmp_path / "test.zip")
        uuid_name = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        sym_content = f'(kicad_symbol_lib (version 20211014)\n  (symbol "{uuid_name}"\n  )\n)'
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr(f"{uuid_name}.kicad_sym", sym_content)

        extractor = SnapEDAExtractor()
        result = extractor.extract(
            zip_path, str(tmp_path / "out"),
            referrer_url="https://www.snapeda.com/parts/KSC721J%20LFS/C%26K/view-part/"
        )
        assert result.mpn == "KSC721J LFS"

    def test_looks_like_uuid(self):
        ext = SnapEDAExtractor()
        assert ext._looks_like_uuid("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        assert ext._looks_like_uuid("A1B2C3D4-E5F6-7890-ABCD-EF1234567890")
        assert not ext._looks_like_uuid("KSC721J-LFS")
        assert not ext._looks_like_uuid("STM32C071RBT6")
        assert not ext._looks_like_uuid("")


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
