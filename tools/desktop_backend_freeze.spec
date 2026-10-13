# PyInstaller spec, executed by its build runner (Analysis/PYZ/EXE/COLLECT).
# Build only with Windows x64 CPython 3.12, approved parser wheels and PyInstaller.
# One exact approved BUILD dependency site may supplement the builder interpreter.
# No installation, caller-selected root or runtime external source search here.
import importlib.util
import sys
from importlib.metadata import version
from pathlib import Path

if sys.platform != "win32" or sys.version_info[:2] != (3, 12) or sys.maxsize <= 2**32:
    raise RuntimeError("Build requires Windows x64 CPython 3.12")

ROOT = Path(SPECPATH).resolve().parent
build_pathex = [str(ROOT)]
APPROVED_BUILD_SITE = Path(
    r"C:\Sumilek-git\worker-patches\espos-mcp-runtime-20261003\.venv\Lib\site-packages"
)
# Optional convenience for this PC only. Portable release/CI builds install the
# hash-checked grammar wheels into their own builder; normal discovery skips it.
if any(importlib.util.find_spec(name) is None for name in ("tree_sitter", "tree_sitter_cpp")):
    if not APPROVED_BUILD_SITE.is_dir():
        raise RuntimeError("Approved build-time parser dependency site is unavailable")
    # These search paths are for the PyInstaller BUILD process and Analysis only.
    # No runtime hook or frozen sys.path entry points to this directory.
    sys.path.insert(0, str(APPROVED_BUILD_SITE))
    build_pathex.append(str(APPROVED_BUILD_SITE))

import tree_sitter._binding as tree_binding
import tree_sitter_cpp._binding as cpp_binding
from PyInstaller.utils.hooks import collect_data_files

if version("tree-sitter") != "0.26.0" or version("tree-sitter-cpp") != "0.23.4":
    raise RuntimeError("Build requires the declared pinned parser dependencies")

ENTRY = ROOT / "tools" / "desktop_backend_entry.py"
for source in (
    ENTRY,
    ROOT / "tools" / "__init__.py",
    ROOT / "tools" / "tabos_code_graph.py",
    ROOT / "tools" / "tabos_sdk_node_catalog.py",
):
    if not source.is_file():
        raise RuntimeError("Backend source package is incomplete")

# Explicit real native extensions, not a copied parser or Python substitute.
native_binaries = []
for extension, destination in ((tree_binding, "tree_sitter"), (cpp_binding, "tree_sitter_cpp")):
    binary = Path(extension.__file__).resolve()
    if not binary.is_file() or binary.suffix.lower() != ".pyd":
        raise RuntimeError("Required native parser extension is unavailable")
    native_binaries.append((str(binary), destination))

a = Analysis(
    [str(ENTRY)],
    pathex=build_pathex,
    binaries=native_binaries,
    datas=collect_data_files("tree_sitter_cpp", includes=["queries/*.scm"]),
    hiddenimports=[
        "tools.tabos_code_graph",
        "tools.tabos_sdk_node_catalog",
        "tree_sitter",
        "tree_sitter._binding",
        "tree_sitter_cpp",
        "tree_sitter_cpp._binding",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["pygame", "tkinter", "PyQt5", "PyQt6", "PySide2", "PySide6"],
    noarchive=False,
)
pyz = PYZ(a.pure)

# Onedir deliberately avoids the onefile extraction parent/child lifecycle.
# console=True preserves binary stdin/stdout; the owning process hides its
# console via CREATE_NO_WINDOW. --windowed would remove the required streams.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="espos_codegraph_backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    contents_directory="_internal",
)
bundle = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="espos_codegraph_backend")
