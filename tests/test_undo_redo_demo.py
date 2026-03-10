"""Test shared_undo_redo demo() function (lines 376-435)."""

from shared_undo_redo import demo


def test_demo_runs_without_error(capsys):
    """Lines 376-435: demo() executes the full undo/redo showcase."""
    demo()
    out = capsys.readouterr().out
    assert "Executing Operations" in out
    assert "Undo" in out
    assert "Redo" in out
    assert "Collaborative" in out
