import httpx
from bs4 import BeautifulSoup

from app.models.fighter import Fighter, Fight

BASE_URL = "http://ufcstats.com/statistics/fighters"
EVENT_URL = "http://ufcstats.com/statistics/events/completed"
UPCOMING_URL = "http://ufcstats.com/statistics/events/upcoming"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


async def fetch_page(url: str, params: dict = None) -> str:
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.text


def parse_fighter_row(row) -> dict:
    """Parse a single fighter row from the fighters list page."""
    cols = row.find_all("td")
    if len(cols) < 11:
        return None

    first_name = cols[0].get_text(strip=True)
    last_name = cols[1].get_text(strip=True)
    nickname = cols[2].get_text(strip=True)
    height = cols[3].get_text(strip=True)
    weight = cols[4].get_text(strip=True)
    reach = cols[5].get_text(strip=True)
    stance = cols[6].get_text(strip=True)
    wins = cols[7].get_text(strip=True)
    losses = cols[8].get_text(strip=True)
    draws = cols[9].get_text(strip=True)

    name = f"{first_name} {last_name}".strip()
    if not name:
        return None

    # Get detail link
    link_tag = cols[0].find("a")
    detail_url = link_tag["href"] if link_tag else ""

    return {
        "name": name,
        "nickname": nickname,
        "height": height,
        "weight_class": weight,
        "reach": reach,
        "stance": stance,
        "wins": int(wins) if wins.isdigit() else 0,
        "losses": int(losses) if losses.isdigit() else 0,
        "draws": int(draws) if draws.isdigit() else 0,
        "detail_url": detail_url,
    }


def _parse_age_from_dob(dob_str: str) -> int:
    """Parse 'Jul 14, 1988' to current age."""
    from datetime import datetime
    if not dob_str or dob_str == "--":
        return 0
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            dob = datetime.strptime(dob_str.strip(), fmt)
            today = datetime.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            return age
        except ValueError:
            continue
    return 0


def _parse_fight_date(date_str: str) -> str:
    """Parse 'Jul. 10, 2021' to 'YYYY-MM-DD'."""
    from datetime import datetime
    if not date_str:
        return ""
    date_str = date_str.strip().replace(".", "")
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            d = datetime.strptime(date_str, fmt)
            return d.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str


async def get_fighter_details(url: str) -> dict:
    """Fetch detailed stats for a single fighter."""
    html = await fetch_page(url)
    soup = BeautifulSoup(html, "lxml")

    stats = {}

    # Parse career statistics
    career_stats = soup.find_all("li", class_="b-list__box-list-item")
    for stat in career_stats:
        text = stat.get_text(strip=True)
        if "DOB" in text:
            dob = text.replace("DOB:", "").strip()
            stats["age"] = _parse_age_from_dob(dob)
        elif "SLpM" in text:
            val = text.replace("SLpM:", "").strip()
            stats["sig_strikes_landed_per_min"] = float(val) if val else 0.0
        elif "Str. Acc" in text:
            val = text.replace("Str. Acc.:", "").replace("%", "").strip()
            stats["sig_strike_accuracy"] = float(val) / 100 if val else 0.0
        elif "SApM" in text:
            val = text.replace("SApM:", "").strip()
            stats["sig_strikes_absorbed_per_min"] = float(val) if val else 0.0
        elif "Str. Def" in text:
            val = text.replace("Str. Def:", "").replace("Str. Def.:", "").replace("%", "").strip()
            stats["sig_strike_defense"] = float(val) / 100 if val else 0.0
        elif "TD Avg" in text:
            val = text.replace("TD Avg.:", "").strip()
            stats["takedown_avg"] = float(val) if val else 0.0
        elif "TD Acc" in text:
            val = text.replace("TD Acc.:", "").replace("%", "").strip()
            stats["takedown_accuracy"] = float(val) / 100 if val else 0.0
        elif "TD Def" in text:
            val = text.replace("TD Def.:", "").replace("TD Def:", "").replace("%", "").strip()
            stats["takedown_defense"] = float(val) / 100 if val else 0.0
        elif "Sub. Avg" in text:
            val = text.replace("Sub. Avg.:", "").strip()
            stats["submission_avg"] = float(val) if val else 0.0

    # Parse win methods from record section
    record_section = soup.find("div", class_="b-list__info-box")
    if record_section:
        items = record_section.find_all("li")
        for item in items:
            text = item.get_text(strip=True)
            if "by KO/TKO" in text.replace("\n", " "):
                parts = text.split(":")
                if len(parts) > 1:
                    val = parts[-1].strip()
                    stats["ko_wins"] = int(val) if val.isdigit() else 0
            elif "by Sub" in text.replace("\n", " "):
                parts = text.split(":")
                if len(parts) > 1:
                    val = parts[-1].strip()
                    stats["sub_wins"] = int(val) if val.isdigit() else 0
            elif "by Dec" in text.replace("\n", " "):
                parts = text.split(":")
                if len(parts) > 1:
                    val = parts[-1].strip()
                    stats["dec_wins"] = int(val) if val.isdigit() else 0

    # Parse full fight history
    recent_fights = []
    opponents = []  # list of opponent names (all fights)
    head_to_head = {}  # opponent_name -> {"wins": N, "losses": N}
    last_fight_date = ""

    fight_rows = soup.find_all("tr", class_="b-fight-details__table-row")
    # Skip header row (first match usually has links)
    data_rows = [r for r in fight_rows if r.find_all("td")]

    for idx, row in enumerate(data_rows):
        cols = row.find_all("td")
        if len(cols) < 7:
            continue

        result_text = cols[0].get_text(strip=True).upper()
        if result_text in ("WIN", "W"):
            result = "W"
        elif result_text in ("LOSS", "L"):
            result = "L"
        elif result_text in ("DRAW", "D", "NC"):
            result = "D"
        else:
            continue

        # First 5 fights → recent_fights
        if len(recent_fights) < 5:
            recent_fights.append(result)

        # Extract opponent name (2nd fighter link in cols[1])
        fighter_links = cols[1].find_all("a")
        if len(fighter_links) >= 2:
            opponent_name = fighter_links[1].get_text(strip=True)
            if opponent_name:
                opponents.append(opponent_name)
                # H2H tracking
                if opponent_name not in head_to_head:
                    head_to_head[opponent_name] = {"wins": 0, "losses": 0}
                if result == "W":
                    head_to_head[opponent_name]["wins"] += 1
                elif result == "L":
                    head_to_head[opponent_name]["losses"] += 1

        # Last fight date (first row = most recent)
        if idx == 0 and len(cols) > 6:
            event_text = cols[6].get_text(strip=True)
            # Format: "UFC 264: Poirier vs. McGregor 3Jul. 10, 2021"
            # Date pattern is at the end
            import re as _re
            m = _re.search(r"([A-Za-z]+\.?\s+\d+,?\s+\d{4})$", event_text)
            if m:
                last_fight_date = _parse_fight_date(m.group(1))

    stats["recent_fights"] = recent_fights
    stats["opponents"] = opponents
    stats["head_to_head"] = head_to_head
    stats["last_fight_date"] = last_fight_date

    # Calculate win/loss streak
    streak = 0
    for r in recent_fights:
        if r == "W":
            if streak >= 0:
                streak += 1
            else:
                break
        elif r == "L":
            if streak <= 0:
                streak -= 1
            else:
                break
        else:
            break
    stats["recent_win_streak"] = streak

    return stats


def _parse_height(height_str: str) -> float:
    """Parse height string like '5\\' 9\"' to total inches."""
    import re
    match = re.search(r"(\d+)'\s*(\d+)", height_str)
    if match:
        feet = int(match.group(1))
        inches = int(match.group(2))
        return feet * 12 + inches
    return 0.0


def _parse_reach(reach_str: str) -> float:
    """Parse reach string like '74.0\"' to inches."""
    import re
    match = re.search(r"([\d.]+)", reach_str)
    if match:
        return float(match.group(1))
    return 0.0


def _determine_style(fighter_data: dict) -> str:
    """Determine fighter style based on stats."""
    td_avg = fighter_data.get("takedown_avg", 0)
    sub_avg = fighter_data.get("submission_avg", 0)
    slpm = fighter_data.get("sig_strikes_landed_per_min", 0)

    grappling_score = td_avg * 2 + sub_avg * 3
    striking_score = slpm

    if grappling_score > striking_score * 0.8 and grappling_score > 2:
        return "grappler"
    elif striking_score > grappling_score * 1.5 and striking_score > 3:
        return "striker"
    else:
        return "balanced"


# In-memory cache of all fighters for fast suggestions
_fighter_cache: list[dict] = []
_cache_loaded = False


async def load_fighter_cache():
    """Load all UFC fighters into memory for fast search."""
    global _fighter_cache, _cache_loaded
    if _cache_loaded:
        return

    all_fighters = []
    for char in "abcdefghijklmnopqrstuvwxyz":
        try:
            html = await fetch_page(BASE_URL, params={"char": char, "page": "all"})
            soup = BeautifulSoup(html, "lxml")
            rows = soup.find_all("tr", class_="b-statistics__table-row")
            for row in rows:
                data = parse_fighter_row(row)
                if data:
                    all_fighters.append(data)
        except Exception:
            continue

    _fighter_cache = all_fighters
    _cache_loaded = True


async def suggest_fighters(query: str, limit: int = 10) -> list[dict]:
    """Search for UFC fighters matching a partial name query."""
    query = query.strip().lower()
    if not query:
        return []

    await load_fighter_cache()

    results = []
    for data in _fighter_cache:
        name_lower = data["name"].lower()
        nickname_lower = data["nickname"].lower()
        if query in name_lower or query in nickname_lower or any(
            part.startswith(query) for part in name_lower.split()
        ):
            results.append({
                "name": data["name"],
                "nickname": data["nickname"],
                "record": f"{data['wins']}-{data['losses']}-{data['draws']}",
                "weight_class": data["weight_class"],
            })
            if len(results) >= limit:
                break

    return results


async def search_fighter(name: str) -> Fighter | None:
    """Search for a UFC fighter by name and return their stats."""
    parts = name.strip().split()
    if not parts:
        return None

    target = name.lower().strip()

    # Try multiple character pages to find the fighter
    chars_to_try = set()
    chars_to_try.add(parts[0][0].lower())  # first name initial
    if len(parts) > 1:
        chars_to_try.add(parts[-1][0].lower())  # last name initial

    for char in chars_to_try:
        html = await fetch_page(BASE_URL, params={"char": char, "page": "all"})
        soup = BeautifulSoup(html, "lxml")
        rows = soup.find_all("tr", class_="b-statistics__table-row")

        for row in rows:
            data = parse_fighter_row(row)
            if not data:
                continue

            name_lower = data["name"].lower()
            # Exact match or partial match
            if name_lower == target or target in name_lower:
                detail_url = data.pop("detail_url", "")

                fighter_data = {
                    "name": data["name"],
                    "nickname": data["nickname"],
                    "height": data["height"],
                    "reach": data["reach"],
                    "weight_class": data["weight_class"],
                    "stance": data["stance"],
                    "wins": data["wins"],
                    "losses": data["losses"],
                    "draws": data["draws"],
                    "record": f"{data['wins']}-{data['losses']}-{data['draws']}",
                    "organization": "UFC",
                }

                if detail_url:
                    details = await get_fighter_details(detail_url)
                    fighter_data.update(details)

                # Compute opponent_avg_win_rate using cache
                opponents = fighter_data.pop("opponents", [])
                if opponents:
                    opp_rates = []
                    await load_fighter_cache()
                    # Build lookup map
                    cache_map = {f["name"].lower(): f for f in _fighter_cache}
                    for opp_name in opponents:
                        opp = cache_map.get(opp_name.lower())
                        if opp:
                            total = opp["wins"] + opp["losses"] + opp["draws"]
                            if total > 0:
                                opp_rates.append(opp["wins"] / total)
                    if opp_rates:
                        fighter_data["opponent_avg_win_rate"] = sum(opp_rates) / len(opp_rates)
                    else:
                        fighter_data["opponent_avg_win_rate"] = -1.0
                else:
                    fighter_data["opponent_avg_win_rate"] = -1.0

                # Parse height to inches
                fighter_data["height_inches"] = _parse_height(data["height"])
                # Parse reach to inches
                fighter_data["reach_inches"] = _parse_reach(data["reach"])
                # Determine fighting style
                fighter_data["style"] = _determine_style(fighter_data)

                return Fighter(**fighter_data)

    return None


async def get_upcoming_events() -> list[dict]:
    """Fetch upcoming UFC events and their fight cards."""
    html = await fetch_page(UPCOMING_URL)
    soup = BeautifulSoup(html, "lxml")

    events = []
    rows = soup.find_all("tr", class_="b-statistics__table-row")

    for row in rows:
        link = row.find("a", class_="b-link")
        if not link:
            continue

        event_name = link.get_text(strip=True)
        event_url = link.get("href", "")

        date_col = row.find("span", class_="b-statistics__date")
        event_date = date_col.get_text(strip=True) if date_col else ""

        if event_name and event_url:
            events.append({
                "name": event_name,
                "date": event_date,
                "url": event_url,
            })

    return events


async def get_event_fights(event_url: str) -> list[Fight]:
    """Fetch fight card for a specific event."""
    html = await fetch_page(event_url)
    soup = BeautifulSoup(html, "lxml")

    fights = []

    # Get event name
    event_name_tag = soup.find("h2", class_="b-content__title")
    event_name = event_name_tag.get_text(strip=True) if event_name_tag else ""

    # Get event date
    date_items = soup.find_all("li", class_="b-list__box-list-item")
    event_date = ""
    for item in date_items:
        if "Date:" in item.get_text():
            event_date = item.get_text().replace("Date:", "").strip()
            break

    rows = soup.find_all("tr", class_="b-fight-details__table-row")
    for row in rows:
        fighters = row.find_all("a", class_="b-link")
        if len(fighters) >= 2:
            fighter_a = fighters[0].get_text(strip=True)
            fighter_b = fighters[1].get_text(strip=True)

            weight_col = row.find("td", class_="b-fight-details__table-col")
            weight_class = ""
            cols = row.find_all("td")
            if len(cols) >= 7:
                weight_class = cols[6].get_text(strip=True)

            fights.append(Fight(
                event_name=event_name,
                event_date=event_date,
                fighter_a=fighter_a,
                fighter_b=fighter_b,
                weight_class=weight_class,
                organization="UFC",
            ))

    return fights
