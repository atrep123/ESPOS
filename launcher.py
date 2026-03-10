#!/usr/bin/env python3
"""ESP32 OS - Quick Launcher for the Pygame UI Designer."""

from __future__ import annotations

import argparse
import subprocess
import sys


def print_menu() -> None:
    print("\n" + "=" * 50)
    print("  ESP32 OS UI TOOLKIT")
    print("=" * 50)
    print("\n  Available apps:\n")
    print("  1. UI Designer (Pygame)  - Visual editor")
    print("\n  0. Exit")
    print("\n" + "=" * 50)


def run_designer() -> None:
    """Launch UI Designer (non-blocking)."""
    print("\n>> Launching UI Designer (Pygame)...")
    subprocess.Popen([sys.executable, "run_designer.py"])


def main() -> None:
    """Main menu loop."""
    while True:
        print_menu()
        try:
            choice = input("\nChoose (0-1): ").strip()
            if choice == "1":
                run_designer()
            elif choice == "0":
                print("\n<< Bye.")
                break
            else:
                print("\nInvalid choice. Enter 0 or 1.")
        except KeyboardInterrupt:
            print("\n\n<< Interrupted by user.")
            break
        except Exception as exc:  # pragma: no cover - defensive
            print(f"\nError: {exc}")


if __name__ == "__main__":
    argparse.ArgumentParser(
        description="ESP32 OS Quick Launcher — interactive menu for the Pygame UI Designer"
    ).parse_args()
    main()
