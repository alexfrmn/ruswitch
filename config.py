"""Configuration management for RuSwitch."""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


def _default_excluded() -> list[str]:
    return ['KeePass.exe', '1Password.exe', 'Bitwarden.exe']


@dataclass
class Config:
    auto_mode: bool = True
    hotkey_manual: str = 'insert'
    hotkey_toggle: str = 'ctrl+alt+r'
    min_word_length: int = 2
    auto_learn_threshold: int = 3
    excluded_processes: list[str] = field(default_factory=_default_excluded)
    show_notification: bool = True

    @classmethod
    def _config_path(cls) -> Path:
        appdata = os.environ.get('APPDATA', '')
        if appdata:
            base = Path(appdata) / 'RuSwitch'
        else:
            # Fallback for Linux (dev/test)
            base = Path.home() / '.config' / 'ruswitch'
        base.mkdir(parents=True, exist_ok=True)
        return base / 'config.json'

    @classmethod
    def load(cls, path: Optional[Path] = None) -> 'Config':
        """Load config from JSON file. Returns defaults if file doesn't exist."""
        config_path = path or cls._config_path()
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return cls(**{k: v for k, v in data.items()
                             if k in cls.__dataclass_fields__})
            except (json.JSONDecodeError, TypeError):
                pass
        return cls()

    def save(self, path: Optional[Path] = None) -> None:
        """Save config to JSON file."""
        config_path = path or self._config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)
