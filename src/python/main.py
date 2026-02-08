"""KiPartBridge Python sidecar — CLI and JSON-RPC server."""

import argparse
import json
import os
import shutil
import sys
import tempfile
import traceback

from models import Provider, ProcessingResult
from provider_classifier import classify
from extractors import get_extractor
from normalizer import sanitize_name, normalize_symbol, normalize_footprint, link_symbol_to_footprint, upgrade_symbol_lib
from library_injector import (
    get_default_library_root, detect_existing_library_root,
    ensure_library_dirs, ensure_library_tables, setup_environment_variable,
    get_kicad_config_dir,
)
from database import ComponentDB


LIB_NAME = "kipartbridge"


def process_download(zip_path: str, source_url: str | None = None,
                     referrer_url: str | None = None,
                     library_root: str | None = None,
                     overwrite: bool = False) -> ProcessingResult:
    """Process a downloaded ZIP through the full pipeline.

    Steps: classify -> extract -> normalize symbol -> normalize footprint ->
           link -> register lib tables -> setup env var -> insert DB -> cleanup
    """
    if library_root is None:
        # Use existing KiCad-registered path if available, else default
        library_root = detect_existing_library_root() or get_default_library_root()

    warnings = []
    extract_dir = tempfile.mkdtemp(prefix="kipartbridge_")

    try:
        # Ensure library structure exists
        ensure_library_dirs(library_root)

        sym_lib_path = os.path.join(library_root, f"{LIB_NAME}.kicad_sym")
        fp_dir = os.path.join(library_root, f"{LIB_NAME}.pretty")
        models_dir = os.path.join(library_root, "3dmodels")

        # 1. Classify provider
        provider = classify(zip_path, source_url, referrer_url)

        # 2. Extract
        extractor = get_extractor(provider)
        component = extractor.extract(zip_path, extract_dir, source_url, referrer_url)

        mpn = sanitize_name(component.mpn)

        # Check for existing component
        db_path = os.path.join(library_root, "components.db")
        db = ComponentDB(db_path)
        try:
            if db.component_exists(mpn) and not overwrite:
                warnings.append(f"Component {mpn} already exists, updating")

            # 3. Normalize symbol
            symbol_name = None
            if component.symbol_file:
                symbol_name = normalize_symbol(component, sym_lib_path)
            else:
                warnings.append("No symbol file found in download")

            # 4. Normalize footprint
            footprint_name = None
            if component.footprint_file:
                footprint_name = normalize_footprint(component, fp_dir, models_dir)
            else:
                warnings.append("No footprint file found in download")

            # 5. Link symbol to footprint
            if symbol_name and footprint_name:
                link_symbol_to_footprint(sym_lib_path, symbol_name, LIB_NAME, footprint_name)

            # 5b. Upgrade symbol lib to KiCad 9 format (must run AFTER all kiutils writes)
            if symbol_name:
                upgrade_symbol_lib(sym_lib_path)

            # 6. Register library tables
            ensure_library_tables(library_root)

            # 7. Setup environment variable
            setup_environment_variable(library_root)

            # 8. Insert into database
            has_3d = component.model_step is not None or component.model_wrl is not None
            comp_id = db.upsert_component(
                mpn=mpn,
                symbol_name=symbol_name,
                footprint_name=footprint_name,
                has_3d_model=has_3d,
                manufacturer=component.manufacturer,
                description=component.description,
                source_provider=provider.value if provider else None,
                source_url=source_url,
                referrer_url=referrer_url,
            )
            db.log_import(comp_id, "import", zip_path)

            if not has_3d:
                warnings.append("No 3D model found in download")

            status = "success" if symbol_name and footprint_name else "partial"
            return ProcessingResult(
                status=status,
                mpn=mpn,
                symbol_name=symbol_name,
                footprint_name=footprint_name,
                has_3d_model=has_3d,
                warnings=warnings,
            )
        finally:
            db.close()

    except Exception as e:
        return ProcessingResult(
            status="error",
            error=str(e),
            warnings=warnings,
        )
    finally:
        # Cleanup extract dir
        shutil.rmtree(extract_dir, ignore_errors=True)


# ── JSON-RPC Server ──────────────────────────────────────────────────────────

def _jsonrpc_response(id, result=None, error=None):
    resp = {"jsonrpc": "2.0", "id": id}
    if error is not None:
        resp["error"] = {"code": -32000, "message": str(error)}
    else:
        resp["result"] = result
    return resp


def handle_jsonrpc(request: dict) -> dict:
    """Handle a single JSON-RPC request."""
    req_id = request.get("id")
    method = request.get("method", "")
    params = request.get("params", {})

    try:
        if method == "ping":
            return _jsonrpc_response(req_id, "pong")

        elif method == "process_download":
            result = process_download(
                zip_path=params["filepath"],
                source_url=params.get("source_url"),
                referrer_url=params.get("referrer_url"),
                library_root=params.get("library_root"),
                overwrite=params.get("overwrite", False),
            )
            return _jsonrpc_response(req_id, {
                "status": result.status,
                "mpn": result.mpn,
                "symbol_name": result.symbol_name,
                "footprint_name": result.footprint_name,
                "has_3d_model": result.has_3d_model,
                "error": result.error,
                "warnings": result.warnings,
            })

        elif method == "list_components":
            root = params.get("library_root") or detect_existing_library_root() or get_default_library_root()
            db_path = os.path.join(root, "components.db")
            if not os.path.exists(db_path):
                return _jsonrpc_response(req_id, [])
            db = ComponentDB(db_path)
            try:
                components = db.list_components(
                    limit=params.get("limit", 100),
                    offset=params.get("offset", 0)
                )
                return _jsonrpc_response(req_id, components)
            finally:
                db.close()

        elif method == "search_components":
            root = params.get("library_root") or detect_existing_library_root() or get_default_library_root()
            db_path = os.path.join(root, "components.db")
            if not os.path.exists(db_path):
                return _jsonrpc_response(req_id, [])
            db = ComponentDB(db_path)
            try:
                components = db.search_components(params.get("query", ""))
                return _jsonrpc_response(req_id, components)
            finally:
                db.close()

        else:
            return _jsonrpc_response(req_id, error=f"Unknown method: {method}")

    except Exception as e:
        return _jsonrpc_response(req_id, error=str(e))


def serve():
    """Run JSON-RPC server on stdin/stdout."""
    print("KiPartBridge sidecar ready", file=sys.stderr, flush=True)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_jsonrpc(request)
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except json.JSONDecodeError as e:
            err = _jsonrpc_response(None, error=f"Invalid JSON: {e}")
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="KiPartBridge — KiCad library manager pipeline"
    )
    subparsers = parser.add_subparsers(dest="command")

    # process command
    proc = subparsers.add_parser("process", help="Process a downloaded ZIP file")
    proc.add_argument("zipfile", help="Path to the ZIP file")
    proc.add_argument("--source-url", help="Download source URL")
    proc.add_argument("--referrer-url", help="Referrer page URL")
    proc.add_argument("--library-root", help="Library root directory")
    proc.add_argument("--overwrite", action="store_true", help="Overwrite existing component")

    # serve command
    subparsers.add_parser("serve", help="Run JSON-RPC server on stdin/stdout")

    args = parser.parse_args()

    if args.command == "process":
        result = process_download(
            zip_path=args.zipfile,
            source_url=args.source_url,
            referrer_url=args.referrer_url,
            library_root=args.library_root,
            overwrite=args.overwrite,
        )
        print(f"Status: {result.status}")
        if result.mpn:
            print(f"MPN: {result.mpn}")
        if result.symbol_name:
            print(f"Symbol: {result.symbol_name}")
        if result.footprint_name:
            print(f"Footprint: {result.footprint_name}")
        print(f"3D Model: {'yes' if result.has_3d_model else 'no'}")
        if result.warnings:
            for w in result.warnings:
                print(f"Warning: {w}")
        if result.error:
            print(f"Error: {result.error}")
            sys.exit(1)

    elif args.command == "serve":
        serve()

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
