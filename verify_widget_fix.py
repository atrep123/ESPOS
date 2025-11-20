#!/usr/bin/env python3
"""
Verification script for widget operations fix.
Run this to confirm the fix is working correctly.
"""
import subprocess
import sys


def run_tests(test_files):
    """Run pytest on specified test files"""
    cmd = ["python", "-m", "pytest", "-v", "--tb=short"] + test_files
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout


def check_imports():
    """Verify critical modules can be imported"""
    try:
        import sim_run
        import ui_designer
        import web_sim_bridge
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def main():
    print("=" * 60)
    print("Widget Operations Fix - Verification Script")
    print("=" * 60)
    print()
    
    # Step 1: Check imports
    print("Step 1: Checking module imports...")
    if check_imports():
        print("✅ All critical modules import successfully")
    else:
        print("❌ Import check failed")
        return 1
    print()
    
    # Step 2: Run unit tests
    print("Step 2: Running unit tests...")
    test_files = [
        "test_bridge_widget_update.py",
        "test_widget_operations_e2e.py",
    ]
    
    success, output = run_tests(test_files)
    if success:
        print("✅ All unit tests passed")
    else:
        print("❌ Some tests failed:")
        print(output)
        return 1
    print()
    
    # Step 3: Summary
    print("=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    print("✅ Module imports: OK")
    print("✅ Unit tests: OK")
    print("✅ Widget operations fix: VERIFIED")
    print()
    print("The following operations are now working:")
    print("  • widget_add    - Creates widgets in simulator")
    print("  • widget_update - Updates positions (drag & drop)")
    print("  • widget_delete - Removes widgets from simulator")
    print()
    print("Modified files:")
    print("  • sim_run.py (lines 1039-1065)")
    print("  • test_bridge_widget_update.py (new)")
    print("  • test_widget_operations_e2e.py (new)")
    print()
    print("Documentation:")
    print("  • DRAG_DROP_FIX.md")
    print("  • WIDGET_OPERATIONS_GUIDE.md")
    print()
    print("=" * 60)
    print("✅ ALL CHECKS PASSED - FIX IS PRODUCTION READY")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
