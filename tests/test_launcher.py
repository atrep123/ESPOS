"""Tests for launcher.py — ESP32 OS quick launcher menu."""

from __future__ import annotations

from unittest.mock import patch

from launcher import main, print_menu, run_designer

# ===================================================================
# print_menu
# ===================================================================


class TestPrintMenu:
    def test_outputs_header(self, capsys):
        print_menu()
        out = capsys.readouterr().out
        assert "ESP32 OS" in out

    def test_outputs_designer_option(self, capsys):
        print_menu()
        out = capsys.readouterr().out
        assert "1." in out
        assert "Designer" in out

    def test_outputs_exit_option(self, capsys):
        print_menu()
        out = capsys.readouterr().out
        assert "0." in out
        assert "Exit" in out


# ===================================================================
# run_designer
# ===================================================================


class TestRunDesigner:
    def test_launches_subprocess(self):
        with patch("launcher.subprocess.Popen") as mock_popen:
            run_designer()
            mock_popen.assert_called_once()
            args = mock_popen.call_args[0][0]
            assert "run_designer.py" in args[-1]


# ===================================================================
# main
# ===================================================================


class TestMain:
    def test_exit_on_zero(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "0")
        main()  # Should return without error

    def test_invalid_choice_then_exit(self, monkeypatch):
        inputs = iter(["9", "0"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        main()

    def test_choice_one_launches_designer(self, monkeypatch):
        inputs = iter(["1", "0"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        with patch("launcher.subprocess.Popen"):
            main()

    def test_keyboard_interrupt(self, monkeypatch, capsys):
        def raise_interrupt(_):
            raise KeyboardInterrupt
        monkeypatch.setattr("builtins.input", raise_interrupt)
        main()
        out = capsys.readouterr().out
        assert "Interrupted" in out
