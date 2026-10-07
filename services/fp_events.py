import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


FP_EVENTS_URL = "https://www.fp.vut.cz/cs/o-fakulte/kalendar-akci"


MONTHS = {
    "leden": 1,
    "únor": 2,
    "brezen": 3,
    "březen": 3,
    "duben": 4,
    "květen": 5,
    "kveten": 5,
    "červen": 6,
    "cerven": 6,
    "červenec": 7,
    "cervenec": 7,
    "srpen": 8,
    "září": 9,
    "zari": 9,
    "říjen": 10,
    "rijen": 10,
    "listopad": 11,
    "prosinec": 12,
}


EVENT_RE = re.compile(
    r"^\s*(\d{1,2})\s+([^\d\s]+)\s+(\d{4})\s+(.+?)\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CalendarEvent:
    title: str
    event_date: str
    url: str


def _clean_text(value: str) -> str:
    return " ".join(value.split()).strip()


def _normalize_url(href: str) -> str | None:
    url = urljoin(FP_EVENTS_URL, href)
    parsed = urlparse(url)

    if parsed.netloc not in {
        "fp.vut.cz",
        "www.fp.vut.cz",
    }:
        return None

    return url


def parse_events(
    html: str
) -> list[CalendarEvent]:

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    root = soup.find("main") or soup

    found: dict[str, CalendarEvent] = {}


    for link in root.find_all(
        "a",
        href=True
    ):

        text = _clean_text(
            link.get_text(
                " ",
                strip=True
            )
        )

        match = EVENT_RE.match(
            text
        )

        if not match:
            continue


        day = int(
            match.group(1)
        )

        month_name = (
            match.group(2)
            .lower()
        )

        year = int(
            match.group(3)
        )

        title = _clean_text(
            match.group(4)
        )


        month = MONTHS.get(
            month_name
        )


        if month is None or not title:
            continue


        url = _normalize_url(
            link["href"]
        )


        if not url:
            continue


        found[url] = CalendarEvent(
            title=title,
            event_date=(
                f"{day:02d}."
                f"{month:02d}."
                f"{year}"
            ),
            url=url,
        )


    return list(
        found.values()
    )