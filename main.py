import random
import arxiv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import requests

app = FastAPI()
templates = Jinja2Templates(directory="templates")

DEFAULT_TOPICS = [
    {"name": "Quantum Physics", "arxiv_cat": "cat:quant-ph", "weight": 0.3},
    {"name": "Quantum Machine Learning", "arxiv_cat": "cat:cs.LG", "weight": 0.2},
    {
        "name": "Statistical Mechanics",
        "arxiv_cat": "cat:cond-mat.stat-mech",
        "weight": 0.2,
    },
    {"name": "Fluid Dynamics", "arxiv_cat": "cat:physics.flu-dyn", "weight": 0.2},
    {
        "name": "Neuroscience & Math Bio",
        "arxiv_cat": "cat:q-bio.NC",
        "weight": 0.1,
    },
]

FALLBACK_CLASSICS = [
    {
        "title": "Simulating Physics with Computers",
        "authors": "Richard P. Feynman",
        "year": "1982",
        "category": "Classic / Physics & CS",
        "summary": "Feynman proposes using quantum mechanical systems to simulate physical phenomena, laying the conceptual groundwork for modern quantum computing.",
        "url": "https://doi.org/10.1007/BF02650179",
        "pdf": "https://dspace.mit.edu/bitstream/handle/1721.1/11724/SimulatingPhysicsWithComputers.pdf",
        "type": "Seminal Classic",
    },
    {
        "title": "A Mathematical Theory of Communication",
        "authors": "Claude E. Shannon",
        "year": "1948",
        "category": "Classic / Information Theory",
        "summary": "Shannon lays the foundation for information theory, digital communication, and information entropy.",
        "url": "https://doi.org/10.1002/j.1538-7305.1948.tb01338.x",
        "pdf": "https://math.harvard.edu/~ctm/home/text/others/shannon/entropy/entropy.pdf",
        "type": "Seminal Classic",
    },
    {
        "title": "The Chemical Basis of Morphogenesis",
        "authors": "Alan M. Turing",
        "year": "1952",
        "category": "Classic / Mathematical Biology",
        "summary": "Turing proposes a reaction-diffusion model for pattern formation in biology, introducing fundamental mathematical biology principles.",
        "url": "https://doi.org/10.1098/rstb.1952.0012",
        "pdf": "https://www.dna.caltech.edu/courses/cs191/papersturing.pdf",
        "type": "Seminal Classic",
    },
    {
        "title": (
            "Algorithms for Quantum Computation: Discrete Logarithms and"
            " Factoring"
        ),
        "authors": "Peter W. Shor",
        "year": "1994",
        "category": "Classic / Quantum & CS",
        "summary": "Shor introduces quantum polynomial-time algorithms for prime factorization and discrete logarithms, demonstrating exponential quantum speedups.",
        "url": "https://arxiv.org/abs/quant-ph/9508027",
        "pdf": "https://arxiv.org/pdf/quant-ph/9508027",
        "type": "Seminal Classic",
    },
]


def fetch_arxiv_preprints(limit=4):
    papers = []
    try:
        client = arxiv.Client(page_size=limit, delay_seconds=3, num_retries=1)
        search = arxiv.Search(
            query=(
                "cat:quant-ph OR cat:physics.flu-dyn OR cat:cond-mat.stat-mech"
                " OR cat:cs.LG"
            ),
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
                "type": "Fresh arXiv Upload",
            })
    except Exception as e:
        print(f"arXiv API note: {e}")
    return papers


def fetch_broad_landmarks(limit=2):
    landmarks = []
    terms = [
        "quantum computing",
        "neural network dynamics",
        "fluid turbulence",
        "information theory",
        "pattern formation biology",
    ]
    query_term = random.choice(terms)

    try:
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={query_term}&limit=10&fields=title,abstract,authors,year,citationCount,openAccessPdf"
        res = requests.get(url, timeout=4).json()
        data = res.get("data", [])

        highly_cited = [p for p in data if p.get("citationCount", 0) > 500]
        sample = (
            random.sample(highly_cited, min(limit, len(highly_cited)))
            if highly_cited
            else []
        )

        for p in sample:
            pdf_url = (
                p.get("openAccessPdf", {}).get("url")
                if p.get("openAccessPdf")
                else f"https://www.google.com/search?q={p['title']}"
            )
            landmarks.append({
                "title": p["title"],
                "authors": ", ".join([a["name"] for a in p.get("authors", [])[:2]])
                + (" et al." if len(p.get("authors", [])) > 2 else ""),
                "year": str(p.get("year", "N/A")),
                "category": f"Classic ({p.get('citationCount', 0):,} Citations)",
                "summary": p.get("abstract", "Abstract not available via API."),
                "url": pdf_url,
                "pdf": pdf_url,
                "type": "Seminal Classic",
            })
    except Exception as e:
        print(f"Semantic Scholar API note: {e}")

    return landmarks


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    modern = fetch_arxiv_preprints(limit=4)
    classic = fetch_broad_landmarks(limit=2)

    combined = modern + classic
    if len(combined) < 5:
        combined.extend(
            random.sample(
                FALLBACK_CLASSICS, min(5 - len(combined), len(FALLBACK_CLASSICS))
            )
        )

    random.shuffle(combined)
    card_deck = combined[:5]

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"papers": card_deck, "topics": DEFAULT_TOPICS},
    )