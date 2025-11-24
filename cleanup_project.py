#!/usr/bin/env python3
"""
Cleanup script - Move test files to test/ folder and remove demos
"""

import shutil
from pathlib import Path


def cleanup_project():
    """Organize project structure"""
    root = Path(__file__).parent

    print("🧹 Čistím projekt...")

    # Ensure test/ directory exists
    test_dir = root / "test"
    test_dir.mkdir(exist_ok=True)

    # Move test files from root to test/
    test_files = list(root.glob("test_*.py"))
    moved = 0

    for test_file in test_files:
        target = test_dir / test_file.name
        if not target.exists():
            try:
                shutil.move(str(test_file), str(target))
                moved += 1
                print(f"  ✓ Přesunuto: {test_file.name}")
            except Exception as e:
                print(f"  ✗ Chyba při přesunu {test_file.name}: {e}")

    print(f"\n✅ Přesunuto {moved} testovacích souborů do test/")

    # Move test artifacts (json, html, png from tests)
    artifacts = []
    for pattern in ["test_*.json", "test_*.html", "test_*.png", "test_*.txt"]:
        artifacts.extend(root.glob(pattern))

    moved_artifacts = 0
    for artifact in artifacts:
        target = test_dir / artifact.name
        if not target.exists():
            try:
                shutil.move(str(artifact), str(target))
                moved_artifacts += 1
            except:
                pass

    if moved_artifacts > 0:
        print(f"✅ Přesunuto {moved_artifacts} testovacích artefaktů")

    # List demo files in examples/
    examples_dir = root / "examples"
    if examples_dir.exists():
        demos = list(examples_dir.glob("demo_*.py"))
        if demos:
            print(f"\n📁 Nalezeno {len(demos)} demo souborů v examples/:")
            for demo in demos:
                print(f"  • {demo.name}")
            print("  (Ponechány pro referenci, můžeš je smazat pokud nechceš)")

    print("\n✨ Hotovo! Projekt je čistší.")
    print("\n💡 Další kroky:")
    print("  1. Spusť: python esp32os_workspace.py")
    print("  2. Vytvoř nový projekt nebo otevři existující")
    print("  3. Klikni na '🔗 Oba' pro Designer + Simulátor")


if __name__ == "__main__":
    cleanup_project()
