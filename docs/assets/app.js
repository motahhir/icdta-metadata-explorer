const PAGE_SIZE = 25;

const state = {
  papers: [],
  filtered: [],
  page: 1,
  q: "",
  year: "",
  volume: "",
  conference: "ICDTA",
  generatedAt: "",
};

const el = {
  title: document.getElementById("conference-title"),
  totalIndexed: document.getElementById("total-indexed"),
  updatedAtWrap: document.getElementById("updated-at-wrap"),
  form: document.getElementById("filters-form"),
  q: document.getElementById("q"),
  year: document.getElementById("year"),
  volume: document.getElementById("volume"),
  reset: document.getElementById("reset-btn"),
  resultsMeta: document.getElementById("results-meta"),
  resultsList: document.getElementById("results-list"),
  prev: document.getElementById("prev-link"),
  next: document.getElementById("next-link"),
  pageLabel: document.getElementById("page-label"),
};

function parseQueryParams() {
  const params = new URLSearchParams(window.location.search);
  state.q = (params.get("q") || "").trim();
  state.year = (params.get("year") || "").trim();
  state.volume = (params.get("volume") || "").trim();
  const parsedPage = Number.parseInt(params.get("page") || "1", 10);
  state.page = Number.isFinite(parsedPage) && parsedPage > 0 ? parsedPage : 1;
}

function syncQueryParams() {
  const params = new URLSearchParams();
  if (state.q) params.set("q", state.q);
  if (state.year) params.set("year", state.year);
  if (state.volume) params.set("volume", state.volume);
  if (state.page > 1) params.set("page", String(state.page));
  const next = `${window.location.pathname}${params.toString() ? "?" + params.toString() : ""}`;
  window.history.replaceState({}, "", next);
}

function escapeHtml(value) {
  return (value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function applyFilters() {
  const needle = state.q.toLowerCase();
  state.filtered = state.papers.filter((p) => {
    if (state.year && String(p.conference_year || "") !== state.year) return false;
    if (state.volume && (p.proceedings_volume || "") !== state.volume) return false;

    if (!needle) return true;
    const haystack = [
      p.title,
      p.doi,
      (p.authors || []).join(" "),
      (p.keywords || []).join(" "),
      p.abstract,
      p.conference_name,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

    return haystack.includes(needle);
  });

  const maxPage = Math.max(1, Math.ceil(state.filtered.length / PAGE_SIZE));
  if (state.page > maxPage) state.page = maxPage;
}

function populateFilters() {
  const years = [...new Set(state.papers.map((p) => p.conference_year).filter(Boolean))]
    .map(String)
    .sort((a, b) => Number(b) - Number(a));
  const volumes = [...new Set(state.papers.map((p) => p.proceedings_volume).filter(Boolean))]
    .sort((a, b) => a.localeCompare(b));

  for (const y of years) {
    const opt = document.createElement("option");
    opt.value = y;
    opt.textContent = y;
    el.year.appendChild(opt);
  }

  for (const v of volumes) {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = v;
    el.volume.appendChild(opt);
  }

  el.q.value = state.q;
  el.year.value = state.year;
  el.volume.value = state.volume;
}

function render() {
  const start = (state.page - 1) * PAGE_SIZE;
  const end = start + PAGE_SIZE;
  const items = state.filtered.slice(start, end);

  el.resultsMeta.textContent = `Showing ${items.length} of ${state.filtered.length} matching papers`;
  el.pageLabel.textContent = `Page ${state.page}`;

  el.prev.style.visibility = state.page > 1 ? "visible" : "hidden";
  el.next.style.visibility = end < state.filtered.length ? "visible" : "hidden";

  el.resultsList.innerHTML = items.length
    ? items
        .map((p) => {
          const title = escapeHtml(p.title || "Untitled");
          const authors = (p.authors || []).map(escapeHtml).join(", ") || "N/A";
          const doi = escapeHtml(p.doi || "N/A");
          const conf = escapeHtml(
            p.conference_name || "International Conference on Digital Technologies and Applications"
          );
          const year = escapeHtml(String(p.conference_year || "N/A"));
          const volume = escapeHtml(p.proceedings_volume || "N/A");
          const published = escapeHtml(p.date_published || "N/A");
          const keywords = (p.keywords || []).map(escapeHtml).join(", ");
          const abs = escapeHtml(p.abstract || "");
          const url = escapeHtml(p.url || "#");
          const localPaperUrl = p.paper_id ? `papers/${encodeURIComponent(p.paper_id)}.html` : url;

          return `
            <article class="card">
              <h2><a href="${localPaperUrl}">${title}</a></h2>
              <p><strong>Authors:</strong> ${authors}</p>
              <p><strong>Conference:</strong> ${conf}</p>
              <p><strong>DOI:</strong> ${doi}</p>
              <p><strong>Year:</strong> ${year} | <strong>Volume:</strong> ${volume}</p>
              <p><strong>Published:</strong> ${published}</p>
              <p><strong>Source:</strong> <a href="${url}" target="_blank" rel="noreferrer">Springer Chapter Page</a></p>
              ${keywords ? `<p><strong>Keywords:</strong> ${keywords}</p>` : ""}
              ${abs ? `<p class="abstract">${abs}</p>` : ""}
            </article>
          `;
        })
        .join("")
    : "<p>No papers found.</p>";

  syncQueryParams();
}

function bindEvents() {
  el.form.addEventListener("submit", (e) => {
    e.preventDefault();
    state.q = el.q.value.trim();
    state.year = el.year.value;
    state.volume = el.volume.value;
    state.page = 1;
    applyFilters();
    render();
  });

  el.reset.addEventListener("click", (e) => {
    e.preventDefault();
    state.q = "";
    state.year = "";
    state.volume = "";
    state.page = 1;
    el.q.value = "";
    el.year.value = "";
    el.volume.value = "";
    applyFilters();
    render();
  });

  el.prev.addEventListener("click", (e) => {
    e.preventDefault();
    if (state.page > 1) {
      state.page -= 1;
      render();
    }
  });

  el.next.addEventListener("click", (e) => {
    e.preventDefault();
    if (state.page * PAGE_SIZE < state.filtered.length) {
      state.page += 1;
      render();
    }
  });
}

async function init() {
  parseQueryParams();

  const resp = await fetch("data/papers.json", { cache: "no-cache" });
  if (!resp.ok) {
    throw new Error(`Failed to load metadata: HTTP ${resp.status}`);
  }

  const data = await resp.json();
  state.papers = data.papers || [];
  state.conference = data.conference || "ICDTA";
  state.generatedAt = data.generated_at || "";

  el.title.textContent = state.conference;
  el.totalIndexed.textContent = String(data.count || state.papers.length || 0);
  el.updatedAtWrap.textContent = state.generatedAt ? ` | Last update: ${state.generatedAt}` : "";

  populateFilters();
  bindEvents();
  applyFilters();
  render();
}

init().catch((err) => {
  el.resultsMeta.textContent = "Failed to load paper metadata.";
  el.resultsList.innerHTML = `<p>${escapeHtml(String(err.message || err))}</p>`;
});
