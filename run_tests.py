#!/usr/bin/env python3
"""
Pomocný skript pro spuštění testů ESP32OS projektu.
"""

import os
import subprocess
import sys


def run_tests():
    """Spustí základní Python testy pomocí pytest."""
    print("=" * 60)
    print("ESP32OS - Spouštění testů")
    print("=" * 60)
    
    # Ujisti se, že jsme ve správném adresáři
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Spusť pytest
    print("\n📦 Spouštím pytest...")
    result = subprocess.run([sys.executable, "-m", "pytest", "-q"], capture_output=False)
    
    if result.returncode == 0:
        print("\n✅ Všechny testy prošly úspěšně!")
    else:
        print("\n❌ Některé testy selhaly.")
        sys.exit(result.returncode)
    
    return result.returncode

if __name__ == "__main__":
    run_tests()
