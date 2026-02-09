# KiPartBridge

A desktop app that embeds a browser for component supplier sites (DigiKey, Mouser, LCSC, SnapEDA, SamacSys), intercepts EDA model downloads, and automatically imports them into a unified KiCad library. No more unzip-copy-rename workflows.

## How It Works

1. Browse supplier sites inside the app
2. Click "Download" on any KiCad model — the app intercepts it
3. The Python backend classifies the provider, extracts files, normalizes everything to KiCad 8 format, and injects it into your library
4. Open KiCad — your component is ready to use

Supported providers: Ultra Librarian (DigiKey), SnapEDA, SamacSys (Mouser, Component Search Engine), EasyEDA/JLCPCB.

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+

### Setup

```bash
# Clone
git clone https://github.com/capaulson/KiPartBridge.git
cd KiPartBridge

# Python dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r src/python/requirements.txt

# Node dependencies
npm install

# Run
npm start
```

### Build Standalone App (macOS)

```bash
npm run build
open out/mac-arm64/KiPartBridge.app
```

This produces a self-contained `.app` and `.dmg` in `out/` — no Python or Node.js required on the target machine.

## KiCad Setup

KiPartBridge automatically configures KiCad on first use:

- **Library tables** — Registers `kipartbridge` in KiCad's global `sym-lib-table` and `fp-lib-table`
- **3D models** — Sets the `KIPARTBRIDGE_3DMODELS` environment variable in `kicad_common.json` so footprints can find their STEP/WRL files

The default library location is `~/kicad_libs/kipartbridge/`.

### Verifying in KiCad

After importing your first component:

1. Open KiCad and go to **Preferences > Manage Symbol Libraries**
2. You should see a `kipartbridge` entry in the Global Libraries tab
3. Do the same for **Preferences > Manage Footprint Libraries**
4. In the schematic editor, click **Add Symbol** and search for your part's MPN — it will appear under the `kipartbridge` library

### Library Structure on Disk

```
~/kicad_libs/kipartbridge/
├── kipartbridge.kicad_sym      # All symbols (single file)
├── kipartbridge.pretty/        # Footprint .kicad_mod files
└── 3dmodels/                   # .step and .wrl files
```

## Running Tests

```bash
PYTHONPATH=src/python pytest tests/ -v
```

## License

MIT
