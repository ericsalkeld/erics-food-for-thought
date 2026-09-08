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

DIVERSE_CLASSICS_DATABASE = [
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
        "summary": "Turing introduces the imitation game (Turing Test) and considers the question: Can machines think?",
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
        "summary": "Miller proposes that human short-term memory capacity is limited to roughly seven chunks of information.",
        "pdf": "https://psychclassics.yorku.ca/Miller/",
        "type": "Seminal Classic",
    },
]


def fetch_arxiv_papers(topics, limit=5):
    queries = [
        t["code"] for t in topics if t.get("code", "").startswith("cat:")
    ]
    if not queries:
        return []

    try:
        client = arxiv.Client(page_size=limit * 2, delay_seconds=2, num_retries=1)
        search = arxiv.Search(
            query=" OR ".join(queries),
            max_results=limit * 2,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )
        papers = []
        seen_titles = set()
        for r in list(client.results(search)):
            t_clean = r.title.replace("\n", " ").strip()
            if t_clean not in seen_titles:
                seen_titles.add(t_clean)
                papers.append({
                    "id": f"m_{r.entry_id.split('/')[-1]}",
                    "title": t_clean,
                    "authors": ", ".join([a.name for a in r.authors[:2]])
                    + (" et al." if len(r.authors) > 2 else ""),
                    "year": r.published.strftime("%Y"),
                    "category": r.primary_category,
                    "summary": r.summary.replace("\n", " "),
                    "url": r.entry_id,
                    "pdf": r.pdf_url,
                    "type": "Fresh Preprint",
                })
        return papers[:limit]
    except Exception as e:
        print(f"arXiv error: {e}")
        return []


def fetch_semantic_scholar_classics(classic_topics, limit=5):
    topic_names = [t["name"] for t in classic_topics]
    search_term = random.choice(topic_names) if topic_names else "Physics"

    papers = []
    seen_titles = set()
    try:
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={search_term}&limit=10&publicationDateOrYear=-2012&fields=title,abstract,authors,year,citationCount,openAccessPdf"
        res = requests.get(url, timeout=4).json()
        data = res.get("data", [])
        sorted_data = sorted(
            data, key=lambda x: x.get("citationCount", 0), reverse=True
        )

        for p in sorted_data:
            if p.get("title"):
                t_clean = p["title"].strip()
                if t_clean not in seen_titles:
                    seen_titles.add(t_clean)
                    pdf_url = (
                        p.get("openAccessPdf", {}).get("url")
                        if p.get("openAccessPdf")
                        else f"https://www.google.com/search?q={p['title']}"
                    )
                    papers.append({
                        "id": f"c_{p.get('paperId', random.randint(1000, 9999))}",
                        "title": t_clean,
                        "authors": ", ".join([a["name"] for a in p.get("authors", [])[:2]])
                        + (" et al." if len(p.get("authors", [])) > 2 else ""),
                        "year": str(p.get("year", "N/A")),
                        "category": f"Classic ({p.get('citationCount', 0):,} Citations)",
                        "summary": p.get("abstract", "Abstract available via source record."),
                        "url": pdf_url,
                        "pdf": pdf_url,
                        "type": "Seminal Classic",
                    })
    except Exception as e:
        print(f"Semantic Scholar error: {e}")

    if len(papers) < limit:
        for c in DIVERSE_CLASSICS_DATABASE:
            if c["title"] not in seen_titles:
                seen_titles.add(c["title"])
                papers.append(c)

    return papers[:limit]


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

    modern_papers = fetch_arxiv_papers(modern_topics, limit=modern_count) if modern_count > 0 else []
    classic_papers = fetch_semantic_scholar_classics(classic_topics, limit=classic_count) if classic_count > 0 else []

    combined = modern_papers + classic_papers

    # Ensure unique items across the combined deck
    unique_deck = []
    seen = set()
    for p in combined:
        if p["title"] not in seen:
            seen.add(p["title"])
            unique_deck.append(p)

    if len(unique_deck) < 5:
        for c in DIVERSE_CLASSICS_DATABASE:
            if c["title"] not in seen:
                seen.add(c["title"])
                unique_deck.append(c)
                if len(unique_deck) >= 5:
                    break

    random.shuffle(unique_deck)
    return JSONResponse({"deck": unique_deck[:5]})