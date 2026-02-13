"""Dictionary manager with auto-learning support."""

import json
from pathlib import Path
from typing import Optional

from config import Config


class DictionaryManager:
    """Manages Russian and English word dictionaries with user learning."""

    def __init__(self, config: Config, dict_dir: Optional[Path] = None):
        self.config = config
        if dict_dir:
            self.dict_dir = dict_dir
        else:
            # PyInstaller bundles data into sys._MEIPASS temp dir
            import sys
            base = getattr(sys, '_MEIPASS', Path(__file__).parent)
            self.dict_dir = Path(base) / 'dictionaries'
        self._ru_words: set[str] = set()
        self._en_words: set[str] = set()
        self._user_words: dict[str, set[str]] = {'ru': set(), 'en': set()}
        self._word_counts: dict[str, int] = {}  # word -> seen count
        self._user_data_path = self._get_user_data_path()
        self._load_dicts()
        self._load_user_data()

    def _get_user_data_path(self) -> Path:
        import os
        appdata = os.environ.get('APPDATA', '')
        if appdata:
            base = Path(appdata) / 'RuSwitch'
        else:
            base = Path.home() / '.config' / 'ruswitch'
        base.mkdir(parents=True, exist_ok=True)
        return base / 'user_words.json'

    def _load_dicts(self) -> None:
        """Load base dictionaries from text files."""
        ru_path = self.dict_dir / 'ru_words.txt'
        en_path = self.dict_dir / 'en_words.txt'
        if ru_path.exists():
            with open(ru_path, 'r', encoding='utf-8') as f:
                self._ru_words = {line.strip().lower() for line in f if line.strip()}
        if en_path.exists():
            with open(en_path, 'r', encoding='utf-8') as f:
                self._en_words = {line.strip().lower() for line in f if line.strip()}

    def _load_user_data(self) -> None:
        """Load user words and learning counters."""
        if self._user_data_path.exists():
            try:
                with open(self._user_data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._user_words['ru'] = set(data.get('ru', []))
                self._user_words['en'] = set(data.get('en', []))
                self._word_counts = data.get('counts', {})
            except (json.JSONDecodeError, TypeError):
                pass

    def _save_user_data(self) -> None:
        """Persist user words and learning counters."""
        data = {
            'ru': sorted(self._user_words['ru']),
            'en': sorted(self._user_words['en']),
            'counts': self._word_counts,
        }
        self._user_data_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._user_data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def check(self, word: str, language: str) -> bool:
        """Check if word exists in dictionary (base + user).

        Args:
            word: Word to check (case-insensitive).
            language: 'ru' or 'en'.
        """
        w = word.lower()
        if language == 'ru':
            return w in self._ru_words or w in self._user_words['ru']
        return w in self._en_words or w in self._user_words['en']

    def record_word(self, word: str, language: str) -> bool:
        """Record a word occurrence. Auto-adds to user dict after threshold.

        Returns True if word was auto-learned this call.
        """
        w = word.lower()
        if self.check(w, language):
            return False
        key = f"{language}:{w}"
        self._word_counts[key] = self._word_counts.get(key, 0) + 1
        if self._word_counts[key] >= self.config.auto_learn_threshold:
            self._user_words[language].add(w)
            del self._word_counts[key]
            self._save_user_data()
            return True
        self._save_user_data()
        return False

    def add_word(self, word: str, language: str) -> None:
        """Manually add a word to user dictionary."""
        w = word.lower()
        self._user_words[language].add(w)
        key = f"{language}:{w}"
        self._word_counts.pop(key, None)
        self._save_user_data()

    def remove_word(self, word: str, language: str) -> None:
        """Remove a word from user dictionary."""
        w = word.lower()
        self._user_words[language].discard(w)
        self._save_user_data()

    def get_user_words(self, language: str) -> list[str]:
        """Get sorted list of user words for a language."""
        return sorted(self._user_words[language])

    @property
    def stats(self) -> dict:
        """Return dictionary statistics."""
        return {
            'ru_base': len(self._ru_words),
            'en_base': len(self._en_words),
            'ru_user': len(self._user_words['ru']),
            'en_user': len(self._user_words['en']),
            'learning': len(self._word_counts),
        }
