"""Run the same mandatory UI boundary outside SCons (direct IDF/CMake)."""

import runpy
import sys
from pathlib import Path


def main():
    project = Path(sys.argv[1]).resolve()
    runpy.run_path(
        str(project / "scripts/pio_generate_ui_design.py"),
        init_globals={"env": {"PROJECT_DIR": str(project)}, "Import": lambda _: None},
    )


if __name__ == "__main__":
    main()
