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
        "arxiv_query": "cat:quant-ph OR cat:physics.flu-dyn OR cat:cond-mat.stat-mech OR cat:hep-th OR cat:gr-qc OR cat:physics.hist-ph",
        "subcategories": {
            "Quantum Physics": "cat:quant-ph",
            "Fluid Dynamics": "cat:physics.flu-dyn",
            "Statistical Mechanics": "cat:cond-mat.stat-mech",
            "High Energy Physics": "cat:hep-th",
            "Relativity & Cosmology": "cat:gr-qc",
            "History & Philosophy of Physics": "cat:physics.hist-ph",
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

EXPANDED_CLASSICS_DATABASE = [
    {"id": "c1", "title": "Simulating Physics with Computers", "authors": "Richard P. Feynman", "year": "1982", "category": "Classic / Physics", "summary": "Feynman proposes using quantum mechanical systems to simulate physical phenomena.", "pdf": "https://dspace.mit.edu/bitstream/handle/1721.1/11724/SimulatingPhysicsWithComputers.pdf", "type": "Seminal Classic"},
    {"id": "c2", "title": "On the Electrodynamics of Moving Bodies", "authors": "Albert Einstein", "year": "1905", "category": "Classic / Physics", "summary": "Einstein introduces special relativity, reconciling Maxwell's equations with relativity principles.", "pdf": "https://www.pro-physik.de/restricted-files/87021", "type": "Seminal Classic"},
    {"id": "c3", "title": "Computing Machinery and Intelligence", "authors": "Alan M. Turing", "year": "1950", "category": "Classic / AI & Philosophy", "summary": "Turing introduces the imitation game (Turing Test) and considers: Can machines think?", "pdf": "https://www.csee.umbc.edu/courses/471/papers/turing.pdf", "type": "Seminal Classic"},
    {"id": "c4", "title": "A Mathematical Theory of Communication", "authors": "Claude E. Shannon", "year": "1948", "category": "Classic / Information Theory", "summary": "Shannon lays the foundation for information theory and digital communication.", "pdf": "https://math.harvard.edu/~ctm/home/text/others/shannon/entropy/entropy.pdf", "type": "Seminal Classic"},
    {"id": "c5", "title": "Principles of Topological Psychology", "authors": "Kurt Lewin", "year": "1936", "category": "Classic / Psychology", "summary": "Lewin applies mathematical topology concepts to human behavior and psychological field theory.", "pdf": "https://www.google.com/search?q=Kurt+Lewin+Principles+of+Topological+Psychology", "type": "Seminal Classic"},
    {"id": "c6", "title": "The Magical Number Seven, Plus or Minus Two", "authors": "George A. Miller", "year": "1956", "category": "Classic / Cognitive Psychology", "summary": "Miller proposes that human short-term memory capacity is limited to roughly seven chunks.", "pdf": "https://psychclassics.yorku.ca/Miller/", "type": "Seminal Classic"},
    {"id": "c7", "title": "Can Quantum-Mechanical Description of Physical Reality be Considered Complete?", "authors": "A. Einstein, B. Podolsky, N. Rosen", "year": "1935", "category": "Classic / Quantum Physics", "summary": "The famous EPR paradox paper introducing quantum entanglement questions.", "pdf": "https://journals.aps.org/pr/abstract/10.1103/PhysRev.47.777", "type": "Seminal Classic"},
    {"id": "c8", "title": "On the Einstein Podolsky Rosen Paradox", "authors": "J. S. Bell", "year": "1964", "category": "Classic / Quantum Physics", "summary": "Bell introduces Bell's Theorem, demonstrating that local hidden-variable theories are incompatible with quantum mechanics.", "pdf": "https://cds.cern.ch/record/111416/files/vol1p195-200_001.pdf", "type": "Seminal Classic"},
    {"id": "c9", "title": "The Quantum Theory of Radiation", "authors": "P. A. M. Dirac", "year": "1927", "category": "Classic / Quantum Physics", "summary": "Dirac initiates quantum field theory by quantizing the electromagnetic field.", "pdf": "https://royalsocietypublishing.org/doi/10.1098/rspa.1927.0039", "type": "Seminal Classic"},
    {"id": "c10", "title": "Thermal Radiation and the Quantum Hypothesis", "authors": "Max Planck", "year": "1900", "category": "Classic / Physics", "summary": "Planck introduces energy quanta to resolve the blackbody radiation problem.", "pdf": "https://www.google.com/search?q=Max+Planck+1900+paper+pdf", "type": "Seminal Classic"}
]

def fetch_arxiv_papers(topics, limit=5, sort_criterion=arxiv.SortCriterion.SubmittedDate):
    queries = [t["code"] for t in topics if t.get("code", "").startswith("cat:")]
    if not queries:
        return []

    try:
        client = arxiv.Client(page_size=limit * 3, delay_seconds=2, num_retries=1)
        search = arxiv.Search(
            query=" OR ".join(queries),
            max_results=limit * 3,
            sort_by=sort_criterion,
            sort_order=arxiv.SortOrder.Descending,
        )
        papers = []
        seen_titles = set()
        results = list(client.results(search))
        random.shuffle(results)
        
        for r in results:
            t_clean = r.title.replace("\n", " ").strip()
            if t_clean not in seen_titles:
                seen_titles.add(t_clean)
                papers.append({
                    "id": f"m_{r.entry_id.split('/')[-1]}",
                    "title": t_clean,
                    "authors": ", ".join([a.name for a in r.authors[:2]]) + (" et al." if len(r.authors) > 2 else ""),
                    "year": r.published.strftime("%Y"),
                    "category": r.primary_category,
                    "summary": r.summary.replace("\n", " "),
                    "url": r.entry_id,
                    "pdf": r.pdf_url,
                    "type": "ArXiv Paper",
                })
                if len(papers) >= limit:
                    break
        return papers
    except Exception as e:
        print(f"arXiv error: {e}")
        return []

def fetch_multi_database_classics(classic_topics, limit=5):
    """Multi-database provider querying Semantic Scholar, OpenAlex, and arXiv historical archives."""
    topic_names = [t["name"] for t in classic_topics]
    search_term = random.choice(topic_names) if topic_names else "Physics"
    papers = []
    seen_titles = set()

    # Database 1: Semantic Scholar pre-2015 high-citation query
    try:
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={search_term}&limit=15&publicationDateOrYear=-2015&fields=title,abstract,authors,year,citationCount,openAccessPdf"
        res = requests.get(url, timeout=4).json()
        data = res.get("data", [])
        sorted_data = sorted(data, key=lambda x: x.get("citationCount", 0), reverse=True)

        for p in sorted_data:
            if p.get("title") and p.get("abstract"):
                t_clean = p["title"].strip()
                if t_clean not in seen_titles:
                    seen_titles.add(t_clean)
                    pdf_url = p.get("openAccessPdf", {}).get("url") if p.get("openAccessPdf") else f"https://www.google.com/search?q={p['title']}"
                    papers.append({
                        "id": f"s2_{p.get('paperId', random.randint(1000, 9999))}",
                        "title": t_clean,
                        "authors": ", ".join([a["name"] for a in p.get("authors", [])[:2]]) + (" et al." if len(p.get("authors", [])) > 2 else ""),
                        "year": str(p.get("year", "N/A")),
                        "category": f"Landmark ({p.get('citationCount', 0):,} Citations)",
                        "summary": p.get("abstract", "Abstract available via source record."),
                        "url": pdf_url,
                        "pdf": pdf_url,
                        "type": "Seminal Classic",
                    })
    except Exception as e:
        print(f"Semantic Scholar error: {e}")

    # Database 2: OpenAlex Open Access API
    if len(papers) < limit:
        try:
            oa_url = f"https://api.openalex.org/works?search={search_term}&filter=is_oa:true,publication_year:<2015&sort=cited_by_count:desc&per-page=10"
            res = requests.get(oa_url, timeout=4).json()
            results = res.get("results", [])
            for r in results:
                t_clean = r.get("display_name", "").strip()
                if t_clean and t_clean not in seen_titles:
                    seen_titles.add(t_clean)
                    oa_pdf = r.get("open_access", {}).get("oa_url") or f"https://www.google.com/search?q={t_clean}"
                    authorships = r.get("authorships", [])
                    authors_str = ", ".join([a.get("author", {}).get("display_name", "") for a in authorships[:2]])
                    papers.append({
                        "id": f"oa_{r.get('id', random.randint(1000, 9999))}",
                        "title": t_clean,
                        "authors": authors_str or "Unknown Authors",
                        "year": str(r.get("publication_year", "N/A")),
                        "category": f"Classic ({r.get('cited_by_count', 0):,} Citations)",
                        "summary": f"Foundational paper in {search_term}. Citation count: {r.get('cited_by_count', 0):,}.",
                        "url": oa_pdf,
                        "pdf": oa_pdf,
                        "type": "Seminal Classic",
                    })
        except Exception as e:
            print(f"OpenAlex error: {e}")

    # Database 3: arXiv Historical Re-prints & Relevance Search
    if len(papers) < limit:
        arxiv_classics = fetch_arxiv_papers(classic_topics, limit=(limit - len(papers)), sort_criterion=arxiv.SortCriterion.Relevance)
        for ap in arxiv_classics:
            if ap["title"] not in seen_titles:
                seen_titles.add(ap["title"])
                ap["type"] = "Seminal Classic"
                papers.append(ap)

    # Database 4: Expanded Internal Classic Database
    if len(papers) < limit:
        for c in EXPANDED_CLASSICS_DATABASE:
            if c["title"] not in seen_titles:
                seen_titles.add(c["title"])
                papers.append(c)

    random.shuffle(papers)
    return papers[:limit]

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"taxonomy": BROAD_TAXONOMY})

@app.post("/api/generate-deck")
async def generate_deck(request: Request):
    data = await request.json()
    modern_topics = data.get("modernTopics", [])
    classic_topics = data.get("classicTopics", [])
    classic_ratio = float(data.get("classicRatio", 0.3))

    classic_count = round(5 * classic_ratio)
    modern_count = 5 - classic_count

    modern_papers = fetch_arxiv_papers(modern_topics, limit=modern_count) if modern_count > 0 else []
    classic_papers = fetch_multi_database_classics(classic_topics, limit=classic_count) if classic_count > 0 else []

    combined = modern_papers + classic_papers
    unique_deck = []
    seen = set()
    for p in combined:
        if p["title"] not in seen:
            seen.add(p["title"])
            unique_deck.append(p)

    if len(unique_deck) < 5:
        for c in EXPANDED_CLASSICS_DATABASE:
            if c["title"] not in seen:
                seen.add(c["title"])
                unique_deck.append(c)
                if len(unique_deck) >= 5:
                    break

    random.shuffle(unique_deck)
    return JSONResponse({"deck": unique_deck[:5]})

@app.post("/api/replacement-card")
async def get_replacement_card(request: Request):
    data = await request.json()
    type_needed = data.get("type", "modern")
    topics = data.get("topics", [])
    seen_titles = set(data.get("seenTitles", []))

    if type_needed == "classic":
        candidates = fetch_multi_database_classics(topics, limit=5)
    else:
        candidates = fetch_arxiv_papers(topics, limit=5)

    for c in candidates:
        if c["title"] not in seen_titles:
            return JSONResponse({"paper": c})

    # Fallback from expanded db
    for c in EXPANDED_CLASSICS_DATABASE:
        if c["title"] not in seen_titles:
            return JSONResponse({"paper": c})

    return JSONResponse({"paper": random.choice(EXPANDED_CLASSICS_DATABASE)})