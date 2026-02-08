"""Normalizer — converts extracted files to standardized KiCad 8/9 format.

Handles:
- Symbol renaming to MPN
- Footprint renaming to MPN
- 3D model path rewriting to use ${KIPARTBRIDGE_3DMODELS}
- Legacy .lib -> .kicad_sym conversion via kicad-cli
- Appending to a unified symbol library
"""

import os
import re
import shutil
import subprocess
import sys

from kiutils.symbol import SymbolLib
from kiutils.footprint import Footprint, Model
from kiutils.items.common import Property

from models import ComponentFiles

# Characters not allowed in file/symbol names
_SANITIZE_RE = re.compile(r'[/\\:*?"<>|]')

# kicad-cli path (macOS)
_KICAD_CLI_PATHS = [
    "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
    shutil.which("kicad-cli") or "",
]


def sanitize_name(name: str) -> str:
    """Replace filesystem-unsafe characters with underscores."""
    return _SANITIZE_RE.sub('_', name)


def _find_kicad_cli() -> str | None:
    """Find the kicad-cli binary."""
    for path in _KICAD_CLI_PATHS:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def convert_legacy_symbol(lib_path: str, output_path: str) -> str:
    """Convert a legacy .lib symbol file to .kicad_sym using kicad-cli.

    Returns path to the converted file.
    """
    cli = _find_kicad_cli()
    if not cli:
        raise RuntimeError(
            "kicad-cli not found. Cannot convert legacy .lib files. "
            "Install KiCad or ensure kicad-cli is in PATH."
        )
    result = subprocess.run(
        [cli, "sym", "upgrade", lib_path, "-o", output_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"kicad-cli sym upgrade failed: {result.stderr}")
    if not os.path.exists(output_path):
        raise RuntimeError(f"kicad-cli did not produce output file: {output_path}")
    return output_path


def upgrade_symbol_lib(lib_path: str) -> None:
    """Fix kiutils output header and upgrade to current KiCad format via kicad-cli.

    kiutils 1.4.8 writes version 20211014 and generator None, which KiCad 9 cannot load.
    We fix the header so kicad-cli can parse it, then run kicad-cli sym upgrade --force.
    """
    # Fix the header: replace "(generator None)" with "(generator "kipartbridge")"
    with open(lib_path, 'r') as f:
        content = f.read()
    content = content.replace('(generator None)', '(generator "kipartbridge")')
    with open(lib_path, 'w') as f:
        f.write(content)

    # Run kicad-cli to upgrade to current format
    cli = _find_kicad_cli()
    if not cli:
        return  # Can't upgrade, but the header fix alone may suffice for some KiCad versions
    result = subprocess.run(
        [cli, "sym", "upgrade", lib_path, "--force"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        # Non-fatal: log but don't fail the whole pipeline
        print(f"Warning: kicad-cli sym upgrade failed: {result.stderr}", file=sys.stderr)


def normalize_symbol(component: ComponentFiles, target_lib_path: str) -> str:
    """Normalize a symbol and append it to the target library.

    - Renames symbol to sanitized MPN
    - Ensures standard properties (Reference, Value, Footprint, Datasheet)
    - Handles duplicates by replacing existing symbol with same name
    - Converts legacy .lib if needed

    Returns the symbol name.
    """
    if not component.symbol_file:
        raise ValueError("No symbol file in component")

    source_path = component.symbol_file
    mpn = sanitize_name(component.mpn)

    # Convert legacy format if needed
    if component.symbol_format == "legacy_lib":
        converted = source_path + ".kicad_sym"
        convert_legacy_symbol(source_path, converted)
        source_path = converted

    # Load source symbol library
    source_lib = SymbolLib.from_file(source_path)
    if not source_lib.symbols:
        raise ValueError(f"No symbols found in {source_path}")

    # Take the first symbol and rename it
    symbol = source_lib.symbols[0]
    symbol.entryName = mpn

    # Update sub-symbol names (e.g. "OrigName_0_1" -> "MPN_0_1")
    # KiCad sub-symbols always end with _<digit>_<digit> suffix
    _SUB_SUFFIX = re.compile(r'_(\d+)_(\d+)$')
    for sub in symbol.units:
        m = _SUB_SUFFIX.search(sub.entryName)
        if m:
            sub.entryName = f"{mpn}_{m.group(1)}_{m.group(2)}"
        else:
            sub.entryName = mpn

    # Ensure standard properties
    _set_property(symbol, "Reference", "U")
    _set_property(symbol, "Value", mpn)

    # Load or create target library
    if os.path.exists(target_lib_path):
        target_lib = SymbolLib.from_file(target_lib_path)
    else:
        target_lib = SymbolLib()

    # Remove existing symbol with same name (for overwrite/update)
    target_lib.symbols = [s for s in target_lib.symbols if s.entryName != mpn]

    # Append
    target_lib.symbols.append(symbol)
    target_lib.to_file(target_lib_path)

    return mpn


def normalize_footprint(component: ComponentFiles, footprint_dir: str,
                        models_dir: str) -> str:
    """Normalize a footprint and copy it to the library directory.

    - Renames footprint to sanitized MPN
    - Rewrites 3D model paths to use ${KIPARTBRIDGE_3DMODELS}
    - Copies .step/.wrl files to models_dir

    Returns the footprint name.
    """
    if not component.footprint_file:
        raise ValueError("No footprint file in component")

    mpn = sanitize_name(component.mpn)
    fp = Footprint.from_file(component.footprint_file)

    # Rename footprint
    fp.entryName = mpn

    # Copy 3D model files and set up references
    model_filename = None
    if component.model_step:
        ext = os.path.splitext(component.model_step)[1]
        model_filename = f"{mpn}{ext}"
        dest = os.path.join(models_dir, model_filename)
        shutil.copy2(component.model_step, dest)

    if component.model_wrl:
        ext = os.path.splitext(component.model_wrl)[1]
        wrl_filename = f"{mpn}{ext}"
        dest = os.path.join(models_dir, wrl_filename)
        shutil.copy2(component.model_wrl, dest)
        if not model_filename:
            model_filename = wrl_filename

    # Rewrite 3D model references
    if model_filename:
        model_path = f"${{KIPARTBRIDGE_3DMODELS}}/{model_filename}"
        fp.models = [Model(path=model_path)]
    else:
        fp.models = []

    # Write footprint to target directory
    target_path = os.path.join(footprint_dir, f"{mpn}.kicad_mod")
    fp.to_file(target_path)

    return mpn


def link_symbol_to_footprint(target_lib_path: str, symbol_name: str,
                             library_name: str, footprint_name: str) -> None:
    """Set the Footprint property on a symbol to point to the correct footprint.

    Sets it to "library_name:footprint_name" (e.g. "kipartbridge:STM32C071RBT6").
    """
    lib = SymbolLib.from_file(target_lib_path)
    for symbol in lib.symbols:
        if symbol.entryName == symbol_name:
            footprint_ref = f"{library_name}:{footprint_name}"
            _set_property(symbol, "Footprint", footprint_ref)
            lib.to_file(target_lib_path)
            return
    raise ValueError(f"Symbol '{symbol_name}' not found in {target_lib_path}")


def _set_property(symbol, key: str, value: str) -> None:
    """Set or update a property on a symbol."""
    for prop in symbol.properties:
        if prop.key == key:
            prop.value = value
            return
    # Add new property if not found
    new_id = max((p.id for p in symbol.properties if p.id is not None), default=-1) + 1
    symbol.properties.append(Property(key=key, value=value, id=new_id))
