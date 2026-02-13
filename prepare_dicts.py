#!/usr/bin/env python3
"""One-time script: download and prepare dictionaries for RuSwitch.

Downloads:
  - Russian words from danakt/russian-words (OpenCorpora, all word forms)
  - Russian base forms from hunspell-ru (LibreOffice)
  - English words from dwyl/english-words (GitHub)

Output:
  - dictionaries/ru_words.txt (~500K words including all common forms)
  - dictionaries/en_words.txt (~370K words)
"""

import re
import urllib.request
from pathlib import Path

DICT_DIR = Path(__file__).parent / 'dictionaries'

# OpenCorpora-based Russian word forms (CP1251 encoding!)
RU_FORMS_URL = 'https://raw.githubusercontent.com/danakt/russian-words/master/russian.txt'
# Hunspell-ru dictionary for base forms (UTF-8)
RU_HUNSPELL_URL = 'https://raw.githubusercontent.com/LibreOffice/dictionaries/master/ru_RU/ru_RU.dic'
# English words from dwyl (clean, one word per line)
EN_URL = 'https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt'


def download(url: str, encoding: str = 'utf-8') -> str:
    print(f'Downloading {url} ...')
    req = urllib.request.Request(url, headers={'User-Agent': 'RuSwitch/1.0'})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode(encoding, errors='replace')


def process_russian(forms_raw: str, hunspell_raw: str) -> list[str]:
    """Build comprehensive Russian dictionary from OpenCorpora forms + hunspell stems.

    Strategy:
    - All word forms up to 8 chars from OpenCorpora (covers common words)
    - Medium forms (9-12 chars) with common suffixes from OpenCorpora
    - All hunspell base forms (any length, for rare/long words)
    """
    words = set()

    # 1. Short forms from OpenCorpora (all forms up to 8 chars)
    for line in forms_raw.splitlines():
        w = line.strip().lower()
        if w and 2 <= len(w) <= 8 and re.fullmatch(r'[а-яё]+', w):
            words.add(w)

    # 2. Medium forms (9-12 chars) with common verb/noun suffixes
    common_suffixes = (
        'ать', 'ять', 'ить', 'еть', 'ова', 'ива', 'ыва',
        'ение', 'ание', 'ость', 'ство', 'ся',
        'ает', 'ают', 'ует', 'уют', 'ить',
    )
    for line in forms_raw.splitlines():
        w = line.strip().lower()
        if w and 9 <= len(w) <= 12 and re.fullmatch(r'[а-яё]+', w):
            if any(w.endswith(s) for s in common_suffixes):
                words.add(w)

    # 3. Hunspell base forms (any length)
    for line in hunspell_raw.splitlines():
        line = line.strip()
        if not line or line[0].isdigit():
            continue
        word = line.split('/')[0].strip()
        if word and re.fullmatch(r'[а-яёА-ЯЁ\-]+', word):
            words.add(word.lower())

    return sorted(words)


def process_english(raw: str) -> list[str]:
    """Process English word list: filter, deduplicate."""
    words = set()
    for line in raw.splitlines():
        word = line.strip()
        if word and len(word) >= 2 and word.isalpha():
            words.add(word.lower())
    return sorted(words)


def main():
    DICT_DIR.mkdir(parents=True, exist_ok=True)

    # Russian: OpenCorpora forms (CP1251) + hunspell stems (UTF-8)
    ru_forms = download(RU_FORMS_URL, encoding='cp1251')
    ru_hunspell = download(RU_HUNSPELL_URL, encoding='utf-8')
    ru_words = process_russian(ru_forms, ru_hunspell)
    ru_path = DICT_DIR / 'ru_words.txt'
    with open(ru_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(ru_words) + '\n')
    print(f'Russian: {len(ru_words)} words -> {ru_path}')

    # English
    en_raw = download(EN_URL)
    en_words = process_english(en_raw)
    en_path = DICT_DIR / 'en_words.txt'
    with open(en_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(en_words) + '\n')
    print(f'English: {len(en_words)} words -> {en_path}')

    print('Done!')


if __name__ == '__main__':
    main()
