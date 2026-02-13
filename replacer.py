"""Text replacement engine using clipboard-based approach (Windows only)."""

import time
import sys
from collections import deque
from dataclasses import dataclass
from typing import Optional

# Windows-only imports are guarded for Linux dev/test
if sys.platform == 'win32':
    import ctypes
    import ctypes.wintypes
    import keyboard

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    CF_UNICODETEXT = 13

    OpenClipboard = user32.OpenClipboard
    CloseClipboard = user32.CloseClipboard
    EmptyClipboard = user32.EmptyClipboard
    GetClipboardData = user32.GetClipboardData
    SetClipboardData = user32.SetClipboardData
    GlobalAlloc = kernel32.GlobalAlloc
    GlobalLock = kernel32.GlobalLock
    GlobalUnlock = kernel32.GlobalUnlock
    GlobalFree = kernel32.GlobalFree

    GMEM_MOVEABLE = 0x0002


@dataclass
class UndoEntry:
    original: str
    corrected: str
    timestamp: float


class Replacer:
    """Replaces typed text via backspace + clipboard paste."""

    UNDO_MAX = 20
    BACKSPACE_DELAY = 0.01   # 10ms between backspaces
    PRE_PASTE_DELAY = 0.02   # 20ms before paste
    POST_PASTE_DELAY = 0.05  # 50ms after paste

    def __init__(self):
        self.is_replacing = False
        self._undo_stack: deque[UndoEntry] = deque(maxlen=self.UNDO_MAX)
        self._saved_clipboard: Optional[str] = None

    def replace_word(self, original: str, corrected: str,
                     boundary_char: str = '') -> bool:
        """Replace the just-typed word with corrected version.

        The boundary character (space, period, etc.) has already been typed
        into the application, so we must remove it too and re-type it after.

        Sequence: backspace × (len + 1 for boundary) → paste corrected +
        boundary → restore clipboard.

        Returns True on success.
        """
        if sys.platform != 'win32':
            return False

        self.is_replacing = True
        try:
            # Small delay to let the boundary char reach the application
            time.sleep(0.03)

            # Save current clipboard
            self._saved_clipboard = self._get_clipboard()

            # Backspace to remove original word + boundary char
            total_bs = len(original) + (1 if boundary_char else 0)
            for _ in range(total_bs):
                keyboard.send('backspace')
                time.sleep(self.BACKSPACE_DELAY)

            time.sleep(self.PRE_PASTE_DELAY)

            # Paste corrected word + boundary char
            paste_text = corrected + boundary_char
            self._set_clipboard(paste_text)
            keyboard.send('ctrl+v')

            time.sleep(self.POST_PASTE_DELAY)

            # Restore original clipboard
            if self._saved_clipboard is not None:
                self._set_clipboard(self._saved_clipboard)

            # Record for undo
            self._undo_stack.append(UndoEntry(
                original=original,
                corrected=corrected,
                timestamp=time.time(),
            ))
            return True
        finally:
            self.is_replacing = False

    def undo_last(self) -> bool:
        """Undo the last correction (revert to original text).

        Returns True if undo was performed.
        """
        if sys.platform != 'win32':
            return False
        if not self._undo_stack:
            return False
        # Only undo recent corrections (within 30 seconds)
        entry = self._undo_stack[-1]
        if time.time() - entry.timestamp > 30:
            return False

        self._undo_stack.pop()
        self.is_replacing = True
        try:
            self._saved_clipboard = self._get_clipboard()
            for _ in range(len(entry.corrected)):
                keyboard.send('backspace')
                time.sleep(self.BACKSPACE_DELAY)
            time.sleep(self.PRE_PASTE_DELAY)
            self._set_clipboard(entry.original)
            keyboard.send('ctrl+v')
            time.sleep(self.POST_PASTE_DELAY)
            if self._saved_clipboard is not None:
                self._set_clipboard(self._saved_clipboard)
            return True
        finally:
            self.is_replacing = False

    @staticmethod
    def _get_clipboard() -> Optional[str]:
        """Read current clipboard text (Windows only)."""
        try:
            OpenClipboard(0)
            handle = GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return None
            ptr = GlobalLock(handle)
            if not ptr:
                return None
            try:
                return ctypes.wstring_at(ptr)
            finally:
                GlobalUnlock(handle)
        except Exception:
            return None
        finally:
            try:
                CloseClipboard()
            except Exception:
                pass

    @staticmethod
    def _set_clipboard(text: str) -> None:
        """Set clipboard text (Windows only)."""
        try:
            OpenClipboard(0)
            EmptyClipboard()
            data = text.encode('utf-16-le') + b'\x00\x00'
            h = GlobalAlloc(GMEM_MOVEABLE, len(data))
            ptr = GlobalLock(h)
            ctypes.memmove(ptr, data, len(data))
            GlobalUnlock(h)
            SetClipboardData(CF_UNICODETEXT, h)
        except Exception:
            pass
        finally:
            try:
                CloseClipboard()
            except Exception:
                pass
