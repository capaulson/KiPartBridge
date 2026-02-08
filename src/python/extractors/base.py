"""Base extractor with common helpers."""

import os
import zipfile
from abc import ABC, abstractmethod

from models import ComponentFiles


class BaseExtractor(ABC):
    """Abstract base class for provider extractors."""

    @abstractmethod
    def extract(self, zip_path: str, extract_dir: str,
                source_url: str | None = None,
                referrer_url: str | None = None) -> ComponentFiles:
        """Extract component files from a ZIP archive.

        Args:
            zip_path: Path to the downloaded ZIP file.
            extract_dir: Directory to extract files into.
            source_url: The download URL.
            referrer_url: The page URL where the download was initiated.

        Returns:
            ComponentFiles with paths to extracted files.
        """
        ...

    def _unzip(self, zip_path: str, extract_dir: str) -> list[str]:
        """Extract ZIP and return list of extracted file paths."""
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)
            return [os.path.join(extract_dir, name) for name in zf.namelist()
                    if not name.endswith('/')]

    def _find_files(self, directory: str, extensions: tuple[str, ...]) -> list[str]:
        """Recursively find files matching given extensions."""
        results = []
        for root, _dirs, files in os.walk(directory):
            for f in files:
                if f.lower().endswith(extensions):
                    results.append(os.path.join(root, f))
        return results

    def _guess_mpn_from_filename(self, filepath: str) -> str:
        """Extract MPN guess from a filename (strip extension)."""
        return os.path.splitext(os.path.basename(filepath))[0]
