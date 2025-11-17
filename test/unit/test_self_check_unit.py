#!/usr/bin/env python3
from tools import self_check


def test_check_imports_returns_results():
    results = self_check.check_imports()
    assert isinstance(results, list)
    assert results  # očekáváme alespoň pár záznamů
    for r in results:
        assert hasattr(r, "name")
        assert hasattr(r, "ok")


def test_check_sim_help_runs():
    res = self_check.check_sim_help()
    assert hasattr(res, "name")
    assert "sim_run.py" in res.name
