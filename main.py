import random
import arxiv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import requests

app = FastAPI()
templates = Jinja2Templates(directory="templates")

BROAD_TAXONOMY = {
    "Physics": {
        "arxiv_query": "cat:quant-ph OR cat:physics.flu-dyn OR cat:cond-mat.stat-mech OR cat:hep-th OR cat:nucl-th OR cat:gr-qc",
        "subcategories": {
            "Quantum Physics": "cat:quant-ph",
            "Nuclear & Atomic Physics": "cat:nucl-th OR cat:physics.atom-ph",
            "Fluid Dynamics": "cat:physics.flu-dyn",
            "Statistical Mechanics": "cat:cond-mat.stat-mech",
            "High Energy Physics": "cat:hep-th",
        },
    },
    "Computer Science & AI": {
        "arxiv_query": "cat:cs.LG OR cat:cs.AI OR cat:cs.CV OR cat:cs.CC",
        "subcategories": {
            "Machine Learning": "cat:cs.LG",
            "Artificial Intelligence": "cat:cs.AI",
            "Computer Vision": "cat:cs.CV",
            "Theory of Computation": "cat:cs.CC",
        },
    },
    "Psychology & Cognitive Science": {
        "arxiv_query": None,
        "subcategories": {
            "General Psychology": "Psychology",
            "Social Psychology": "Social Psychology",
            "Cognitive Psychology": "Cognitive Psychology",
            "Developmental Psychology": "Developmental Psychology",
        },
    },
    "Biology & Medicine": {
        "arxiv_query": "cat:q-bio.NC OR cat:q-bio.BM OR cat:q-bio.GN",
        "subcategories": {
            "Neurons & Cognition": "cat:q-bio.NC",
            "Genomics": "cat:q-bio.GN",
            "Biomolecules": "cat:q-bio.BM",
        },
    },
}

# Curated landmark database covering true classics (pre-2005)
HIGH_IMPACT_CLASSICS = [
    {
        "id": "c1",
        "title": "Simulating Physics with Computers",
        "authors": "Richard P. Feynman",
        "year": "1982",
        "category": "Classic / Physics",
        "summary": "Feynman proposes using quantum mechanical systems to simulate physical phenomena.",
        "pdf": "https://dspace.mit.edu/bitstream/handle/1721.1/11724/SimulatingPhysicsWithComputers.pdf",
        "type": "Seminal Classic",
    },
    {
        "id": "c2",
        "title": "On the Electrodynamics of Moving Bodies",
        "authors": "Albert Einstein",
        "year": "1905",
        "category": "Classic / Physics",
        "summary": "Einstein introduces special relativity, reconciling Maxwell's equations with relativity principles.",
        "pdf": "https://www.pro-physik.de/restricted-files/87021",
        "type": "Seminal Classic",
    },
    {
        "id": "c3",
        "title": "Computing Machinery and Intelligence",
        "authors": "Alan M. Turing",
        "year": "1950",
        "category": "Classic / AI & Philosophy",
        "summary": "Turing introduces the imitation game (Turing Test) and asks: Can machines think?",
        "pdf": "https://www.csee.umbc.edu/courses/471/papers/turing.pdf",
        "type": "Seminal Classic",
    },
    {
        "id": "c4",
        "title": "A Mathematical Theory of Communication",
        "authors": "Claude E. Shannon",
        "year": "1948",
        "category": "Classic / Information Theory",
        "summary": "Shannon lays the foundation for information theory and digital communication.",
        "pdf": "https://math.harvard.edu/~ctm/home/text/others/shannon/entropy/entropy.pdf",
        "type": "Seminal Classic",
    },
    {
        "id": "c5",
        "title": "Principles of Topological Psychology",
        "authors": "Kurt Lewin",
        "year": "1936",
        "category": "Classic / Psychology",
        "summary": "Lewin applies mathematical topology concepts to human behavior and psychological field theory.",
        "pdf": "https://www.google.com/search?q=Kurt+Lewin+Principles+of+Topological+Psychology",
        "type": "Seminal Classic",
    },
    {
        "id": "c6",
        "title": "The Magical Number Seven, Plus or Minus Two",
        "authors": "George A. Miller",
        "year": "1956",
        "category": "Classic / Cognitive Psychology",
        "summary": "Miller proposes that human short-term memory capacity is limited to roughly seven chunks.",
        "pdf": "https://psychclassics.yorku.ca/Miller/",
        "type": "Seminal Classic",
    },
]

SEARCH_SUGGESTIONS = {
    "nuclear spin": {
        "code": "cat:quant-ph OR cat:physics.chem-ph OR abs:\"nuclear spin\"",
        "parent": "Physics",
    },
    "quantum optics": {
        "code": "cat:quant-ph AND abs:optics",
        "parent": "Physics",
    },
    "social psychology": {
        "code": "Social Psychology",
        "parent": "Psychology & Cognitive Science",
    },
    "general psychology": {
        "code": "Psychology",
        "parent": "Psychology & Cognitive Science",
    },
}


@app.get("/api/suggest-topics")
async def suggest_topics(q: str):
    query = q.lower().strip()
    results = []
    for k, v in SEARCH_SUGGESTIONS.items():
        if query in k:
            results.append(
                {"name": k.title(), "code": v["code"], "parent": v["parent"]}
            )

    if not results and query:
        results.append({"name": q.title(), "code": q, "parent": "Custom"})

    return JSONResponse({"results": results})


def fetch_arxiv_domain(topics, limit=5, is_classic=False):
    """Fetches STEM research directly via arXiv API."""
    if not topics or limit <= 0:
        return []

    papers = []
    seen_titles = set()
    per_topic = max(1, limit // len(topics))

    for t in topics:
        code = t.get("code", "")
        query_str = code if "cat:" in code else f"abs:\"{code}\""

        try:
            client = arxiv.Client(page_size=12, delay_seconds=1, num_retries=1)
            sort_order = (
                arxiv.SortCriterion.Relevance
                if is_classic
                else arxiv.SortCriterion.SubmittedDate
            )

            search = arxiv.Search(
                query=query_str,
                max_results=12,
                sort_by=sort_order,
                sort_order=arxiv.SortOrder.Descending,
            )

            count = 0
            for r in list(client.results(search)):
                t_clean = r.title.replace("\n", " ").strip()
                pub_year = int(r.published.strftime("%Y"))

                # Strict classic filter for arXiv items (must be pre-2005 or high relevance)
                if is_classic and pub_year > 2005:
                    continue

                if t_clean not in seen_titles:
                    seen_titles.add(t_clean)
                    papers.append({
                        "id": f"arxiv_{r.entry_id.split('/')[-1]}",
                        "title": t_clean,
                        "authors": ", ".join([a.name for a in r.authors[:2]])
                        + (" et al." if len(r.authors) > 2 else ""),
                        "year": str(pub_year),
                        "category": t["name"],
                        "summary": r.summary.replace("\n", " "),
                        "url": r.entry_id,
                        "pdf": r.pdf_url,
                        "type": "Seminal Classic" if is_classic else "Fresh Preprint",
                    })
                    count += 1
                    if count >= per_topic:
                        break
        except Exception as e:
            print(f"arXiv fetch error for {code}: {e}")

    return papers[:limit]


def fetch_openalex_domain(topics, limit=5, is_classic=False):
    """Fetches Psychology & Social Sciences directly via OpenAlex API."""
    if not topics or limit <= 0:
        return []

    papers = []
    seen_titles = set()
    per_topic = max(1, limit // len(topics))

    for t in topics:
        search_term = t["name"].replace("All ", "")
        # Enforce pre-2005 ceiling and high citation thresholds for classic literature
        filter_str = (
            "is_oa:true,publication_year:<2005" if is_classic else "is_oa:true"
        )
        sort_str = "cited_by_count:desc" if is_classic else "publication_year:desc"

        try:
            url = f"https://api.openalex.org/works?search={search_term}&filter={filter_str}&sort={sort_str}&per-page=10"
            res = requests.get(url, timeout=3).json()
            results = res.get("results", [])

            count = 0
            for r in results:
                t_clean = r.get("display_name", "").strip()
                citations = r.get("cited_by_count", 0)

                if is_classic and citations < 200:
                    continue  # Require high citation consensus for classics

                if t_clean and t_clean not in seen_titles:
                    seen_titles.add(t_clean)
                    oa_pdf = (
                        r.get("open_access", {}).get("oa_url")
                        or f"https://www.google.com/search?q={t_clean}"
                    )
                    authorships = r.get("authorships", [])
                    authors_str = ", ".join([
                        a.get("author", {}).get("display_name", "")
                        for a in authorships[:2]
                    ])

                    papers.append({
                        "id": f"oa_{r.get('id', random.randint(1000, 9999))}",
                        "title": t_clean,
                        "authors": authors_str or "Unknown Authors",
                        "year": str(r.get("publication_year", "N/A")),
                        "category": (
                            f"{t['name']} ({citations:,} Citations)"
                            if is_classic
                            else t["name"]
                        ),
                        "summary": (
                            f"Key research work in {search_term}. Citation"
                            f" count: {citations:,}."
                        ),
                        "url": oa_pdf,
                        "pdf": oa_pdf,
                        "type": "Seminal Classic" if is_classic else "Fresh Paper",
                    })
                    count += 1
                    if count >= per_topic:
                        break
        except Exception as e:
            print(f"OpenAlex fetch error for {search_term}: {e}")

    return papers[:limit]


def route_topic_fetch(topics, limit, is_classic=False):
    """Routes topics to their dedicated API domain based on broad parent field."""
    arxiv_topics = [
        t for t in topics if t.get("parent") != "Psychology & Cognitive Science"
    ]
    openalex_topics = [
        t for t in topics if t.get("parent") == "Psychology & Cognitive Science"
    ]

    results = []

    if arxiv_topics:
        results.extend(
            fetch_arxiv_domain(
                arxiv_topics,
                limit=max(1, limit - len(openalex_topics)),
                is_classic=is_classic,
            )
        )

    if openalex_topics:
        results.extend(
            fetch_openalex_domain(
                openalex_topics,
                limit=max(1, limit - len(arxiv_topics)),
                is_classic=is_classic,
            )
        )

    # Fallback to curated classic database if classic query is underfilled
    if is_classic and len(results) < limit:
        seen = {p["title"] for p in results}
        for c in HIGH_IMPACT_CLASSICS:
            if c["title"] not in seen:
                results.append(c)
                if len(results) >= limit:
                    break

    return results[:limit]


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"taxonomy": BROAD_TAXONOMY},
    )


@app.post("/api/generate-deck")
async def generate_deck(request: Request):
    data = await request.json()
    modern_topics = data.get("modernTopics", [])
    classic_topics = data.get("classicTopics", [])
    classic_ratio = float(data.get("classicRatio", 0.3))

    classic_count = round(5 * classic_ratio)
    modern_count = 5 - classic_count

    modern_papers = (
        route_topic_fetch(modern_topics, limit=modern_count, is_classic=False)
        if modern_count > 0
        else []
    )
    classic_papers = (
        route_topic_fetch(classic_topics, limit=classic_count, is_classic=True)
        if classic_count > 0
        else []
    )

    combined = modern_papers + classic_papers

    if len(combined) == 0:
        return JSONResponse({
            "deck": [],
            "error": (
                "No Papers found matching your active topic filters. Please"
                " edit your search."
            ),
        })

    random.shuffle(combined)
    return JSONResponse({"deck": combined[:5], "error": None})


@app.post("/api/replacement-card")
async def get_replacement_card(request: Request):
    data = await request.json()
    type_needed = data.get("type", "modern")
    topics = data.get("topics", [])
    seen_titles = set(data.get("seenTitles", []))

    is_classic = type_needed == "classic"
    candidates = route_topic_fetch(topics, limit=5, is_classic=is_classic)

    for c in candidates:
        if c["title"] not in seen_titles:
            return JSONResponse({"paper": c})

    # Backup from internal classics
    for c in HIGH_IMPACT_CLASSICS:
        if c["title"] not in seen_titles:
            return JSONResponse({"paper": c})

    return JSONResponse({"paper": random.choice(HIGH_IMPACT_CLASSICS)})