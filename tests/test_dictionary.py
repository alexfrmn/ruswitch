"""Tests for dictionary module."""

import sys
import os
import json
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pathlib import Path
from config import Config
from dictionary import DictionaryManager


def _make_dict(ru=None, en=None, threshold=3):
    """Create a DictionaryManager with temp directories."""
    tmpdir = tempfile.mkdtemp()
    dict_dir = Path(tmpdir) / 'dicts'
    dict_dir.mkdir()
    (dict_dir / 'ru_words.txt').write_text(
        '\n'.join(ru or ['привет', 'мир']), encoding='utf-8')
    (dict_dir / 'en_words.txt').write_text(
        '\n'.join(en or ['hello', 'world']), encoding='utf-8')
    # Override user data path to temp
    config = Config(auto_learn_threshold=threshold)
    dm = DictionaryManager(config, dict_dir=dict_dir)
    dm._user_data_path = Path(tmpdir) / 'user_words.json'
    return dm


class TestDictionaryLoad:
    def test_check_ru_word(self):
        dm = _make_dict()
        assert dm.check('привет', 'ru') is True
        assert dm.check('Привет', 'ru') is True  # case-insensitive

    def test_check_en_word(self):
        dm = _make_dict()
        assert dm.check('hello', 'en') is True
        assert dm.check('Hello', 'en') is True

    def test_missing_word(self):
        dm = _make_dict()
        assert dm.check('неизвестное', 'ru') is False
        assert dm.check('unknown', 'en') is False


class TestDictionaryUserWords:
    def test_add_word(self):
        dm = _make_dict()
        dm.add_word('тест', 'ru')
        assert dm.check('тест', 'ru') is True

    def test_remove_word(self):
        dm = _make_dict()
        dm.add_word('тест', 'ru')
        dm.remove_word('тест', 'ru')
        assert dm.check('тест', 'ru') is False

    def test_get_user_words(self):
        dm = _make_dict()
        dm.add_word('бот', 'ru')
        dm.add_word('api', 'en')
        assert 'бот' in dm.get_user_words('ru')
        assert 'api' in dm.get_user_words('en')


class TestAutoLearn:
    def test_learn_after_threshold(self):
        dm = _make_dict(threshold=3)
        # Record "новое" 3 times
        assert dm.record_word('новое', 'ru') is False
        assert dm.record_word('новое', 'ru') is False
        assert dm.record_word('новое', 'ru') is True  # learned!
        assert dm.check('новое', 'ru') is True

    def test_no_learn_below_threshold(self):
        dm = _make_dict(threshold=3)
        dm.record_word('новое', 'ru')
        dm.record_word('новое', 'ru')
        assert dm.check('новое', 'ru') is False

    def test_known_word_not_counted(self):
        dm = _make_dict()
        # "привет" is already in dict
        result = dm.record_word('привет', 'ru')
        assert result is False


class TestDictionaryPersistence:
    def test_save_and_reload(self):
        dm = _make_dict()
        dm.add_word('тест', 'ru')
        dm._save_user_data()
        # Reload
        dm2 = _make_dict()
        dm2._user_data_path = dm._user_data_path
        dm2._load_user_data()
        assert dm2.check('тест', 'ru') is True


class TestDictionaryStats:
    def test_stats(self):
        dm = _make_dict()
        s = dm.stats
        assert s['ru_base'] == 2
        assert s['en_base'] == 2
        assert s['ru_user'] == 0
        assert s['en_user'] == 0
