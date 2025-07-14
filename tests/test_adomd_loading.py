import os
import sys
import importlib
from unittest.mock import MagicMock


def test_adomd_additional_references(monkeypatch, tmp_path):
    monkeypatch.setenv("ADOMD_LIB_DIR", str(tmp_path))
    monkeypatch.syspath_prepend(os.path.join(os.path.dirname(__file__), '..', 'src'))

    class DummyPythonnet:
        def set_runtime(self, runtime):
            pass
    monkeypatch.setitem(sys.modules, "pythonnet", DummyPythonnet())
    monkeypatch.setitem(sys.modules, "pyadomd", MagicMock())

    add_refs = []

    clr_mock = MagicMock()
    clr_mock.AddReference.side_effect = lambda dll: add_refs.append(dll)
    monkeypatch.setitem(sys.modules, "clr", clr_mock)

    orig_exists = os.path.exists
    monkeypatch.setattr(os.path, "exists", lambda p: True if p == str(tmp_path) else orig_exists(p))

    orig_server = sys.modules.pop("server", None)
    server = importlib.import_module("server")
    expected = [
        str(tmp_path / "Microsoft.AnalysisServices.Platform.Core.dll"),
        str(tmp_path / "Microsoft.AnalysisServices.Platform.Windows.dll"),
        str(tmp_path / "Microsoft.AnalysisServices.AdomdClient.dll"),
    ]
    try:
        assert server.adomd_loaded is True
        assert add_refs == expected
    finally:
        if orig_server is not None:
            sys.modules["server"] = orig_server
        else:
            sys.modules.pop("server", None)
