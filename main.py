import random
import arxiv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from classics_db import CLASSICS_DATABASE

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
    "Mathematics": {
        "arxiv_query": "cat:math.CO OR cat:math.NT OR cat:math.PR OR cat:math.AP OR cat:math.AG OR cat:math.DG",
        "subcategories": {
            "Combinatorics": "cat:math.CO",
            "Number Theory": "cat:math.NT",
            "Probability": "cat:math.PR",
            "Analysis of PDEs": "cat:math.AP",
            "Algebraic Geometry": "cat:math.AG",
            "Differential Geometry": "cat:math.DG",
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
        "arxiv_query": "cat:q-bio.NC",
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


def fetch_arxiv_papers(topics, limit=5):
    """Fetches modern preprints via arXiv with robust fallback search."""
    if not topics or limit <= 0:
        return []

    papers = []
    seen = set()

    for t in topics:
        code = t.get("code", "")
        query_str = (
            code
            if "cat:" in code
            else f'abs:"{t.get("name", "").replace("All ", "")}"'
        )

        try:
            client = arxiv.Client(page_size=20, delay_seconds=1, num_retries=2)
            search = arxiv.Search(
                query=query_str,
                max_results=20,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending,
            )
            for r in list(client.results(search)):
                t_clean = r.title.replace("\n", " ").strip()
                if t_clean not in seen:
                    seen.add(t_clean)
                    papers.append({
                        "id": f"m_{r.entry_id.split('/')[-1]}",
                        "title": t_clean,
                        "authors": ", ".join([a.name for a in r.authors[:2]])
                        + (" et al." if len(r.authors) > 2 else ""),
                        "year": r.published.strftime("%Y"),
                        "category": t["name"],
                        "summary": r.summary.replace("\n", " "),
                        "url": r.entry_id,
                        "pdf": r.pdf_url,
                        "type": "Fresh Preprint",
                    })
        except Exception as e:
            print(f"arXiv fetch error: {e}")

    random.shuffle(papers)
    return papers[:limit]


def get_classics_from_db(topics, limit=5, seen_titles=set()):
    """Guarantees instant, zero-latency retrieval of classic papers matching selected categories."""
    if not topics or limit <= 0:
        return []

    matched = []
    parent_categories = set(
        [t.get("parent") for t in topics if t.get("parent")]
    )
    topic_names = [
        t.get("name", "").replace("All ", "").lower() for t in topics
    ]

    for card in CLASSICS_DATABASE:
        if card["title"] in seen_titles:
            continue

        # Match by parent category OR subcategory name
        if card.get("parent") in parent_categories or any(
            tn in card.get("category", "").lower() for tn in topic_names
        ):
            card_copy = dict(card)
            card_copy["type"] = "Seminal Classic"
            matched.append(card_copy)

    # General subject fallback if specific sub-filter yields few items
    if len(matched) < limit:
        for card in CLASSICS_DATABASE:
            if card["title"] not in seen_titles and card not in matched:
                card_copy = dict(card)
                card_copy["type"] = "Seminal Classic"
                matched.append(card_copy)

    random.shuffle(matched)
    return matched[:limit]


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
        fetch_arxiv_papers(modern_topics, limit=modern_count)
        if modern_count > 0
        else []
    )
    classic_papers = (
        get_classics_from_db(classic_topics, limit=classic_count)
        if classic_count > 0
        else []
    )

    combined = modern_papers + classic_papers
    seen = {p["title"] for p in combined}

    # Strict Guarantee: ALWAYS maintain 5 cards in the deck
    if len(combined) < 5:
        fill_needed = 5 - len(combined)
        fallback_classics = get_classics_from_db(
            classic_topics or modern_topics, limit=fill_needed, seen_titles=seen
        )
        combined.extend(fallback_classics)

    random.shuffle(combined)
    return JSONResponse({"deck": combined[:5]})


@app.post("/api/replacement-card")
async def get_replacement_card(request: Request):
    data = await request.json()
    type_needed = data.get("type", "modern")
    topics = data.get("topics", [])
    seen_titles = set(data.get("seenTitles", []))

    if type_needed == "classic":
        candidates = get_classics_from_db(
            topics, limit=5, seen_titles=seen_titles
        )
    else:
        candidates = fetch_arxiv_papers(topics, limit=5)

    for c in candidates:
        if c["title"] not in seen_titles:
            return JSONResponse({"paper": c})

    # Backup from global classic DB
    backup = get_classics_from_db([], limit=5, seen_titles=seen_titles)
    if backup:
        return JSONResponse({"paper": backup[0]})

    return JSONResponse({"paper": None})