"""RuSwitch — Punto Switcher alternative. Entry point and orchestrator."""

import sys
import os
import threading
import logging
import time
import queue
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

# --- File logging setup ---
def _get_log_dir() -> Path:
    appdata = os.environ.get('APPDATA', '')
    if appdata:
        d = Path(appdata) / 'RuSwitch' / 'logs'
    else:
        d = Path.home() / '.config' / 'ruswitch' / 'logs'
    d.mkdir(parents=True, exist_ok=True)
    return d

_log_dir = _get_log_dir()
_file_handler = TimedRotatingFileHandler(
    _log_dir / 'ruswitch.log',
    when='D', interval=1, backupCount=1,  # keep today + 1 day
    encoding='utf-8',
)
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s'))

_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s'))

logging.basicConfig(level=logging.DEBUG, handlers=[_console_handler, _file_handler])
log = logging.getLogger('ruswitch')
log.info('Log file: %s', _log_dir / 'ruswitch.log')

# Ensure single instance (Windows only)
_mutex = None

# Shift key mappings for US QWERTY (physical key -> shifted character)
_SHIFT_MAP = {
    '`': '~', '1': '!', '2': '@', '3': '#', '4': '$', '5': '%',
    '6': '^', '7': '&', '8': '*', '9': '(', '0': ')', '-': '_',
    '=': '+', '[': '{', ']': '}', '\\': '|', ';': ':', "'": '"',
    ',': '<', '.': '>', '/': '?',
}


def _ensure_single_instance() -> bool:
    if sys.platform != 'win32':
        return True
    import ctypes
    global _mutex
    _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, 'Global\\RuSwitch_Mutex')
    if ctypes.windll.kernel32.GetLastError() == 183:
        return False
    return True


def _get_current_layout() -> str:
    """Get keyboard layout of the foreground window: 'ru' or 'en'."""
    if sys.platform != 'win32':
        return 'en'
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        thread_id = user32.GetWindowThreadProcessId(hwnd, None)
        hkl = user32.GetKeyboardLayout(thread_id)
        lang_id = hkl & 0xFFFF
        return 'ru' if lang_id == 0x0419 else 'en'
    except Exception:
        return 'en'


def _get_foreground_process() -> str:
    if sys.platform != 'win32':
        return ''
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if handle:
            buf = ctypes.create_unicode_buffer(260)
            size = wintypes.DWORD(260)
            ctypes.windll.kernel32.QueryFullProcessImageNameW(
                handle, 0, buf, ctypes.byref(size))
            ctypes.windll.kernel32.CloseHandle(handle)
            return os.path.basename(buf.value)
    except Exception:
        pass
    return ''


def _translate_key(event_name: str, layout: str, shift_held: bool) -> str:
    """Translate physical key name to actual on-screen character."""
    from keymap import EN_TO_RU

    char = event_name

    # Step 1: Apply shift
    if shift_held:
        if char.isalpha():
            char = char.upper()
        else:
            char = _SHIFT_MAP.get(char, char)

    # Step 2: Apply layout
    if layout == 'ru':
        char = EN_TO_RU.get(char, char)

    return char


class RuSwitch:
    """Main application class."""

    def __init__(self):
        from config import Config
        from dictionary import DictionaryManager
        from detector import LayoutDetector
        from replacer import Replacer
        from tray import TrayIcon
        from settings_gui import SettingsWindow

        self.config = Config.load()
        log.info('Config loaded: auto_mode=%s, hotkey_manual=%s, hotkey_toggle=%s',
                 self.config.auto_mode, self.config.hotkey_manual, self.config.hotkey_toggle)

        self.dictionary = DictionaryManager(self.config)
        stats = self.dictionary.stats
        log.info('Dictionaries: %d RU + %d EN base, %d+%d user',
                 stats['ru_base'], stats['en_base'], stats['ru_user'], stats['en_user'])

        self.detector = LayoutDetector(self.config, self.dictionary)
        self.replacer = Replacer()
        self._active = self.config.auto_mode
        self._manual_hotkey_id = None
        self._toggle_hotkey_id = None
        self._key_queue = queue.Queue()
        self._settings_window = SettingsWindow(
            self.config, self.dictionary, on_save=self._on_settings_save)

        self.tray = TrayIcon(
            on_toggle=self._toggle,
            on_add_word=self._show_add_word,
            on_settings=self._show_settings,
            on_exit=self._exit,
        )

    def run(self) -> None:
        if sys.platform != 'win32':
            log.error('RuSwitch requires Windows. Exiting.')
            return

        import keyboard

        # Start key processing thread (keeps hook callback fast for other apps)
        t = threading.Thread(target=self._process_keys, daemon=True)
        t.start()

        keyboard.on_press(self._on_key_press_fast, suppress=False)
        self._register_hotkeys()

        log.info('RuSwitch started. Hotkeys: manual=%s, toggle=%s',
                 self.config.hotkey_manual, self.config.hotkey_toggle)

        self.tray.run()

    def _register_hotkeys(self) -> None:
        """Register hotkeys, removing old ones first."""
        import keyboard
        # Remove previous hotkeys if any
        if self._manual_hotkey_id is not None:
            try:
                keyboard.remove_hotkey(self._manual_hotkey_id)
            except Exception:
                pass
        if self._toggle_hotkey_id is not None:
            try:
                keyboard.remove_hotkey(self._toggle_hotkey_id)
            except Exception:
                pass

        self._manual_hotkey_id = keyboard.add_hotkey(
            self.config.hotkey_manual, self._manual_remap, suppress=True)
        self._toggle_hotkey_id = keyboard.add_hotkey(
            self.config.hotkey_toggle, self._toggle, suppress=True)
        log.info('Hotkeys registered: manual=%s, toggle=%s',
                 self.config.hotkey_manual, self.config.hotkey_toggle)

    def _on_key_press_fast(self, event) -> None:
        """Lightweight hook callback — just enqueue and return fast.

        This keeps the Windows low-level hook responsive so other programs
        (Vowen AI, AutoHotkey, etc.) still receive keystrokes.
        """
        import keyboard as kb
        # Capture shift state NOW (in the hook thread) before it changes
        shift_held = kb.is_pressed('shift')
        self._key_queue.put((event.name, shift_held))

    def _process_keys(self) -> None:
        """Background thread: process keystrokes from the queue."""
        while True:
            try:
                key_name, shift_held = self._key_queue.get()
            except Exception:
                continue

            try:
                self._handle_key(key_name, shift_held)
            except Exception:
                log.exception('Error processing key %r', key_name)

    def _handle_key(self, key_name: str, shift_held: bool) -> None:
        """Process a single keystroke (runs in background thread)."""
        if self.replacer.is_replacing:
            return

        proc = _get_foreground_process()
        if proc in self.config.excluded_processes:
            return

        # Clear buffer on modifier keys
        if key_name in ('ctrl', 'alt', 'shift', 'tab', 'escape',
                        'left ctrl', 'right ctrl', 'left alt', 'right alt',
                        'left shift', 'right shift', 'caps lock',
                        'left windows', 'right windows'):
            self.detector.clear_buffer()
            return

        if len(key_name) != 1:
            if key_name == 'space':
                key_name = ' '
            elif key_name == 'enter':
                key_name = '\n'
            elif key_name in ('backspace', 'delete', 'home', 'end',
                              'left', 'right', 'up', 'down',
                              'page up', 'page down'):
                self.detector.clear_buffer()
                return
            else:
                # Unknown special key (incl. insert) — ignore, keep buffer
                return

        if not self._active:
            return

        # Translate physical key to actual on-screen character
        if key_name in (' ', '\n'):
            actual_char = key_name
            layout = _get_current_layout()
        else:
            layout = _get_current_layout()
            actual_char = _translate_key(key_name, layout, shift_held)

        log.debug('key=%r layout=%s shift=%s -> char=%r buf=%s',
                  key_name, layout, shift_held, actual_char,
                  ''.join(self.detector._buffer) + actual_char)

        result = self.detector.feed_char(actual_char)
        if result:
            log.info('CORRECT: "%s" -> "%s" (%s) boundary=%r',
                     result.original, result.corrected,
                     result.direction, result.boundary_char)
            threading.Thread(
                target=self._do_replace, args=(result,), daemon=True).start()

    def _do_replace(self, result) -> None:
        success = self.replacer.replace_word(
            result.original, result.corrected, result.boundary_char)
        log.info('REPLACE: %s -> %s  success=%s',
                 result.original, result.corrected, success)
        if success and self.config.show_notification:
            self.tray.notify(f'{result.original} -> {result.corrected}')

    def _manual_remap(self) -> None:
        log.info('MANUAL REMAP triggered (Insert/hotkey)')
        result = self.detector.force_check()
        if result:
            log.info('Manual: "%s" -> "%s"', result.original, result.corrected)
            self.replacer.replace_word(result.original, result.corrected)
        else:
            log.info('Manual: buffer empty or no remap possible')

    def _toggle(self) -> None:
        self._active = not self._active
        self.tray.update(self._active)
        state = 'ON' if self._active else 'OFF'
        log.info('Auto-correction %s', state)
        self.tray.notify(f'RuSwitch: {state}')

    def _show_add_word(self) -> None:
        threading.Thread(target=self._settings_window._add_word_dialog,
                         daemon=True).start()

    def _show_settings(self) -> None:
        threading.Thread(target=self._settings_window.show, daemon=True).start()

    def _on_settings_save(self) -> None:
        self._active = self.config.auto_mode
        self.tray.update(self._active)
        self._register_hotkeys()
        log.info('Settings saved and applied')

    def _exit(self) -> None:
        log.info('RuSwitch shutting down')
        self.tray.stop()


def main():
    if not _ensure_single_instance():
        log.warning('RuSwitch is already running.')
        return

    log.info('=== RuSwitch starting ===')
    log.info('Python %s, platform %s', sys.version, sys.platform)
    app = RuSwitch()
    app.run()


if __name__ == '__main__':
    main()
