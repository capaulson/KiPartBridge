"""Tests for provider_classifier."""

import pytest
from models import Provider
from provider_classifier import classify, classify_by_url, classify_by_content


class TestClassifyByURL:
    def test_digikey_models_url(self):
        assert classify_by_url(
            "https://www.digikey.com/en/models/24770021",
            None
        ) == Provider.ULTRA_LIBRARIAN

    def test_ultralibrarian_direct(self):
        assert classify_by_url(
            "https://app.ultralibrarian.com/details/abc123/STM/STM32",
            None
        ) == Provider.ULTRA_LIBRARIAN

    def test_snapeda(self):
        assert classify_by_url("https://www.snapeda.com/parts/ABC/xyz/", None) == Provider.SNAPEDA

    def test_samacsys(self):
        assert classify_by_url("https://componentsearchengine.com/part/123", None) == Provider.SAMACSYS

    def test_mouser(self):
        assert classify_by_url("https://www.mouser.com/models/abc", None) == Provider.SAMACSYS

    def test_easyeda(self):
        assert classify_by_url("https://easyeda.com/component/abc", None) == Provider.EASYEDA

    def test_lcsc(self):
        assert classify_by_url("https://www.lcsc.com/product/abc", None) == Provider.EASYEDA

    def test_unknown_url(self):
        assert classify_by_url("https://www.example.com/file.zip", None) is None

    def test_referrer_url_fallback(self):
        assert classify_by_url(
            None,
            "https://www.digikey.com/en/models/24770021"
        ) == Provider.ULTRA_LIBRARIAN

    def test_none_urls(self):
        assert classify_by_url(None, None) is None


class TestClassifyByContent:
    def test_ultra_librarian_fixture(self, ul_fixture_path):
        assert classify_by_content(ul_fixture_path) == Provider.ULTRA_LIBRARIAN


class TestClassify:
    def test_url_takes_priority(self, ul_fixture_path):
        """URL classification should be used even if content would give different result."""
        result = classify(
            ul_fixture_path,
            source_url="https://app.ultralibrarian.com/details/abc",
            referrer_url="https://www.digikey.com/en/models/24770021"
        )
        assert result == Provider.ULTRA_LIBRARIAN

    def test_content_fallback(self, ul_fixture_path):
        """When no URL matches, fall back to content classification."""
        result = classify(ul_fixture_path)
        assert result == Provider.ULTRA_LIBRARIAN

    def test_generic_fallback(self, tmp_path):
        """Non-ZIP file with no URL should return GENERIC."""
        fake = tmp_path / "test.zip"
        fake.write_bytes(b"not a zip")
        result = classify(str(fake))
        assert result == Provider.GENERIC
