"""PlatformIO pre-build hook: regenerate the firmware theme header from the shared
single source tools/m5_theme.json before every build.

Guarantees firmware/din-rx/src/ui_theme_generated.h is always fresh and JSON-validated
even if the M5 Studio web tool was never opened. The generator is stdlib-only and
write-if-changed, so this is cheap. See tools/gen_firmware_theme.py.
"""

import os
import shlex
import subprocess
import sys

Import("env")  # noqa: F821  (SCons injects Import/env into extra_scripts)

_ROOT = os.path.abspath(os.path.join(env["PROJECT_DIR"], "..", ".."))  # noqa: F821
_GEN = os.path.join(_ROOT, "tools", "gen_firmware_theme.py")

_release_flags = os.environ.get("PROP_RELEASE_BUILD_FLAGS", "").strip()
if _release_flags:
    _parsed_release_flags = shlex.split(_release_flags)
    env.Append(BUILD_FLAGS=_parsed_release_flags)  # noqa: F821
    print(f"[gen_theme] applied {len(_parsed_release_flags)} PROP_RELEASE_BUILD_FLAGS")

print("[gen_theme] regenerating firmware theme headers from tools/m5_theme.json")
subprocess.run([sys.executable, _GEN], check=True)
