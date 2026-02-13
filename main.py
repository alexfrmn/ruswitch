"""RuSwitch — Punto Switcher alternative. Entry point and orchestrator."""

import sys
import os
import threading
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger('ruswitch')

# Ensure single instance (Windows only)
_mutex = None


def _ensure_single_instance() -> bool:
    """Create a Windows mutex to prevent multiple instances. Returns False if already running."""
    if sys.platform != 'win32':
        return True
    import ctypes
    global _mutex
    _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, 'Global\\RuSwitch_Mutex')
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        return False
    return True


def _get_foreground_process() -> str:
    """Get the exe name of the currently focused window (Windows only)."""
    if sys.platform != 'win32':
        return ''
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        # Open process to get name
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
        log.info('Config loaded: auto_mode=%s', self.config.auto_mode)

        self.dictionary = DictionaryManager(self.config)
        stats = self.dictionary.stats
        log.info('Dictionaries loaded: %d RU + %d EN base, %d+%d user',
                 stats['ru_base'], stats['en_base'], stats['ru_user'], stats['en_user'])

        self.detector = LayoutDetector(self.config, self.dictionary)
        self.replacer = Replacer()
        self._active = self.config.auto_mode
        self._settings_window = SettingsWindow(
            self.config, self.dictionary, on_save=self._on_settings_save)

        self.tray = TrayIcon(
            on_toggle=self._toggle,
            on_add_word=self._show_add_word,
            on_settings=self._show_settings,
            on_exit=self._exit,
        )

    def run(self) -> None:
        """Start RuSwitch: keyboard hook in background, tray icon in main thread."""
        if sys.platform != 'win32':
            log.error('RuSwitch requires Windows. Exiting.')
            return

        import keyboard

        # Register keyboard hook
        keyboard.on_press(self._on_key_press, suppress=False)

        # Register hotkeys
        keyboard.add_hotkey(self.config.hotkey_manual, self._manual_remap)
        keyboard.add_hotkey(self.config.hotkey_toggle, self._toggle)

        log.info('RuSwitch started. Hotkeys: manual=%s, toggle=%s',
                 self.config.hotkey_manual, self.config.hotkey_toggle)

        # Tray icon runs in main thread (pystray requirement on Windows)
        self.tray.run()

    def _on_key_press(self, event) -> None:
        """Keyboard hook callback."""
        import keyboard as kb

        # Skip our own keystrokes during replacement
        if self.replacer.is_replacing:
            return

        # Check excluded process
        proc = _get_foreground_process()
        if proc in self.config.excluded_processes:
            return

        # Clear buffer on modifier keys
        if event.name in ('ctrl', 'alt', 'shift', 'tab', 'escape',
                          'left ctrl', 'right ctrl', 'left alt', 'right alt',
                          'left shift', 'right shift'):
            self.detector.clear_buffer()
            return

        # Skip non-character keys
        char = event.name
        if len(char) != 1:
            # Handle special named keys
            if char == 'space':
                char = ' '
            elif char == 'enter':
                char = '\n'
            elif char in ('backspace', 'delete', 'home', 'end',
                          'left', 'right', 'up', 'down',
                          'page up', 'page down', 'insert'):
                self.detector.clear_buffer()
                return
            else:
                return

        if not self._active:
            return

        result = self.detector.feed_char(char)
        if result:
            log.info('Correction: "%s" -> "%s" (%s)',
                     result.original, result.corrected, result.direction)
            self.replacer.replace_word(result.original, result.corrected)
            if self.config.show_notification:
                self.tray.notify(f'{result.original} -> {result.corrected}')

    def _manual_remap(self) -> None:
        """Insert key: force remap current buffer without dictionary check."""
        result = self.detector.force_check()
        if result:
            log.info('Manual remap: "%s" -> "%s"', result.original, result.corrected)
            self.replacer.replace_word(result.original, result.corrected)

    def _toggle(self) -> None:
        """Toggle auto-correction on/off."""
        self._active = not self._active
        self.tray.update(self._active)
        state = 'ON' if self._active else 'OFF'
        log.info('Auto-correction %s', state)
        self.tray.notify(f'RuSwitch: {state}')

    def _show_add_word(self) -> None:
        """Show add word dialog."""
        threading.Thread(target=self._settings_window._add_word_dialog,
                         daemon=True).start()

    def _show_settings(self) -> None:
        """Show settings window in a separate thread."""
        threading.Thread(target=self._settings_window.show, daemon=True).start()

    def _on_settings_save(self) -> None:
        """Called when settings are saved."""
        self._active = self.config.auto_mode
        self.tray.update(self._active)
        # Re-register hotkeys
        import keyboard
        keyboard.remove_all_hotkeys()
        keyboard.add_hotkey(self.config.hotkey_manual, self._manual_remap)
        keyboard.add_hotkey(self.config.hotkey_toggle, self._toggle)
        log.info('Settings saved and applied')

    def _exit(self) -> None:
        """Exit the application."""
        log.info('RuSwitch shutting down')
        self.tray.stop()


def main():
    if not _ensure_single_instance():
        log.warning('RuSwitch is already running.')
        return

    app = RuSwitch()
    app.run()


if __name__ == '__main__':
    main()
