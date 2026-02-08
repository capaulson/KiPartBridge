# KiCad Library Manager — Product Design Review (PDR)

## Project: KiPartBridge

**Author:** Chris  
**Date:** 2026-02-07  
**Version:** 1.0  
**Status:** Design Phase

---

## 1. Executive Summary

KiPartBridge is a desktop application with an embedded browser that allows users to browse component supplier websites (DigiKey, Mouser, LCSC, SnapEDA, SamacSys/Component Search Engine), download EDA models (schematic symbols, footprints, 3D models), and automatically process and inject them into a unified KiCad 8 library. The app intercepts downloads at the browser level, eliminating the manual unzip-copy-rename workflow that currently plagues KiCad users.

---

## 2. Problem Statement

Getting component models from supplier websites into KiCad libraries currently requires:
1. Navigate to supplier site, find the component model page
2. Select "KiCad" as the EDA tool
3. Download a ZIP file to an arbitrary location
4. Manually unzip the archive
5. Identify which files are symbols, footprints, and 3D models
6. Copy each file to the correct KiCad library directory
7. Edit the footprint `.kicad_mod` file to fix the 3D model path
8. Ensure the library tables (`sym-lib-table`, `fp-lib-table`) reference the library

This is 8+ steps per component. Engineers designing boards with 50-200 unique components waste hours on library management. Different providers (Ultra Librarian, SnapEDA, SamacSys, EasyEDA) each structure their downloads differently, adding cognitive overhead.

---

## 3. Target Users

- Electronics engineers using KiCad 8+ for PCB design
- Hardware engineers who source components from DigiKey, Mouser, LCSC, and similar distributors
- Makers and hobbyists who want a streamlined component library workflow

---

## 4. Architecture Overview

### 4.1 Technology Stack

| Layer | Technology | Justification |
|-------|-----------|---------------|
| Desktop Framework | **Electron** | Mature WebView download interception API, large ecosystem, fast to prototype. Evaluate Tauri migration later for smaller binary. |
| Frontend UI | **React + Tailwind CSS** | Status panel, library browser, settings. Minimal UI — the embedded browser IS the main interface. |
| Backend Processing | **Python (subprocess sidecar)** | `kiutils` library for KiCad file parsing/writing. Python is the only language with a mature KiCad file manipulation library. |
| Database | **SQLite** | Track imported components, dedup by MPN, store metadata. |
| Package Format | **Electron Builder** | Cross-platform builds (macOS, Linux, Windows). |

### 4.2 System Diagram

```
┌──────────────────────────────────────────────────────────────┐
│  Electron Main Process                                        │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  BrowserView / WebView (Chromium)                        │ │
│  │  - User browses DigiKey, Mouser, LCSC, SnapEDA, etc.    │ │
│  │  - Standard web browsing experience                      │ │
│  │  - Navigation bar with bookmarks sidebar                 │ │
│  └──────────────┬───────────────────────────────────────────┘ │
│                  │                                              │
│                  │  session.on('will-download')                 │
│                  ▼                                              │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Download Interceptor (main process)                      │ │
│  │  - Captures ALL downloads from the WebView               │ │
│  │  - Extracts source URL for provider identification       │ │
│  │  - Routes file to staging directory                      │ │
│  │  - Emits IPC event to renderer on completion             │ │
│  └──────────────┬───────────────────────────────────────────┘ │
│                  │                                              │
│                  ▼                                              │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Python Sidecar Process (long-running)                    │ │
│  │  Communicates via stdin/stdout JSON-RPC                   │ │
│  │                                                            │ │
│  │  ┌────────────────┐  ┌─────────────────┐  ┌───────────┐ │ │
│  │  │ Provider        │  │ Normalizer      │  │ Library   │ │ │
│  │  │ Classifier      │→│ (kiutils)       │→│ Injector  │ │ │
│  │  │                 │  │                  │  │           │ │ │
│  │  │ - SnapEDA       │  │ - .lib→.kicad_  │  │ - Append  │ │ │
│  │  │ - UltraLibr.    │  │    sym          │  │   symbol  │ │ │
│  │  │ - SamacSys      │  │ - Fix 3D paths  │  │ - Copy    │ │ │
│  │  │ - EasyEDA       │  │ - Validate pins │  │   footpr. │ │ │
│  │  │ - Generic       │  │ - Standardize   │  │ - Copy 3D │ │ │
│  │  └────────────────┘  └─────────────────┘  └───────────┘ │ │
│  │                                                            │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │ SQLite: components.db                                 │ │ │
│  │  │ - mpn, manufacturer, description, provider           │ │ │
│  │  │ - symbol_name, footprint_name, model_path            │ │ │
│  │  │ - import_date, source_url                            │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Renderer Process (React)                                 │ │
│  │  - Status panel: import progress, recent imports         │ │
│  │  - Library browser: search/filter imported components    │ │
│  │  - Settings: library paths, 3D model path template       │ │
│  │  - Activity log: processing events                       │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  KiCad Library on Disk                                        │
│                                                                │
│  ~/.kicad_libs/                                                │
│  ├── kipartbridge.kicad_sym    (all symbols, single file)     │
│  ├── kipartbridge.pretty/      (directory of .kicad_mod)      │
│  │   ├── STM32C071RBT6.kicad_mod                              │
│  │   ├── LQFP-64_10x10mm_P0.5mm.kicad_mod                    │
│  │   └── ...                                                   │
│  └── 3dmodels/                                                 │
│      ├── STM32C071RBT6.step                                    │
│      ├── STM32C071RBT6.wrl                                     │
│      └── ...                                                   │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. Detailed Component Specifications

### 5.1 Electron Main Process — Download Interceptor

**Purpose:** Intercept all file downloads from the embedded WebView and route them to a controlled staging directory.

**Implementation:**

```javascript
// In main.js
const { session } = require('electron');

const stagingDir = path.join(app.getPath('userData'), 'staging');

session.defaultSession.on('will-download', (event, item, webContents) => {
  const filename = item.getFilename();
  const sourceURL = item.getURL();
  const referrerURL = webContents.getURL();
  
  // Force save to staging directory
  const savePath = path.join(stagingDir, `${Date.now()}_${filename}`);
  item.setSavePath(savePath);
  
  item.on('done', (event, state) => {
    if (state === 'completed') {
      // Send to Python sidecar for processing
      pythonProcess.send({
        method: 'process_download',
        params: {
          filepath: savePath,
          filename: filename,
          source_url: sourceURL,
          referrer_url: referrerURL,
          download_time: new Date().toISOString()
        }
      });
      
      // Notify renderer
      mainWindow.webContents.send('download-processing', { filename, sourceURL });
    }
  });
});
```

**Key behaviors:**
- ALL downloads are intercepted — the user never sees a "Save As" dialog
- Files are timestamped to prevent collisions
- Source URL and referrer URL are captured for provider identification
- IPC events notify the React renderer of download state changes

### 5.2 Provider Classifier

**Purpose:** Determine which EDA model provider generated the downloaded file, since each structures their ZIP contents differently.

**Provider signatures (by URL pattern AND file contents):**

| Provider | URL Pattern | ZIP Contents Signature |
|----------|------------|----------------------|
| Ultra Librarian | `ultralibrarian.com`, `digikey.com/en/models` | Contains `KiCad/` subfolder, sometimes `.bxl` files |
| SnapEDA | `snapeda.com` | Root-level `.kicad_sym`, `.kicad_mod`, `.step` files. May include `README.txt` with SnapEDA branding |
| SamacSys (CSE) | `componentsearchengine.com`, `samacsys.com` | `KiCad/` folder with subfolders: `KiCad/symbol/`, `KiCad/footprint/`, `KiCad/3dmodel/` |
| EasyEDA/JLCPCB | `easyeda.com`, `jlcpcb.com` | JSON files (`.json`). Requires conversion via `easyeda2kicad` |
| Mouser (via Samacsys) | `mouser.com` | Same as SamacSys structure |
| Generic/Unknown | Any other | Scan for `.kicad_sym`, `.kicad_mod`, `.lib`, `.step`, `.wrl` at any depth |

**Implementation (Python):**

```python
# provider_classifier.py

import zipfile
import os
from urllib.parse import urlparse
from enum import Enum

class Provider(Enum):
    ULTRA_LIBRARIAN = "ultra_librarian"
    SNAPEDA = "snapeda"
    SAMACSYS = "samacsys"
    EASYEDA = "easyeda"
    GENERIC = "generic"

def classify(filepath: str, source_url: str, referrer_url: str) -> Provider:
    """
    Classify the download provider using URL patterns first,
    then fall back to ZIP content analysis.
    """
    # URL-based classification (highest confidence)
    urls = [source_url, referrer_url]
    for url in urls:
        domain = urlparse(url).netloc.lower()
        if 'ultralibrarian' in domain:
            return Provider.ULTRA_LIBRARIAN
        if 'snapeda' in domain:
            return Provider.SNAPEDA
        if 'componentsearchengine' in domain or 'samacsys' in domain:
            return Provider.SAMACSYS
        if 'easyeda' in domain or 'jlcpcb' in domain:
            return Provider.EASYEDA
    
    # Content-based classification (fallback)
    if zipfile.is_zipfile(filepath):
        with zipfile.ZipFile(filepath) as zf:
            names = zf.namelist()
            if any('KiCad/' in n for n in names):
                # Check for SamacSys subfolder structure
                if any('KiCad/symbol/' in n or 'KiCad/footprint/' in n for n in names):
                    return Provider.SAMACSYS
                return Provider.ULTRA_LIBRARIAN
            if any(n.endswith('.json') and not n.endswith('.kicad_sym') for n in names):
                return Provider.EASYEDA
            if any('snapeda' in n.lower() or 'readme' in n.lower() for n in names):
                return Provider.SNAPEDA
    
    return Provider.GENERIC
```

### 5.3 Provider-Specific Extractors

Each provider extractor must return a standardized `ComponentFiles` dataclass:

```python
# models.py

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

@dataclass
class ComponentFiles:
    """Standardized output from any provider extractor."""
    mpn: str                              # Manufacturer Part Number
    manufacturer: Optional[str] = None
    description: Optional[str] = None
    
    symbol_file: Optional[Path] = None     # .kicad_sym file
    footprint_file: Optional[Path] = None  # .kicad_mod file
    model_step: Optional[Path] = None      # .step file
    model_wrl: Optional[Path] = None       # .wrl file
    
    symbol_format: str = "kicad8"          # "kicad8", "kicad_legacy", "bxl"
    footprint_format: str = "kicad8"       # "kicad8", "kicad_legacy"
    
    source_provider: str = ""
    source_url: str = ""
    
    # Files that need conversion before use
    needs_symbol_conversion: bool = False
    needs_footprint_conversion: bool = False
    
    # Raw extracted directory for cleanup
    extract_dir: Optional[Path] = None
```

**Extractor interface:**

```python
# extractors/base.py

from abc import ABC, abstractmethod
from pathlib import Path
from models import ComponentFiles

class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, zip_path: Path, extract_dir: Path) -> ComponentFiles:
        """
        Extract and classify files from a provider-specific ZIP.
        Returns a ComponentFiles with paths to the extracted files.
        """
        pass
    
    def _find_files_by_extension(self, directory: Path, extensions: list[str]) -> list[Path]:
        """Recursively find files matching given extensions."""
        results = []
        for ext in extensions:
            results.extend(directory.rglob(f"*{ext}"))
        return results
```

**Each provider gets its own extractor module:**
- `extractors/ultra_librarian.py`
- `extractors/snapeda.py`
- `extractors/samacsys.py`
- `extractors/easyeda.py` (uses `easyeda2kicad` for conversion)
- `extractors/generic.py`

### 5.4 Normalizer (kiutils-based)

**Purpose:** Convert all extracted files to KiCad 8 format and standardize naming, paths, and structure.

**Dependencies:** `pip install kiutils`

**Operations:**

#### 5.4.1 Symbol Normalization

```python
# normalizer.py

from kiutils.symbol import SymbolLib, Symbol
from kiutils.items.common import Property
from pathlib import Path

def normalize_symbol(component: ComponentFiles, target_lib: Path) -> str:
    """
    Read the source symbol, normalize it, and append to the target library.
    Returns the symbol name as written to the library.
    """
    # Load source symbol
    source_lib = SymbolLib.from_file(str(component.symbol_file))
    
    if not source_lib.symbols:
        raise ValueError(f"No symbols found in {component.symbol_file}")
    
    symbol = source_lib.symbols[0]
    
    # Standardize symbol name to MPN
    symbol_name = sanitize_name(component.mpn)
    symbol.entryName = symbol_name
    # Update the id as well (KiCad 8 uses entryName as primary)
    symbol.id = symbol_name
    
    # Ensure required properties exist
    ensure_property(symbol, "Reference", "U")
    ensure_property(symbol, "Value", component.mpn)
    ensure_property(symbol, "Footprint", "")  # Will be set after footprint processing
    ensure_property(symbol, "Datasheet", "")
    ensure_property(symbol, "MPN", component.mpn)
    if component.manufacturer:
        ensure_property(symbol, "Manufacturer", component.manufacturer)
    
    # Load or create target library
    if target_lib.exists():
        target = SymbolLib.from_file(str(target_lib))
    else:
        target = SymbolLib()
    
    # Check for duplicates
    existing_names = [s.entryName for s in target.symbols]
    if symbol_name in existing_names:
        # Remove old version (update in place)
        target.symbols = [s for s in target.symbols if s.entryName != symbol_name]
    
    target.symbols.append(symbol)
    target.to_file(str(target_lib))
    
    return symbol_name


def ensure_property(symbol: Symbol, name: str, default_value: str):
    """Add property if missing, don't overwrite if present."""
    for prop in symbol.properties:
        if prop.key == name:
            return
    symbol.properties.append(Property(key=name, value=default_value))


def sanitize_name(name: str) -> str:
    """
    Sanitize component name for KiCad compatibility.
    KiCad names cannot contain: / \\ : * ? \" < > |
    """
    invalid_chars = '/\\:*?"<>|'
    result = name
    for char in invalid_chars:
        result = result.replace(char, '_')
    return result.strip()
```

#### 5.4.2 Footprint Normalization

```python
def normalize_footprint(component: ComponentFiles, 
                         footprint_dir: Path, 
                         models_dir: Path) -> str:
    """
    Copy and normalize footprint file. Fix 3D model path references.
    Returns the footprint filename (without extension).
    """
    from kiutils.footprint import Footprint
    
    fp = Footprint.from_file(str(component.footprint_file))
    
    # Standardize footprint name
    fp_name = sanitize_name(component.mpn)
    
    # Fix 3D model paths
    # KiCad convention: use environment variable for portability
    # ${KIPARTBRIDGE_3DMODELS}/ModelName.step
    for model in fp.models:
        original_path = model.path
        model_filename = Path(original_path).name
        
        # Rewrite to use env variable
        model.path = f"${{KIPARTBRIDGE_3DMODELS}}/{model_filename}"
    
    # If no 3D model reference exists but we have a model file, add it
    if not fp.models and (component.model_step or component.model_wrl):
        from kiutils.items.fpitems import Model
        from kiutils.items.common import Position
        
        if component.model_step:
            model_filename = component.model_step.name
        else:
            model_filename = component.model_wrl.name
        
        new_model = Model(
            path=f"${{KIPARTBRIDGE_3DMODELS}}/{model_filename}"
        )
        fp.models.append(new_model)
    
    # Write normalized footprint
    target_path = footprint_dir / f"{fp_name}.kicad_mod"
    fp.to_file(str(target_path))
    
    # Copy 3D model files
    if component.model_step:
        shutil.copy2(component.model_step, models_dir / component.model_step.name)
    if component.model_wrl:
        shutil.copy2(component.model_wrl, models_dir / component.model_wrl.name)
    
    return fp_name
```

#### 5.4.3 Post-Normalization: Link Symbol to Footprint

After both symbol and footprint are processed, update the symbol's `Footprint` property:

```python
def link_symbol_to_footprint(target_lib: Path, symbol_name: str, 
                              library_name: str, footprint_name: str):
    """
    Set the Footprint property on the symbol to reference the correct footprint.
    Format: "LibraryName:FootprintName"
    """
    lib = SymbolLib.from_file(str(target_lib))
    for symbol in lib.symbols:
        if symbol.entryName == symbol_name:
            for prop in symbol.properties:
                if prop.key == "Footprint":
                    prop.value = f"{library_name}:{footprint_name}"
                    break
            break
    lib.to_file(str(target_lib))
```

### 5.5 Library Injector

**Purpose:** Manage the on-disk KiCad library structure and ensure KiCad's library tables are configured correctly.

**Library structure managed by the app:**

```
{library_root}/                          # User-configurable, default: ~/.kicad_libs/kipartbridge/
├── kipartbridge.kicad_sym               # Single symbol library file (all symbols)
├── kipartbridge.pretty/                 # Footprint library directory
│   ├── STM32C071RBT6.kicad_mod
│   ├── ESP32-S3-WROOM-1.kicad_mod
│   └── ...
└── 3dmodels/                            # 3D model directory
    ├── STM32C071RBT6.step
    ├── ESP32-S3-WROOM-1.step
    └── ...
```

**Library table management:**

On first run (or when library root changes), the app must register itself in KiCad's global library tables:

```python
def ensure_library_tables(library_root: Path, library_name: str = "kipartbridge"):
    """
    Add library entries to KiCad's global sym-lib-table and fp-lib-table
    if not already present.
    """
    kicad_config = get_kicad_config_dir()  # Platform-dependent
    
    # Symbol library table
    sym_table = kicad_config / "sym-lib-table"
    sym_entry = f'  (lib (name "{library_name}")(type "KiCad")(uri "{library_root / (library_name + ".kicad_sym")}")(options "")(descr "KiPartBridge auto-imported symbols"))'
    _add_table_entry_if_missing(sym_table, library_name, sym_entry)
    
    # Footprint library table
    fp_table = kicad_config / "fp-lib-table"
    fp_entry = f'  (lib (name "{library_name}")(type "KiCad")(uri "{library_root / (library_name + ".pretty")}")(options "")(descr "KiPartBridge auto-imported footprints"))'
    _add_table_entry_if_missing(fp_table, library_name, fp_entry)


def get_kicad_config_dir() -> Path:
    """Return KiCad 8 config directory for the current platform."""
    import platform
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Preferences" / "kicad" / "8.0"
    elif system == "Linux":
        return Path.home() / ".config" / "kicad" / "8.0"
    elif system == "Windows":
        return Path(os.environ["APPDATA"]) / "kicad" / "8.0"
    raise RuntimeError(f"Unsupported platform: {system}")


def setup_environment_variable(library_root: Path):
    """
    Configure the KIPARTBRIDGE_3DMODELS environment variable in KiCad's
    kicad_common.json so 3D model paths resolve correctly.
    """
    kicad_config = get_kicad_config_dir()
    common_file = kicad_config / "kicad_common.json"
    
    # Read existing config
    import json
    with open(common_file) as f:
        config = json.load(f)
    
    # Add or update environment variable
    if "environment" not in config:
        config["environment"] = {"vars": {}}
    
    config["environment"]["vars"]["KIPARTBRIDGE_3DMODELS"] = str(library_root / "3dmodels")
    
    with open(common_file, 'w') as f:
        json.dump(config, f, indent=2)
```

### 5.6 SQLite Schema

```sql
CREATE TABLE IF NOT EXISTS components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mpn TEXT NOT NULL,
    manufacturer TEXT,
    description TEXT,
    
    -- Library references
    symbol_name TEXT NOT NULL,
    footprint_name TEXT,
    model_step_filename TEXT,
    model_wrl_filename TEXT,
    
    -- Source tracking
    source_provider TEXT NOT NULL,        -- "ultra_librarian", "snapeda", etc.
    source_url TEXT,
    referrer_url TEXT,
    
    -- Metadata
    package_type TEXT,                     -- "LQFP-64", "0402", "SOT-23", etc.
    pin_count INTEGER,
    
    -- Timestamps
    imported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(mpn)                           -- Prevent duplicate imports
);

CREATE INDEX idx_mpn ON components(mpn);
CREATE INDEX idx_manufacturer ON components(manufacturer);
CREATE INDEX idx_imported_at ON components(imported_at);

CREATE TABLE IF NOT EXISTS import_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    component_id INTEGER REFERENCES components(id),
    action TEXT NOT NULL,                  -- "imported", "updated", "failed"
    source_file TEXT,
    error_message TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 5.7 Electron Renderer UI

**Layout: Split pane**

```
┌────────────────────────────────────────────────────────────┐
│ [←] [→] [🔄] [ URL Bar                          ] [⚙️]   │
│ ┌─────────┬──────────────────────────────────────────────┐ │
│ │ Quick   │                                              │ │
│ │ Links   │   Embedded WebView                           │ │
│ │         │   (DigiKey, Mouser, LCSC, etc.)              │ │
│ │ DigiKey │                                              │ │
│ │ Mouser  │                                              │ │
│ │ LCSC    │                                              │ │
│ │ SnapEDA │                                              │ │
│ │ CSE     │                                              │ │
│ │         │                                              │ │
│ │─────────│                                              │ │
│ │ Recent  │                                              │ │
│ │ Imports │                                              │ │
│ │         │                                              │ │
│ │ ✅ STM32│                                              │ │
│ │ ✅ ESP32│                                              │ │
│ │ ⏳ LM358│                                              │ │
│ │         │                                              │ │
│ └─────────┴──────────────────────────────────────────────┘ │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Status: Imported STM32C071RBT6 → kipartbridge library   ││
│ └──────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────┘
```

**Quick Links sidebar entries (default bookmarks):**

| Name | URL |
|------|-----|
| DigiKey Models | `https://www.digikey.com/en/resources/design-tools/design-tools` |
| Mouser | `https://www.mouser.com` |
| LCSC | `https://www.lcsc.com` |
| SnapEDA | `https://www.snapeda.com` |
| Component Search Engine | `https://componentsearchengine.com` |
| Ultra Librarian | `https://www.ultralibrarian.com` |

**Status bar states:**
- `⏳ Downloading {filename}...`
- `🔄 Processing {mpn} from {provider}...`
- `✅ Imported {mpn} → {library_name} (symbol + footprint + 3D model)`
- `⚠️ Imported {mpn} → {library_name} (symbol + footprint, no 3D model available)`
- `❌ Failed to process {filename}: {error}`

### 5.8 Settings Panel

User-configurable options (stored in Electron `electron-store` or similar):

```json
{
  "library": {
    "root_path": "~/.kicad_libs/kipartbridge",
    "symbol_lib_name": "kipartbridge",
    "footprint_lib_name": "kipartbridge",
    "auto_register_tables": true
  },
  "processing": {
    "auto_process_downloads": true,
    "overwrite_existing": false,
    "3d_model_env_var": "KIPARTBRIDGE_3DMODELS",
    "preferred_3d_format": "step"
  },
  "browser": {
    "homepage": "https://www.digikey.com",
    "bookmarks": [
      { "name": "DigiKey", "url": "https://www.digikey.com" },
      { "name": "Mouser", "url": "https://www.mouser.com" },
      { "name": "LCSC", "url": "https://www.lcsc.com" },
      { "name": "SnapEDA", "url": "https://www.snapeda.com" },
      { "name": "CSE", "url": "https://componentsearchengine.com" }
    ]
  },
  "notifications": {
    "show_desktop_notifications": true,
    "play_sound_on_import": false
  }
}
```

---

## 6. Processing Pipeline — Complete Flow

### Step-by-step for a single download:

```
1. USER clicks "Download KiCad" on DigiKey Ultra Librarian page

2. ELECTRON intercepts the download via session.on('will-download')
   → Captures: filename, source_url, referrer_url
   → Saves to: {staging_dir}/{timestamp}_{filename}
   → Sends IPC: 'download-started'

3. ELECTRON sends JSON-RPC to Python sidecar:
   {
     "method": "process_download",
     "params": {
       "filepath": "/path/to/staging/1707321600_STM32C071RBT6.zip",
       "source_url": "https://app.ultralibrarian.com/...",
       "referrer_url": "https://www.digikey.com/en/models/24770021"
     }
   }

4. PYTHON: Provider Classifier
   → URL contains "ultralibrarian" → Provider.ULTRA_LIBRARIAN

5. PYTHON: Ultra Librarian Extractor
   → Unzips to temp directory
   → Finds: KiCad/STM32C071RBT6.kicad_sym
   → Finds: KiCad/STM32C071RBT6.kicad_mod
   → Finds: KiCad/STM32C071RBT6.step
   → Returns ComponentFiles(
       mpn="STM32C071RBT6",
       symbol_file=Path("...kicad_sym"),
       footprint_file=Path("...kicad_mod"),
       model_step=Path("...step")
     )

6. PYTHON: Symbol Normalizer
   → Reads source .kicad_sym via kiutils
   → Sets symbol name to "STM32C071RBT6"
   → Ensures properties: Reference=U, Value=STM32C071RBT6, MPN, etc.
   → Appends to ~/.kicad_libs/kipartbridge/kipartbridge.kicad_sym

7. PYTHON: Footprint Normalizer
   → Reads source .kicad_mod via kiutils
   → Rewrites 3D model path: ${KIPARTBRIDGE_3DMODELS}/STM32C071RBT6.step
   → Copies to ~/.kicad_libs/kipartbridge/kipartbridge.pretty/STM32C071RBT6.kicad_mod
   → Copies STM32C071RBT6.step to ~/.kicad_libs/kipartbridge/3dmodels/

8. PYTHON: Link symbol Footprint property
   → Sets to "kipartbridge:STM32C071RBT6"

9. PYTHON: SQLite insert
   → INSERT INTO components (mpn, symbol_name, footprint_name, ...)

10. PYTHON: Responds via JSON-RPC:
    {
      "result": {
        "status": "success",
        "mpn": "STM32C071RBT6",
        "symbol_name": "STM32C071RBT6",
        "footprint_name": "STM32C071RBT6",
        "has_3d_model": true
      }
    }

11. ELECTRON: Updates renderer via IPC
    → Status bar: "✅ Imported STM32C071RBT6"
    → Recent imports list updated

12. CLEANUP: Delete staging ZIP and temp extraction directory
```

---

## 7. Edge Cases and Error Handling

### 7.1 Duplicate Components

When a component with the same MPN already exists:
- **Default behavior:** Skip import, notify user "STM32C071RBT6 already in library"
- **If `overwrite_existing` is true:** Replace symbol, footprint, and 3D model. Update SQLite record.
- **Never silently overwrite.** Always log the action.

### 7.2 Missing Files in Download

Not all providers include all three file types:

| Scenario | Behavior |
|----------|----------|
| Symbol only, no footprint | Import symbol, warn user. Set Footprint property to empty. |
| Footprint only, no symbol | Import footprint to `.pretty/` dir. Log warning. |
| No 3D model | Import symbol + footprint normally. Status shows "no 3D model". |
| Only `.bxl` file (Ultra Librarian binary) | Log error: "BXL format requires Ultra Librarian desktop tool for conversion. Please select KiCad as output format on the download page." |
| EasyEDA JSON format | Convert using `easyeda2kicad` Python package. If conversion fails, log error with details. |

### 7.3 Legacy KiCad Formats

Some providers still export old formats:
- `.lib` (legacy symbol) → Convert to `.kicad_sym` using kiutils
- `.mod` (legacy footprint) → Convert to `.kicad_mod` using kiutils
- `.wrl` only (no STEP) → Use `.wrl` as 3D model, note in metadata

### 7.4 Non-EDA Downloads

User might download datasheets, images, or other files while browsing. The pipeline should:
1. Check if file is a ZIP → if not, ignore (move to a `passthrough/` folder and let OS handle it)
2. If ZIP, check if it contains any KiCad-related files → if not, treat as passthrough
3. Only process ZIPs that contain recognizable EDA content

### 7.5 Network Errors

- Download interrupted → Electron `will-download` item emits 'done' with state='interrupted'. Log and notify user.
- Python sidecar crashes → Electron monitors child process. Restart automatically. Queue failed imports for retry.

---

## 8. File/Folder Structure (Project Repository)

```
kipartbridge/
├── package.json                    # Electron app config
├── electron-builder.yml            # Build/packaging config
├── src/
│   ├── main/
│   │   ├── main.js                 # Electron main process entry
│   │   ├── download-interceptor.js # Download capture logic
│   │   ├── python-bridge.js        # JSON-RPC communication with Python sidecar
│   │   ├── window-manager.js       # BrowserView/WebView setup
│   │   └── preload.js              # Context bridge for renderer IPC
│   ├── renderer/
│   │   ├── index.html
│   │   ├── App.jsx                 # Root React component
│   │   ├── components/
│   │   │   ├── Sidebar.jsx         # Quick links + recent imports
│   │   │   ├── StatusBar.jsx       # Import progress/status
│   │   │   ├── SettingsPanel.jsx   # Configuration UI
│   │   │   └── LibraryBrowser.jsx  # Search/filter imported components
│   │   └── styles/
│   │       └── tailwind.css
│   └── python/
│       ├── main.py                 # Sidecar entry point (JSON-RPC server on stdin/stdout)
│       ├── models.py               # ComponentFiles dataclass
│       ├── provider_classifier.py  # URL + content-based provider detection
│       ├── normalizer.py           # kiutils-based normalization
│       ├── library_injector.py     # KiCad library file management
│       ├── database.py             # SQLite operations
│       ├── extractors/
│       │   ├── __init__.py
│       │   ├── base.py             # BaseExtractor ABC
│       │   ├── ultra_librarian.py
│       │   ├── snapeda.py
│       │   ├── samacsys.py
│       │   ├── easyeda.py
│       │   └── generic.py
│       └── requirements.txt        # kiutils, easyeda2kicad
├── tests/
│   ├── fixtures/                   # Sample ZIPs from each provider
│   │   ├── ultra_librarian_stm32.zip
│   │   ├── snapeda_esp32.zip
│   │   ├── samacsys_lm358.zip
│   │   └── easyeda_ne555.zip
│   ├── test_classifier.py
│   ├── test_extractors.py
│   ├── test_normalizer.py
│   └── test_library_injector.py
└── README.md
```

---

## 9. Implementation Order (Build Phases)

### Phase 1: Python Pipeline (standalone CLI) — Week 1

Build and test the core processing pipeline independent of Electron. This is the highest-risk component and should be validated first.

**Deliverables:**
1. `models.py` — ComponentFiles dataclass
2. `provider_classifier.py` — classify by URL + ZIP contents  
3. `extractors/` — all 5 provider extractors (start with Ultra Librarian + SnapEDA)
4. `normalizer.py` — kiutils symbol + footprint normalization, 3D model path rewriting
5. `library_injector.py` — create/append to KiCad library files, manage lib tables
6. `database.py` — SQLite schema + CRUD
7. `main.py` — CLI mode for testing: `python main.py process /path/to/download.zip --source-url "..."`
8. Tests with real sample ZIPs from each provider

**Acceptance criteria:**
- Download a KiCad ZIP from DigiKey Ultra Librarian for STM32C071RBT6
- Run `python main.py process STM32C071RBT6.zip --source-url "https://digikey.com/..."`
- Open KiCad 8, verify symbol appears in library browser
- Verify footprint appears and has correct 3D model attached
- Verify 3D model renders in footprint editor

### Phase 2: Electron Shell + Download Interception — Week 2

**Deliverables:**
1. Electron app with embedded BrowserView
2. Navigation bar (back, forward, reload, URL input)
3. Download interception — all downloads routed to staging dir
4. Python sidecar spawned as child process with JSON-RPC on stdin/stdout
5. Basic status bar showing download/processing state

**Acceptance criteria:**
- Open app, navigate to DigiKey
- Click "Download KiCad" on any component
- File downloads silently to staging dir (no Save As dialog)
- Python processes it automatically
- Status bar confirms import

### Phase 3: UI Polish + Library Browser — Week 3

**Deliverables:**
1. Sidebar with quick links and recent imports list
2. Settings panel (library path, overwrite behavior, bookmarks)
3. Library browser: searchable table of all imported components with MPN, manufacturer, package, date
4. Right-click context menu on imported components: "Open in KiCad", "Delete", "Re-import"
5. Desktop notifications on import success/failure

### Phase 4: Advanced Features — Week 4+

**Deliverables:**
1. EasyEDA/JLCPCB conversion support
2. Batch import: drag-and-drop multiple ZIPs onto the app
3. Export library to a portable ZIP (for sharing with team)
4. Optional: HTTP API endpoint for Wormhole integration (GET /api/library/status, GET /api/library/components)
5. Auto-update via Electron updater

---

## 10. Dependencies

### Python (requirements.txt)

```
kiutils>=2.0.0          # KiCad file format parsing/writing
easyeda2kicad>=0.6.0    # EasyEDA JSON to KiCad conversion (optional, Phase 4)
```

### Node.js (package.json dependencies)

```json
{
  "dependencies": {
    "electron-store": "^8.0.0"
  },
  "devDependencies": {
    "electron": "^28.0.0",
    "electron-builder": "^24.0.0",
    "react": "^18.0.0",
    "react-dom": "^18.0.0",
    "tailwindcss": "^3.0.0",
    "@vitejs/plugin-react": "^4.0.0",
    "vite": "^5.0.0"
  }
}
```

---

## 11. KiCad File Format Quick Reference

### Symbol Library (.kicad_sym) — S-expression format

```
(kicad_symbol_lib
  (version 20231120)
  (generator "kipartbridge")
  (symbol "STM32C071RBT6"
    (property "Reference" "U" (at 0 0 0) (effects (font (size 1.27 1.27))))
    (property "Value" "STM32C071RBT6" (at 0 -2.54 0) (effects (font (size 1.27 1.27))))
    (property "Footprint" "kipartbridge:STM32C071RBT6" (at 0 0 0) (effects (hide yes)))
    (property "MPN" "STM32C071RBT6" (at 0 0 0) (effects (hide yes)))
    (symbol "STM32C071RBT6_0_1"
      ;; Graphics (rectangles, pins, etc.)
    )
  )
  ;; More symbols can follow...
)
```

### Footprint (.kicad_mod) — S-expression format

```
(footprint "STM32C071RBT6"
  (version 20231120)
  (generator "kipartbridge")
  (layer "F.Cu")
  ;; Pads, lines, text, etc.
  (model "${KIPARTBRIDGE_3DMODELS}/STM32C071RBT6.step"
    (offset (xyz 0 0 0))
    (scale (xyz 1 1 1))
    (rotate (xyz 0 0 0))
  )
)
```

### Library Tables (sym-lib-table / fp-lib-table)

```
(sym_lib_table
  (version 7)
  (lib (name "kipartbridge")(type "KiCad")(uri "/home/user/.kicad_libs/kipartbridge/kipartbridge.kicad_sym")(options "")(descr "KiPartBridge imports"))
)
```

---

## 12. Testing Strategy

### Unit Tests (Python)
- **Classifier tests:** Given URL + ZIP fixture → correct Provider enum
- **Extractor tests:** Given provider ZIP fixture → correct ComponentFiles with all paths populated
- **Normalizer tests:** Given ComponentFiles → valid KiCad 8 format output, parseable by kiutils
- **Library injector tests:** Append to empty lib, append to existing lib, duplicate handling, lib table updates

### Integration Tests
- End-to-end: ZIP file in → KiCad library files out → validate with kiutils
- Test with real downloads from each provider (committed as test fixtures)

### Manual Testing Checklist
- [ ] Import Ultra Librarian download from DigiKey → opens correctly in KiCad 8
- [ ] Import SnapEDA download → opens correctly in KiCad 8  
- [ ] Import SamacSys download from Component Search Engine → opens correctly
- [ ] Import same component twice → correct duplicate handling
- [ ] Import component with no 3D model → symbol + footprint work, warning shown
- [ ] Open KiCad after import → new component visible in library browser
- [ ] Place imported symbol → correct footprint auto-associated
- [ ] View imported footprint → 3D model renders correctly in 3D viewer
- [ ] Change library root path in settings → library tables updated correctly

---

## 13. Open Questions

1. **Multi-library support:** Should the app support multiple named libraries (e.g., one per project), or is a single global library sufficient for MVP?

2. **KiCad version compatibility:** Should we support KiCad 7 format alongside KiCad 8? KiCad 7 uses a slightly different s-expression format.

3. **Library locking:** KiCad may have the library file open. Need to test whether appending to `.kicad_sym` while KiCad is running causes issues. May need to implement file locking or prompt user to close KiCad.

4. **Footprint naming strategy:** Should footprints use MPN names (e.g., `STM32C071RBT6.kicad_mod`) or generic package names (e.g., `LQFP-64_10x10mm_P0.5mm.kicad_mod`)? MPN is unique but creates many similar footprints. Package name enables reuse but risks conflicts.

5. **JLCPCB/EasyEDA priority:** The `easyeda2kicad` tool is a separate dependency. Should Phase 1 include it or defer to Phase 4?
