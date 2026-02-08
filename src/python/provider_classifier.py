"""Provider classification — identifies download source by URL or ZIP content."""

import zipfile
from models import Provider


# URL patterns mapped to providers (checked in order)
_URL_PATTERNS = [
    # Ultra Librarian direct
    ("ultralibrarian.com", Provider.ULTRA_LIBRARIAN),
    ("app.ultralibrarian.com", Provider.ULTRA_LIBRARIAN),
    # DigiKey models page (uses Ultra Librarian)
    ("digikey.com/en/models", Provider.ULTRA_LIBRARIAN),
    # SnapEDA
    ("snapeda.com", Provider.SNAPEDA),
    # SamacSys / Component Search Engine
    ("componentsearchengine.com", Provider.SAMACSYS),
    ("samacsys.com", Provider.SAMACSYS),
    # Mouser uses SamacSys
    ("mouser.com", Provider.SAMACSYS),
    # EasyEDA / JLCPCB / LCSC
    ("easyeda.com", Provider.EASYEDA),
    ("jlcpcb.com", Provider.EASYEDA),
    ("lcsc.com", Provider.EASYEDA),
]


def classify_by_url(source_url: str | None, referrer_url: str | None) -> Provider | None:
    """Classify provider from URL patterns. Returns None if no match."""
    for url in (source_url, referrer_url):
        if not url:
            continue
        url_lower = url.lower()
        for pattern, provider in _URL_PATTERNS:
            if pattern in url_lower:
                return provider
    return None


def classify_by_content(filepath: str) -> Provider | None:
    """Classify provider by inspecting ZIP contents."""
    try:
        with zipfile.ZipFile(filepath, 'r') as zf:
            names = zf.namelist()
    except (zipfile.BadZipFile, FileNotFoundError):
        return None

    has_kicad_sym = False
    has_kicad_mod = False
    has_json = False

    for name in names:
        name_lower = name.lower()

        # Ultra Librarian: KiCADv6/ or KiCAD/ directory (uppercase D)
        if name.startswith('KiCAD') and '/' in name:
            return Provider.ULTRA_LIBRARIAN

        # SamacSys: KiCad/ directory (lowercase d)
        if name.startswith('KiCad/'):
            return Provider.SAMACSYS

        if name_lower.endswith('.kicad_sym'):
            has_kicad_sym = True
        if name_lower.endswith('.kicad_mod'):
            has_kicad_mod = True
        if name_lower.endswith('.json'):
            has_json = True

    # SnapEDA: root-level .kicad_sym + .kicad_mod
    if has_kicad_sym and has_kicad_mod:
        return Provider.SNAPEDA

    # EasyEDA: JSON files
    if has_json and not has_kicad_sym and not has_kicad_mod:
        return Provider.EASYEDA

    return None


def classify(filepath: str, source_url: str | None = None,
             referrer_url: str | None = None) -> Provider:
    """Classify the provider for a downloaded file.

    Strategy: URL-based first (high confidence), then ZIP content fallback.
    Returns Provider.GENERIC if unrecognized.
    """
    # Try URL-based classification first
    provider = classify_by_url(source_url, referrer_url)
    if provider is not None:
        return provider

    # Fall back to content-based classification
    provider = classify_by_content(filepath)
    if provider is not None:
        return provider

    return Provider.GENERIC
