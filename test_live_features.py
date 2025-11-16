#!/usr/bin/env python3
"""
Quick test for live preview and C export features
"""
import subprocess
import sys
import time
from pathlib import Path

def test_c_export():
    """Test C header export"""
    print("\n=== Testing C Header Export ===")
    
    test_json = Path("examples/demo_scene.json")
    test_h = Path("examples/test_export.h")
    
    if not test_json.exists():
        print(f"❌ Test JSON not found: {test_json}")
        return False
    
    # Run export
    cmd = [
        sys.executable,
        "ui_export_c_header.py",
        str(test_json),
        "-o", str(test_h)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Export failed: {result.stderr}")
        return False
    
    print(result.stdout)
    
    # Verify output
    if not test_h.exists():
        print(f"❌ Output header not created: {test_h}")
        return False
    
    content = test_h.read_text()
    
    # Check for expected patterns
    checks = [
        "ui_widget_t",
        "ui_scene_t",
        "UI_WIDGET_",
        "#ifndef",
        "#define",
        "#endif"
    ]
    
    for pattern in checks:
        if pattern not in content:
            print(f"❌ Missing expected pattern: {pattern}")
            return False
    
    print(f"✓ C header export successful: {test_h}")
    print(f"  Size: {len(content)} bytes")
    
    # Cleanup
    test_h.unlink()
    
    return True


def test_live_preview_startup():
    """Test live preview server startup (without browser)"""
    print("\n=== Testing Live Preview Startup ===")
    
    test_json = Path("examples/demo_scene.json")
    
    if not test_json.exists():
        print(f"❌ Test JSON not found: {test_json}")
        return False
    
    # Start server in background
    cmd = [
        sys.executable,
        "ui_designer_live.py",
        "--json", str(test_json),
        "--no-browser"
    ]
    
    print("Starting live preview server (will terminate after 3 seconds)...")
    
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Let it run briefly
    time.sleep(3)
    
    # Terminate
    proc.terminate()
    stdout, stderr = proc.communicate(timeout=2)
    
    # Check output
    if "WebSocket server running" in stdout or "WebSocket server running" in stderr:
        print("✓ Live preview server started successfully")
        print(f"  Output preview:\n{stdout[:200]}")
        return True
    else:
        print(f"❌ Server startup issue")
        print(f"  stdout: {stdout[:200]}")
        print(f"  stderr: {stderr[:200]}")
        return False


def main():
    print("╔════════════════════════════════════════╗")
    print("║ Live Preview & C Export Feature Test  ║")
    print("╚════════════════════════════════════════╝")
    
    results = []
    
    # Test C export
    results.append(("C Header Export", test_c_export()))
    
    # Test live preview
    results.append(("Live Preview Startup", test_live_preview_startup()))
    
    # Summary
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
