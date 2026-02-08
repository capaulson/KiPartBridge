"""Tests for the library injector module."""

import json
import os
import pytest

from library_injector import (
    ensure_library_dirs, ensure_sym_lib_table, ensure_fp_lib_table,
    ensure_library_tables, setup_environment_variable,
    detect_existing_library_root,
)


class TestEnsureLibraryDirs:
    def test_creates_dirs(self, tmp_path):
        root = str(tmp_path / "kipartbridge")
        ensure_library_dirs(root)
        assert os.path.isdir(root)
        assert os.path.isdir(os.path.join(root, "kipartbridge.pretty"))
        assert os.path.isdir(os.path.join(root, "3dmodels"))


class TestSymLibTable:
    def test_creates_new_table(self, tmp_path):
        root = str(tmp_path / "lib")
        config_dir = str(tmp_path / "config")
        os.makedirs(root)
        os.makedirs(config_dir)

        ensure_sym_lib_table(root, config_dir)

        table_path = os.path.join(config_dir, "sym-lib-table")
        assert os.path.exists(table_path)
        content = open(table_path).read()
        assert '(name "kipartbridge")' in content
        assert '(type "KiCad")' in content

    def test_appends_to_existing(self, tmp_path):
        root = str(tmp_path / "lib")
        config_dir = str(tmp_path / "config")
        os.makedirs(root)
        os.makedirs(config_dir)

        # Create pre-existing table
        table_path = os.path.join(config_dir, "sym-lib-table")
        with open(table_path, 'w') as f:
            f.write('(sym_lib_table\n  (lib (name "other")(type "KiCad")(uri "/other.kicad_sym")(options "")(descr ""))\n)\n')

        ensure_sym_lib_table(root, config_dir)

        content = open(table_path).read()
        assert '(name "other")' in content
        assert '(name "kipartbridge")' in content

    def test_idempotent(self, tmp_path):
        root = str(tmp_path / "lib")
        config_dir = str(tmp_path / "config")
        os.makedirs(root)
        os.makedirs(config_dir)

        ensure_sym_lib_table(root, config_dir)
        ensure_sym_lib_table(root, config_dir)

        content = open(os.path.join(config_dir, "sym-lib-table")).read()
        assert content.count('(name "kipartbridge")') == 1


class TestFpLibTable:
    def test_creates_new_table(self, tmp_path):
        root = str(tmp_path / "lib")
        config_dir = str(tmp_path / "config")
        os.makedirs(root)
        os.makedirs(config_dir)

        ensure_fp_lib_table(root, config_dir)

        table_path = os.path.join(config_dir, "fp-lib-table")
        assert os.path.exists(table_path)
        content = open(table_path).read()
        assert '(name "kipartbridge")' in content
        assert 'kipartbridge.pretty' in content


class TestDetectExistingLibraryRoot:
    def test_returns_none_when_no_table(self, tmp_path):
        config_dir = str(tmp_path / "config")
        os.makedirs(config_dir)
        assert detect_existing_library_root(config_dir) is None

    def test_returns_none_when_no_entry(self, tmp_path):
        config_dir = str(tmp_path / "config")
        os.makedirs(config_dir)
        with open(os.path.join(config_dir, "sym-lib-table"), 'w') as f:
            f.write('(sym_lib_table\n  (lib (name "other")(type "KiCad")(uri "/other.kicad_sym")(options "")(descr ""))\n)\n')
        assert detect_existing_library_root(config_dir) is None

    def test_returns_root_from_existing_entry(self, tmp_path):
        config_dir = str(tmp_path / "config")
        os.makedirs(config_dir)
        with open(os.path.join(config_dir, "sym-lib-table"), 'w') as f:
            f.write('(sym_lib_table\n  (lib (name "kipartbridge")(type "KiCad")(uri "/my/custom/path/kipartbridge.kicad_sym")(options "")(descr ""))\n)\n')
        assert detect_existing_library_root(config_dir) == "/my/custom/path"


class TestSymLibTableUriUpdate:
    def test_updates_uri_when_different(self, tmp_path):
        root_old = str(tmp_path / "old_lib")
        root_new = str(tmp_path / "new_lib")
        config_dir = str(tmp_path / "config")
        os.makedirs(root_old)
        os.makedirs(root_new)
        os.makedirs(config_dir)

        # Create table with old path
        ensure_sym_lib_table(root_old, config_dir)
        content = open(os.path.join(config_dir, "sym-lib-table")).read()
        assert str(root_old) in content

        # Update with new path
        ensure_sym_lib_table(root_new, config_dir)
        content = open(os.path.join(config_dir, "sym-lib-table")).read()
        assert str(root_new) in content
        assert str(root_old) not in content
        assert content.count('(name "kipartbridge")') == 1

    def test_fp_updates_uri_when_different(self, tmp_path):
        root_old = str(tmp_path / "old_lib")
        root_new = str(tmp_path / "new_lib")
        config_dir = str(tmp_path / "config")
        os.makedirs(root_old)
        os.makedirs(root_new)
        os.makedirs(config_dir)

        ensure_fp_lib_table(root_old, config_dir)
        content = open(os.path.join(config_dir, "fp-lib-table")).read()
        assert str(root_old) in content

        ensure_fp_lib_table(root_new, config_dir)
        content = open(os.path.join(config_dir, "fp-lib-table")).read()
        assert str(root_new) in content
        assert str(root_old) not in content


class TestSetupEnvironmentVariable:
    def test_creates_new_config(self, tmp_path):
        root = str(tmp_path / "lib")
        config_dir = str(tmp_path / "config")
        os.makedirs(root)
        os.makedirs(os.path.join(root, "3dmodels"))
        os.makedirs(config_dir)

        setup_environment_variable(root, config_dir)

        config_path = os.path.join(config_dir, "kicad_common.json")
        assert os.path.exists(config_path)
        config = json.load(open(config_path))
        assert config["environment"]["vars"]["KIPARTBRIDGE_3DMODELS"] == os.path.join(root, "3dmodels")

    def test_handles_null_vars(self, tmp_path):
        root = str(tmp_path / "lib")
        config_dir = str(tmp_path / "config")
        os.makedirs(root)
        os.makedirs(os.path.join(root, "3dmodels"))
        os.makedirs(config_dir)

        # Create config with null vars
        config_path = os.path.join(config_dir, "kicad_common.json")
        with open(config_path, 'w') as f:
            json.dump({"environment": {"vars": None}}, f)

        setup_environment_variable(root, config_dir)

        config = json.load(open(config_path))
        assert config["environment"]["vars"]["KIPARTBRIDGE_3DMODELS"] == os.path.join(root, "3dmodels")

    def test_preserves_existing_vars(self, tmp_path):
        root = str(tmp_path / "lib")
        config_dir = str(tmp_path / "config")
        os.makedirs(root)
        os.makedirs(os.path.join(root, "3dmodels"))
        os.makedirs(config_dir)

        config_path = os.path.join(config_dir, "kicad_common.json")
        with open(config_path, 'w') as f:
            json.dump({"environment": {"vars": {"EXISTING_VAR": "/some/path"}}}, f)

        setup_environment_variable(root, config_dir)

        config = json.load(open(config_path))
        assert config["environment"]["vars"]["EXISTING_VAR"] == "/some/path"
        assert "KIPARTBRIDGE_3DMODELS" in config["environment"]["vars"]
