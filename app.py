import json
from pathlib import Path
from typing import Dict, List

from flask import Flask, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "papers.json"
PAGE_SIZE = 25

app = Flask(__name__)


def load_data() -> Dict:
    if not DATA_FILE.exists():
        return {"conference": "ICDTA", "count": 0, "papers": [], "generated_at": None}
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def apply_filters(papers: List[Dict], q: str, year: str, volume: str) -> List[Dict]:
    out = papers

    if year:
        out = [p for p in out if str(p.get("conference_year", "")) == year]

    if volume:
        out = [p for p in out if p.get("proceedings_volume", "") == volume]

    if q:
        needle = q.lower()
        def match(p: Dict) -> bool:
            hay = [
                p.get("title", ""),
                p.get("doi", ""),
                " ".join(p.get("authors", [])),
                " ".join(p.get("keywords", [])),
                p.get("abstract", ""),
            ]
            return any(needle in (h or "").lower() for h in hay)
        out = [p for p in out if match(p)]

    return out


@app.route("/")
def index():
    data = load_data()
    papers = data.get("papers", [])

    q = request.args.get("q", "").strip()
    year = request.args.get("year", "").strip()
    volume = request.args.get("volume", "").strip()
    page = max(1, int(request.args.get("page", "1")))

    filtered = apply_filters(papers, q, year, volume)

    total = len(filtered)
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    page_items = filtered[start:end]

    years = sorted({str(p.get("conference_year")) for p in papers if p.get("conference_year")}, reverse=True)
    volumes = sorted({p.get("proceedings_volume") for p in papers if p.get("proceedings_volume")})

    return render_template(
        "index.html",
        conference=data.get("conference"),
        generated_at=data.get("generated_at"),
        count=data.get("count", 0),
        results=page_items,
        total=total,
        page=page,
        page_size=PAGE_SIZE,
        has_prev=page > 1,
        has_next=end < total,
        q=q,
        year=year,
        volume=volume,
        years=years,
        volumes=volumes,
    )


@app.route("/api/papers")
def api_papers():
    data = load_data()
    papers = data.get("papers", [])

    q = request.args.get("q", "").strip()
    year = request.args.get("year", "").strip()
    volume = request.args.get("volume", "").strip()

    filtered = apply_filters(papers, q, year, volume)

    return jsonify(
        {
            "conference": data.get("conference"),
            "generated_at": data.get("generated_at"),
            "count": len(filtered),
            "papers": filtered,
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
