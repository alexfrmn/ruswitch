#!/usr/bin/env python3
"""One-time script: download and prepare dictionaries for RuSwitch.

Downloads:
  - Russian words from hunspell-ru dictionary
  - English words from dwyl/english-words (GitHub)

Output:
  - dictionaries/ru_words.txt (~100K words)
  - dictionaries/en_words.txt (~50K words)
"""

import re
import urllib.request
from pathlib import Path

DICT_DIR = Path(__file__).parent / 'dictionaries'

# Hunspell-ru dictionary (raw .dic file from LibreOffice repo)
RU_URL = 'https://raw.githubusercontent.com/LibreOffice/dictionaries/master/ru_RU/ru_RU.dic'
# English words from dwyl (clean, one word per line)
EN_URL = 'https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt'


def download(url: str) -> str:
    print(f'Downloading {url} ...')
    req = urllib.request.Request(url, headers={'User-Agent': 'RuSwitch/1.0'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode('utf-8', errors='replace')


def process_russian(raw: str) -> list[str]:
    """Process hunspell .dic file: strip affix flags, deduplicate."""
    words = set()
    for line in raw.splitlines():
        line = line.strip()
        if not line or line[0].isdigit():
            continue
        # Hunspell format: word/flags
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

    # Russian
    ru_raw = download(RU_URL)
    ru_words = process_russian(ru_raw)
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
