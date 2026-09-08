import random
import arxiv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import requests

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Master dictionary with valid arXiv queries mapped to specific subcategories
BROAD_CATEGORIES = {
    "Physics": {
        "arxiv_broad": "cat:quant-ph OR cat:physics.flu-dyn OR cat:cond-mat.stat-mech",
        "access_note": None,
        "subcategories": {
            "Quantum Physics": "cat:quant-ph",
            "Fluid Dynamics": "cat:physics.flu-dyn",
            "Statistical Mechanics": "cat:cond-mat.stat-mech",
            "Condensed Matter": "cat:cond-mat.str-el",
        },
    },
    "Computer Science": {
        "arxiv_broad": "cat:cs.LG OR cat:cs.AI OR cat:cs.ET",
        "access_note": None,
        "subcategories": {
            "Machine Learning": "cat:cs.LG",
            "Artificial Intelligence": "cat:cs.AI",
            "Quantum Computing": "cat:quant-ph AND (ti:quantum OR abs:quantum)",
            "Theory of Computation": "cat:cs.CC",
        },
    },
    "Biology": {
        "arxiv_broad": "cat:q-bio.NC OR cat:q-bio.BM OR cat:q-bio.MN",
        "access_note": None,
        "subcategories": {
            "Neuroscience": "cat:q-bio.NC",
            "Biomolecules": "cat:q-bio.BM",
            "Genomics": "cat:q-bio.GN",
            "Mathematical Biology": "cat:q-bio.MN",
        },
    },
    "Psychology": {
        "arxiv_broad": None,
        "access_note": "Psychology preprints are drawn via Semantic Scholar open access.",
        "subcategories": {
            "Developmental Psychology": "Developmental Psychology",
            "Cognitive Psychology": "Cognitive Psychology",
            "Neuroscience": "Cognitive Neuroscience",
            "Social Psychology": "Social Psychology",
        },
    },
    "Chemistry": {
        "arxiv_broad": None,
        "access_note": "Chemistry open preprints rely on Semantic Scholar.",
        "subcategories": {
            "Physical Chemistry": "Physical Chemistry",
            "Biochemistry": "Biochemistry",
            "Materials Science": "Materials Science",
        },
    },
    "Humanities & Social Sciences": {
        "arxiv_broad": None,
        "access_note": "Humanities preprints rely on Semantic Scholar open repositories.",
        "subcategories": {
            "Philosophy of Science": "Philosophy of Science",
            "Linguistics": "Linguistics",
            "Sociology": "Sociology",
            "Economics": "cat:econ.EM",
        },
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
]


def build_arxiv_query(selected_categories, selected_subcategories):
    """If specific subcategories are chosen, strictly restricts modern queries to those tags.

    Otherwise falls back to broad category tags.
    """
    strict_queries = []

    # Check if selected subcategories map to arXiv codes
    if selected_subcategories:
        for broad_cat in selected_categories:
            if broad_cat in BROAD_CATEGORIES:
                sub_dict = BROAD_CATEGORIES[broad_cat]["subcategories"]
                for sub in selected_subcategories:
                    if sub in sub_dict and sub_dict[sub].startswith("cat:"):
                        strict_queries.append(sub_dict[sub])

    # If subcategories were selected for arXiv, return strictly filtered query
    if strict_queries:
        return " OR ".join(strict_queries)

    # Otherwise default to broad subject area queries
    broad_queries = [
        BROAD_CATEGORIES[c]["arxiv_broad"]
        for c in selected_categories
        if c in BROAD_CATEGORIES and BROAD_CATEGORIES[c]["arxiv_broad"]
    ]

    return " OR ".join(broad_queries) if broad_queries else None


def fetch_arxiv_papers(query, limit=3):
    if not query:
        return []

    papers = []
    try:
        client = arxiv.Client(page_size=limit, delay_seconds=2, num_retries=1)
        search = arxiv.Search(
            query=query,
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
    classic_ratio = float(data.get("classicRatio", 0.3))
    landmark_scope = data.get("landmarkScope", "broad")

    if custom_topic:
        selected_subs.append(custom_topic)

    classic_count = round(5 * classic_ratio)
    modern_count = 5 - classic_count

    # Build strict query if specific topics are selected, otherwise broad
    arxiv_query = build_arxiv_query(selected_categories, selected_subs)

    modern_papers = fetch_arxiv_papers(arxiv_query, limit=modern_count)
    classic_papers = fetch_semantic_scholar_papers(
        selected_categories,
        selected_subs,
        scope=landmark_scope,
        limit=classic_count,
    )

    combined = modern_papers + classic_papers

    if len(combined) < 5:
        combined.extend(
            random.sample(
                FALLBACK_CLASSICS, min(5 - len(combined), len(FALLBACK_CLASSICS))
            )
        )

    random.shuffle(combined)

    warnings = [
        BROAD_CATEGORIES[c]["access_note"]
        for c in selected_categories
        if c in BROAD_CATEGORIES and BROAD_CATEGORIES[c]["access_note"]
    ]

    return JSONResponse({
        "deck": combined[:5],
        "warnings": list(set(warnings)),
    })