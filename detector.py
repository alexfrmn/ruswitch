"""Layout detection engine — core logic of RuSwitch."""

import re
from dataclasses import dataclass
from typing import Optional

from config import Config
from dictionary import DictionaryManager
from keymap import remap_word, detect_script

# Patterns to skip (URLs, emails, paths, numbers)
_SKIP_PATTERNS = [
    re.compile(r'https?://\S+', re.IGNORECASE),
    re.compile(r'\S+@\S+\.\S+'),
    re.compile(r'[a-zA-Z]:\\[\S]+'),       # Windows paths
    re.compile(r'/[\w/]+'),                 # Unix paths
    re.compile(r'\d+[\d.,]+\d*'),           # Numbers with separators
]

# Word boundary characters
_WORD_BOUNDARIES = set(' \t\n\r.,;:!?()[]{}/<>@#$%^&*+=|\\~`"')


@dataclass
class CorrectionResult:
    original: str
    corrected: str
    direction: str  # 'en_to_ru' or 'ru_to_en'


class LayoutDetector:
    """Buffers keystrokes and detects wrong-layout words at word boundaries."""

    def __init__(self, config: Config, dictionary: DictionaryManager):
        self.config = config
        self.dictionary = dictionary
        self._buffer: list[str] = []

    def _should_skip(self, word: str) -> bool:
        """Check if word should be skipped from correction."""
        if len(word) < self.config.min_word_length:
            return True
        # Mixed script (intentional)
        if detect_script(word) == 'mixed':
            return True
        # Contains digits
        if any(ch.isdigit() for ch in word):
            return True
        # Matches skip patterns
        for pattern in _SKIP_PATTERNS:
            if pattern.fullmatch(word):
                return True
        return False

    def feed_char(self, char: str) -> Optional[CorrectionResult]:
        """Feed a character into the buffer. Returns correction at word boundary.

        Args:
            char: The typed character.

        Returns:
            CorrectionResult if a correction is needed, None otherwise.
        """
        if char in _WORD_BOUNDARIES:
            result = self._analyze_buffer()
            self._buffer.clear()
            return result
        self._buffer.append(char)
        return None

    def force_check(self) -> Optional[CorrectionResult]:
        """Force remap of current buffer (Insert key — manual mode, no dict check)."""
        if not self._buffer:
            return None
        word = ''.join(self._buffer)
        script = detect_script(word)
        if script == 'latin':
            corrected = remap_word(word, 'en_to_ru')
            result = CorrectionResult(word, corrected, 'en_to_ru')
        elif script == 'cyrillic':
            corrected = remap_word(word, 'ru_to_en')
            result = CorrectionResult(word, corrected, 'ru_to_en')
        else:
            return None
        self._buffer.clear()
        return result

    def clear_buffer(self) -> None:
        """Clear the keystroke buffer (e.g., on Ctrl press)."""
        self._buffer.clear()

    def _analyze_buffer(self) -> Optional[CorrectionResult]:
        """Analyze buffered word and determine if layout correction is needed."""
        if not self._buffer:
            return None
        word = ''.join(self._buffer)
        if self._should_skip(word):
            return None

        script = detect_script(word)

        if script == 'latin':
            # Word looks Latin — check if it's a valid EN word
            if self.dictionary.check(word, 'en'):
                self.dictionary.record_word(word, 'en')
                return None
            # Try remapping to Russian
            remapped = remap_word(word, 'en_to_ru')
            if self.dictionary.check(remapped, 'ru'):
                self.dictionary.record_word(remapped, 'ru')
                return CorrectionResult(word, remapped, 'en_to_ru')
            # Unknown word in both — no correction
            return None

        if script == 'cyrillic':
            # Word looks Cyrillic — check if it's a valid RU word
            if self.dictionary.check(word, 'ru'):
                self.dictionary.record_word(word, 'ru')
                return None
            # Try remapping to English
            remapped = remap_word(word, 'ru_to_en')
            if self.dictionary.check(remapped, 'en'):
                self.dictionary.record_word(remapped, 'en')
                return CorrectionResult(word, remapped, 'ru_to_en')
            return None

        return None
