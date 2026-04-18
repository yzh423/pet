# coding: utf-8
"""
Parse spoken English and drive the car via comm.py (UART F/B/L/R/S).
"""
from typing import List, Tuple

import comm


def apply_commands_from_speech(text):
    # type: (str) -> List[str]
    """
    Match at most one driving intent per utterance.

    Priority: stop > backward > forward > left > right

    Phrases are matched case-insensitively on the full utterance.
    """
    if not text or not text.strip():
        return []
    t = text.lower().strip()

    def any_phrase(phrases):
        # type: (Tuple[str, ...]) -> bool
        return any(p in t for p in phrases)

    if any_phrase(
        ("stop", "halt", "brake", "hold it", "full stop", "stay", "freeze")
    ):
        comm.stop()
        return ["stop"]
    if any_phrase(
        ("go backward", "move backward", "backward", "backwards", "reverse", "go back")
    ):
        comm.backward()
        return ["backward"]
    if any_phrase(("go forward", "move forward", "forward", "go ahead", "drive forward")):
        comm.forward()
        return ["forward"]
    if any_phrase(("turn left", "left turn", "steer left", "bear left")):
        comm.left()
        return ["left"]
    if any_phrase(("turn right", "right turn", "steer right", "bear right")):
        comm.right()
        return ["right"]

    return []
