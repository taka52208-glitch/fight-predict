"""Cache all RIZIN fighters with Japanese name mapping.

On first load, scrapes recent RIZIN events from Sherdog to build a
comprehensive fighter list with Japanese name lookups.
"""
import re
import httpx
from bs4 import BeautifulSoup

SHERDOG_BASE = "https://www.sherdog.com"
RIZIN_ORG_URL = "https://www.sherdog.com/organizations/Rizin-Fighting-Federation-10333"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Comprehensive manual mapping for RIZIN fighters (Japanese -> English)
# This covers fighters whose names can't be accurately converted by romaji
MANUAL_JP_MAP = {
    # Main RIZIN fighters
    "朝倉未来": "Mikuru Asakura",
    "朝倉海": "Kai Asakura",
    "堀口恭司": "Kyoji Horiguchi",
    "那須川天心": "Tenshin Nasukawa",
    "皇治": "Koji",
    "平本蓮": "Ren Hiramoto",
    "牛久絢太郎": "Juntaro Ushiku",
    "斎藤裕": "Yutaka Saito",
    "萩原京平": "Kyohei Hagiwara",
    "金太郎": "Kintaro",
    "扇久保博正": "Hiromasa Ougikubo",
    "元谷友貴": "Yuki Motoya",
    "石渡伸太郎": "Shintaro Ishiwatari",
    "矢地祐介": "Yusuke Yachi",
    "武田光司": "Koji Takeda",
    "安保瑠輝也": "Rukiya Anpo",
    "鈴木千裕": "Chihiro Suzuki",
    "久保優太": "Yuta Kubo",
    "所英男": "Hideo Tokoro",
    "五味隆典": "Takanori Gomi",
    "浅倉カンナ": "Kanna Asakura",
    "武尊": "Takeru",
    "白鳥大珠": "Taishu Shiratori",
    "中村K太郎": "K-Taro Nakamura",
    "瀧澤謙太": "Kenta Takizawa",
    "大尊伸光": "Nobumitsu Otaka",
    "中村優作": "Yusaku Nakamura",
    "佐々木憂流迦": "Ulka Sasaki",
    "太田忍": "Shinobu Ota",
    "井上直樹": "Naoki Inoue",
    "伊藤空也": "Kuya Ito",
    "弥益ドミネーター聡志": "Satoshi Yamasu",
    "摩嶋一整": "Issei Mashima",
    "徳留一樹": "Kazuki Tokudome",
    "大島沙緒里": "Saori Oshima",
    "浜崎朱加": "Ayaka Hamasaki",
    "山本美憂": "Miyuu Yamamoto",
    "RENA": "RENA",
    "レナ": "RENA",
    "YA-MAN": "YA-MAN",
    "ヤーマン": "YA-MAN",
    "シビサイ頌真": "Shoma Shibisai",
    "スダリオ剛": "Sudario Tsuyoshi",
    "加藤久輝": "Hisaki Kato",
    "中原由貴": "Yuki Nakahara",
    "大雅": "Taiga",
    "原口健飛": "Kento Haraguchi",
    "梅野源治": "Genji Umeno",
    "江幡塁": "Rui Ebata",
    "江幡睦": "Mutsuki Ebata",
    "秋元皓貴": "Kyoma Akimoto",
    "桜庭大世": "Taisei Sakuraba",
    "高木亮": "Ryo Takagi",
    "木村柊也": "Shuya Kimura",
    "小山慶人": "Keito Oyama",
    "伊藤裕樹": "Yuki Ito",
    "樫村仁之介": "Jinnosuke Kashimura",
    "佐藤将光": "Shoko Sato",
    "征矢貴": "Takaki Soya",
    "荒井仁": "Jo Arai",
    "成田宣則": "Noeru Narita",
    "金原正徳": "Masanori Kanehara",
    "中村大介": "Daisuke Nakamura",
    "北岡悟": "Satoru Kitaoka",
    "川名雄生": "Yuki Kawana",
    "倉本一真": "Kazuma Kuramoto",
    "クレベル・コイケ": "Kleber Koike",
    "クレベルコイケ": "Kleber Koike",
    "サトシ・ソウザ": "Roberto Satoshi Souza",
    "ホベルト・サトシ・ソウザ": "Roberto Satoshi Souza",
    "ヴガール・ケラモフ": "Vugar Keramov",
    "パトリック・ミックス": "Patrick Mix",
    "フアン・アーチュレッタ": "Juan Archuleta",
    "マネル・ケイプ": "Manel Kape",
    "ホベルト・デ・ソウザ": "Roberto de Souza",
    "トフィック・ムサエフ": "Tofiq Musayev",
    "ルイス・グスタボ": "Luiz Gustavo",
    "ヴィクトル・コレスニック": "Viktor Kolesnik",
    "カルロス・モタ": "Carlos Mota",
    # 追加選手
    "平良達郎": "Tatsuro Taira",
    "鶴屋怜": "Rei Tsuruya",
    "堀江圭功": "Yoshinori Horie",
    "手塚裕之": "Hiroyuki Tezuka",
    "藤田大和": "Yamato Fujita",
    "大塚隆史": "Takafumi Otsuka",
    "昇侍": "Shoji",
    "芦田崇宏": "Takahiro Ashida",
    "髙谷裕之": "Hiroyuki Takaya",
    "山本空良": "Sora Yamamoto",
    "倉本大悟": "Daigo Kuramoto",
    "後藤丈治": "Joji Goto",
    "後藤神龍誠": "Shinryusei Goto",
    "白川陸斗": "Rikuto Shirakawa",
    "中島太一": "Taichi Nakajima",
    "スパイク・カーライル": "Spike Carlyle",
    "ベラトール": "Bellator",
    "宇佐美正パトリック": "Sei Patrick Usami",
    "竿本樹生": "Tatsuki Saomoto",
    "青木真也": "Shinya Aoki",
    "川口雄介": "Yusuke Kawaguchi",
    "石司晃一": "Koichi Ishizuka",
    "中務修良": "Shura Nakazuma",
    "渡部修斗": "Shooto Watanabe",
    "今成正和": "Masakazu Imanari",
    "山本アーセン": "Asen Yamamoto",
    "才賀紀左衛門": "Kizaemon Saiga",
    "中村倫也": "Rin Nakamura",
    "斉藤裕": "Yutaka Saito",
    "朝倉": "Mikuru Asakura",

    # 外国人選手のカタカナ表記揺れ
    "サバテロ": "Danny Sabatello",
    "ダニーサバテロ": "Danny Sabatello",
    "ダニー・サバテロ": "Danny Sabatello",
    "ダニーサバテッロ": "Danny Sabatello",
    "ダニー・サバテッロ": "Danny Sabatello",
    "リッキーサバテロ": "Ricky Sabatello",
    "リッキー・サバテロ": "Ricky Sabatello",
    "リッキーサバテッロ": "Ricky Sabatello",
    "サバテッロ": "Danny Sabatello",
    "アーロン・ピコ": "Aaron Pico",
    "ピコ": "Aaron Pico",
    "ケラモフ": "Vugar Keramov",
    "ムサエフ": "Tofiq Musayev",
    "パトリシオ・フレイレ": "Patricio Freire",
    "ピットブル": "Patricio Freire",
    "AJ・マッキー": "AJ McKee",
    "マッキー": "AJ McKee",
    "ホリー・ホルム": "Holly Holm",
    "ジョン・ドッドソン": "John Dodson",
    "ドッドソン": "John Dodson",
    "堀口": "Kyoji Horiguchi",
    "クレベル": "Kleber Koike",
    "サトシ": "Roberto Satoshi Souza",
    # シェイドゥラエフ（表記揺れ）
    "シェイドゥラエフ": "Rajabali Shaidullaev",
    "シャイドゥラエフ": "Rajabali Shaidullaev",
    "シャイドゥルアエフ": "Rajabali Shaidullaev",
    "シェイドゥルアエフ": "Rajabali Shaidullaev",
    "ラジャバリ": "Rajabali Shaidullaev",
    "ラジャバリ・シェイドゥラエフ": "Rajabali Shaidullaev",
}

# Hiragana reading -> same English mapping
# Allows searching by hiragana input
HIRAGANA_MAP = {
    "あさくらみくる": "Mikuru Asakura",
    "あさくらかい": "Kai Asakura",
    "あさくら": "Mikuru Asakura",
    "ほりぐちきょうじ": "Kyoji Horiguchi",
    "ほりぐち": "Kyoji Horiguchi",
    "なすかわてんしん": "Tenshin Nasukawa",
    "てんしん": "Tenshin Nasukawa",
    "ひらもとれん": "Ren Hiramoto",
    "ひらもと": "Ren Hiramoto",
    "うしくじゅんたろう": "Juntaro Ushiku",
    "うしく": "Juntaro Ushiku",
    "さいとうゆたか": "Yutaka Saito",
    "さいとう": "Yutaka Saito",
    "はぎわらきょうへい": "Kyohei Hagiwara",
    "はぎわら": "Kyohei Hagiwara",
    "きんたろう": "Kintaro",
    "おうぎくぼひろまさ": "Hiromasa Ougikubo",
    "おうぎくぼ": "Hiromasa Ougikubo",
    "もとやゆうき": "Yuki Motoya",
    "もとや": "Yuki Motoya",
    "いしわたりしんたろう": "Shintaro Ishiwatari",
    "いしわたり": "Shintaro Ishiwatari",
    "やちゆうすけ": "Yusuke Yachi",
    "やち": "Yusuke Yachi",
    "たけだこうじ": "Koji Takeda",
    "たけだ": "Koji Takeda",
    "あんぽるきや": "Rukiya Anpo",
    "あんぽ": "Rukiya Anpo",
    "すずきちひろ": "Chihiro Suzuki",
    "すずき": "Chihiro Suzuki",
    "くぼゆうた": "Yuta Kubo",
    "くぼ": "Yuta Kubo",
    "ところひでお": "Hideo Tokoro",
    "ところ": "Hideo Tokoro",
    "ごみたかのり": "Takanori Gomi",
    "ごみ": "Takanori Gomi",
    "あさくらかんな": "Kanna Asakura",
    "たける": "Takeru",
    "しびさいしょうま": "Shoma Shibisai",
    "しびさい": "Shoma Shibisai",
    "すだりおつよし": "Sudario Tsuyoshi",
    "すだりお": "Sudario Tsuyoshi",
    "おおしまさおり": "Saori Oshima",
    "おおしま": "Saori Oshima",
    "はまさきあやか": "Ayaka Hamasaki",
    "はまさき": "Ayaka Hamasaki",
    "やまもとみゆう": "Miyuu Yamamoto",
    "おおたしのぶ": "Shinobu Ota",
    "おおた": "Shinobu Ota",
    "いのうえなおき": "Naoki Inoue",
    "いのうえ": "Naoki Inoue",
    "あきもときょうま": "Kyoma Akimoto",
    "あきもと": "Kyoma Akimoto",
    "さくらばたいせい": "Taisei Sakuraba",
    "さくらば": "Taisei Sakuraba",
    "たかぎりょう": "Ryo Takagi",
    "きむらしゅうや": "Shuya Kimura",
    "こやまけいと": "Keito Oyama",
    "こやま": "Keito Oyama",
    "かしむらじんのすけ": "Jinnosuke Kashimura",
    "さとうしょうこう": "Shoko Sato",
    "あらいじょう": "Jo Arai",
    "なりたのえる": "Noeru Narita",
    "かねはらまさのり": "Masanori Kanehara",
    "かねはら": "Masanori Kanehara",
    "きたおかさとる": "Satoru Kitaoka",
    "きたおか": "Satoru Kitaoka",
    "くらもとかずま": "Kazuma Kuramoto",
    "くらもと": "Kazuma Kuramoto",
    "うめのげんじ": "Genji Umeno",
    "うめの": "Genji Umeno",
    "はらぐちけんと": "Kento Haraguchi",
    "はらぐち": "Kento Haraguchi",
    "なかむらだいすけ": "Daisuke Nakamura",
    "しらとりたいしゅ": "Taishu Shiratori",
    "しらとり": "Taishu Shiratori",
    "ささきうるか": "Ulka Sasaki",
    "ささき": "Ulka Sasaki",
    "ごとうじょうじ": "Joji Goto",
    "ごとう": "Joji Goto",
    "ごとうしんりゅうせい": "Shinryusei Goto",
    "しらかわりくと": "Rikuto Shirakawa",
    "しらかわ": "Rikuto Shirakawa",
    "なかじまたいち": "Taichi Nakajima",
    "なかじま": "Taichi Nakajima",
    "あおきしんや": "Shinya Aoki",
    "あおき": "Shinya Aoki",
    "いまなりまさかず": "Masakazu Imanari",
    "いまなり": "Masakazu Imanari",
    "やまもとあーせん": "Asen Yamamoto",
    "なかむらりんや": "Rin Nakamura",
    "こうじ": "Koji",
    "だにーさばてろ": "Danny Sabatello",
    "だにーさばてっろ": "Danny Sabatello",
    "さばてろ": "Danny Sabatello",
    "さばてっろ": "Danny Sabatello",
    "りっきーさばてろ": "Ricky Sabatello",
    "りっきーさばてっろ": "Ricky Sabatello",
}

# Reverse map: English -> Japanese
MANUAL_EN_MAP = {v: k for k, v in MANUAL_JP_MAP.items()}

# Runtime cache
_rizin_fighters: list[dict] = []  # {"name": "English", "jp_name": "日本語", "url": "..."}
_cache_loaded = False


async def _fetch_page(url: str) -> str:
    async with httpx.AsyncClient(timeout=30, headers=HEADERS, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


def _english_to_japanese(name: str) -> str:
    """Convert an English name to Japanese katakana approximation."""
    # Check manual mapping first
    if name in MANUAL_EN_MAP:
        return MANUAL_EN_MAP[name]

    # Auto-generate katakana from English name
    from app.services.en_to_katakana import english_to_katakana
    return english_to_katakana(name)


async def load_rizin_fighters():
    """Load ALL RIZIN fighters from all events on Sherdog."""
    global _rizin_fighters, _cache_loaded
    if _cache_loaded:
        return

    fighters = {}  # name -> {"name", "jp_name", "katakana", "url"}

    # Add all manually mapped fighters first
    for jp, en in MANUAL_JP_MAP.items():
        if en not in fighters:
            fighters[en] = {
                "name": en,
                "jp_name": jp,
                "katakana": "",
                "url": "",
            }

    # Get ALL RIZIN events from Sherdog
    try:
        html = await _fetch_page(RIZIN_ORG_URL)
        soup = BeautifulSoup(html, "lxml")

        event_links = soup.find_all("a", href=lambda h: h and "/events/" in str(h))
        event_urls = []
        seen = set()
        for link in event_links:
            href = link.get("href", "")
            name = link.get_text(strip=True)
            if href not in seen and name and "rizin" in name.lower():
                seen.add(href)
                url = SHERDOG_BASE + href if href.startswith("/") else href
                event_urls.append(url)

        # Scrape fighters from ALL events
        for event_url in event_urls:
            try:
                html = await _fetch_page(event_url)
                soup = BeautifulSoup(html, "lxml")
                fighter_links = soup.find_all("a", href=lambda h: h and "/fighter/" in str(h))

                for flink in fighter_links:
                    fname = flink.get_text(strip=True)
                    fhref = flink.get("href", "")
                    if not fname or len(fname) < 3 or fname in fighters:
                        continue
                    # Fix concatenated names like "KyomaAkimoto"
                    fname = re.sub(r"([a-z])([A-Z])", r"\1 \2", fname)

                    furl = SHERDOG_BASE + fhref if fhref.startswith("/") else fhref
                    jp_name = _english_to_japanese(fname)
                    # Also generate katakana for non-Japanese names
                    katakana = ""
                    if jp_name and jp_name == fname:
                        jp_name = ""  # conversion returned same string
                    if not jp_name or jp_name == fname:
                        from app.services.en_to_katakana import english_to_katakana
                        katakana = english_to_katakana(fname)

                    fighters[fname] = {
                        "name": fname,
                        "jp_name": jp_name if jp_name else katakana,
                        "katakana": katakana,
                        "url": furl,
                    }
            except Exception:
                continue

    except Exception:
        pass

    _rizin_fighters = list(fighters.values())
    _cache_loaded = True


async def suggest_rizin_all(query: str, limit: int = 10) -> list[dict]:
    """Suggest RIZIN fighters from cache. Supports Japanese, hiragana, katakana, and English."""
    await load_rizin_fighters()

    query = query.strip()
    query_lower = query.lower()
    if not query:
        return []

    results = []
    seen = set()

    # 1. Check MANUAL_JP_MAP (kanji + katakana entries)
    for jp_key, en_name in MANUAL_JP_MAP.items():
        if query in jp_key or query_lower in jp_key.lower():
            if en_name not in seen:
                seen.add(en_name)
                jp_display = MANUAL_EN_MAP.get(en_name, jp_key)
                results.append({
                    "name": en_name,
                    "nickname": jp_display,
                    "record": "",
                    "weight_class": "",
                })
                if len(results) >= limit:
                    return results

    # 2. Check hiragana map
    for hiragana, en_name in HIRAGANA_MAP.items():
        if query_lower in hiragana:
            if en_name not in seen:
                seen.add(en_name)
                jp_name = MANUAL_EN_MAP.get(en_name, "")
                results.append({
                    "name": en_name,
                    "nickname": jp_name,
                    "record": "",
                    "weight_class": "",
                })
                if len(results) >= limit:
                    return results

    # 3. Search cached fighters (English name + katakana match)
    for f in _rizin_fighters:
        if f["name"] in seen:
            continue
        name_lower = f["name"].lower()
        jp_name = f.get("jp_name", "") or ""
        katakana = f.get("katakana", "") or ""

        if (query_lower in name_lower
                or query in jp_name
                or query in katakana
                or any(part.startswith(query_lower) for part in name_lower.split())):
            seen.add(f["name"])
            display_name = jp_name or katakana
            results.append({
                "name": f["name"],
                "nickname": display_name,
                "record": "",
                "weight_class": "",
            })
            if len(results) >= limit:
                break

    return results


async def preload_rizin_cache():
    """Pre-load RIZIN fighter cache at startup."""
    await load_rizin_fighters()


def get_all_jp_names() -> dict[str, str]:
    """Return the full Japanese->English mapping including manual + hiragana."""
    combined = dict(MANUAL_JP_MAP)
    combined.update(HIRAGANA_MAP)
    return combined
