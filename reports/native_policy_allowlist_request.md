# Native Policy Allow-List Request

Generated: 2026-03-09T19:39:42.4709615+01:00
Repository: C:\Users\atrep\Desktop\ESPOS\ESPOS
Probe Source: C:\Users\atrep\Desktop\ESPOS\ESPOS\reports\native_policy_probe_auto.json

## Why This Request

Native PlatformIO test runs are intermittently blocked by Windows App Control policy (WinError 4551).
Request allow-listing for local test executables and toolchain runtime so firmware CI-like checks can run reliably on this workstation.

## Recommended Allow-List Targets

- Directory: C:\Users\atrep\Desktop\ESPOS\ESPOS\.pio\build\native
- Pattern: C:\Users\atrep\Desktop\ESPOS\ESPOS\.pio\build\native\*.exe
- Python runtime: C:\Users\atrep\.platformio\penv\Scripts\python.exe

## Current Probe Summary

- Triggered: True
- PolicyBlockCount: 2
- TransientPolicyBlockCount: 0
- FailureCount: 0

## Suites With POLICY_BLOCK

- test_msgbus
- test_seesaw

