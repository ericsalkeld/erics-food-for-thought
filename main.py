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
        "access_note": None,
        "subcategories": {
            "Quantum Physics": "cat:quant-ph",
            "Fluid Dynamics": "cat:physics.flu-dyn",
            "Statistical Mechanics": "cat:cond-mat.stat-mech",
            "Condensed Matter Physics": "cat:cond-mat.str-el",
            "High Energy Physics - Theory": "cat:hep-th",
            "High Energy Physics - Phenomenology": "cat:hep-ph",
            "Astrophysics": "cat:astro-ph",
            "General Relativity & Quantum Cosmology": "cat:gr-qc",
            "Atomic & Molecular Physics": "cat:physics.atom-ph",
            "Mathematical Physics": "cat:math-ph",
            "Optics & Photonics": "cat:physics.optics",
            "Plasma Physics": "cat:physics.plasm-ph",
        },
    },
    "Computer Science": {
        "access_note": None,
        "subcategories": {
            "Machine Learning": "cat:cs.LG",
            "Artificial Intelligence": "cat:cs.AI",
            "Quantum Computing": "cat:quant-ph AND (ti:quantum OR abs:quantum)",
            "Computer Vision": "cat:cs.CV",
            "Cryptography & Security": "cat:cs.CR",
            "Theory of Computation": "cat:cs.CC",
            "Robotics": "cat:cs.RO",
            "Neural & Evolutionary Computing": "cat:cs.NE",
        },
    },
    "Biology": {
        "access_note": None,
        "subcategories": {
            "Neurons & Cognition": "cat:q-bio.NC",
            "Biomolecules & Structural Biology": "cat:q-bio.BM",
            "Genomics & Bioinformatics": "cat:q-bio.GN",
            "Molecular Networks": "cat:q-bio.MN",
            "Cell Behavior": "cat:q-bio.CB",
            "Populations & Evolution": "cat:q-bio.PE",
            "Quantitative Methods": "cat:q-bio.QM",
        },
    },
    "Mathematics": {
        "access_note": None,
        "subcategories": {
            "Analysis of PDEs": "cat:math.AP",
            "Differential Geometry": "cat:math.DG",
            "Probability & Stochastic Processes": "cat:math.PR",
            "Algebraic Geometry": "cat:math.AG",
            "Combinatorics": "cat:math.CO",
            "Dynamical Systems": "cat:math.DS",
            "Number Theory": "cat:math.NT",
        },
    },
    "Psychology & Cognitive Science": {
        "access_note": "Psychology preprints are drawn via Semantic Scholar open access.",
        "subcategories": {
            "Cognitive Psychology": "Cognitive Psychology",
            "Developmental Psychology": "Developmental Psychology",
            "Cognitive Neuroscience": "Cognitive Neuroscience",
            "Social Psychology": "Social Psychology",
            "Clinical Psychology": "Clinical Psychology",
            "Behavioral Neuroscience": "Behavioral Neuroscience",
        },
    },
    "Humanities & Social Sciences": {
        "access_note": "Humanities preprints rely on Semantic Scholar open repositories.",
        "subcategories": {
            "Philosophy of Science": "Philosophy of Science",
            "Econometrics & Quantitative Economics": "cat:econ.EM",
            "Linguistics": "Linguistics",
            "Sociology": "Sociology",
            "Political Science": "Political Science",
        },
    },
}

# Known alias dictionary for dynamic topic search resolution
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
    "quantum information": {
        "display": "Quantum Information & Computing",
        "code": "cat:quant-ph",
        "parent": "Physics",
    },
    "quantum gravity": {
        "display": "General Relativity & Quantum Cosmology",
        "code": "cat:gr-qc OR cat:hep-th",
        "parent": "Physics",
    },
    "turbulence": {
        "display": "Fluid Dynamics (Turbulence)",
        "code": "cat:physics.flu-dyn AND (abs:turbulence OR ti:turbulence)",
        "parent": "Physics",
    },
    "deep learning": {
        "display": "Machine Learning (Deep Learning)",
        "code": "cat:cs.LG",
        "parent": "Computer Science",
    },
    "reinforcement learning": {
        "display": "Machine Learning (Reinforcement Learning)",
        "code": "cat:cs.LG AND abs:reinforcement",
        "parent": "Computer Science",
    },
    "neuroscience": {
        "display": "Neurons & Cognition (Neuroscience)",
        "code": "cat:q-bio.NC",
        "parent": "Biology",
    },
    "synthetic biology": {
        "display": "Quantitative Methods (Synthetic Biology)",
        "code": "cat:q-bio.MN OR cat:q-bio.QM",
        "parent": "Biology",
    },
    "behavioral economics": {
        "display": "Cognitive & Behavioral Economics",
        "code": "Behavioral Economics",
        "parent": "Humanities & Social Sciences",
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
        "title": "A Mathematical Theory of Communication",
        "authors": "Claude E. Shannon",
        "year": "1948",
        "category": "Classic / Information Theory",
        "summary": "Shannon lays the foundation for information theory and digital communication.",
        "pdf": "https://math.harvard.edu/~ctm/home/text/others/shannon/entropy/entropy.pdf",
        "type": "Seminal Classic",
    },
]


@app.get("/api/search-topics")
async def search_topics(q: str):
    """Searches official taxonomy and alias mapping to return verified topic suggestions."""
    query = q.lower().strip()
    matches = []

    if not query:
        return JSONResponse({"results": []})

    # 1. Search alias dictionary
    for alias_key, data in TAXONOMY_ALIASES.items():
        if query in alias_key or alias_key in query:
            matches.append({
                "name": data["display"],
                "code": data["code"],
                "parent": data["parent"],
                "match_type": "Direct Topic Match",
            })

    # 2. Search taxonomy subcategories across broad fields
    for broad, bdata in BROAD_TAXONOMY.items():
        for sub_name, code in bdata["subcategories"].items():
            if query in sub_name.lower():
                matches.append({
                    "name": sub_name,
                    "code": code,
                    "parent": broad,
                    "match_type": f"Official {broad} Subcategory",
                })

    # Deduplicate matches
    seen = set()
    unique_matches = []
    for m in matches:
        if m["name"] not in seen:
            seen.add(m["name"])
            unique_matches.append(m)

    return JSONResponse({"results": unique_matches})


def fetch_arxiv_papers(selected_topics, limit=3):
    queries = [
        t["code"] for t in selected_topics if t.get("code", "").startswith("cat:")
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


def fetch_semantic_scholar_papers(
    selected_categories, selected_topics, limit=2
):
    terms = [
        t["name"]
        for t in selected_topics
        if not t.get("code", "").startswith("cat:")
    ]
    if not terms:
        terms = selected_categories

    term = random.choice(terms) if terms else "Physics"

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

        papers = []
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
        return papers
    except Exception as e:
        print(f"Semantic Scholar error: {e}")
        return []


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html", context={"taxonomy": BROAD_TAXONOMY}
    )


@app.post("/api/generate-deck")
async def generate_deck(request: Request):
    data = await request.json()

    selected_categories = data.get("categories", ["Physics"])
    selected_topics = data.get("selectedTopics", [])
    classic_ratio = float(data.get("classicRatio", 0.3))

    classic_count = round(5 * classic_ratio)
    modern_count = 5 - classic_count

    modern_papers = fetch_arxiv_papers(selected_topics, limit=modern_count)
    classic_papers = fetch_semantic_scholar_papers(
        selected_categories, selected_topics, limit=classic_count
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
        BROAD_TAXONOMY[c]["access_note"]
        for c in selected_categories
        if c in BROAD_TAXONOMY and BROAD_TAXONOMY[c]["access_note"]
    ]

    return JSONResponse({
        "deck": combined[:5],
        "warnings": list(set(warnings)),
    })