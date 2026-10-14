"""Pure child-environment builder for the owned simulator process runner.

The caller must validate executable files and create/validate a private, owned
temporary directory (including symlink/reparse-point checks) before launching.
This module only validates lexical paths; it never inspects the filesystem or
inherits the parent environment, and does not launch processes or change cwd.
"""

from __future__ import annotations

import os
from pathlib import Path

_WINDOWS = os.name == "nt"
_SYSTEMROOT = "C:/Windows"
_WINDOWS_DEVICES = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"} | {
    f"{prefix}{number}" for prefix in ("COM", "LPT") for number in "123456789\u00b9\u00b2\u00b3"
}


def _validate_path(path: Path, label: str) -> None:
    if not isinstance(path, Path):
        raise TypeError(f"{label} must be a Path")
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{label} must be absolute without parent traversal")
    if path == Path(path.anchor):
        raise ValueError(f"{label} must not be a filesystem root")
    if _WINDOWS:
        if (
            len(path.drive) != 2
            or path.drive[1] != ":"
            or not path.drive[0].isascii()
            or not path.drive[0].isalpha()
        ):
            raise ValueError(f"{label} must be an ordinary local drive path")
    elif path.anchor != "/":
        raise ValueError(f"{label} must not be a UNC path")
    for part in path.parts[1:]:
        if any(ord(character) < 32 or ord(character) == 127 for character in part):
            raise ValueError(f"{label} contains a control character")
        if _WINDOWS:
            if (
                any(character in '<>:"|?*;' for character in part)
                or part.endswith((" ", "."))
                or part.split(".", 1)[0].rstrip(" ").upper() in _WINDOWS_DEVICES
            ):
                raise ValueError(f"{label} must be an ordinary Windows path")
        elif ":" in part:
            raise ValueError(f"{label} contains a PATH separator")


def build_environment(compiler: Path, python: Path, temporary: Path) -> dict[str, str]:
    """Return a fresh allowlisted environment using only explicit local paths.

    Paths use the current host's lexical flavour. Root directories, direct children
    of a root, shared system/temp directories and executable ancestors are not
    private temporary directories. Ownership and symlink safety belong to the caller.
    """
    for label, path in (("compiler", compiler), ("python", python), ("temporary", temporary)):
        _validate_path(path, label)

    system_dirs = (
        [Path("C:/Windows/System32"), Path(_SYSTEMROOT)]
        if _WINDOWS
        else [Path("/usr/bin"), Path("/bin")]
    )
    shared_temp_dirs = (
        [Path("C:/Windows/Temp")] if _WINDOWS else [Path("/var/tmp")]  # noqa: S108 -- forbidden broad temporary path, never used for output
    )
    if (
        len(temporary.parts) < 3
        or temporary in system_dirs + shared_temp_dirs
        or compiler.is_relative_to(temporary)
        or python.is_relative_to(temporary)
    ):
        raise ValueError("temporary must be a private directory, not a broad root directory")

    directories: list[Path] = []
    for directory in [compiler.parent, python.parent, *system_dirs]:
        if directory not in directories:
            directories.append(directory)
    environment = {
        "PATH": (";" if _WINDOWS else ":").join(map(str, directories)),
        "TEMP": str(temporary),
        "TMP": str(temporary),
        "PYTHONUTF8": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    if _WINDOWS:
        environment.update(SYSTEMROOT=_SYSTEMROOT, WINDIR=_SYSTEMROOT)
    return environment
