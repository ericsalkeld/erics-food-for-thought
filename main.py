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
        "subcategories": {
            "Quantum Physics": "cat:quant-ph",
            "Fluid Dynamics": "cat:physics.flu-dyn",
            "Statistical Mechanics": "cat:cond-mat.stat-mech",
        }
    },
    "Computer Science & AI": {
        "subcategories": {
            "Machine Learning": "cat:cs.LG",
            "Artificial Intelligence": "cat:cs.AI",
        }
    },
    "Psychology & Cognitive Science": {
        "subcategories": {
            "Cognitive Psychology": "Cognitive Psychology",
            "Developmental Psychology": "Developmental Psychology",
            "Cognitive Neuroscience": "Cognitive Neuroscience",
            "Social Psychology": "Social Psychology",
        }
    },
}

TAXONOMY_ALIASES = {
    "classical psychology": {
        "display": "Classic & Foundational Psychology",
        "code": "Psychology",
        "parent": "Psychology & Cognitive Science",
    },
    "quantum optics": {
        "display": "Quantum Optics & Photonics",
        "code": "cat:quant-ph AND (abs:optics OR ti:optics)",
        "parent": "Physics",
    },
}

DIVERSE_CLASSICS_DATABASE = [
    {
        "title": "Principles of Topological Psychology",
        "authors": "Kurt Lewin",
        "year": "1936",
        "category": "Classic / Psychology",
        "summary": "Lewin applies mathematical topology concepts to human behavior and psychological field theory.",
        "pdf": "https://www.google.com/search?q=Kurt+Lewin+Principles+of+Topological+Psychology",
        "type": "Seminal Classic",
    },
    {
        "title": "The Magical Number Seven, Plus or Minus Two",
        "authors": "George A. Miller",
        "year": "1956",
        "category": "Classic / Cognitive Psychology",
        "summary": "Miller proposes that human short-term memory capacity is limited to roughly seven chunks of information.",
        "pdf": "https://psychclassics.yorku.ca/Miller/",
        "type": "Seminal Classic",
    },
    {
        "title": "Computing Machinery and Intelligence",
        "authors": "Alan M. Turing",
        "year": "1950",
        "category": "Classic / AI & Philosophy",
        "summary": "Turing introduces the imitation game (Turing Test) and asks: Can machines think?",
        "pdf": "https://www.csee.umbc.edu/courses/471/papers/turing.pdf",
        "type": "Seminal Classic",
    },
]


@app.get("/api/search-topics")
async def search_topics(q: str):
    query = q.lower().strip()
    matches = []
    if not query:
        return JSONResponse({"results": []})

    for alias_key, data in TAXONOMY_ALIASES.items():
        if query in alias_key or alias_key in query:
            matches.append({
                "name": data["display"],
                "code": data["code"],
                "parent": data["parent"],
            })

    for broad, bdata in BROAD_TAXONOMY.items():
        for sub_name, code in bdata["subcategories"].items():
            if query in sub_name.lower():
                matches.append(
                    {"name": sub_name, "code": code, "parent": broad}
                )

    if not matches:
        matches.append({
            "name": f"Search: {q.title()}",
            "code": q,
            "parent": "Psychology & Cognitive Science",
        })

    return JSONResponse({"results": matches})


def fetch_arxiv_papers(selected_topics, limit=3):
    queries = [
        t["code"] for t in selected_topics if t.get("code", "").startswith("cat:")
    ]
    if not queries:
        return []

    try:
        client = arxiv.Client(page_size=limit, delay_seconds=2, num_retries=1)
        search = arxiv.Search(
            query=" OR ".join(queries),
            max_results=limit,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )
        papers = []
        for r in list(client.results(search)):
            papers.append({
                "title": r.title.replace("\n", " "),
                "authors": ", ".join([a.name for a in r.authors[:2]])
                + (" et al." if len(r.authors) > 2 else ""),
                "year": r.published.strftime("%Y"),
                "category": r.primary_category,
                "summary": r.summary.replace("\n", " "),
                "url": r.entry_id,
                "pdf": r.pdf_url,
                "type": "Fresh Preprint",
            })
        return papers
    except Exception as e:
        print(f"arXiv error: {e}")
        return []


def fetch_semantic_scholar_classics(selected_topics, limit=2):
    """Fetches high-citation landmark papers strictly filtered to pre-2012 publication dates."""
    topic_names = [t["name"].replace("Search: ", "") for t in selected_topics]
    search_term = random.choice(topic_names) if topic_names else "Psychology"

    papers = []
    try:
        # Enforce pre-2012 year filter via Semantic Scholar or Europe PMC
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={search_term}&limit=10&publicationDateOrYear=-2012&fields=title,abstract,authors,year,citationCount,openAccessPdf"
        res = requests.get(url, timeout=4).json()
        data = res.get("data", [])

        # Sort by citation count descending
        sorted_data = sorted(
            data, key=lambda x: x.get("citationCount", 0), reverse=True
        )

        for p in sorted_data[:limit]:
            if p.get("title"):
                pdf_url = (
                    p.get("openAccessPdf", {}).get("url")
                    if p.get("openAccessPdf")
                    else f"https://www.google.com/search?q={p['title']}"
                )
                papers.append({
                    "title": p["title"],
                    "authors": ", ".join([a["name"] for a in p.get("authors", [])[:2]])
                    + (" et al." if len(p.get("authors", [])) > 2 else ""),
                    "year": str(p.get("year", "N/A")),
                    "category": f"Classic ({p.get('citationCount', 0):,} Citations)",
                    "summary": p.get(
                        "abstract", "Abstract available via source record."
                    ),
                    "url": pdf_url,
                    "pdf": pdf_url,
                    "type": "Seminal Classic",
                })
    except Exception as e:
        print(f"Semantic Scholar classic fetch error: {e}")

    # Fallback search in static classic database if API returns zero pre-2012 papers
    if not papers:
        psych_classics = [
            p
            for p in DIVERSE_CLASSICS_DATABASE
            if "Psychology" in p["category"] or "Psychology" in search_term
        ]
        papers = (
            random.sample(psych_classics, min(limit, len(psych_classics)))
            if psych_classics
            else []
        )

    return papers


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html", context={"taxonomy": BROAD_TAXONOMY}
    )


@app.post("/api/generate-deck")
async def generate_deck(request: Request):
    data = await request.json()
    selected_topics = data.get("selectedTopics", [])
    classic_ratio = float(data.get("classicRatio", 0.3))

    classic_count = round(5 * classic_ratio)
    modern_count = 5 - classic_count

    modern_papers = fetch_arxiv_papers(selected_topics, limit=modern_count)
    classic_papers = fetch_semantic_scholar_classics(
        selected_topics, limit=classic_count
    )

    no_classics = False
    if classic_count > 0 and len(classic_papers) == 0:
        no_classics = True

    combined = modern_papers + classic_papers

    # If deck still needs items, fill remaining slots
    if len(combined) < 5:
        needed = 5 - len(combined)
        combined.extend(
            random.sample(
                DIVERSE_CLASSICS_DATABASE,
                min(needed, len(DIVERSE_CLASSICS_DATABASE)),
            )
        )

    random.shuffle(combined)

    return JSONResponse(
        {"deck": combined[:5], "no_classics_found": no_classics}
    )