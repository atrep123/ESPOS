#!/usr/bin/env python3
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import sim_run  # type: ignore


def test_first_diff_visual_identical_strings():
    prev = "hello"
    curr = "hello"
    ip, ic = sim_run._first_diff_visual(prev, curr)
    assert ip == len(prev)
    assert ic == len(curr)


def test_first_diff_visual_with_ansi_sequences():
    prev = "\033[31mHELLO\033[0m"
    curr = "\033[31mHEXXO\033[0m"
    ip, ic = sim_run._first_diff_visual(prev, curr)
    # first differing visible character is at column 2 ("L" vs "X")
    assert sim_run._col_of_index(prev, ip) == 2
    assert sim_run._col_of_index(curr, ic) == 2


def test_col_of_index_skips_ansi():
    s = "\033[31mHELLO\033[0m"
    # index right after the color code should map to visible column 0
    i = s.index("H")
    assert sim_run._col_of_index(s, i) == 0
    # full length -> number of visible characters
    assert sim_run._col_of_index(s, len(s)) == 5
