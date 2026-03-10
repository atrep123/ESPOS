---
description: "Validate a UI design JSON file against the ESP32OS schema, check widget types, geometry bounds, duplicate IDs, and export compatibility. Optionally treat warnings as errors."
---

# Validate UI Scene

Validate the design JSON for correctness and firmware export compatibility.

## Steps

1. Run the structural validator:
   ```
   python tools/validate_design.py ${file:main_scene.json} ${{ input: flags }}
   ```

2. If errors are found, report them with file location and widget index.

3. If the file is valid, also verify it can be loaded by the designer:
   ```
   python run_designer.py ${file:main_scene.json} --headless-export --profile esp32os_256x128_gray4
   ```

4. Summarize: total errors, warnings, and whether the file is ready for firmware export.
