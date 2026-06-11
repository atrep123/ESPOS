"""PlatformIO pre-build hook: regenerate the firmware theme header from the shared
single source tools/m5_theme.json before every build.

Guarantees firmware/din-rx/src/ui_theme_generated.h is always fresh and JSON-validated
even if the M5 Studio web tool was never opened. The generator is stdlib-only and
write-if-changed, so this is cheap. See tools/gen_firmware_theme.py.
"""

import os
import subprocess
import sys

Import("env")  # noqa: F821  (SCons injects Import/env into extra_scripts)

_ROOT = os.path.abspath(os.path.join(env["PROJECT_DIR"], "..", ".."))  # noqa: F821
_GEN = os.path.join(_ROOT, "tools", "gen_firmware_theme.py")

print("[gen_theme] regenerating firmware theme headers from tools/m5_theme.json")
subprocess.run([sys.executable, _GEN], check=True)
