import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


FP_NEWS_URL = "https://www.fp.vut.cz/cs/o-fakulte/aktuality"

DATE_RE = re.compile(r"(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})")


@dataclass(frozen=True)
class NewsItem:
    title: str
    published_date: str
    url: str


def _clean_text(value: str) -> str:
    return " ".join(value.split()).strip()


def _normalize_url(href: str) -> str | None:
    url = urljoin(FP_NEWS_URL, href)
    parsed = urlparse(url)

    # bereme jen odkazy z webu FP
    if parsed.netloc not in {"fp.vut.cz", "www.fp.vut.cz"}:
        return None

    return url


def parse_news(html: str) -> list[NewsItem]:
    soup = BeautifulSoup(html, "html.parser")

    root = soup.find("main") or soup

    found: dict[str, NewsItem] = {}

    # varianta, kdy je datum i nazev uvnitr odkazu
    for link in root.find_all("a", href=True):
        text = _clean_text(link.get_text(" ", strip=True))

        match = DATE_RE.match(text)

        if not match:
            continue

        title = _clean_text(text[match.end():])
        url = _normalize_url(link["href"])

        if not title or not url:
            continue

        found[url] = NewsItem(
            title=title,
            published_date=_clean_text(match.group(1)),
            url=url,
        )

    # zaloha, kdyby bylo datum a odkaz v HTML oddelene
    for text_node in root.find_all(string=DATE_RE):
        text = _clean_text(str(text_node))

        match = DATE_RE.fullmatch(text)

        if not match:
            continue

        container = text_node.parent
        link = text_node.find_parent("a", href=True)

        if link is None:
            for _ in range(4):
                if container is None:
                    break

                link = container.find("a", href=True)

                if link is not None:
                    break

                container = container.parent

        if link is None:
            continue

        url = _normalize_url(link["href"])

        if not url or url in found:
            continue

        title = _clean_text(link.get_text(" ", strip=True))
        title = _clean_text(DATE_RE.sub("", title, count=1))

        if not title:
            continue

        found[url] = NewsItem(
            title=title,
            published_date=_clean_text(match.group(1)),
            url=url,
        )

    return list(found.values())