"""Tests for the normalizer module."""

import os
import pytest
from kiutils.symbol import SymbolLib
from kiutils.footprint import Footprint

from normalizer import sanitize_name, normalize_symbol, normalize_footprint, link_symbol_to_footprint
from extractors.ultra_librarian import UltraLibrarianExtractor


class TestSanitizeName:
    def test_basic(self):
        assert sanitize_name("STM32C071RBT6") == "STM32C071RBT6"

    def test_slashes(self):
        assert sanitize_name("A/B\\C") == "A_B_C"

    def test_special_chars(self):
        assert sanitize_name('A:B*C?"D<E>F|G') == "A_B_C__D_E_F_G"

    def test_preserves_hyphens_and_dots(self):
        assert sanitize_name("STM32F4-LQFP.100") == "STM32F4-LQFP.100"


class TestNormalizeSymbol:
    def test_normalize_ul_fixture(self, ul_fixture_path, tmp_path):
        extractor = UltraLibrarianExtractor()
        component = extractor.extract(ul_fixture_path, str(tmp_path / "extract"))

        target_lib = str(tmp_path / "test.kicad_sym")
        symbol_name = normalize_symbol(component, target_lib)

        assert symbol_name == "STM32C071RBT6"
        assert os.path.exists(target_lib)

        # Verify with kiutils round-trip
        lib = SymbolLib.from_file(target_lib)
        assert len(lib.symbols) == 1
        sym = lib.symbols[0]
        assert sym.entryName == "STM32C071RBT6"

        # Check properties
        props = {p.key: p.value for p in sym.properties}
        assert props["Reference"] == "U"
        assert props["Value"] == "STM32C071RBT6"

    def test_append_to_existing_lib(self, ul_fixture_path, tmp_path):
        extractor = UltraLibrarianExtractor()
        component = extractor.extract(ul_fixture_path, str(tmp_path / "extract"))

        target_lib = str(tmp_path / "test.kicad_sym")

        # First import
        normalize_symbol(component, target_lib)

        # Modify MPN to simulate a different component
        component.mpn = "FAKE_PART_123"
        normalize_symbol(component, target_lib)

        lib = SymbolLib.from_file(target_lib)
        names = [s.entryName for s in lib.symbols]
        assert "STM32C071RBT6" in names
        assert "FAKE_PART_123" in names
        assert len(lib.symbols) == 2

    def test_overwrite_existing(self, ul_fixture_path, tmp_path):
        extractor = UltraLibrarianExtractor()
        component = extractor.extract(ul_fixture_path, str(tmp_path / "extract"))

        target_lib = str(tmp_path / "test.kicad_sym")

        # Import twice with same MPN
        normalize_symbol(component, target_lib)
        normalize_symbol(component, target_lib)

        lib = SymbolLib.from_file(target_lib)
        assert len(lib.symbols) == 1  # Should not duplicate


class TestNormalizeFootprint:
    def test_normalize_ul_fixture(self, ul_fixture_path, tmp_path):
        extractor = UltraLibrarianExtractor()
        component = extractor.extract(ul_fixture_path, str(tmp_path / "extract"))

        fp_dir = str(tmp_path / "kipartbridge.pretty")
        models_dir = str(tmp_path / "3dmodels")
        os.makedirs(fp_dir)
        os.makedirs(models_dir)

        fp_name = normalize_footprint(component, fp_dir, models_dir)

        assert fp_name == "STM32C071RBT6"

        # Check footprint file exists
        fp_path = os.path.join(fp_dir, "STM32C071RBT6.kicad_mod")
        assert os.path.exists(fp_path)

        # Verify with kiutils
        fp = Footprint.from_file(fp_path)
        assert fp.entryName == "STM32C071RBT6"

        # Check 3D model reference
        assert len(fp.models) == 1
        assert "${KIPARTBRIDGE_3DMODELS}" in fp.models[0].path
        assert "STM32C071RBT6.step" in fp.models[0].path

        # Check STEP file was copied
        assert os.path.exists(os.path.join(models_dir, "STM32C071RBT6.step"))


class TestLinkSymbolToFootprint:
    def test_link(self, ul_fixture_path, tmp_path):
        extractor = UltraLibrarianExtractor()
        component = extractor.extract(ul_fixture_path, str(tmp_path / "extract"))

        target_lib = str(tmp_path / "test.kicad_sym")
        normalize_symbol(component, target_lib)
        link_symbol_to_footprint(target_lib, "STM32C071RBT6", "kipartbridge", "STM32C071RBT6")

        lib = SymbolLib.from_file(target_lib)
        sym = lib.symbols[0]
        props = {p.key: p.value for p in sym.properties}
        assert props["Footprint"] == "kipartbridge:STM32C071RBT6"
