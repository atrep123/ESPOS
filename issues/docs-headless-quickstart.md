---
title: "Docs: Add QUICKSTART blurb for headless preview"
labels: [documentation, good-first-issue]
assignees: []
---

Summary:

- Add a short section to `QUICKSTART.md` demonstrating headless PNG export via `ui_designer_preview.py --headless`.

Details:

- Include a PowerShell example:
  - `python .\ui_designer_preview.py --headless --out-png .\preview.png`
- Mention that it creates a default 320x240 scene and that `--headless-preview` with `--in-json` remains unchanged for JSON-driven exports.
- Link to `SIMULATOR_README.md` for the full headless notes.

Acceptance Criteria:

- `QUICKSTART.md` contains a concise "Headless preview" subsection with the example command and 1-2 bullets of context.
- CI/tests not affected.

Notes:

- Keep wording consistent with `SIMULATOR_README.md` terminology.
