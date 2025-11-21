# Changelog

Generated automatically during release. For the latest changes since the last tag, run `python tools/generate_changelog.py`.

## Unreleased

- CI: ESP32 firmware build workflow now uploads artifact `esp32-firmware-esp32-s3-devkitm-1` with `firmware.bin` and `firmware.elf`.
- Docs: Added CI/workflow overview (tests matrix, security dashboard + SARIF bundle, deps-outdated artifacts, ESP32 build) to README and TECH_STACK.
- Release: changelog generator highlights `[BREAKING]` commits; release workflow now publishes SHA256 `CHECKSUMS.txt` alongside artifacts.
- Launcher: unified CLI launcher added; release builds include a launcher variant; shared logging/config helpers added; simulator gains `--snapshot` (txt/html) for CI artifacts; tools-tests job uploads a simulator snapshot.
- Launcher web mode runs backend + frontend server with start/stop menu; simulator snapshot supports PNG when Pillow is available.
- Launcher status: port/PID health shown via menu option `p`.
- Launcher web health: reports WebSocket ping (if `websockets` is installed) to confirm backend responsiveness.
- Release verification docs added to `reports/RELEASE_ARTIFACTS.md` (checksum commands).
- Release workflow now auto-appends actual artifact listing (names + sizes) to `RELEASE_ARTIFACTS.md` during publish.
- Release body now includes both changelog and artifact summary (`RELEASE_NOTES.md`).
- Release job fails fast if no artifacts are downloaded; release body explicitly mentions artifact summary.
- Launcher adds config helpers: status (`p`), reset (`r`), edit (`e`).
- Launcher now supports optional Tk GUI mode (`--gui`) with buttons for start/stop/status/config/docs.
- Launcher GUI: auto-refresh status; buttons to open frontend/backend URLs.
- Tests: main matrix (Ubuntu) now uploads simulator snapshots (txt/png/html) for visual regression checks.
- UI Designer: quick-insert now shows a live placement preview (ghost overlay) before click-to-place; snap toggle with `G`; overlay shows size/coords; auto-opens properties after placing; can be cancelled with right-click or Esc.
