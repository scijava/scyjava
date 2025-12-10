from __future__ import annotations

import ast
import sys
from pathlib import Path
from unittest.mock import patch

import jpype
import pytest

import scyjava
from scyjava._stubs import _cli


@pytest.mark.skipif(
    scyjava.config.mode != scyjava.config.Mode.JPYPE,
    reason="Stubgen not supported in JEP",
)
def test_stubgen(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # run the stubgen command as if it was run from the command line
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scyjava-stubgen",
            "org.scijava:parsington:3.1.0",
            "--output-dir",
            str(tmp_path),
        ],
    )
    _cli.main()

    # remove the `jpype.imports` magic from the import system if present
    mp = [x for x in sys.meta_path if not isinstance(x, jpype.imports._JImportLoader)]
    monkeypatch.setattr(sys, "meta_path", mp)

    # add tmp_path to the import path
    monkeypatch.setattr(sys, "path", [str(tmp_path)])

    # first cleanup to make sure we are not importing from the cache
    sys.modules.pop("org", None)
    sys.modules.pop("org.scijava", None)
    sys.modules.pop("org.scijava.parsington", None)
    # make sure the stubgen command works and that we can now impmort stuff

    with patch.object(scyjava._jvm, "start_jvm") as mock_start_jvm:
        from org.scijava.parsington import Function

        assert Function is not None
        # ensure that no calls to start_jvm were made
        mock_start_jvm.assert_not_called()

        # only after instantiating the class should we have a call to start_jvm
        func = Function(1)
        mock_start_jvm.assert_called_once()
        assert isinstance(func, jpype.JObject)


@pytest.mark.skipif(
    scyjava.config.mode != scyjava.config.Mode.JPYPE,
    reason="Stubgen not supported in JEP",
)
def test_stubgen_type_references(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test that generated stubs have properly qualified type references.

    This validates that when stubs are generated with a Python package prefix,
    all type references are properly rewritten so type checkers can resolve them.
    """
    import tempfile

    # Generate stubs with --output-python-path so a prefix is used
    # (rather than --output-dir which doesn't imply a Python module path)
    stubs_module = "test_stubs"

    # Create a temporary directory and add it to sys.path
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        original_path = sys.path.copy()

        try:
            sys.path.insert(0, str(tmpdir))

            # Create the parent module package
            stubs_pkg = tmpdir / stubs_module
            stubs_pkg.mkdir()
            (stubs_pkg / "__init__.py").touch()

            monkeypatch.setattr(
                sys,
                "argv",
                [
                    "scyjava-stubgen",
                    "org.scijava:parsington:3.1.0",
                    "--output-python-path",
                    stubs_module,
                ],
            )
            _cli.main()

            # Check that import statements were rewritten with the prefix
            init_stub = stubs_pkg / "org" / "scijava" / "parsington" / "__init__.pyi"
            assert init_stub.exists(), f"Expected stub file {init_stub} not found"

            content = init_stub.read_text()
            stub_ast = ast.parse(content)

            # Find all Import and ImportFrom nodes
            imports = [
                node
                for node in ast.walk(stub_ast)
                if isinstance(node, (ast.Import, ast.ImportFrom))
            ]

            # Collect imported module names
            imported_modules = set()
            for imp in imports:
                if isinstance(imp, ast.Import):
                    for alias in imp.names:
                        imported_modules.add(alias.name)
                elif isinstance(imp, ast.ImportFrom) and imp.module:
                    imported_modules.add(imp.module)

            # Verify that bare org.scijava.* imports don't exist (they should be prefixed)
            org_imports = {
                m for m in imported_modules if m and m.startswith("org.scijava.")
            }
            assert not org_imports, (
                f"Found unrewritten org.scijava imports in {init_stub}: {org_imports}. "
                f"These should have been prefixed with '{stubs_module}.'"
            )
        finally:
            sys.path = original_path
