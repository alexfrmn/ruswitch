# RuSwitch

Automatic keyboard layout switcher for Windows (RU/EN). Punto Switcher alternative.

## Features

- Auto-detection and correction of wrong keyboard layout
- QWERTY <-> JCUKEN mapping with case preservation
- 146K Russian + 370K English word dictionaries
- Auto-learning: words used 3+ times are added to user dictionary
- Manual remap: select text and press Insert
- System tray icon with settings GUI
- Excluded processes (password managers, etc.)
- Undo last correction with Ctrl+Z (within 30s)

## Quick Start

```cmd
git clone https://github.com/alexfrmn/ruswitch
cd ruswitch
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Hotkeys

| Key | Action |
|-----|--------|
| Insert | Manual remap current word |
| Ctrl+Alt+R | Toggle auto-correction |

## Build .exe

```cmd
build.bat
```

Or use GitHub Actions (auto-builds on tag push).

## Config

Settings stored in `%APPDATA%\RuSwitch\config.json`.
User dictionary in `%APPDATA%\RuSwitch\user_words.json`.

## License

MIT
