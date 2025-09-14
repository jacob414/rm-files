from __future__ import annotations

from math import isclose, pi
from pathlib import Path

from rmfiles import RemarkableNotebook


def test_left_right_setheading_deg_mode() -> None:
    nb = RemarkableNotebook(deg=True)
    assert nb.heading == 0
    nb.left(90)
    assert nb.heading == 90
    nb.right(45)
    assert nb.heading == 45
    nb.setheading(180)
    assert nb.heading == 180
    # Switch to radians; set absolute heading via radians
    nb.set_deg(False)
    nb.setheading(pi)
    assert isclose(nb.heading, pi, rel_tol=1e-9)


def test_goto_and_home(tmp_path: Path) -> None:
    nb = RemarkableNotebook(deg=True)
    nb.goto(10, 20)
    assert nb.position == (10.0, 20.0)
    nb.home()
    assert nb.position == (0.0, 0.0)
