import re
import httpx
from bs4 import BeautifulSoup

from app.models.fighter import Fighter, Fight

SHERDOG_BASE = "https://www.sherdog.com"
SHERDOG_SEARCH = "https://www.sherdog.com/stats/fightfinder"
RIZIN_ORG_URL = "https://www.sherdog.com/organizations/Rizin-Fighting-Federation-10333"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


async def fetch_page(url: str, params: dict = None) -> str:
    async with httpx.AsyncClient(timeout=30, headers=HEADERS, follow_redirects=True) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.text


async def _search_sherdog_links(query: str) -> list[dict]:
    """Search Sherdog and return fighter links from search results only."""
    html = await fetch_page(SHERDOG_SEARCH, params={"SearchTxt": query})
    soup = BeautifulSoup(html, "lxml")

    results = []
    seen = set()
    query_lower = query.lower()

    query_words = query_lower.split()

    all_links = soup.find_all("a", href=lambda h: h and "/fighter/" in h)
    for link in all_links:
        name = link.get_text(strip=True)
        href = link.get("href", "")
        if not name or href in seen:
            continue
        # Word-level match: at least one query word must match a whole word in the name
        name_words = name.lower().split()
        if not any(qw in name_words for qw in query_words):
            continue
        seen.add(href)
        url = SHERDOG_BASE + href if href.startswith("/") else href
        results.append({"name": name, "url": url})

    return results


async def suggest_rizin_fighters(query: str, limit: int = 10) -> list[dict]:
    """Search for fighters on Sherdog matching a partial name query."""
    query = query.strip()
    if not query:
        return []

    # Try last name if full name given
    search_terms = [query]
    parts = query.split()
    if len(parts) > 1:
        search_terms.append(parts[-1])

    results = []
    seen = set()
    for term in search_terms:
        links = await _search_sherdog_links(term)
        for item in links:
            if item["name"] not in seen:
                seen.add(item["name"])
                results.append({
                    "name": item["name"],
                    "nickname": "",
                    "record": "",
                    "weight_class": "",
                })
            if len(results) >= limit:
                break
        if len(results) >= limit:
            break

    return results[:limit]


def _name_variants(name: str) -> list[str]:
    """Generate romaji variants for Japanese name spellings (e.g., Ogikubo/Ougikubo)."""
    variants = {name}
    # Long vowel variants: Ou <-> O, Oh <-> O, Uu <-> U, Ei <-> E
    for pair in [("ou", "o"), ("oh", "o"), ("uu", "u"), ("ei", "e"), ("aa", "a"), ("ii", "i")]:
        new_set = set()
        for v in variants:
            new_set.add(v.replace(pair[0], pair[1]))
            new_set.add(v.replace(pair[1], pair[0]))
            new_set.add(v.replace(pair[0].capitalize(), pair[1].capitalize()))
            new_set.add(v.replace(pair[1].capitalize(), pair[0].capitalize()))
        variants.update(new_set)
    return list(variants)


def _name_match_score(target: str, found: str) -> int:
    """Score how well two fighter names match. Higher = better. 0 = no match."""
    target = target.lower().strip()
    found = found.lower().strip()

    # Exact match
    if target == found:
        return 100

    target_parts = target.split()
    found_parts = found.split()

    # Full name match (first + last in either order)
    if len(target_parts) >= 2 and len(found_parts) >= 2:
        # Both first and last name must appear
        first_match = target_parts[0] in found_parts or any(
            fp.startswith(target_parts[0]) for fp in found_parts
        )
        last_match = target_parts[-1] in found_parts or any(
            fp.startswith(target_parts[-1]) for fp in found_parts
        )
        if first_match and last_match:
            return 90

    # Single name token: require exact word match, not substring
    if len(target_parts) == 1:
        if target_parts[0] in found_parts:
            return 70
        # Allow startswith for single names (e.g., "Ito" matches "Ito Yuki")
        if any(fp.startswith(target_parts[0]) and len(target_parts[0]) >= 4 for fp in found_parts):
            return 50

    # Last name exact match (only if target has multiple parts)
    if len(target_parts) >= 2 and target_parts[-1] in found_parts:
        return 40

    return 0


async def _has_rizin_history(url: str) -> bool:
    """Check if a fighter's Sherdog page mentions RIZIN in fight history."""
    try:
        html = await fetch_page(url)
        return "RIZIN" in html or "Rizin" in html
    except Exception:
        return False


async def search_fighter_sherdog(name: str, prefer_rizin: bool = False) -> dict | None:
    """Search for a fighter on Sherdog and return their profile URL.

    When prefer_rizin=True and multiple candidates share the same score,
    verify fight history and prefer the one with RIZIN bouts.
    """
    target = name.strip()
    parts = target.split()
    if not parts:
        return None

    # Build search terms: full name, reversed order, first name, last name
    search_terms = [target]
    if len(parts) > 1:
        reversed_name = " ".join(reversed(parts))
        search_terms.append(reversed_name)   # "Goto Shinryusei" ↔ "Shinryusei Goto"
        search_terms.append(parts[0])        # first name / ring name
        search_terms.append(parts[-1])       # last name
    # Deduplicate while preserving order
    seen_terms = set()
    unique_terms = []
    for t in search_terms:
        if t.lower() not in seen_terms:
            seen_terms.add(t.lower())
            unique_terms.append(t)
    search_terms = unique_terms

    # Collect all candidates with their scores
    candidates: list[tuple[int, dict]] = []
    seen_urls = set()

    for term in search_terms:
        links = await _search_sherdog_links(term)
        for item in links:
            if item["url"] in seen_urls:
                continue
            seen_urls.add(item["url"])
            # Score against both original and reversed name
            score = _name_match_score(target, item["name"])
            if len(parts) > 1:
                rev_score = _name_match_score(reversed_name, item["name"])
                score = max(score, rev_score)
            if score > 0:
                candidates.append((score, item))

    # Fallback: try romaji variants of the last name
    if not any(s >= 40 for s, _ in candidates) and len(parts) > 1:
        for variant in _name_variants(parts[-1]):
            if variant == parts[-1]:
                continue
            links = await _search_sherdog_links(variant)
            for item in links:
                if item["url"] in seen_urls:
                    continue
                seen_urls.add(item["url"])
                score = _name_match_score(target, item["name"])
                if score > 0:
                    candidates.append((score, item))

    if not candidates:
        return None

    # Sort by score descending
    candidates.sort(key=lambda x: x[0], reverse=True)
    best_score = candidates[0][0]

    if best_score < 40:
        return None

    # Filter to top-scoring candidates
    top = [item for score, item in candidates if score == best_score]

    # If only one top candidate or RIZIN check not needed, return it
    if len(top) == 1 or not prefer_rizin:
        return top[0]

    # Multiple candidates with same score → verify RIZIN history
    for item in top:
        if await _has_rizin_history(item["url"]):
            return item

    # None had RIZIN history, return first
    return top[0]


def _parse_height_inches(height_str: str) -> float:
    """Parse height like 5'10\" to inches."""
    match = re.search(r"(\d+)'(\d+)", height_str)
    if match:
        return int(match.group(1)) * 12 + int(match.group(2))
    return 0.0


def _estimate_stats(wins: int, losses: int, ko_wins: int, sub_wins: int,
                    dec_wins: int, total_fights: int, height: str) -> dict:
    """Estimate detailed fighting stats from win/loss record data.

    Uses statistical averages from MMA as baselines, then adjusts based on
    the fighter's win methods to create reasonable approximations.
    Returns is_estimated=True to flag these as estimates (not real data).
    """
    if total_fights == 0:
        return {
            "sig_strikes_landed_per_min": 0.0,
            "sig_strike_accuracy": 0.0,
            "sig_strikes_absorbed_per_min": 0.0,
            "sig_strike_defense": 0.0,
            "takedown_avg": 0.0,
            "takedown_accuracy": 0.0,
            "takedown_defense": 0.0,
            "submission_avg": 0.0,
            "height_inches": _parse_height_inches(height),
            "style": "balanced",
            "is_estimated": True,
        }

    win_rate = wins / total_fights
    ko_rate = ko_wins / wins if wins > 0 else 0.0
    sub_rate = sub_wins / wins if wins > 0 else 0.0
    dec_rate = dec_wins / wins if wins > 0 else 0.0

    # Ensure method rates don't exceed 1.0 (data error guard)
    total_method = ko_rate + sub_rate + dec_rate
    if total_method > 1.0 and total_method > 0:
        ko_rate /= total_method
        sub_rate /= total_method
        dec_rate /= total_method

    # MMA averages (from UFC data): SLpM ~3.5, SApM ~3.0, Str.Acc ~0.45
    # Adjust based on fighter profile

    # Striking: KO fighters land more per minute
    base_slpm = 3.5
    slpm = base_slpm * (1.0 + ko_rate * 0.5 - sub_rate * 0.15)
    slpm = max(1.5, min(6.5, slpm))

    # Accuracy: correlates with win rate and finishing ability
    acc = 0.44 + (win_rate - 0.5) * 0.12 + ko_rate * 0.04
    acc = max(0.32, min(0.60, acc))

    # Absorbed: inversely correlates with win rate
    base_sapm = 3.0
    sapm = base_sapm * (1.0 - (win_rate - 0.5) * 0.3)
    sapm = max(1.5, min(5.5, sapm))

    # Strike defense: better fighters defend better
    str_def = 0.52 + (win_rate - 0.5) * 0.16
    str_def = max(0.38, min(0.68, str_def))

    # Takedowns: grapplers/submission fighters take down more
    td_avg = 1.2 * (1.0 + sub_rate * 1.2)
    td_avg = max(0.0, min(4.0, td_avg))

    td_acc = 0.38 + sub_rate * 0.12 + (win_rate - 0.5) * 0.08
    td_acc = max(0.28, min(0.58, td_acc))

    # TD defense
    td_def = 0.58 + (win_rate - 0.5) * 0.12 + sub_rate * 0.04
    td_def = max(0.38, min(0.78, td_def))

    # Submissions per fight (scaled to per-fight frequency)
    sub_avg = (sub_wins / total_fights) * 1.5 if total_fights > 0 else 0.0
    sub_avg = max(0.0, min(2.5, sub_avg))

    # Determine style using clearer thresholds
    if ko_rate >= 0.5 and sub_rate < 0.2:
        style = "striker"
    elif sub_rate >= 0.3 or (td_avg > 2.0 and sub_rate >= 0.15):
        style = "grappler"
    else:
        style = "balanced"

    return {
        "sig_strikes_landed_per_min": round(slpm, 2),
        "sig_strike_accuracy": round(acc, 2),
        "sig_strikes_absorbed_per_min": round(sapm, 2),
        "sig_strike_defense": round(str_def, 2),
        "takedown_avg": round(td_avg, 2),
        "takedown_accuracy": round(td_acc, 2),
        "takedown_defense": round(td_def, 2),
        "submission_avg": round(sub_avg, 2),
        "height_inches": _parse_height_inches(height),
        "style": style,
        "is_estimated": True,
    }


def _extract_number(text: str) -> int:
    """Extract first number from text."""
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else 0


async def get_fighter_from_sherdog(url: str) -> Fighter | None:
    """Scrape fighter details from their Sherdog profile page."""
    html = await fetch_page(url)
    soup = BeautifulSoup(html, "lxml")

    # Name
    h1 = soup.find("h1")
    name = h1.get_text(strip=True) if h1 else ""
    if not name:
        return None

    # Nickname
    nickname = ""
    nick_el = soup.find("span", class_="nickname")
    if nick_el:
        nickname = nick_el.get_text(strip=True).strip('"')

    # Record - parse from the wins/losses section
    wins = 0
    losses = 0
    draws = 0
    ko_wins = 0
    sub_wins = 0
    dec_wins = 0

    # Find the win/loss stat block
    page_text = soup.get_text()

    # Parse Wins section
    wins_match = re.search(r"Wins\s*(\d+)", page_text)
    if wins_match:
        wins = int(wins_match.group(1))

    losses_match = re.search(r"Losses\s*(\d+)", page_text)
    if losses_match:
        losses = int(losses_match.group(1))

    draws_match = re.search(r"Draws\s*(\d+)", page_text)
    if draws_match:
        draws = int(draws_match.group(1))

    # Win methods - look for KO/TKO, SUBMISSIONS, DECISIONS after "Wins"
    # Text has newlines between values: "Wins\n19\n\nKO / TKO\n\n9\n..."
    wins_section = re.search(
        r"Wins\s+\d+\s+KO\s*/?\s*TKO\s+(\d+).*?SUBMISSION\S*\s+(\d+).*?DECISION\S*\s+(\d+)",
        page_text, re.DOTALL | re.IGNORECASE
    )
    if wins_section:
        ko_wins = int(wins_section.group(1))
        sub_wins = int(wins_section.group(2))
        dec_wins = int(wins_section.group(3))

    record_text = f"{wins}-{losses}-{draws}"

    # Physical attributes from fighter-data section
    height = ""
    weight_class = ""
    age = 0
    reach = ""

    age_match = re.search(r"AGE\s*(\d+)", page_text)
    if age_match:
        age = int(age_match.group(1))

    height_match = re.search(r"HEIGHT\s*([\d'\"]+(?:/[\d.]+\s*cm)?)", page_text)
    if height_match:
        height = height_match.group(1).split("/")[0].strip()

    # Reach: "REACH 70.0" or "REACH 70\" / 178 cm"
    reach_match = re.search(r"REACH\s*([\d.]+)\s*(?:\"|in)?", page_text, re.IGNORECASE)
    if reach_match:
        reach = f'{reach_match.group(1)}"'

    class_match = re.search(r"CLASS\s*(\w+)", page_text)
    if class_match:
        weight_class = class_match.group(1)
    else:
        weight_match = re.search(r"WEIGHT\s*([\d.]+\s*lbs)", page_text)
        if weight_match:
            weight_class = weight_match.group(1)

    # Recent fights - parse only from "FIGHT HISTORY - PRO" section,
    # stopping before any EXHIBITION / AMATEUR / RELATED NEWS / REBOUT section.
    recent_fights = []
    history_text = ""
    fight_history_match = re.search(
        r"FIGHT HISTORY\s*-\s*PRO\b(.*?)(?:FIGHT HISTORY\s*-\s*(?:PRO\s+)?EXHIBITION|FIGHT HISTORY\s*-\s*AMATEUR|RELATED NEWS|$)",
        page_text,
        re.DOTALL | re.IGNORECASE,
    )
    if not fight_history_match:
        # Fallback: just "FIGHT HISTORY" (older layouts)
        fight_history_match = re.search(
            r"FIGHT HISTORY\b(.*?)(?:RELATED NEWS|$)",
            page_text,
            re.DOTALL | re.IGNORECASE,
        )
    if fight_history_match:
        history_text = fight_history_match.group(1)
        # Match lines containing ONLY the result word (Sherdog renders each
        # result on its own line). This avoids picking up "draw" from
        # "Draw (Time Limit)" or news article prose.
        results = re.findall(
            r"^\s*(win|loss|draw|nc)\s*$",
            history_text,
            re.IGNORECASE | re.MULTILINE,
        )
        for r in results:
            if len(recent_fights) >= 5:
                break
            r_lower = r.lower()
            if r_lower == "win":
                recent_fights.append("W")
            elif r_lower == "loss":
                recent_fights.append("L")
            elif r_lower == "draw":
                recent_fights.append("D")
            # skip nc (No Contest) — not a competitive result

    # Last fight date: Sherdog shows dates like "Dec / 31 / 2023" in history
    last_fight_date = ""
    if history_text:
        date_match = re.search(
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*/\s*(\d{1,2})\s*/\s*(\d{4})",
            history_text,
        )
        if date_match:
            from datetime import datetime
            try:
                d = datetime.strptime(
                    f"{date_match.group(1)} {date_match.group(2)} {date_match.group(3)}",
                    "%b %d %Y",
                )
                last_fight_date = d.strftime("%Y-%m-%d")
            except ValueError:
                last_fight_date = ""

    # Calculate streak
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

    # Estimate detailed stats from available data
    total_fights = wins + losses + draws
    estimated = _estimate_stats(wins, losses, ko_wins, sub_wins, dec_wins, total_fights, height)

    # Parse reach to inches
    reach_inches = 0.0
    reach_num = re.search(r"([\d.]+)", reach)
    if reach_num:
        try:
            reach_inches = float(reach_num.group(1))
        except ValueError:
            reach_inches = 0.0

    return Fighter(
        name=name,
        nickname=nickname,
        record=record_text,
        wins=wins,
        losses=losses,
        draws=draws,
        ko_wins=ko_wins,
        sub_wins=sub_wins,
        dec_wins=dec_wins,
        height=height,
        reach=reach,
        weight_class=weight_class,
        age=age,
        organization="RIZIN",
        recent_fights=recent_fights,
        recent_win_streak=streak,
        last_fight_date=last_fight_date,
        reach_inches=reach_inches,
        height_inches=estimated["height_inches"],
        style=estimated["style"],
        sig_strikes_landed_per_min=estimated["sig_strikes_landed_per_min"],
        sig_strike_accuracy=estimated["sig_strike_accuracy"],
        sig_strikes_absorbed_per_min=estimated["sig_strikes_absorbed_per_min"],
        sig_strike_defense=estimated["sig_strike_defense"],
        takedown_avg=estimated["takedown_avg"],
        takedown_accuracy=estimated["takedown_accuracy"],
        takedown_defense=estimated["takedown_defense"],
        submission_avg=estimated["submission_avg"],
        is_estimated=estimated.get("is_estimated", True),
    )


async def search_rizin_fighter(name: str) -> Fighter | None:
    """Search for a RIZIN fighter by name.

    Prefers the cached Sherdog URL from the RIZIN event scrape to avoid
    matching the wrong person when multiple fighters share the same name.
    """
    from app.services.rizin_cache import get_cached_fighter_url

    # Try cached URL first (scraped from RIZIN event pages → correct person)
    cached_url = get_cached_fighter_url(name)
    if cached_url:
        fighter = await get_fighter_from_sherdog(cached_url)
        if fighter:
            fighter.organization = "RIZIN"
            return fighter

    # Fallback: search Sherdog (prefer RIZIN fighters when multiple matches)
    result = await search_fighter_sherdog(name, prefer_rizin=True)
    if not result:
        return None
    fighter = await get_fighter_from_sherdog(result["url"])
    if fighter:
        fighter.organization = "RIZIN"
    return fighter


def _parse_sherdog_event_date(text: str):
    """Parse a Sherdog-style date cell like 'May 10 2026' into a datetime (or None)."""
    from datetime import datetime
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"([A-Za-z]+)\s*(\d{1,2})\s*,?\s*(\d{4})", r"\1 \2 \3", text)
    m = re.search(r"([A-Za-z]{3,9})\s+(\d{1,2})\s+(\d{4})", text)
    if not m:
        return None
    try:
        return datetime.strptime(f"{m.group(1)[:3]} {m.group(2)} {m.group(3)}", "%b %d %Y")
    except ValueError:
        return None


def _parse_sherdog_event_tables(html: str, org_filter: str, organization_label: str) -> list[dict]:
    """Extract upcoming (future-dated) events from a Sherdog organization page HTML.

    Sherdog row layout: cells[0]=date, cells[1]=title (event link), cells[2]=location.
    Past events live in the same-classed table, so we filter by parsing the date
    and keeping only those on/after today.
    """
    from datetime import datetime

    soup = BeautifulSoup(html, "lxml")
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    events: list[dict] = []
    seen: set[str] = set()

    tables = soup.find_all("table", class_="new_table")
    for table in tables:
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            link = None
            # Prefer cells[1] (title cell) but fall back to any cell with an /events/ link
            for c in (cells[1:] + cells[:1]):
                a = c.find("a", href=lambda h: h and "/events/" in h)
                if a:
                    link = a
                    break
            if not link:
                continue

            event_name = link.get_text(strip=True)
            if org_filter and org_filter not in event_name.lower():
                continue

            href = link.get("href", "")
            event_url = SHERDOG_BASE + href if href.startswith("/") else href

            date_text = cells[0].get_text(" ", strip=True)
            parsed = _parse_sherdog_event_date(date_text)
            if not parsed or parsed < today:
                continue  # past or unparseable → skip

            if event_url in seen:
                continue
            seen.add(event_url)

            events.append({
                "name": event_name,
                "date": date_text,
                "url": event_url,
                "organization": organization_label,
            })

    def _sort_key(e):
        d = _parse_sherdog_event_date(e["date"])
        return d or datetime.max
    events.sort(key=_sort_key)
    return events


async def get_upcoming_rizin_events() -> list[dict]:
    """Get upcoming RIZIN events from Sherdog."""
    try:
        html = await fetch_page(RIZIN_ORG_URL)
    except Exception:
        return []
    return _parse_sherdog_event_tables(html, org_filter="rizin", organization_label="RIZIN")[:5]


UFC_SHERDOG_URL = "https://www.sherdog.com/organizations/Ultimate-Fighting-Championship-UFC-2"


async def get_upcoming_ufc_events_via_sherdog() -> list[dict]:
    """Fallback UFC upcoming events source — Sherdog UFC page (when ufcstats.com is unreachable)."""
    try:
        html = await fetch_page(UFC_SHERDOG_URL)
    except Exception:
        return []
    return _parse_sherdog_event_tables(html, org_filter="ufc", organization_label="UFC")[:5]


def _split_concatenated_name(raw: str) -> str:
    """Sherdog's <span itemprop=\"name\"> renders first/last with no separator.
    Example: 'KylerPhillips' -> 'Kyler Phillips'. Apply camel-case split while
    preserving already-spaced names.
    """
    if not raw:
        return raw
    # Insert space between lowercase+uppercase boundary
    fixed = re.sub(r"([a-z])([A-Z])", r"\1 \2", raw)
    # Also handle dotted initials like "J.J.Aldrich" -> "J.J. Aldrich"
    fixed = re.sub(r"(\.)([A-Z][a-z])", r"\1 \2", fixed)
    # Collapse multiple spaces
    fixed = re.sub(r"\s+", " ", fixed).strip()
    return fixed


async def get_rizin_event_fights(event_url: str) -> list[Fight]:
    """Get fight card for a Sherdog-hosted event (RIZIN or UFC)."""
    html = await fetch_page(event_url)
    soup = BeautifulSoup(html, "lxml")

    fights: list[Fight] = []

    title_tag = soup.find("h1")
    event_name = title_tag.get_text(strip=True) if title_tag else ""

    date_tag = soup.find("meta", itemprop="startDate")
    event_date = date_tag["content"] if date_tag and date_tag.get("content") else ""

    # Decide organization from the event title so UFC events hosted on
    # Sherdog don't get mislabeled as RIZIN.
    org_label = "RIZIN"
    title_lower = (event_name or event_url).lower()
    if "ufc" in title_lower:
        org_label = "UFC"
    elif "rizin" in title_lower:
        org_label = "RIZIN"

    fight_rows = soup.find_all("tr", itemprop="subEvent")
    if not fight_rows:
        fight_rows = soup.find_all("section", class_="fight-card")

    for row in fight_rows:
        fighters = row.find_all("span", itemprop="name")
        if not fighters:
            fighters = row.find_all("a", class_="fighter-name")

        if len(fighters) >= 2:
            fighter_a = _split_concatenated_name(fighters[0].get_text(strip=True))
            fighter_b = _split_concatenated_name(fighters[1].get_text(strip=True))

            fights.append(Fight(
                event_name=event_name,
                event_date=event_date,
                fighter_a=fighter_a,
                fighter_b=fighter_b,
                organization=org_label,
            ))

    return fights
