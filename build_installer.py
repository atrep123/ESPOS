# PyInstaller Build Script for ESP32OS UI Designer
# Creates standalone executable for Windows/macOS/Linux
#
# Build standalone executable for ESP32OS UI Designer
#
# Usage:
#     python build_installer.py
#
# Options:
#     --onefile       Create single executable (slower startup)
#     --windowed      Hide console window (GUI only)
#     --debug         Keep console for debugging

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


class InstallerBuilder:
    """Build standalone installer for ESP32OS UI Designer"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).absolute()
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        self.spec_file = self.project_root / "ui_designer.spec"
        
    def check_pyinstaller(self) -> bool:
        """Check if PyInstaller is installed"""
        if importlib.util.find_spec("PyInstaller") is None:
            print("❌ PyInstaller not installed")
            print("Install with: pip install pyinstaller")
            return False
        return True
    
    def create_spec_file(self, onefile: bool = False, windowed: bool = True, entry_script: str = "ui_designer_pro.py") -> str:
        """Create PyInstaller spec file"""
        exe_binaries = "a.binaries" if onefile else "[]"
        exe_zipfiles = "a.zipfiles" if onefile else "[]"
        exe_datas = "a.datas" if onefile else "[]"
        exclude_binaries = "False" if onefile else "True"
        collect_section = ""
        if not onefile:
            collect_section = """
# Collect mode (multiple files)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ESP32OS_UI_Designer",
)
"""

        spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Collect all data files
datas = [
    ('*.md', '.'),
    ('assets', 'assets'),
]

# Hidden imports
hiddenimports = [
    'PIL._tkinter_finder',
    'tkinter',
    'tkinter.ttk',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'tkinter.colorchooser',
    'websockets',
    'reportlab',
    'watchdog',
]

a = Analysis(
    ['{entry_script}'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'scipy', 'pandas'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    {exe_binaries},
    {exe_zipfiles},
    {exe_datas},
    [],
    exclude_binaries={exclude_binaries},
    name='ESP32OS_UI_Designer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console={'False' if windowed else 'True'},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,
)

{collect_section}
"""
        
        with open(self.spec_file, 'w') as f:
            f.write(spec_content)
        
        print(f"✅ Created spec file: {self.spec_file}")
        return str(self.spec_file)
    
    def build_executable(self, spec_file: str) -> bool:
        """Build executable using PyInstaller"""
        print("🔨 Building executable...")
        
        cmd = ["pyinstaller", "--clean", spec_file]
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(result.stdout)
            print("✅ Build successful!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Build failed: {e}")
            print(e.stderr)
            return False
    
    def create_readme(self):
        """Create README for distribution"""
        readme = """# ESP32OS UI Designer - Standalone Application

## Installation

### Windows
1. Extract ZIP archive
2. Run `ESP32OS_UI_Designer.exe`

### macOS
1. Extract ZIP archive
2. Run `ESP32OS_UI_Designer.app`
3. If macOS blocks it: Right-click → Open → Confirm

### Linux
1. Extract archive
2. Make executable: `chmod +x ESP32OS_UI_Designer`
3. Run: `./ESP32OS_UI_Designer`

## Features

- Visual UI designer for ESP32 displays
- Drag & drop widget placement
- Real-time preview
- Export to PNG, SVG, PDF, C code
- Animation designer
- Template library
- Icon manager
- Performance profiler

## Quick Start

1. Launch the application
2. Add widgets from the left palette
3. Position and resize widgets on canvas
4. Export your design

## Keyboard Shortcuts

- Ctrl+Z/Y: Undo/Redo
- Ctrl+C/V: Copy/Paste
- Ctrl+S: Save
- Delete: Delete widget
- Arrow keys: Nudge widget
- Ctrl+1-9: Quick add widgets
- Space+Drag: Pan canvas
- Ctrl+Wheel: Zoom

## Support

GitHub: https://github.com/atrep123/ESPOS
Issues: https://github.com/atrep123/ESPOS/issues

## License

See LICENSE file for details.
"""
        
        readme_path = self.dist_dir / "README.txt"
        with open(readme_path, 'w') as f:
            f.write(readme)
        
        print(f"✅ Created README: {readme_path}")
    
    def create_launcher_script(self):
        """Create launcher script for better error handling"""
        if sys.platform == "win32":
            launcher = """@echo off
echo Starting ESP32OS UI Designer...
ESP32OS_UI_Designer.exe
if errorlevel 1 (
    echo.
    echo Error: Application crashed
    echo Press any key to exit...
    pause >nul
)
"""
            launcher_path = self.dist_dir / "ESP32OS_UI_Designer" / "Launch.bat"
            with open(launcher_path, 'w') as f:
                f.write(launcher)
            print(f"✅ Created launcher: {launcher_path}")
        else:
            launcher = """#!/bin/bash
echo "Starting ESP32OS UI Designer..."
./ESP32OS_UI_Designer
if [ $? -ne 0 ]; then
    echo ""
    echo "Error: Application crashed"
    read -p "Press Enter to exit..."
fi
"""
            launcher_path = self.dist_dir / "ESP32OS_UI_Designer" / "launch.sh"
            with open(launcher_path, 'w') as f:
                f.write(launcher)
            os.chmod(launcher_path, 0o755)
            print(f"✅ Created launcher: {launcher_path}")
    
    def create_archive(self, archive_name: Optional[str] = None, suffix: str = "") -> Optional[str]:
        """Create distribution archive (ZIP/TAR.GZ)"""
        if archive_name is None:
            if sys.platform == "win32":
                archive_name = "ESP32OS_UI_Designer_Windows.zip"
            elif sys.platform == "darwin":
                archive_name = "ESP32OS_UI_Designer_macOS.zip"
            else:
                archive_name = "ESP32OS_UI_Designer_Linux.tar.gz"
        assert archive_name is not None
        if suffix:
            stem, ext = os.path.splitext(archive_name)
            archive_name = f"{stem}{suffix}{ext}"
        
        print(f"📦 Creating archive: {archive_name}")
        
        dist_folder = self.dist_dir / "ESP32OS_UI_Designer"
        if not dist_folder.exists():
            print(f"❌ Dist folder not found: {dist_folder}")
            return None
        
        archive_path = self.dist_dir / archive_name
        
        # Create archive
        if archive_name.endswith('.zip'):
            shutil.make_archive(
                str(archive_path.with_suffix('')),
                'zip',
                self.dist_dir,
                'ESP32OS_UI_Designer'
            )
        else:
            shutil.make_archive(
                str(archive_path.with_suffix('')),
                'gztar',
                self.dist_dir,
                'ESP32OS_UI_Designer'
            )
        
        print(f"✅ Archive created: {archive_path}")
        return str(archive_path)
    
    def clean_build_artifacts(self):
        """Clean build artifacts"""
        print("🧹 Cleaning build artifacts...")
        
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
            print(f"  Removed: {self.build_dir}")
        
        if self.spec_file.exists():
            os.remove(self.spec_file)
            print(f"  Removed: {self.spec_file}")
        
        # Remove __pycache__ directories
        for pycache in self.project_root.rglob("__pycache__"):
            shutil.rmtree(pycache)
        
        print("✅ Cleanup complete")
    
    def build_all(self, onefile: bool = False, windowed: bool = True, 
                  create_archive_flag: bool = True, entry_script: str = "ui_designer_pro.py",
                  archive_suffix: str = "") -> bool:
        """Complete build process"""
        print("=" * 60)
        print("ESP32OS UI Designer - Installer Builder")
        print("=" * 60)
        print()
        
        # Check PyInstaller
        if not self.check_pyinstaller():
            return False
        
        # Create spec file
        spec_file = self.create_spec_file(onefile=onefile, windowed=windowed, entry_script=entry_script)
        
        # Build executable
        if not self.build_executable(spec_file):
            return False
        
        # Create additional files
        self.create_readme()
        self.create_launcher_script()
        
        # Create archive
        if create_archive_flag:
            archive = self.create_archive(suffix=archive_suffix)
            if archive:
                print()
                print("=" * 60)
                print("✅ BUILD SUCCESSFUL!")
                print("=" * 60)
                print(f"Archive: {archive}")
                print(f"Size: {os.path.getsize(archive) / 1024 / 1024:.1f} MB")
        
        return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Build ESP32OS UI Designer installer")
    parser.add_argument("--onefile", action="store_true",
                       help="Create single executable (slower startup)")
    parser.add_argument("--windowed", action="store_true", default=True,
                       help="Hide console window (GUI only)")
    parser.add_argument("--debug", action="store_true",
                       help="Keep console for debugging")
    parser.add_argument("--no-archive", action="store_true",
                       help="Skip archive creation")
    parser.add_argument("--clean", action="store_true",
                       help="Clean build artifacts only")
    parser.add_argument("--entry", choices=["designer", "launcher"], default="designer",
                        help="Entry script to bundle (designer or unified launcher)")
    parser.add_argument("--archive-suffix", type=str, default="",
                        help="Optional suffix to append to archive filename (e.g., _Launcher)")
    
    args = parser.parse_args()
    
    builder = InstallerBuilder()
    
    if args.clean:
        builder.clean_build_artifacts()
        return 0
    
    windowed = args.windowed and not args.debug
    entry_script = "ui_designer_pro.py" if args.entry == "designer" else "tools/esp32os_launcher.py"
    
    success = builder.build_all(
        onefile=args.onefile,
        windowed=windowed,
        create_archive_flag=not args.no_archive,
        entry_script=entry_script,
        archive_suffix=args.archive_suffix,
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
