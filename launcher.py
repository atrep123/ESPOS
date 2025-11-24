#!/usr/bin/env python3
"""
ESP32 OS - Quick Launcher
Spouštěč pro 3 hlavní aplikace
"""
import subprocess
import sys


def print_menu():
    print("\n" + "="*50)
    print("  ESP32 OS UI TOOLKIT")
    print("="*50)
    print("\n📱 Hlavní aplikace:\n")
    print("  1. 🎨 UI Designer     - Vizuální editor (drag & drop)")
    print("  2. 📺 Simulator       - Vizuální display okno")
    print("  3. 🏢 Workspace       - Unified launcher (oboje)")
    print("\n  0. ❌ Ukončit")
    print("\n" + "="*50)

def run_designer():
    """Spustí UI Designer (non-blocking)"""
    print("\n🎨 Spouštím UI Designer...")
    subprocess.Popen([sys.executable, "run_designer.py"])

def run_simulator():
    """Spustí Simulator GUI (non-blocking)"""
    print("\n📺 Spouštím Simulator...")
    subprocess.Popen([sys.executable, "run_simulator_gui.py"])

def run_workspace():
    """Spustí Workspace (non-blocking)"""
    print("\n🏢 Spouštím Workspace...")
    subprocess.Popen([sys.executable, "esp32os_workspace.py"])

def main():
    """Main menu loop"""
    while True:
        print_menu()
        
        try:
            choice = input("\nVyber možnost (0-3): ").strip()
            
            if choice == "1":
                run_designer()
            elif choice == "2":
                run_simulator()
            elif choice == "3":
                run_workspace()
            elif choice == "0":
                print("\n👋 Ukončuji...")
                break
            else:
                print("\n❌ Neplatná volba! Zadej číslo 0-3.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Ukončeno uživatelem.")
            break
        except Exception as e:
            print(f"\n❌ Chyba: {e}")

if __name__ == "__main__":
    main()
