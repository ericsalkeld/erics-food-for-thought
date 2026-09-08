import random
import arxiv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import requests

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Master taxonomy mapping broad fields to comprehensive subcategories and arXiv codes
BROAD_TAXONOMY = {
    "Physics": {
        "subcategories": {
            "Quantum Physics": "cat:quant-ph",
            "Fluid Dynamics": "cat:physics.flu-dyn",
            "Statistical Mechanics": "cat:cond-mat.stat-mech",
            "Condensed Matter Physics": "cat:cond-mat.str-el",
            "High Energy Physics - Theory": "cat:hep-th",
            "Optics & Photonics": "cat:physics.optics",
        }
    },
    "Computer Science & AI": {
        "subcategories": {
            "Machine Learning": "cat:cs.LG",
            "Artificial Intelligence": "cat:cs.AI",
            "Computer Vision": "cat:cs.CV",
            "Theory of Computation": "cat:cs.CC",
            "Neural & Evolutionary Computing": "cat:cs.NE",
        }
    },
    "Psychology & Cognitive Science": {
        "subcategories": {
            "Cognitive Psychology": "Cognitive Psychology",
            "Developmental Psychology": "Developmental Psychology",
            "Cognitive Neuroscience": "Cognitive Neuroscience",
            "Social Psychology": "Social Psychology",
            "Clinical Psychology": "Clinical Psychology",
        }
    },
    "Art, Humanities & Culture": {
        "subcategories": {
            "Painting & Visual Arts": "Painting Visual Arts",
            "Art History & Aesthetics": "Art History Aesthetics",
            "Musicology & Sound": "Musicology Sound",
            "Philosophy of Mind & Science": "Philosophy of Mind",
            "Literature & Critical Theory": "Literature Critical Theory",
        }
    },
    "Biology & Medicine": {
        "subcategories": {
            "Neurons & Cognition": "cat:q-bio.NC",
            "Genomics & Bioinformatics": "cat:q-bio.GN",
            "Cell Behavior": "cat:q-bio.CB",
            "Populations & Evolution": "cat:q-bio.PE",
        }
    },
}

# Diverse, cross-disciplinary classic landmark database
DIVERSE_CLASSICS_DATABASE = [
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
        "title": "Computing Machinery and Intelligence",
        "authors": "Alan M. Turing",
        "year": "1950",
        "category": "Classic / AI & Philosophy",
        "summary": "Turing introduces the imitation game (Turing Test) and considers the question: Can machines think?",
        "pdf": "https://www.csee.umbc.edu/courses/471/papers/turing.pdf",
        "type": "Seminal Classic",
    },
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
        "title": "The Art of Painting",
        "authors": "Cennino Cennini",
        "year": "1400",
        "category": "Classic / Visual Arts",
        "summary": "A foundational treatise detailing medieval and Renaissance painting techniques and pigments.",
        "pdf": "https://www.google.com/search?q=Cennino+Cennini+The+Craftsman+Handbook",
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
        "title": "The Magical Number Seven, Plus or Minus Two",
        "authors": "George A. Miller",
        "year": "1956",
        "category": "Classic / Cognitive Psychology",
        "summary": "Miller proposes that human short-term memory capacity is limited to roughly seven chunks of information.",
        "pdf": "https://psychclassics.yorku.ca/Miller/",
        "type": "Seminal Classic",
    },
]

TAXONOMY_ALIASES = {
    "classical field theory": {
        "display": "High Energy Physics - Theory (Classical Field Theory)",
        "code": "cat:hep-th OR cat:math-ph",
        "parent": "Physics",
    },
    "quantum optics": {
        "display": "Quantum Optics & Photonics",
        "code": "cat:quant-ph AND (abs:optics OR ti:optics)",
        "parent": "Physics",
    },
    "classical ai": {
        "display": "Symbolic & Classical AI",
        "code": "cat:cs.AI",
        "parent": "Computer Science & AI",
    },
    "painting": {
        "display": "Painting & Visual Arts",
        "code": "Painting Visual Arts",
        "parent": "Art, Humanities & Culture",
    },
}


@app.get("/api/search-topics")
async def search_topics(q: str):
    query = q.lower().strip()
    matches = []

    if not query:
        return JSONResponse({"results": []})

    # Search known aliases
    for alias_key, data in TAXONOMY_ALIASES.items():
        if query in alias_key or alias_key in query:
            matches.append({
                "name": data["display"],
                "code": data["code"],
                "parent": data["parent"],
            })

    # Search broad taxonomy
    for broad, bdata in BROAD_TAXONOMY.items():
        for sub_name, code in bdata["subcategories"].items():
            if query in sub_name.lower():
                matches.append(
                    {"name": sub_name, "code": code, "parent": broad}
                )

    # Dynamic fallback search item for any non-STEM topic (e.g., "Impressionism", "Music")
    if not matches:
        matches.append({
            "name": f"Custom Search: {q.title()}",
            "code": q,
            "parent": "Art, Humanities & Culture",
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


def fetch_universal_open_access_papers(selected_topics, limit=3):
    """Fetches open-access papers for Humanities, Psychology, Arts, and general topics via Semantic Scholar and Europe PMC."""
    papers = []
    topic_names = [t["name"].replace("Custom Search: ", "") for t in selected_topics]
    search_term = random.choice(topic_names) if topic_names else "Art History"

    # 1. Query Semantic Scholar
    try:
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={search_term}&limit=8&fields=title,abstract,authors,year,citationCount,openAccessPdf"
        res = requests.get(url, timeout=4).json()
        data = res.get("data", [])

        for p in data:
            if p.get("title") and p.get("abstract"):
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
                    "category": f"{search_term} ({p.get('citationCount', 0):,} Citations)",
                    "summary": p.get("abstract", "Abstract available via open source."),
                    "url": pdf_url,
                    "pdf": pdf_url,
                    "type": "Research Article",
                })
    except Exception as e:
        print(f"Semantic Scholar error: {e}")

    # 2. Fallback to Europe PMC if needed
    if len(papers) < limit:
        try:
            epmc_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={search_term}%20OPEN_ACCESS:y&format=json&pageSize=5"
            res = requests.get(epmc_url, timeout=4).json()
            results = res.get("resultList", {}).get("result", [])
            for r in results:
                title = r.get("title", "").strip(".")
                if title:
                    papers.append({
                        "title": title,
                        "authors": r.get("authorString", "Unknown Authors"),
                        "year": str(r.get("pubYear", "N/A")),
                        "category": f"{search_term} (Open Access)",
                        "summary": r.get("abstractText", "Abstract available via Europe PMC."),
                        "url": f"https://europepmc.org/article/MED/{r.get('id')}",
                        "pdf": f"https://europepmc.org/article/MED/{r.get('id')}",
                        "type": "Research Article",
                    })
        except Exception as e:
            print(f"Europe PMC error: {e}")

    return papers[:limit]


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

    # Try arXiv for STEM topics
    arxiv_papers = fetch_arxiv_papers(selected_topics, limit=modern_count)

    # Use Universal Open Access engine for Psychology, Arts, Painting, and general subjects
    universal_papers = fetch_universal_open_access_papers(
        selected_topics, limit=(5 - len(arxiv_papers))
    )

    combined = arxiv_papers + universal_papers

    # If APIs return fewer than 5, pull from diverse classic database
    if len(combined) < 5:
        needed = 5 - len(combined)
        fallback_sample = random.sample(
            DIVERSE_CLASSICS_DATABASE, min(needed, len(DIVERSE_CLASSICS_DATABASE))
        )
        combined.extend(fallback_sample)

    random.shuffle(combined)

    return JSONResponse({"deck": combined[:5]})