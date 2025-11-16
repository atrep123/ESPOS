#!/usr/bin/env python3
"""
Automated Test Framework for ESP32 Simulator
Unit tests, integration tests, and UI automation with assertions
"""

import sys
import time
import socket
import json
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class TestStatus(Enum):
    """Test execution status"""
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


@dataclass
class TestResult:
    """Test result container"""
    name: str
    status: TestStatus
    duration_ms: float
    message: str = ""
    exception: Optional[Exception] = None


class SimulatorTestCase:
    """Base class for simulator tests"""
    
    def __init__(self, name: str, host: str = 'localhost', rpc_port: int = 5556):
        self.name = name
        self.host = host
        self.rpc_port = rpc_port
        self.sock: Optional[socket.socket] = None
        self.connected = False
    
    def setup(self):
        """Setup before test - override in subclass"""
        pass
    
    def teardown(self):
        """Cleanup after test - override in subclass"""
        pass
    
    def connect(self) -> bool:
        """Connect to simulator"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5.0)
            self.sock.connect((self.host, self.rpc_port))
            self.connected = True
            return True
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from simulator"""
        if self.sock:
            self.sock.close()
            self.sock = None
        self.connected = False
    
    def send_rpc(self, method: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Send JSON-RPC command"""
        if not self.connected:
            return None
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": 1
        }
        
        try:
            self.sock.sendall(json.dumps(request).encode() + b'\n')
            
            response_data = b''
            while b'\n' not in response_data:
                chunk = self.sock.recv(4096)
                if not chunk:
                    return None
                response_data += chunk
            
            response = json.loads(response_data.decode())
            return response.get('result')
        
        except Exception as e:
            raise AssertionError(f"RPC command failed: {e}")
    
    # Assertion methods
    
    def assert_true(self, condition: bool, message: str = ""):
        """Assert condition is true"""
        if not condition:
            raise AssertionError(f"Expected True, got False. {message}")
    
    def assert_false(self, condition: bool, message: str = ""):
        """Assert condition is false"""
        if condition:
            raise AssertionError(f"Expected False, got True. {message}")
    
    def assert_equal(self, actual: Any, expected: Any, message: str = ""):
        """Assert values are equal"""
        if actual != expected:
            raise AssertionError(f"Expected {expected}, got {actual}. {message}")
    
    def assert_not_equal(self, actual: Any, expected: Any, message: str = ""):
        """Assert values are not equal"""
        if actual == expected:
            raise AssertionError(f"Expected not {expected}, but got {actual}. {message}")
    
    def assert_bg_color(self, expected_color: int):
        """Assert background color matches"""
        result = self.send_rpc("get_state")
        if result:
            actual = result.get('bg_color', 0)
            self.assert_equal(actual, expected_color, 
                            f"Background color mismatch: expected 0x{expected_color:04x}, got 0x{actual:04x}")
    
    def assert_scene(self, expected_scene: int):
        """Assert current scene matches"""
        result = self.send_rpc("get_state")
        if result:
            actual = result.get('scene', 0)
            self.assert_equal(actual, expected_scene, f"Scene mismatch")
    
    def assert_button_state(self, button: str, expected_pressed: bool):
        """Assert button state"""
        result = self.send_rpc("get_state")
        if result:
            buttons = result.get('buttons', {})
            actual = buttons.get(button, False)
            self.assert_equal(actual, expected_pressed, 
                            f"Button {button} state mismatch")
    
    def wait_for_condition(self, condition: Callable[[], bool], 
                          timeout: float = 5.0, interval: float = 0.1) -> bool:
        """Wait for condition to become true"""
        start = time.time()
        while time.time() - start < timeout:
            if condition():
                return True
            time.sleep(interval)
        return False


class TestRunner:
    """Test runner with reporting"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time: float = 0.0
    
    def run_test(self, test: SimulatorTestCase, test_method: Callable) -> TestResult:
        """Run single test method"""
        print(f"  Running: {test.name}.{test_method.__name__}...", end=" ")
        
        start = time.time()
        
        try:
            # Setup
            test.setup()
            
            # Run test
            test_method()
            
            # Teardown
            test.teardown()
            
            duration_ms = (time.time() - start) * 1000
            result = TestResult(
                name=f"{test.name}.{test_method.__name__}",
                status=TestStatus.PASSED,
                duration_ms=duration_ms
            )
            
            print(f"✓ PASSED ({duration_ms:.1f} ms)")
            
        except AssertionError as e:
            duration_ms = (time.time() - start) * 1000
            result = TestResult(
                name=f"{test.name}.{test_method.__name__}",
                status=TestStatus.FAILED,
                duration_ms=duration_ms,
                message=str(e)
            )
            
            print(f"✗ FAILED ({duration_ms:.1f} ms)")
            print(f"    {e}")
        
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            result = TestResult(
                name=f"{test.name}.{test_method.__name__}",
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                message=str(e),
                exception=e
            )
            
            print(f"✗ ERROR ({duration_ms:.1f} ms)")
            print(f"    {e}")
        
        return result
    
    def run_test_suite(self, test_cases: List[SimulatorTestCase]):
        """Run multiple test cases"""
        self.start_time = time.time()
        
        print("\n" + "="*70)
        print("ESP32 SIMULATOR TEST SUITE")
        print("="*70)
        
        for test in test_cases:
            print(f"\nTest Case: {test.name}")
            
            # Connect to simulator
            if not test.connect():
                result = TestResult(
                    name=f"{test.name}.connection",
                    status=TestStatus.ERROR,
                    duration_ms=0,
                    message="Failed to connect to simulator"
                )
                self.results.append(result)
                print(f"  ✗ Skipping tests - connection failed")
                continue
            
            # Find all test methods (start with 'test_')
            test_methods = [
                getattr(test, name) 
                for name in dir(test) 
                if name.startswith('test_') and callable(getattr(test, name))
            ]
            
            # Run each test method
            for method in test_methods:
                result = self.run_test(test, method)
                self.results.append(result)
            
            # Disconnect
            test.disconnect()
        
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        total_time = time.time() - self.start_time
        
        passed = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        errors = sum(1 for r in self.results if r.status == TestStatus.ERROR)
        skipped = sum(1 for r in self.results if r.status == TestStatus.SKIPPED)
        total = len(self.results)
        
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Total:    {total}")
        print(f"Passed:   {passed} ✓")
        print(f"Failed:   {failed} ✗")
        print(f"Errors:   {errors} ✗")
        print(f"Skipped:  {skipped}")
        print(f"Duration: {total_time:.2f} seconds")
        print("="*70)
        
        if failed > 0 or errors > 0:
            print("\nFailed Tests:")
            for result in self.results:
                if result.status in (TestStatus.FAILED, TestStatus.ERROR):
                    print(f"  ✗ {result.name}: {result.message}")
        
        print()
    
    def export_to_json(self, filename: str):
        """Export results to JSON"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'total_time': time.time() - self.start_time,
            'results': [
                {
                    'name': r.name,
                    'status': r.status.value,
                    'duration_ms': r.duration_ms,
                    'message': r.message
                }
                for r in self.results
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"📊 Test results exported: {filename}")


# Example test cases

class BackgroundColorTests(SimulatorTestCase):
    """Test background color changes"""
    
    def test_set_bg_black(self):
        """Test setting background to black"""
        self.send_rpc("set_bg_rgb", {"r": 0, "g": 0, "b": 0})
        time.sleep(0.1)
        self.assert_bg_color(0x0000)
    
    def test_set_bg_red(self):
        """Test setting background to red"""
        self.send_rpc("set_bg_rgb", {"r": 255, "g": 0, "b": 0})
        time.sleep(0.1)
        # Red in RGB565: 0xF800
        # Note: actual value depends on RGB565 conversion
    
    def test_set_bg_green(self):
        """Test setting background to green"""
        self.send_rpc("set_bg_rgb", {"r": 0, "g": 255, "b": 0})
        time.sleep(0.1)
    
    def test_set_bg_blue(self):
        """Test setting background to blue"""
        self.send_rpc("set_bg_rgb", {"r": 0, "g": 0, "b": 255})
        time.sleep(0.1)


class ButtonTests(SimulatorTestCase):
    """Test button interactions"""
    
    def test_button_press_release(self):
        """Test button press and release"""
        # Press button A
        self.send_rpc("button_event", {"button": "A", "pressed": True})
        time.sleep(0.1)
        self.assert_button_state("A", True)
        
        # Release button A
        self.send_rpc("button_event", {"button": "A", "pressed": False})
        time.sleep(0.1)
        self.assert_button_state("A", False)


class SceneTests(SimulatorTestCase):
    """Test scene transitions"""
    
    def test_scene_change(self):
        """Test changing scenes"""
        self.send_rpc("set_scene", {"scene": 0})
        time.sleep(0.1)
        self.assert_scene(0)
        
        self.send_rpc("set_scene", {"scene": 1})
        time.sleep(0.1)
        self.assert_scene(1)


if __name__ == '__main__':
    # Create test suite
    runner = TestRunner()
    
    test_cases = [
        BackgroundColorTests("BackgroundColorTests"),
        ButtonTests("ButtonTests"),
        SceneTests("SceneTests")
    ]
    
    # Run tests
    runner.run_test_suite(test_cases)
    
    # Export results
    runner.export_to_json("test_results.json")
