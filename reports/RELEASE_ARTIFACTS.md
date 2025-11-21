# Release Artifacts Cheat Sheet

- Designer build archives: `ESP32OS_UI_Designer_<OS>.zip`/`.tar.gz`
- Launcher build archives: `ESP32OS_UI_Designer_<OS>_Launcher.zip`/`.tar.gz` (entry = unified launcher)
- Checksums: `CHECKSUMS.txt` (SHA256 for all artifacts)
- Launcher config path: `~/.esp32os/config.json`
- Ports (defaults): backend 8000, frontend 8001 (configurable)
- Verify integrity: `sha256sum -c CHECKSUMS.txt` (or `shasum -a 256 -c CHECKSUMS.txt` on macOS)
- Release notes body combines changelog + this artifact summary (auto-generated).
- If the download is empty (no `esp32os-*/*`), release job fails fast (sanity check).
