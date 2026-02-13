"""Text replacement engine using direct Unicode input (Windows only)."""

import time
import sys
from collections import deque
from dataclasses import dataclass
from typing import Optional

if sys.platform == 'win32':
    import keyboard


@dataclass
class UndoEntry:
    original: str
    corrected: str
    boundary_char: str
    timestamp: float


class Replacer:
    """Replaces typed text via backspace + direct Unicode write."""

    UNDO_MAX = 20
    BACKSPACE_DELAY = 0.012  # 12ms between backspaces
    CHAR_DELAY = 0.008       # 8ms between typed characters
    PRE_TYPE_DELAY = 0.03    # 30ms before typing corrected text
    POST_REPLACE_DELAY = 0.05  # 50ms after replacement

    def __init__(self):
        self.is_replacing = False
        self._undo_stack: deque[UndoEntry] = deque(maxlen=self.UNDO_MAX)

    def replace_word(self, original: str, corrected: str,
                     boundary_char: str = '') -> bool:
        """Replace the just-typed word with corrected version.

        Uses backspace to delete, then keyboard.write() for Unicode input.
        No clipboard involved — avoids race conditions.
        """
        if sys.platform != 'win32':
            return False

        self.is_replacing = True
        try:
            # Wait for the boundary char to reach the application
            time.sleep(self.PRE_TYPE_DELAY)

            # Delete: original word + boundary character
            total_bs = len(original) + (1 if boundary_char else 0)
            for _ in range(total_bs):
                keyboard.press_and_release('backspace')
                time.sleep(self.BACKSPACE_DELAY)

            time.sleep(self.PRE_TYPE_DELAY)

            # Type corrected word + boundary using Unicode input
            text = corrected + boundary_char
            keyboard.write(text, delay=self.CHAR_DELAY)

            time.sleep(self.POST_REPLACE_DELAY)

            self._undo_stack.append(UndoEntry(
                original=original,
                corrected=corrected,
                boundary_char=boundary_char,
                timestamp=time.time(),
            ))
            return True
        except Exception:
            return False
        finally:
            self.is_replacing = False

    def undo_last(self) -> bool:
        """Undo the last correction (revert to original text)."""
        if sys.platform != 'win32':
            return False
        if not self._undo_stack:
            return False
        entry = self._undo_stack[-1]
        if time.time() - entry.timestamp > 30:
            return False

        self._undo_stack.pop()
        self.is_replacing = True
        try:
            # Delete corrected word + boundary
            total_bs = len(entry.corrected) + (1 if entry.boundary_char else 0)
            for _ in range(total_bs):
                keyboard.press_and_release('backspace')
                time.sleep(self.BACKSPACE_DELAY)

            time.sleep(self.PRE_TYPE_DELAY)

            # Retype original + boundary
            text = entry.original + entry.boundary_char
            keyboard.write(text, delay=self.CHAR_DELAY)

            time.sleep(self.POST_REPLACE_DELAY)
            return True
        except Exception:
            return False
        finally:
            self.is_replacing = False
