"""Tests for detector module."""

import sys
import os
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import Config
from dictionary import DictionaryManager
from detector import LayoutDetector


def _make_detector(ru_words=None, en_words=None):
    """Create a detector with in-memory dictionaries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from pathlib import Path
        dict_dir = Path(tmpdir) / 'dicts'
        dict_dir.mkdir()
        # Write test dictionaries
        (dict_dir / 'ru_words.txt').write_text(
            '\n'.join(ru_words or ['привет', 'мир', 'код', 'тест']),
            encoding='utf-8')
        (dict_dir / 'en_words.txt').write_text(
            '\n'.join(en_words or ['hello', 'world', 'code', 'test']),
            encoding='utf-8')
        config = Config(min_word_length=2, auto_learn_threshold=100)
        dictionary = DictionaryManager(config, dict_dir=dict_dir)
        detector = LayoutDetector(config, dictionary)
        return detector


class TestDetectorCorrectWord:
    def test_english_word_no_correction(self):
        det = _make_detector()
        # Type "hello " — valid English, no correction
        for ch in 'hello':
            result = det.feed_char(ch)
            assert result is None
        result = det.feed_char(' ')
        assert result is None

    def test_russian_word_no_correction(self):
        det = _make_detector()
        for ch in 'привет':
            result = det.feed_char(ch)
            assert result is None
        result = det.feed_char(' ')
        assert result is None


class TestDetectorWrongLayout:
    def test_en_typed_as_ru_corrected(self):
        """'ghbdtn' (привет typed on EN layout) -> correction to 'привет'."""
        det = _make_detector()
        for ch in 'ghbdtn':
            result = det.feed_char(ch)
            assert result is None
        result = det.feed_char(' ')
        assert result is not None
        assert result.corrected == 'привет'
        assert result.direction == 'en_to_ru'
        assert result.boundary_char == ' '

    def test_ru_typed_as_en_corrected(self):
        """'руддщ' (hello typed on RU layout) -> correction to 'hello'."""
        det = _make_detector()
        for ch in 'руддщ':
            result = det.feed_char(ch)
            assert result is None
        result = det.feed_char(' ')
        assert result is not None
        assert result.corrected == 'hello'
        assert result.direction == 'ru_to_en'


class TestDetectorUnknownWord:
    def test_unknown_word_no_correction(self):
        """Unknown word in both languages should NOT be corrected."""
        det = _make_detector()
        for ch in 'xyzabc':
            det.feed_char(ch)
        result = det.feed_char(' ')
        assert result is None


class TestDetectorSkipPatterns:
    def test_short_word_skipped(self):
        det = _make_detector()
        det.feed_char('a')
        result = det.feed_char(' ')
        assert result is None  # length 1 < min_word_length=2

    def test_digit_word_skipped(self):
        det = _make_detector()
        for ch in 'test123':
            det.feed_char(ch)
        result = det.feed_char(' ')
        assert result is None


class TestDetectorForceCheck:
    def test_force_check_latin(self):
        det = _make_detector()
        for ch in 'ghbdtn':
            det.feed_char(ch)
        result = det.force_check()
        assert result is not None
        assert result.corrected == 'привет'

    def test_force_check_cyrillic(self):
        det = _make_detector()
        for ch in 'руддщ':
            det.feed_char(ch)
        result = det.force_check()
        assert result is not None
        assert result.corrected == 'hello'

    def test_force_check_empty_buffer(self):
        det = _make_detector()
        result = det.force_check()
        assert result is None

    def test_clear_buffer(self):
        det = _make_detector()
        for ch in 'ghb':
            det.feed_char(ch)
        det.clear_buffer()
        result = det.force_check()
        assert result is None
