"""Basic tests for the ui_pipeline helper."""

import os
from pathlib import Path

import argparse

from ui_designer import UIDesigner, WidgetType
import ui_pipeline


def test_export_c_from_json_creates_c_files(tmp_path, monkeypatch):
    """Exporting C via ui_pipeline should create .h/.c next to a temporary src/."""
    # Disable auto-export side effects from UIDesigner.save_to_json
    monkeypatch.setenv("ESP32OS_AUTO_EXPORT", "0")

    designer = UIDesigner(128, 64)
    designer.create_scene("test_scene")
    designer.add_widget(
        WidgetType.LABEL,
        x=2,
        y=2,
        width=20,
        height=8,
        text="Hello",
        border=False,
    )

    design_path = tmp_path / "design.json"
    designer.save_to_json(str(design_path))

    # Run export in an isolated working directory so src/ is created under tmp_path.
    cwd_before = os.getcwd()
    os.chdir(tmp_path)
    try:
        args = argparse.Namespace(
            design=str(design_path),
            scene=None,
            base_name="ui_design",
        )
        rc = ui_pipeline.cmd_export_c(args)
    finally:
        os.chdir(cwd_before)

    assert rc == 0
    assert (tmp_path / "src" / "ui_design.h").is_file()
    assert (tmp_path / "src" / "ui_design.c").is_file()

