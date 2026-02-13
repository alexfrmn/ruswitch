"""QWERTY <-> JCUKEN keyboard layout mapping tables."""

# Physical key positions: EN char -> RU char
EN_TO_RU = {
    'q': 'й', 'w': 'ц', 'e': 'у', 'r': 'к', 't': 'е', 'y': 'н', 'u': 'г',
    'i': 'ш', 'o': 'щ', 'p': 'з', '[': 'х', ']': 'ъ', 'a': 'ф', 's': 'ы',
    'd': 'в', 'f': 'а', 'g': 'п', 'h': 'р', 'j': 'о', 'k': 'л', 'l': 'д',
    ';': 'ж', "'": 'э', 'z': 'я', 'x': 'ч', 'c': 'с', 'v': 'м', 'b': 'и',
    'n': 'т', 'm': 'ь', ',': 'б', '.': 'ю', '/': '.',
    '`': 'ё',
    # Shifted
    'Q': 'Й', 'W': 'Ц', 'E': 'У', 'R': 'К', 'T': 'Е', 'Y': 'Н', 'U': 'Г',
    'I': 'Ш', 'O': 'Щ', 'P': 'З', '{': 'Х', '}': 'Ъ', 'A': 'Ф', 'S': 'Ы',
    'D': 'В', 'F': 'А', 'G': 'П', 'H': 'Р', 'J': 'О', 'K': 'Л', 'L': 'Д',
    ':': 'Ж', '"': 'Э', 'Z': 'Я', 'X': 'Ч', 'C': 'С', 'V': 'М', 'B': 'И',
    'N': 'Т', 'M': 'Ь', '<': 'Б', '>': 'Ю', '?': ',',
    '~': 'Ё',
}

# Reverse mapping: RU char -> EN char
RU_TO_EN = {v: k for k, v in EN_TO_RU.items()}


def remap_word(word: str, direction: str) -> str:
    """Remap a word character-by-character between layouts.

    Args:
        word: Input word to remap.
        direction: 'en_to_ru' or 'ru_to_en'.

    Returns:
        Remapped word. Characters without mapping are kept as-is.
    """
    table = EN_TO_RU if direction == 'en_to_ru' else RU_TO_EN
    return ''.join(table.get(ch, ch) for ch in word)


def detect_script(word: str) -> str:
    """Detect the script of a word.

    Returns:
        'latin' — all alphabetic chars are Latin
        'cyrillic' — all alphabetic chars are Cyrillic
        'mixed' — both Latin and Cyrillic present
        'other' — no alphabetic chars (digits, punctuation only)
    """
    has_latin = False
    has_cyrillic = False
    for ch in word:
        if ch.isalpha():
            # Cyrillic range: U+0400–U+04FF
            if '\u0400' <= ch <= '\u04ff':
                has_cyrillic = True
            else:
                has_latin = True
    if has_latin and has_cyrillic:
        return 'mixed'
    if has_latin:
        return 'latin'
    if has_cyrillic:
        return 'cyrillic'
    return 'other'
