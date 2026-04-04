"""English name to Katakana approximate transliteration."""

# Common syllable/sound mappings for MMA fighter names
_REPLACEMENTS = [
    # Double consonants / special combos first (order matters)
    ("shch", "シチ"), ("tch", "ッチ"), ("sch", "シュ"),
    ("sha", "シャ"), ("shi", "シ"), ("shu", "シュ"), ("she", "シェ"), ("sho", "ショ"),
    ("cha", "チャ"), ("chi", "チ"), ("chu", "チュ"), ("che", "チェ"), ("cho", "チョ"),
    ("tha", "サ"), ("thi", "シ"), ("thu", "ス"), ("the", "ザ"), ("tho", "ソ"),
    ("kha", "ハ"), ("khi", "ヒ"), ("khu", "フ"), ("khe", "ヘ"), ("kho", "ホ"),
    ("pha", "ファ"), ("phi", "フィ"), ("phu", "フ"), ("phe", "フェ"), ("pho", "フォ"),
    ("tsu", "ツ"), ("dzu", "ヅ"),
    ("ja", "ジャ"), ("ji", "ジ"), ("ju", "ジュ"), ("je", "ジェ"), ("jo", "ジョ"),
    ("ga", "ガ"), ("gi", "ギ"), ("gu", "グ"), ("ge", "ゲ"), ("go", "ゴ"),
    ("za", "ザ"), ("zi", "ジ"), ("zu", "ズ"), ("ze", "ゼ"), ("zo", "ゾ"),
    ("da", "ダ"), ("di", "ディ"), ("du", "ドゥ"), ("de", "デ"), ("do", "ド"),
    ("ba", "バ"), ("bi", "ビ"), ("bu", "ブ"), ("be", "ベ"), ("bo", "ボ"),
    ("pa", "パ"), ("pi", "ピ"), ("pu", "プ"), ("pe", "ペ"), ("po", "ポ"),
    ("fa", "ファ"), ("fi", "フィ"), ("fu", "フ"), ("fe", "フェ"), ("fo", "フォ"),
    ("va", "ヴァ"), ("vi", "ヴィ"), ("vu", "ヴ"), ("ve", "ヴェ"), ("vo", "ヴォ"),
    ("wa", "ワ"), ("wi", "ウィ"), ("wu", "ウ"), ("we", "ウェ"), ("wo", "ウォ"),
    ("ya", "ヤ"), ("yi", "イ"), ("yu", "ユ"), ("ye", "イェ"), ("yo", "ヨ"),
    ("la", "ラ"), ("li", "リ"), ("lu", "ル"), ("le", "レ"), ("lo", "ロ"),
    ("ra", "ラ"), ("ri", "リ"), ("ru", "ル"), ("re", "レ"), ("ro", "ロ"),
    ("ka", "カ"), ("ki", "キ"), ("ku", "ク"), ("ke", "ケ"), ("ko", "コ"),
    ("sa", "サ"), ("si", "シ"), ("su", "ス"), ("se", "セ"), ("so", "ソ"),
    ("ta", "タ"), ("ti", "ティ"), ("tu", "トゥ"), ("te", "テ"), ("to", "ト"),
    ("na", "ナ"), ("ni", "ニ"), ("nu", "ヌ"), ("ne", "ネ"), ("no", "ノ"),
    ("ha", "ハ"), ("hi", "ヒ"), ("hu", "フ"), ("he", "ヘ"), ("ho", "ホ"),
    ("ma", "マ"), ("mi", "ミ"), ("mu", "ム"), ("me", "メ"), ("mo", "モ"),
    # Common endings / standalone consonants
    ("ng", "ング"), ("nk", "ンク"), ("ck", "ック"),
    ("ll", "ル"), ("ss", "ス"), ("tt", "ット"), ("ff", "フ"), ("pp", "ップ"),
    ("rr", "ル"), ("nn", "ン"), ("mm", "ム"), ("dd", "ッド"), ("bb", "ッブ"),
    ("gg", "ッグ"),
    ("n", "ン"), ("m", "ム"),
    ("a", "ア"), ("i", "イ"), ("u", "ウ"), ("e", "エ"), ("o", "オ"),
    ("b", "ブ"), ("c", "ク"), ("d", "ド"), ("f", "フ"), ("g", "グ"),
    ("h", "フ"), ("j", "ジ"), ("k", "ク"), ("l", "ル"), ("p", "プ"),
    ("q", "ク"), ("r", "ル"), ("s", "ス"), ("t", "ト"), ("v", "ヴ"),
    ("w", "ウ"), ("x", "クス"), ("y", "イ"), ("z", "ズ"),
]


def english_to_katakana(name: str) -> str:
    """Convert an English name to approximate Katakana.

    This is a rough transliteration, not a perfect translation.
    Good enough for search matching purposes.
    """
    result_parts = []
    for word in name.split():
        text = word.lower()
        katakana = ""
        i = 0
        while i < len(text):
            matched = False
            # Try longest match first (up to 4 chars)
            for length in (4, 3, 2, 1):
                chunk = text[i:i + length]
                for eng, kat in _REPLACEMENTS:
                    if chunk == eng:
                        katakana += kat
                        i += length
                        matched = True
                        break
                if matched:
                    break
            if not matched:
                i += 1  # skip unknown char

        result_parts.append(katakana)

    return "・".join(result_parts)
