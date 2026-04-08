import html
import json
import re
from pathlib import Path
from typing import Dict, List

BASE_DIR = Path(__file__).resolve().parents[1]
DOCS_DIR = BASE_DIR / "docs"
DOCS_DATA_FILE = DOCS_DIR / "data" / "papers.json"
PAPERS_DIR = DOCS_DIR / "papers"
SITEMAP_FILE = DOCS_DIR / "sitemap.xml"
SITE_BASE_URL = "https://motahhir.github.io/icdta-metadata-explorer"


def normalize_date_for_citation(raw: str) -> str:
    if not raw:
        return ""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
    m = re.match(r"^(\d{4})-(\d{2})", raw)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    m = re.match(r"^(\d{4})", raw)
    if m:
        return m.group(1)
    return raw


def meta_tag(name: str, content: str) -> str:
    if not content:
        return ""
    return f'<meta name="{html.escape(name)}" content="{html.escape(content)}">'


def build_paper_html(p: Dict) -> str:
    title = p.get("title") or "Untitled"
    authors: List[str] = p.get("authors") or []
    conf_name = p.get("conference_name") or "International Conference on Digital Technologies and Applications"
    abstract = p.get("abstract") or ""
    doi = p.get("doi") or ""
    source_url = p.get("url") or ""
    year = str(p.get("conference_year") or "")
    volume = p.get("proceedings_volume") or ""
    date_published = p.get("date_published") or ""
    references: List[str] = p.get("references") or []
    paper_id = p.get("paper_id")

    local_path = f"/papers/{paper_id}.html"
    local_url = f"{SITE_BASE_URL}{local_path}"
    citation_date = normalize_date_for_citation(date_published)

    author_meta = "\n".join(meta_tag("citation_author", a) for a in authors if a)
    keyword_meta = "\n".join(meta_tag("citation_keywords", k) for k in (p.get("keywords") or []) if k)

    keywords_html = ", ".join(html.escape(k) for k in (p.get("keywords") or []))
    references_html = "".join(f"<li>{html.escape(r)}</li>" for r in references)
    authors_html = ", ".join(html.escape(a) for a in authors) if authors else "N/A"
    doi_html = html.escape(doi) if doi else "N/A"
    source_url_html = html.escape(source_url) if source_url else "#"
    source_anchor = (
        f'<a href="{source_url_html}" target="_blank" rel="noreferrer">Springer Conference Paper Page</a>'
        if source_url
        else "N/A"
    )

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{html.escape(title)} | ICDTA Metadata Explorer</title>
    <meta name="description" content="{html.escape(abstract[:300] if abstract else title)}">
    {meta_tag("citation_title", title)}
    {author_meta}
    {meta_tag("citation_conference_title", conf_name)}
    {meta_tag("citation_publication_date", citation_date or year)}
    {meta_tag("citation_doi", doi)}
    {meta_tag("citation_abstract", abstract)}
    {meta_tag("citation_abstract_html_url", local_url)}
    {meta_tag("citation_public_url", local_url)}
    {meta_tag("citation_journal_title", conf_name)}
    {keyword_meta}
    <link rel="canonical" href="{html.escape(local_url)}">
    <link rel="stylesheet" href="../assets/style.css">
  </head>
  <body>
    <main class="container">
      <header>
        <h1>{html.escape(title)}</h1>
        <p class="subtitle">{html.escape(conf_name)}</p>
        <p><a href="../index.html">Back to all papers</a></p>
      </header>

      <section class="results">
        <article class="card">
          <p><strong>Authors:</strong> {authors_html}</p>
          <p><strong>Conference:</strong> {html.escape(conf_name)}</p>
          <p><strong>DOI:</strong> {doi_html}</p>
          <p><strong>Year:</strong> {html.escape(year)} | <strong>Volume:</strong> {html.escape(volume)}</p>
          <p><strong>Published:</strong> {html.escape(date_published or "N/A")}</p>
          <p><strong>References:</strong> {len(references)}</p>
          <p><strong>Source:</strong> {source_anchor}</p>
          {"<p><strong>Keywords:</strong> " + keywords_html + "</p>" if keywords_html else ""}
          {"<p class='abstract'>" + html.escape(abstract) + "</p>" if abstract else ""}
          {"<h3>Reference List</h3><ol>" + references_html + "</ol>" if references_html else "<p>No references extracted.</p>"}
        </article>
      </section>
    </main>
  </body>
</html>
"""


def build_sitemap(papers: List[Dict]) -> str:
    urls = [f"{SITE_BASE_URL}/", f"{SITE_BASE_URL}/index.html"]
    for p in papers:
        paper_id = p.get("paper_id")
        if paper_id:
            urls.append(f"{SITE_BASE_URL}/papers/{paper_id}.html")
    items = "\n".join(f"  <url><loc>{html.escape(u)}</loc></url>" for u in urls)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{items}
</urlset>
"""


def build_static_site() -> int:
    payload = json.loads(DOCS_DATA_FILE.read_text(encoding="utf-8"))
    papers = payload.get("papers", [])
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)

    for old in PAPERS_DIR.glob("*.html"):
        old.unlink()

    created = 0
    for p in papers:
        paper_id = p.get("paper_id")
        if not paper_id:
            continue
        (PAPERS_DIR / f"{paper_id}.html").write_text(build_paper_html(p), encoding="utf-8")
        created += 1

    SITEMAP_FILE.write_text(build_sitemap(papers), encoding="utf-8")
    return created


def main() -> None:
    created = build_static_site()
    print(f"Generated {created} paper pages in {PAPERS_DIR}")
    print(f"Generated sitemap at {SITEMAP_FILE}")


if __name__ == "__main__":
    main()
