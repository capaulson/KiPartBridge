"""Library injector — manages KiCad library registration and directory structure."""

import json
import os
import re
import sys


def get_kicad_config_dir(version: str = "9.0") -> str:
    """Get the KiCad configuration directory for the given version."""
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Preferences/kicad")
    elif sys.platform == "win32":
        base = os.path.join(os.environ.get("APPDATA", ""), "kicad")
    else:  # Linux
        base = os.path.expanduser("~/.config/kicad")
    return os.path.join(base, version)


def get_default_library_root() -> str:
    """Get the default library root directory."""
    return os.path.expanduser("~/kicad_libs/kipartbridge")


def detect_existing_library_root(config_dir: str | None = None,
                                  lib_name: str = "kipartbridge") -> str | None:
    """Check KiCad's sym-lib-table for an existing kipartbridge entry.

    Returns the library root directory if found (parent of the .kicad_sym file),
    or None if no entry exists.
    """
    if config_dir is None:
        config_dir = get_kicad_config_dir()
    table_path = os.path.join(config_dir, "sym-lib-table")
    if not os.path.exists(table_path):
        return None
    with open(table_path, 'r') as f:
        content = f.read()
    # Match: (lib (name "kipartbridge")...(uri "/path/to/kipartbridge.kicad_sym")...)
    pattern = rf'\(lib\s+\(name\s+"{re.escape(lib_name)}"\).*?\(uri\s+"([^"]+)"\)'
    m = re.search(pattern, content)
    if m:
        uri = m.group(1)
        # Root is the directory containing the .kicad_sym file
        return os.path.dirname(uri)
    return None


def ensure_library_dirs(root: str) -> None:
    """Create the library directory structure if it doesn't exist."""
    os.makedirs(root, exist_ok=True)
    os.makedirs(os.path.join(root, "kipartbridge.pretty"), exist_ok=True)
    os.makedirs(os.path.join(root, "3dmodels"), exist_ok=True)


def _read_lib_table(path: str) -> str:
    """Read a lib-table file, or return empty template if missing."""
    if os.path.exists(path):
        with open(path, 'r') as f:
            return f.read()
    return ""


def _lib_table_has_entry(content: str, lib_name: str) -> bool:
    """Check if a lib-table already contains an entry for the given library."""
    return f'(name "{lib_name}")' in content


def _update_lib_table_uri(content: str, lib_name: str, new_uri: str) -> str:
    """Update the URI of an existing entry in a lib-table."""
    pattern = rf'(\(lib\s+\(name\s+"{re.escape(lib_name)}"\)\s*\(type\s+"[^"]*"\)\s*\(uri\s+")[^"]*(")'
    return re.sub(pattern, rf'\g<1>{new_uri}\2', content)


def ensure_sym_lib_table(root: str, config_dir: str, lib_name: str = "kipartbridge") -> None:
    """Ensure the symbol library is registered in sym-lib-table.

    If an entry exists but points to a different path, updates the URI.
    """
    table_path = os.path.join(config_dir, "sym-lib-table")
    sym_lib_path = os.path.join(root, f"{lib_name}.kicad_sym")

    content = _read_lib_table(table_path)

    if _lib_table_has_entry(content, lib_name):
        # Entry exists — ensure it points to the right path
        if sym_lib_path not in content:
            content = _update_lib_table_uri(content, lib_name, sym_lib_path)
            with open(table_path, 'w') as f:
                f.write(content)
        return

    entry = f'  (lib (name "{lib_name}")(type "KiCad")(uri "{sym_lib_path}")(options "")(descr "KiPartBridge imported symbols"))\n'

    if content.strip():
        # Insert before closing paren
        content = content.rstrip()
        if content.endswith(')'):
            content = content[:-1] + entry + ')\n'
        else:
            content += '\n' + entry
    else:
        content = f'(sym_lib_table\n{entry})\n'

    os.makedirs(os.path.dirname(table_path), exist_ok=True)
    with open(table_path, 'w') as f:
        f.write(content)


def ensure_fp_lib_table(root: str, config_dir: str, lib_name: str = "kipartbridge") -> None:
    """Ensure the footprint library is registered in fp-lib-table.

    If an entry exists but points to a different path, updates the URI.
    """
    table_path = os.path.join(config_dir, "fp-lib-table")
    fp_lib_path = os.path.join(root, f"{lib_name}.pretty")

    content = _read_lib_table(table_path)

    if _lib_table_has_entry(content, lib_name):
        # Entry exists — ensure it points to the right path
        if fp_lib_path not in content:
            content = _update_lib_table_uri(content, lib_name, fp_lib_path)
            with open(table_path, 'w') as f:
                f.write(content)
        return

    entry = f'  (lib (name "{lib_name}")(type "KiCad")(uri "{fp_lib_path}")(options "")(descr "KiPartBridge imported footprints"))\n'

    if content.strip():
        content = content.rstrip()
        if content.endswith(')'):
            content = content[:-1] + entry + ')\n'
        else:
            content += '\n' + entry
    else:
        content = f'(fp_lib_table\n{entry})\n'

    os.makedirs(os.path.dirname(table_path), exist_ok=True)
    with open(table_path, 'w') as f:
        f.write(content)


def ensure_library_tables(root: str, config_dir: str | None = None,
                          lib_name: str = "kipartbridge") -> None:
    """Register both symbol and footprint libraries in KiCad's config."""
    if config_dir is None:
        config_dir = get_kicad_config_dir()
    ensure_sym_lib_table(root, config_dir, lib_name)
    ensure_fp_lib_table(root, config_dir, lib_name)


def setup_environment_variable(root: str, config_dir: str | None = None,
                               var_name: str = "KIPARTBRIDGE_3DMODELS") -> None:
    """Set the 3D models environment variable in kicad_common.json.

    Handles the case where "environment.vars" is null.
    """
    if config_dir is None:
        config_dir = get_kicad_config_dir()

    common_path = os.path.join(config_dir, "kicad_common.json")
    models_dir = os.path.join(root, "3dmodels")

    if os.path.exists(common_path):
        with open(common_path, 'r') as f:
            config = json.load(f)
    else:
        config = {}

    # Navigate to environment.vars, handling null
    if "environment" not in config:
        config["environment"] = {}
    env = config["environment"]
    if not isinstance(env, dict):
        config["environment"] = {}
        env = config["environment"]

    if "vars" not in env or env["vars"] is None:
        env["vars"] = {}

    env["vars"][var_name] = models_dir

    os.makedirs(os.path.dirname(common_path), exist_ok=True)
    with open(common_path, 'w') as f:
        json.dump(config, f, indent=2)
