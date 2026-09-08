import random
import arxiv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import requests

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Master list of available broad fields and subcategories
BROAD_CATEGORIES = {
    "Physics": {
        "arxiv_code": "cat:quant-ph OR cat:physics.flu-dyn OR cat:cond-mat.stat-mech",
        "access_note": None,
        "subcategories": [
            "Quantum Physics",
            "Fluid Dynamics",
            "Statistical Mechanics",
            "Condensed Matter",
        ],
    },
    "Psychology": {
        "arxiv_code": None,
        "access_note": (
            "Access to Psychology preprints is limited compared to arXiv physics."
            " Drawing from Semantic Scholar."
        ),
        "subcategories": [
            "Developmental Psychology",
            "Cognitive Psychology",
            "Neuroscience",
            "Social Psychology",
        ],
    },
    "Biology": {
        "arxiv_code": "cat:q-bio.NC OR cat:q-bio.BM",
        "access_note": None,
        "subcategories": [
            "Mathematical Biology",
            "Neuroscience",
            "Genomics",
            "Ecology",
        ],
    },
    "Chemistry": {
        "arxiv_code": None,
        "access_note": (
            "Chemistry open-access preprints drawn via Semantic Scholar open"
            " access."
        ),
        "subcategories": [
            "Physical Chemistry",
            "Biochemistry",
            "Organic Chemistry",
            "Materials Science",
        ],
    },
    "Computer Science": {
        "arxiv_code": "cat:cs.LG OR cat:cs.AI",
        "access_note": None,
        "subcategories": [
            "Machine Learning",
            "Artificial Intelligence",
            "Quantum Computing",
            "Theory of Computation",
        ],
    },
    "Humanities & Social Sciences": {
        "arxiv_code": None,
        "access_note": (
            "Humanities coverage relies on open-access repositories and"
            " Semantic Scholar."
        ),
        "subcategories": [
            "Philosophy of Science",
            "Linguistics",
            "Sociology",
            "Economics",
        ],
    },
}

FALLBACK_CLASSICS = [
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
        "title": "The Origin of Species",
        "authors": "Charles Darwin",
        "year": "1859",
        "category": "Classic / Biology",
        "summary": "Darwin introduces the theory of evolution through natural selection.",
        "pdf": "https://www.gutenberg.org/files/1228/1228-h/1228-h.htm",
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
    {
        "title": "Stage Theory of Cognitive Development",
        "authors": "Jean Piaget",
        "year": "1952",
        "category": "Classic / Psychology",
        "summary": "Piaget outlines cognitive development stages in children.",
        "pdf": "https://www.google.com/search?q=Piaget+Cognitive+Development+1952",
        "type": "Seminal Classic",
    },
]


def fetch_arxiv_papers(selected_categories, limit=3):
    papers = []
    # Build combined query for categories supported on arXiv
    queries = [
        BROAD_CATEGORIES[c]["arxiv_code"]
        for c in selected_categories
        if c in BROAD_CATEGORIES and BROAD_CATEGORIES[c]["arxiv_code"]
    ]

    if not queries:
        return []

    combined_query = " OR ".join(queries)

    try:
        client = arxiv.Client(page_size=limit, delay_seconds=2, num_retries=1)
        search = arxiv.Search(
            query=combined_query,
            max_results=limit,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )
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
    except Exception as e:
        print(f"arXiv error: {e}")

    return papers


def fetch_semantic_scholar_papers(
    selected_categories, subcategories, scope="broad", limit=3
):
    papers = []
    search_terms = (
        subcategories
        if (scope == "narrow" and subcategories)
        else selected_categories
    )

    if not search_terms:
        search_terms = ["Psychology", "Physics", "Neuroscience"]

    term = random.choice(search_terms)

    try:
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={term}&limit=8&fields=title,abstract,authors,year,citationCount,openAccessPdf"
        res = requests.get(url, timeout=4).json()
        data = res.get("data", [])

        highly_cited = [p for p in data if p.get("citationCount", 0) > 300]
        sample = (
            random.sample(highly_cited, min(limit, len(highly_cited)))
            if highly_cited
            else data[:limit]
        )

        for p in sample:
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
                "category": f"{term} ({p.get('citationCount', 0):,} Citations)",
                "summary": p.get("abstract", "Abstract available via source."),
                "url": pdf_url,
                "pdf": pdf_url,
                "type": "Seminal Classic",
            })
    except Exception as e:
        print(f"Semantic Scholar error: {e}")

    return papers


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"categories": BROAD_CATEGORIES},
    )


@app.post("/api/generate-deck")
async def generate_deck(request: Request):
    data = await request.json()

    selected_categories = data.get("categories", ["Physics"])
    selected_subs = data.get("subcategories", [])
    custom_topic = data.get("customTopic", "")
    classic_ratio = float(data.get("classicRatio", 0.3))  # e.g., 0.3 = 30%
    landmark_scope = data.get("landmarkScope", "broad")

    if custom_topic:
        selected_subs.append(custom_topic)

    # Calculate modern vs classic counts for a 5-card deck
    classic_count = round(5 * classic_ratio)
    modern_count = 5 - classic_count

    modern_papers = fetch_arxiv_papers(selected_categories, limit=modern_count)
    classic_papers = fetch_semantic_scholar_papers(
        selected_categories,
        selected_subs,
        scope=landmark_scope,
        limit=classic_count,
    )

    combined = modern_papers + classic_papers

    # Fill remaining if APIs rate-limit
    if len(combined) < 5:
        combined.extend(
            random.sample(
                FALLBACK_CLASSICS, min(5 - len(combined), len(FALLBACK_CLASSICS))
            )
        )

    random.shuffle(combined)

    # Collect access warnings
    warnings = [
        BROAD_CATEGORIES[c]["access_note"]
        for c in selected_categories
        if c in BROAD_CATEGORIES and BROAD_CATEGORIES[c]["access_note"]
    ]

    return JSONResponse({
        "deck": combined[:5],
        "warnings": list(set(warnings)),
    })