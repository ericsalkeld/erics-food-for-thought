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
        "arxiv_query": "cat:quant-ph OR cat:physics.flu-dyn OR cat:cond-mat.stat-mech OR cat:hep-th",
        "subcategories": {
            "Quantum Physics": "cat:quant-ph",
            "Fluid Dynamics": "cat:physics.flu-dyn",
            "Statistical Mechanics": "cat:cond-mat.stat-mech",
            "High Energy Physics": "cat:hep-th",
        },
    },
    "Computer Science & AI": {
        "arxiv_query": "cat:cs.LG OR cat:cs.AI OR cat:cs.CV",
        "subcategories": {
            "Machine Learning": "cat:cs.LG",
            "Artificial Intelligence": "cat:cs.AI",
            "Computer Vision": "cat:cs.CV",
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
    "Psychology & Cognitive Science": {
        "arxiv_query": None,
        "subcategories": {
            "Cognitive Psychology": "Cognitive Psychology",
            "Developmental Psychology": "Developmental Psychology",
            "Cognitive Neuroscience": "Cognitive Neuroscience",
            "Social Psychology": "Social Psychology",
        },
    },
}

DIVERSE_CLASSICS_DATABASE = {
    "Physics": [
        {
            "title": "Simulating Physics with Computers",
            "authors": "Richard P. Feynman",
            "year": "1982",
            "category": "Classic / Physics",
            "summary": "Feynman proposes using quantum mechanical systems to simulate physical phenomena.",
            "pdf": "https://dspace.mit.edu/bitstream/handle/1721.1/11724/SimulatingPhysicsWithComputers.pdf",
            "type": "Seminal Classic",
        },
        {
            "title": "On the Electrodynamics of Moving Bodies",
            "authors": "Albert Einstein",
            "year": "1905",
            "category": "Classic / Physics",
            "summary": "Einstein introduces special relativity, reconciling Maxwell's equations with relativity principles.",
            "pdf": "https://www.pro-physik.de/restricted-files/87021",
            "type": "Seminal Classic",
        },
    ],
    "Computer Science & AI": [
        {
            "title": "Computing Machinery and Intelligence",
            "authors": "Alan M. Turing",
            "year": "1950",
            "category": "Classic / AI & Philosophy",
            "summary": "Turing introduces the imitation game (Turing Test) and considers the question: Can machines think?",
            "pdf": "https://www.csee.umbc.edu/courses/471/papers/turing.pdf",
            "type": "Seminal Classic",
        },
        {
            "title": "A Mathematical Theory of Communication",
            "authors": "Claude E. Shannon",
            "year": "1948",
            "category": "Classic / Information Theory",
            "summary": "Shannon lays the foundation for information theory and digital communication.",
            "pdf": "https://math.harvard.edu/~ctm/home/text/others/shannon/entropy/entropy.pdf",
            "type": "Seminal Classic",
        },
    ],
    "Psychology & Cognitive Science": [
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
    ],
}


def fetch_arxiv_papers(topics, limit=3):
    queries = [
        t["code"] for t in topics if t.get("code", "").startswith("cat:")
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


def fetch_semantic_scholar_classics(classic_topics, limit=2):
    topic_names = [t["name"] for t in classic_topics]
    parents = list(set([t.get("parent", "Physics") for t in classic_topics]))
    search_term = random.choice(topic_names) if topic_names else "Physics"

    papers = []
    try:
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={search_term}&limit=8&publicationDateOrYear=-2012&fields=title,abstract,authors,year,citationCount,openAccessPdf"
        res = requests.get(url, timeout=4).json()
        data = res.get("data", [])
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

    # Enforce topic boundaries via static database if API returns empty
    if not papers:
        for parent in parents:
            if parent in DIVERSE_CLASSICS_DATABASE:
                papers.extend(DIVERSE_CLASSICS_DATABASE[parent])
        random.shuffle(papers)
        papers = papers[:limit]

    return papers


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html", context={"taxonomy": BROAD_TAXONOMY}
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
        fetch_arxiv_papers(modern_topics, limit=modern_count)
        if modern_count > 0
        else []
    )
    classic_papers = (
        fetch_semantic_scholar_classics(classic_topics, limit=classic_count)
        if classic_count > 0
        else []
    )

    combined = modern_papers + classic_papers

    # Fill remaining strictly respecting selected parent fields if necessary
    if len(combined) < 5:
        needed = 5 - len(combined)
        fallback_pool = []
        parents = list(
            set([t.get("parent", "Physics") for t in classic_topics])
        )
        for p in parents:
            if p in DIVERSE_CLASSICS_DATABASE:
                fallback_pool.extend(DIVERSE_CLASSICS_DATABASE[p])
        if not fallback_pool:
            fallback_pool = DIVERSE_CLASSICS_DATABASE["Physics"]
        combined.extend(
            random.sample(fallback_pool, min(needed, len(fallback_pool)))
        )

    random.shuffle(combined)
    return JSONResponse({"deck": combined[:5]})