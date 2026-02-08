"""Tests for the database module."""

import os
import pytest
from database import ComponentDB


@pytest.fixture
def db(tmp_path):
    db = ComponentDB(str(tmp_path / "test.db"))
    yield db
    db.close()


class TestComponentDB:
    def test_upsert_and_get(self, db):
        comp_id = db.upsert_component(
            mpn="STM32C071RBT6",
            symbol_name="STM32C071RBT6",
            footprint_name="STM32C071RBT6",
            has_3d_model=True,
            manufacturer="STMicroelectronics",
            source_provider="ultra_librarian",
        )
        assert comp_id > 0

        comp = db.get_component("STM32C071RBT6")
        assert comp is not None
        assert comp["mpn"] == "STM32C071RBT6"
        assert comp["manufacturer"] == "STMicroelectronics"
        assert comp["has_3d_model"] == 1

    def test_upsert_updates_existing(self, db):
        db.upsert_component(mpn="TEST1", manufacturer="Mfr1")
        db.upsert_component(mpn="TEST1", manufacturer="Mfr2")

        comp = db.get_component("TEST1")
        assert comp["manufacturer"] == "Mfr2"

    def test_component_exists(self, db):
        assert not db.component_exists("NOPE")
        db.upsert_component(mpn="TEST1")
        assert db.component_exists("TEST1")

    def test_list_components(self, db):
        db.upsert_component(mpn="A")
        db.upsert_component(mpn="B")
        db.upsert_component(mpn="C")

        result = db.list_components(limit=2)
        assert len(result) == 2

    def test_search_components(self, db):
        db.upsert_component(mpn="STM32C071RBT6", manufacturer="STMicroelectronics")
        db.upsert_component(mpn="ESP32-S3", manufacturer="Espressif")

        result = db.search_components("STM32")
        assert len(result) == 1
        assert result[0]["mpn"] == "STM32C071RBT6"

        result = db.search_components("Espressif")
        assert len(result) == 1

    def test_log_import(self, db):
        comp_id = db.upsert_component(mpn="TEST1")
        db.log_import(comp_id, "import", "test.zip")
        # Should not raise
