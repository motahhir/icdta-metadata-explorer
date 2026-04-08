import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set

import requests
from bs4 import BeautifulSoup
try:
    from build_static_site import build_static_site
except ModuleNotFoundError:
    from scripts.build_static_site import build_static_site

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
OUTPUT_FILE = DATA_DIR / "papers.json"
DOCS_OUTPUT_FILE = BASE_DIR / "docs" / "data" / "papers.json"
CONFERENCE_NAME = "International Conference on Digital Technologies and Applications"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ICDTA-Metadata-Bot/1.0; +https://link.springer.com/conference/icdta)",
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = 30


@dataclass(frozen=True)
class VolumeSource:
    year: int
    volume: str
    url: str


VOLUMES: List[VolumeSource] = [
    VolumeSource(2025, "Volume 1", "https://link.springer.com/book/10.1007/978-3-032-07718-9"),
    VolumeSource(2025, "Volume 2", "https://link.springer.com/book/10.1007/978-3-032-07785-1"),
    VolumeSource(2025, "Volume 3", "https://link.springer.com/book/9783032060600"),
    VolumeSource(2025, "Volume 4", "https://link.springer.com/book/10.1007/978-3-032-07915-2"),
    VolumeSource(2024, "Volume 1", "https://link.springer.com/book/10.1007/978-3-031-68650-4"),
    VolumeSource(2024, "Volume 2", "https://link.springer.com/book/10.1007/978-3-031-68653-5"),
    VolumeSource(2024, "Volume 3", "https://link.springer.com/book/10.1007/978-3-031-68660-3"),
    VolumeSource(2024, "Volume 4", "https://link.springer.com/book/10.1007/978-3-031-68675-7"),
    VolumeSource(2023, "Volume 1", "https://link.springer.com/book/10.1007/978-3-031-29857-8"),
    VolumeSource(2023, "Volume 2", "https://link.springer.com/book/10.1007/978-3-031-29860-8"),
    VolumeSource(2022, "Volume 1", "https://link.springer.com/book/10.1007/978-3-031-01942-5"),
    VolumeSource(2022, "Volume 2", "https://link.springer.com/book/10.1007/978-3-031-02447-4"),
    VolumeSource(2021, "Volume 1", "https://link.springer.com/book/10.1007/978-3-030-73882-2"),
]


def get_html(session: requests.Session, url: str) -> str:
    response = session.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return response.text


def parse_max_page(soup: BeautifulSoup) -> int:
    max_page = 1
    for a in soup.select('a[href*="?page="]'):
        href = a.get("href", "")
        m = re.search(r"[?&]page=(\d+)", href)
        if m:
            max_page = max(max_page, int(m.group(1)))
    return max_page


def extract_chapter_links(html: str) -> Set[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: Set[str] = set()
    for a in soup.select('a[href*="/chapter/"]'):
        href = a.get("href")
        if not href:
            continue
        if href.startswith("/"):
            href = f"https://link.springer.com{href}"
        if "/chapter/" in href:
            links.add(href.split("?")[0])
    return links


def collect_chapter_urls(session: requests.Session, source: VolumeSource) -> List[str]:
    first_html = get_html(session, source.url)
    first_soup = BeautifulSoup(first_html, "html.parser")
    max_page = parse_max_page(first_soup)

    urls: Set[str] = set(extract_chapter_links(first_html))
    for page in range(2, max_page + 1):
        page_url = f"{source.url}?page={page}"
        try:
            html = get_html(session, page_url)
        except requests.RequestException:
            continue
        urls.update(extract_chapter_links(html))
        time.sleep(0.15)

    return sorted(urls)


def parse_jsonld_chapter(soup: BeautifulSoup) -> Optional[Dict]:
    blocks = soup.find_all("script", {"type": "application/ld+json"})
    for block in blocks:
        raw = block.string or block.get_text("", strip=True)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        candidates = data if isinstance(data, list) else [data]
        for obj in candidates:
            if not isinstance(obj, dict):
                continue
            typ = obj.get("@type", "")
            if isinstance(typ, list):
                typ = " ".join(typ)
            if "ScholarlyArticle" in str(typ) or "Chapter" in str(typ):
                return obj
    return None


def normalize_authors(author_field) -> List[str]:
    if not author_field:
        return []
    authors = author_field if isinstance(author_field, list) else [author_field]
    result = []
    for a in authors:
        if isinstance(a, dict):
            name = a.get("name") or " ".join(
                part for part in [a.get("givenName"), a.get("familyName")] if part
            )
            if name:
                result.append(name.strip())
        elif isinstance(a, str):
            result.append(a.strip())
    return [x for x in result if x]


def metadata_from_chapter_url(session: requests.Session, chapter_url: str, source: VolumeSource) -> Optional[Dict]:
    try:
        html = get_html(session, chapter_url)
    except requests.RequestException:
        return None

    soup = BeautifulSoup(html, "html.parser")
    data = parse_jsonld_chapter(soup)

    # Fallback metadata from the page title when JSON-LD is unavailable.
    if data is None:
        title_el = soup.select_one("h1")
        title = title_el.get_text(" ", strip=True) if title_el else ""
        if not title:
            return None
        doi = chapter_url.split("/chapter/")[-1]
        return {
            "title": title,
            "authors": [],
            "doi": doi,
            "url": chapter_url,
            "abstract": "",
            "keywords": [],
            "date_published": None,
            "conference_name": CONFERENCE_NAME,
            "conference_year": source.year,
            "proceedings_volume": source.volume,
            "source_volume_url": source.url,
        }

    identifier = data.get("identifier")
    doi = ""
    if isinstance(identifier, str):
        doi = identifier
    elif isinstance(identifier, dict):
        doi = identifier.get("value") or identifier.get("@id") or ""
    if doi.startswith("https://doi.org/"):
        doi = doi.replace("https://doi.org/", "")

    if not doi and "/chapter/" in chapter_url:
        doi = chapter_url.split("/chapter/")[-1]

    keywords = data.get("keywords") or []
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(",") if k.strip()]

    return {
        "title": (data.get("headline") or data.get("name") or "").strip(),
        "authors": normalize_authors(data.get("author")),
        "doi": doi,
        "url": data.get("url") or chapter_url,
        "abstract": (data.get("description") or "").strip(),
        "keywords": keywords,
        "date_published": data.get("datePublished"),
        "conference_name": CONFERENCE_NAME,
        "conference_year": source.year,
        "proceedings_volume": source.volume,
        "source_volume_url": source.url,
    }


def deduplicate(papers: List[Dict]) -> List[Dict]:
    seen = set()
    out: List[Dict] = []
    for paper in papers:
        key = (paper.get("doi") or "", paper.get("title") or "", paper.get("conference_year"))
        if key in seen:
            continue
        seen.add(key)
        out.append(paper)
    return out


def slugify(text: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return base or "paper"


def assign_paper_ids(papers: List[Dict]) -> None:
    used = set()
    for p in papers:
        year = str(p.get("conference_year") or "")
        seed = p.get("doi") or f"{p.get('title', '')}-{year}"
        slug = slugify(seed)
        candidate = slug
        idx = 2
        while candidate in used:
            candidate = f"{slug}-{idx}"
            idx += 1
        used.add(candidate)
        p["paper_id"] = candidate


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    all_papers: List[Dict] = []
    with requests.Session() as session:
        for source in VOLUMES:
            print(f"Collecting chapter URLs: {source.year} {source.volume}")
            chapter_urls = collect_chapter_urls(session, source)
            print(f"  Found {len(chapter_urls)} chapters")

            futures = []
            with ThreadPoolExecutor(max_workers=8) as ex:
                for url in chapter_urls:
                    futures.append(ex.submit(metadata_from_chapter_url, session, url, source))

                done = 0
                for fut in as_completed(futures):
                    paper = fut.result()
                    if paper and paper.get("title"):
                        all_papers.append(paper)
                    done += 1
                    if done % 50 == 0:
                        print(f"  Parsed {done}/{len(futures)}")

    unique_papers = deduplicate(all_papers)
    unique_papers.sort(key=lambda x: (-int(x.get("conference_year", 0)), x.get("proceedings_volume", ""), x.get("title", "")))
    assign_paper_ids(unique_papers)

    payload = {
        "conference": f"{CONFERENCE_NAME} (ICDTA)",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": [asdict(v) for v in VOLUMES],
        "count": len(unique_papers),
        "papers": unique_papers,
    }

    rendered = json.dumps(payload, indent=2, ensure_ascii=False)
    OUTPUT_FILE.write_text(rendered, encoding="utf-8")
    DOCS_OUTPUT_FILE.write_text(rendered, encoding="utf-8")
    print(f"Saved {len(unique_papers)} papers to {OUTPUT_FILE}")
    print(f"Saved {len(unique_papers)} papers to {DOCS_OUTPUT_FILE}")
    generated = build_static_site()
    print(f"Generated {generated} static paper pages for docs/")


if __name__ == "__main__":
    main()
