"""Tests for keymap module."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from keymap import remap_word, detect_script, EN_TO_RU, RU_TO_EN


class TestRemapWord:
    def test_en_to_ru_basic(self):
        # "ghbdtn" on QWERTY = "привет" on JCUKEN
        assert remap_word('ghbdtn', 'en_to_ru') == 'привет'

    def test_ru_to_en_basic(self):
        # "руддщ" on JCUKEN = "hello" on QWERTY
        assert remap_word('руддщ', 'ru_to_en') == 'hello'

    def test_case_preserved(self):
        # "Ghbdtn" -> "Привет"
        assert remap_word('Ghbdtn', 'en_to_ru') == 'Привет'

    def test_uppercase(self):
        assert remap_word('GHBDTN', 'en_to_ru') == 'ПРИВЕТ'

    def test_roundtrip_en_ru_en(self):
        word = 'hello'
        remapped = remap_word(word, 'en_to_ru')
        back = remap_word(remapped, 'ru_to_en')
        assert back == word

    def test_roundtrip_ru_en_ru(self):
        word = 'привет'
        remapped = remap_word(word, 'ru_to_en')
        back = remap_word(remapped, 'en_to_ru')
        assert back == word

    def test_unmapped_chars_preserved(self):
        # Digits and symbols stay as-is
        assert remap_word('abc123', 'en_to_ru') == 'фис123'

    def test_empty_string(self):
        assert remap_word('', 'en_to_ru') == ''
        assert remap_word('', 'ru_to_en') == ''

    def test_special_chars(self):
        # Semicolon -> Ж
        assert remap_word(';', 'en_to_ru') == 'ж'
        assert remap_word('ж', 'ru_to_en') == ';'


class TestDetectScript:
    def test_latin(self):
        assert detect_script('hello') == 'latin'
        assert detect_script('Hello') == 'latin'
        assert detect_script('WORLD') == 'latin'

    def test_cyrillic(self):
        assert detect_script('привет') == 'cyrillic'
        assert detect_script('Мир') == 'cyrillic'

    def test_mixed(self):
        assert detect_script('helloМир') == 'mixed'

    def test_other(self):
        assert detect_script('12345') == 'other'
        assert detect_script('!@#$') == 'other'
        assert detect_script('') == 'other'


class TestMappingCompleteness:
    def test_all_en_to_ru_have_reverse(self):
        """Every EN->RU mapping should have a reverse RU->EN mapping."""
        for en_char, ru_char in EN_TO_RU.items():
            assert ru_char in RU_TO_EN, f'Missing reverse: {ru_char} -> {en_char}'
            assert RU_TO_EN[ru_char] == en_char

    def test_full_qwerty_row_coverage(self):
        """All letter keys in QWERTY should be mapped."""
        qwerty = 'qwertyuiopasdfghjklzxcvbnm'
        for ch in qwerty:
            assert ch in EN_TO_RU, f'Missing mapping for: {ch}'
            assert ch.upper() in EN_TO_RU, f'Missing mapping for: {ch.upper()}'
