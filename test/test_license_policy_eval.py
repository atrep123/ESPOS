from pathlib import Path

from tools import license_policy_eval


def test_license_policy_eval_flags_disallowed(tmp_path: Path):
    root = tmp_path
    py_dir = root / "python"
    node_dir = root / "node"
    py_dir.mkdir()
    node_dir.mkdir()

    (py_dir / "python_licenses.json").write_text(
        '[{"license": "MIT"}, {"license": "GPL-3.0"}]', encoding="utf-8"
    )
    (node_dir / "node_licenses.json").write_text(
        '{"pkg":{"licenses":"Apache-2.0"}, "bad":{"licenses":"SSPL"}}',
        encoding="utf-8",
    )

    py_bad, node_bad = license_policy_eval.evaluate({"GPL-3.0", "SSPL"}, root=root)

    assert py_bad == {"GPL-3.0"}
    assert node_bad == {"SSPL"}
