import sys
import os
import pytest

# Add src/python to the path so tests can import modules directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'python'))

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def ul_fixture_path():
    path = os.path.join(FIXTURES_DIR, 'ultra_librarian_STM32C071RBT6.zip')
    if not os.path.exists(path):
        pytest.skip('Ultra Librarian test fixture not downloaded yet')
    return path


@pytest.fixture
def tmp_library(tmp_path):
    """Create a temporary library root for testing."""
    lib_root = tmp_path / 'kipartbridge'
    lib_root.mkdir()
    (lib_root / 'kipartbridge.pretty').mkdir()
    (lib_root / '3dmodels').mkdir()
    return lib_root
