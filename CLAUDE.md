# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**KiPartBridge** is a desktop application (Electron + Python sidecar) that embeds a browser for component supplier sites (DigiKey, Mouser, LCSC, SnapEDA, SamacSys), intercepts EDA model downloads, and automatically processes and injects them into a unified KiCad 8 library. The goal is to eliminate the manual unzip-copy-rename workflow for getting component models into KiCad.

## Architecture

### Two-Process Design

1. **Electron (Node.js)** — Desktop shell with embedded Chromium WebView for browsing supplier sites. Intercepts downloads via `session.on('will-download')`, routes files to a staging directory, and communicates with the Python sidecar over stdin/stdout JSON-RPC.

2. **Python Sidecar** — Long-running subprocess that handles all KiCad file processing. Uses `kiutils` for parsing/writing KiCad S-expression files. Pipeline stages:
   - **Provider Classifier** — Identifies download source (Ultra Librarian, SnapEDA, SamacSys, EasyEDA, Generic) by URL pattern first, then ZIP content analysis as fallback.
   - **Provider Extractors** — Each provider has its own extractor (they structure ZIPs differently) that returns a standardized `ComponentFiles` dataclass.
   - **Normalizer** — Converts all files to KiCad 8 format, standardizes naming to MPN, rewrites 3D model paths to use `${KIPARTBRIDGE_3DMODELS}` env var.
   - **Library Injector** — Appends symbols to a single `kipartbridge.kicad_sym`, copies footprints to `kipartbridge.pretty/`, copies 3D models to `3dmodels/`, and manages KiCad's `sym-lib-table`/`fp-lib-table`.
   - **SQLite DB** — Tracks imported components by MPN (unique), source provider, timestamps.

### Data Flow

Download ZIP → staging dir → classify provider → extract per provider format → normalize (kiutils) → inject into KiCad library → record in SQLite → cleanup staging files.

### On-Disk Library Structure

```
{library_root}/
├── kipartbridge.kicad_sym          # All symbols in one file
├── kipartbridge.pretty/            # Directory of .kicad_mod footprints
└── 3dmodels/                       # .step and .wrl files
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Desktop | Electron 28+, Vite 5, React 18, Tailwind CSS 3 |
| Backend | Python 3, kiutils >=2.0, easyeda2kicad >=0.6 (Phase 4) |
| Database | SQLite |
| IPC | JSON-RPC over stdin/stdout |
| Packaging | electron-builder |

## Build & Development Commands

```bash
# Node.js / Electron
npm install
npm start                    # Run Electron app in dev mode
npm run build                # Package with electron-builder

# Python sidecar
pip install -r src/python/requirements.txt
python src/python/main.py process /path/to/download.zip --source-url "https://..."   # CLI test mode

# Tests (Python)
pytest tests/
pytest tests/test_classifier.py           # Single test file
pytest tests/test_classifier.py -k "test_name"  # Single test
```

## Key Design Decisions

- **Single library file for symbols**: All symbols go into one `kipartbridge.kicad_sym` rather than per-component files. Footprints are individual `.kicad_mod` files in a `.pretty/` directory (KiCad convention).
- **MPN as primary key**: Components are deduplicated by Manufacturer Part Number. Symbol and footprint files are named by MPN (sanitized: `/ \ : * ? " < > |` replaced with `_`).
- **3D model paths use env var**: Footprints reference 3D models via `${KIPARTBRIDGE_3DMODELS}/filename.step` for portability. The env var is registered in KiCad's `kicad_common.json`.
- **Non-EDA downloads pass through**: Only ZIPs containing recognizable KiCad files are processed. Datasheets, images, etc. are routed to a `passthrough/` folder.
- **Provider classification is two-tier**: URL pattern matching first (high confidence), ZIP content scanning as fallback.

## Provider-Specific Notes

Each provider structures downloads differently. When adding/modifying extractors in `src/python/extractors/`:

- **Ultra Librarian** (DigiKey): `KiCad/` subfolder, sometimes `.bxl` files (binary, cannot convert — must prompt user to select KiCad format)
- **SnapEDA**: Root-level `.kicad_sym`, `.kicad_mod`, `.step` files
- **SamacSys** (Component Search Engine, Mouser): `KiCad/symbol/`, `KiCad/footprint/`, `KiCad/3dmodel/` subfolders
- **EasyEDA/JLCPCB**: JSON format, requires `easyeda2kicad` conversion

## KiCad Config Paths

The app reads/writes KiCad's global config for library table registration:

| Platform | Path |
|----------|------|
| macOS | `~/Library/Preferences/kicad/8.0/` |
| Linux | `~/.config/kicad/8.0/` |
| Windows | `%APPDATA%/kicad/8.0/` |

## Implementation Phases

1. **Phase 1**: Python pipeline as standalone CLI (extractors, normalizer, injector, SQLite, tests with real ZIPs)
2. **Phase 2**: Electron shell + download interception + Python sidecar IPC
3. **Phase 3**: UI polish (sidebar, settings, library browser, notifications)
4. **Phase 4**: EasyEDA conversion, batch import, export, auto-update
