from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import patch

import jpype
import pytest

import scyjava
from scyjava._stubs import _cli

if TYPE_CHECKING:
    from pathlib import Path


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
