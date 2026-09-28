"""Geometrie drobnych popisku v referencni scene 256x128.

Validator drive hlasil pet viditelnych stitku s vnitrni vyskou 6 px pro
osmipixelovy font. Zvetseni samotnych boxu by ale zakrylo pristroje pod nimi.
"""

from __future__ import annotations

import json
from pathlib import Path

from tools.validate_design import validate_file

ROOT = Path(__file__).resolve().parents[1]
SCENE = ROOT / "main_scene.json"


def test_small_labels_fit_without_covering_instruments() -> None:
    data = json.loads(SCENE.read_text(encoding="utf-8"))

    def widgets(scene: str) -> dict[str, dict]:
        return {w.get("_widget_id"): w for w in data["scenes"][scene]["widgets"]}

    menu = widgets("menu")
    metrics = widgets("metrics")
    assert menu["menu.scroll"]["height"] >= 12
    assert menu["menu.scroll"]["y"] + menu["menu.scroll"]["height"] <= menu["menu.item0"]["y"]

    for label, instrument in (
        ("metrics.heap.label", "metrics.heap"),
        ("metrics.minheap.label", "metrics.minheap"),
        ("metrics.uptime.label", "metrics.uptime"),
        ("metrics.chart.label", "metrics.chart"),
    ):
        assert metrics[label]["height"] >= 12
        assert metrics[label]["y"] + metrics[label]["height"] <= metrics[instrument]["y"]
    assert (
        metrics["metrics.chart"]["y"] + metrics["metrics.chart"]["height"]
        <= metrics["metrics.min_text"]["y"]
    )


def test_validator_no_longer_reports_clipped_reference_labels() -> None:
    ids = (
        "menu.scroll",
        "metrics.heap.label",
        "metrics.minheap.label",
        "metrics.uptime.label",
        "metrics.chart.label",
    )
    issues = validate_file(SCENE, warnings_as_errors=False)
    assert not [
        i.message
        for i in issues
        if any(wid in i.message for wid in ids)
        and ("text cannot fit" in i.message or "< min" in i.message)
    ]
