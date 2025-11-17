#!/usr/bin/env python3
"""
Pomocný skript pro spuštění konkrétního selhávajícího testu.
"""

import os
import subprocess
import sys


def run_failing_test():
    """Spustí konkrétní selhávající test s podrobným výstupem."""
    print("=" * 60)
    print("Spouštění selhávajícího testu")
    print("=" * 60)
    
    # Ujisti se, že jsme ve správném adresáři
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Spusť konkrétní test s verbose výstupem
    print("\n📦 Spouštím test_keyboard_shortcuts.py::test_quick_insert_basic")
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "test_keyboard_shortcuts.py::test_quick_insert_basic",
        "-vvs",  # velmi podrobný výstup + zobraz print statements
        "--tb=short"  # kratší traceback
    ], capture_output=False)
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(run_failing_test())
