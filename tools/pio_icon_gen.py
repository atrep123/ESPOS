import subprocess
from pathlib import Path
import hashlib

from SCons.Script import DefaultEnvironment

env = DefaultEnvironment()
project_dir = Path(env["PROJECT_DIR"])

SVG_DIR = project_dir / "assets" / "icons" / "material" / "filled"
OUT_C = project_dir / "src" / "icons.c"
OUT_H = project_dir / "src" / "icons.h"
STAMP = project_dir / "src" / "icons.sha"
PIPELINE = project_dir / "tools" / "icon_pipeline.py"
SIZE_PX = 16


def _stamp_for_inputs(files) -> str:
    h = hashlib.sha256()
    h.update(str(SIZE_PX).encode("utf-8"))
    h.update(str(PIPELINE.stat().st_mtime_ns if PIPELINE.exists() else 0).encode("utf-8"))
    for p in sorted(files):
        st = p.stat()
        h.update(p.name.encode("utf-8"))
        h.update(str(st.st_size).encode("utf-8"))
        h.update(str(st.st_mtime_ns).encode("utf-8"))
    return h.hexdigest()


def _targets_fresh(svg_dir: Path, out_c: Path, out_h: Path) -> bool:
    if not out_c.exists() or not out_h.exists():
        return False
    svgs = list(svg_dir.glob("*.svg")) + list(svg_dir.glob("*.png"))
    if not svgs:
        return True
    latest_src = max(p.stat().st_mtime for p in svgs)
    oldest_tgt = min(out_c.stat().st_mtime, out_h.stat().st_mtime)
    return oldest_tgt >= latest_src and out_c.stat().st_size > 32 and out_h.stat().st_size > 32


def _ensure_icons():
    if not PIPELINE.exists():
        return
    if not SVG_DIR.exists():
        print("[icon-gen] skip (no icons dir)")
        return

    inputs = list(sorted(SVG_DIR.glob("*.svg"))) + list(sorted(SVG_DIR.glob("*.png")))
    if not inputs:
        print("[icon-gen] skip (no icon files)")
        env.Append(CPPDEFINES=["HAVE_ICONS=0"])
        return

    stamp_new = _stamp_for_inputs(inputs)
    stamp_old = STAMP.read_text(encoding="utf-8").strip() if STAMP.exists() else ""
    if _targets_fresh(SVG_DIR, OUT_C, OUT_H) and stamp_new == stamp_old:
        env.Append(CPPDEFINES=["HAVE_ICONS=1"])
        print("[icon-gen] cached (HAVE_ICONS=1)")
        return

    cmd = [
        env.subst("$PYTHON"),
        str(PIPELINE),
        "--src",
        str(SVG_DIR),
        "--size",
        str(SIZE_PX),
        "--out-c",
        str(OUT_C),
        "--out-h",
        str(OUT_H),
    ]
    try:
        res = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except FileNotFoundError:
        print("[icon-gen] Python not found; skipping icon generation")
        env.Append(CPPDEFINES=["HAVE_ICONS=0"])
        return

    if res.returncode != 0:
        msg = res.stderr.strip() or res.stdout.strip() or "err"
        print(f"[icon-gen] failed ({msg})")
        env.Append(CPPDEFINES=["HAVE_ICONS=0"])
        return

    if _targets_fresh(SVG_DIR, OUT_C, OUT_H):
        STAMP.write_text(stamp_new, encoding="utf-8")
        env.Append(CPPDEFINES=["HAVE_ICONS=1"])
        print("[icon-gen] generated (HAVE_ICONS=1)")
    else:
        env.Append(CPPDEFINES=["HAVE_ICONS=0"])
        print("[icon-gen] generated but targets stale (HAVE_ICONS=0)")


_ensure_icons()
