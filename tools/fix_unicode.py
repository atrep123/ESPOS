#!/usr/bin/env python3
"""Fix Unicode symbols in test files for Windows console compatibility"""

import glob
import os

files_to_fix = glob.glob("test_ui*.py")

for fname in files_to_fix:
    if not os.path.exists(fname):
        continue

    try:
        with open(fname, "r", encoding="utf-8") as f:
            content = f.read()

        original = content
        content = content.replace("✓", "[OK]")
        content = content.replace("✅", "[PASS]")
        content = content.replace("✗", "[FAIL]")

        if content != original:
            with open(fname, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            print(f"Fixed: {fname}")
        else:
            print(f"No changes: {fname}")
    except Exception as e:
        print(f"Error {fname}: {e}")
