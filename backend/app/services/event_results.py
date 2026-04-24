"""Completed event results scraper (Sherdog).

Given a Sherdog event URL, fetch each fight's winner and finish method.
Used by the 的中ログ (hit-log) pipeline to auto-resolve saved predictions
the day after an event.
"""

import logging
import re

from bs4 import BeautifulSoup

from app.services.rizin_scraper import (
    fetch_page,
    _split_concatenated_name,
)

logger = logging.getLogger(__name__)


def _detect_org(event_name: str, event_url: str) -> str:
    text = f"{event_name} {event_url}".lower()
    if "ufc" in text:
        return "UFC"
    if "rizin" in text:
        return "RIZIN"
    return "UNKNOWN"


def _parse_method(raw: str) -> str:
    """Normalize Sherdog's winby text to one of KO/TKO, Submission, Decision, Draw, NC."""
    if not raw:
        return ""
    t = raw.strip().lower()
    if "draw" in t:
        return "Draw"
    if "no contest" in t or t.startswith("nc"):
        return "NC"
    if "submission" in t:
        return "Submission"
    if "ko" in t or "tko" in t:
        return "KO/TKO"
    if "decision" in t:
        return "Decision"
    if "dq" in t or "disqualif" in t:
        return "DQ"
    return raw.strip()


async def fetch_event_results(event_url: str) -> dict | None:
    """Fetch completed event results from Sherdog.

    Returns None if the event page has no final_result markers yet
    (meaning the event hasn't happened / results not filled in).
    """
    try:
        html = await fetch_page(event_url)
    except Exception as e:
        logger.warning(f"fetch_event_results: failed to fetch {event_url}: {e}")
        return None

    soup = BeautifulSoup(html, "lxml")

    title_tag = soup.find("h1")
    event_name = title_tag.get_text(strip=True) if title_tag else ""

    date_tag = soup.find("meta", itemprop="startDate")
    event_date = date_tag["content"] if date_tag and date_tag.get("content") else ""

    org = _detect_org(event_name, event_url)

    rows = soup.find_all("tr", itemprop="subEvent")
    if not rows:
        # Main-event block on some Sherdog pages lives outside subEvent rows.
        # We intentionally skip it here — predictions are keyed by fighter
        # name anyway, and every fight appears as a subEvent row on modern
        # Sherdog layouts.
        return None

    results: list[dict] = []
    any_resolved = False

    for row in rows:
        performers = row.find_all("td", itemprop="performer")
        if len(performers) < 2:
            continue

        def _extract(cell):
            name_tag = cell.find("span", itemprop="name")
            result_tag = cell.find("span", class_="final_result")
            name = _split_concatenated_name(name_tag.get_text(strip=True)) if name_tag else ""
            status = result_tag.get_text(strip=True).lower() if result_tag else ""
            return name, status

        name_a, status_a = _extract(performers[0])
        name_b, status_b = _extract(performers[1])

        if not name_a or not name_b:
            continue

        winby_tag = row.find("td", class_="winby")
        method_raw = winby_tag.find("b").get_text(strip=True) if winby_tag and winby_tag.find("b") else ""
        method = _parse_method(method_raw)

        winner = None
        fight_status = ""
        if status_a == "win":
            winner = name_a
            fight_status = "win"
            any_resolved = True
        elif status_b == "win":
            winner = name_b
            fight_status = "win"
            any_resolved = True
        elif "draw" in (status_a, status_b):
            fight_status = "draw"
            any_resolved = True
        elif status_a == "nc" or status_b == "nc":
            fight_status = "nc"
            any_resolved = True

        results.append({
            "fighter_a": name_a,
            "fighter_b": name_b,
            "winner": winner,
            "method": method,
            "status": fight_status,
        })

    if not any_resolved:
        return None

    return {
        "event_name": event_name,
        "event_date": event_date,
        "organization": org,
        "results": results,
    }
