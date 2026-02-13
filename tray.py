"""System tray icon for RuSwitch (pystray + Pillow)."""

import sys
import threading
from typing import Callable, Optional

if sys.platform == 'win32':
    import pystray
    from PIL import Image, ImageDraw, ImageFont


def _create_icon_image(active: bool) -> 'Image.Image':
    """Generate tray icon: colored circle with 'RS' text."""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Background circle
    color = (76, 175, 80, 255) if active else (158, 158, 158, 255)  # green / gray
    draw.ellipse([2, 2, size - 2, size - 2], fill=color)
    # Text
    try:
        font = ImageFont.truetype('arial.ttf', 24)
    except (OSError, IOError):
        font = ImageFont.load_default()
    text = 'RS'
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) // 2
    y = (size - th) // 2 - 2
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
    return img


class TrayIcon:
    """System tray icon with menu."""

    def __init__(
        self,
        on_toggle: Callable[[], None],
        on_add_word: Callable[[], None],
        on_settings: Callable[[], None],
        on_exit: Callable[[], None],
    ):
        self._on_toggle = on_toggle
        self._on_add_word = on_add_word
        self._on_settings = on_settings
        self._on_exit = on_exit
        self._active = True
        self._icon: Optional['pystray.Icon'] = None

    def _build_menu(self) -> 'pystray.Menu':
        status_text = 'RuSwitch: ON' if self._active else 'RuSwitch: OFF'
        toggle_text = 'Disable' if self._active else 'Enable'
        return pystray.Menu(
            pystray.MenuItem(status_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(toggle_text, lambda _i, _it: self._on_toggle()),
            pystray.MenuItem('Add Word...', lambda _i, _it: self._on_add_word()),
            pystray.MenuItem('Settings', lambda _i, _it: self._on_settings()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Exit', lambda _i, _it: self._on_exit()),
        )

    def run(self) -> None:
        """Start the tray icon (blocking — run in main thread or dedicated thread)."""
        if sys.platform != 'win32':
            return
        image = _create_icon_image(self._active)
        self._icon = pystray.Icon(
            'RuSwitch',
            image,
            'RuSwitch',
            menu=self._build_menu(),
        )
        self._icon.run()

    def update(self, active: bool) -> None:
        """Update icon to reflect active/inactive state."""
        self._active = active
        if self._icon:
            self._icon.icon = _create_icon_image(active)
            self._icon.menu = self._build_menu()
            self._icon.update_menu()

    def stop(self) -> None:
        """Stop the tray icon."""
        if self._icon:
            self._icon.stop()

    def notify(self, message: str) -> None:
        """Show a Windows notification balloon."""
        if self._icon:
            try:
                self._icon.notify(message, 'RuSwitch')
            except Exception:
                pass
