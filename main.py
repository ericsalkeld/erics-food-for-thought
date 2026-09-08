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
        "arxiv_query": "cat:quant-ph OR cat:physics.flu-dyn OR cat:cond-mat.stat-mech OR cat:hep-th OR cat:nucl-th OR cat:physics.chem-ph",
        "subcategories": {
            "Quantum Physics": "cat:quant-ph",
            "Nuclear & Atomic Physics": "cat:nucl-th OR cat:physics.atom-ph",
            "Fluid Dynamics": "cat:physics.flu-dyn",
            "Statistical Mechanics": "cat:cond-mat.stat-mech",
            "High Energy Physics": "cat:hep-th",
            "Chemical Physics": "cat:physics.chem-ph",
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
            "Cognitive Neuroscience": "cat:q-bio.NC",
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

# Auto-suggest dictionary for custom search terms
SEARCH_SUGGESTIONS = {
    "nuclear spin": {"code": "cat:quant-ph OR cat:physics.chem-ph OR abs:\"nuclear spin\"", "parent": "Physics"},
    "quantum optics": {"code": "cat:quant-ph AND abs:optics", "parent": "Physics"},
    "particle physics": {"code": "cat:hep-ph OR cat:hep-ex", "parent": "Physics"},
    "social psychology": {"code": "Social Psychology", "parent": "Psychology & Cognitive Science"},
    "general psychology": {"code": "Psychology", "parent": "Psychology & Cognitive Science"},
}

@app.get("/api/suggest-topics")
async def suggest_topics(q: str):
    query = q.lower().strip()
    results = []
    for k, v in SEARCH_SUGGESTIONS.items():
        if query in k:
            results.append({"name": k.title(), "code": v["code"], "parent": v["parent"]})
    
    if not results and query:
        results.append({"name": q.title(), "code": q, "parent": "Custom"})
        
    return JSONResponse({"results": results})


def fetch_arxiv_papers(topics, limit=5):
    """Fetches papers from arXiv with equal weight distribution per topic."""
    if not topics or limit <= 0:
        return []

    papers = []
    seen_titles = set()
    per_topic_limit = max(1, limit // len(topics))

    for t in topics:
        code = t.get("code", "")
        # Skip pure humanities/psychology strings on arXiv unless they have cat:
        query_str = code if "cat:" in code else f"abs:\"{code}\""
        
        try:
            client = arxiv.Client(page_size=10, delay_seconds=1, num_retries=1)
            search = arxiv.Search(
                query=query_str,
                max_results=10,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending,
            )
            count = 0
            for r in list(client.results(search)):
                t_clean = r.title.replace("\n", " ").strip()
                if t_clean not in seen_titles:
                    seen_titles.add(t_clean)
                    papers.append({
                        "id": f"arxiv_{r.entry_id.split('/')[-1]}",
                        "title": t_clean,
                        "authors": ", ".join([a.name for a in r.authors[:2]]) + (" et al." if len(r.authors) > 2 else ""),
                        "year": r.published.strftime("%Y"),
                        "category": t["name"],
                        "summary": r.summary.replace("\n", " "),
                        "url": r.entry_id,
                        "pdf": r.pdf_url,
                        "type": "Fresh Preprint",
                    })
                    count += 1
                    if count >= per_topic_limit:
                        break
        except Exception as e:
            print(f"arXiv fetch error for {code}: {e}")

    return papers[:limit]


def fetch_multi_database_classics(topics, limit=5):
    """Fetches landmark literature evenly across topics using Semantic Scholar, OpenAlex, and Europe PMC."""
    if not topics or limit <= 0:
        return []

    papers = []
    seen_titles = set()
    per_topic_limit = max(1, limit // len(topics))

    for t in topics:
        search_term = t["name"].replace("All ", "")
        count = 0

        # Database 1: OpenAlex Open Access API
        try:
            oa_url = f"https://api.openalex.org/works?search={search_term}&filter=is_oa:true,publication_year:<2018&sort=cited_by_count:desc&per-page=5"
            res = requests.get(oa_url, timeout=3).json()
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
                        "category": f"{t['name']} ({r.get('cited_by_count', 0):,} Citations)",
                        "summary": f"Foundational paper in {search_term}. Citation count: {r.get('cited_by_count', 0):,}.",
                        "url": oa_pdf,
                        "pdf": oa_pdf,
                        "type": "Seminal Classic",
                    })
                    count += 1
                    if count >= per_topic_limit:
                        break
        except Exception as e:
            print(f"OpenAlex error: {e}")

        # Database 2: Europe PMC Fallback if OpenAlex falls short
        if count < per_topic_limit:
            try:
                epmc_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={search_term}%20PUB_YEAR:[1900%20TO%202015]%20OPEN_ACCESS:y&format=json&pageSize=5"
                res = requests.get(epmc_url, timeout=3).json()
                results = res.get("resultList", {}).get("result", [])
                for r in results:
                    t_clean = r.get("title", "").strip(".")
                    if t_clean and t_clean not in seen_titles:
                        seen_titles.add(t_clean)
                        papers.append({
                            "id": f"epmc_{r.get('id', random.randint(1000, 9999))}",
                            "title": t_clean,
                            "authors": r.get("authorString", "Unknown Authors"),
                            "year": str(r.get("pubYear", "N/A")),
                            "category": f"{t['name']} Classic",
                            "summary": r.get("abstractText", "Abstract available via Europe PMC open access record."),
                            "url": f"https://europepmc.org/article/MED/{r.get('id')}",
                            "pdf": f"https://europepmc.org/article/MED/{r.get('id')}",
                            "type": "Seminal Classic",
                        })
                        count += 1
                        if count >= per_topic_limit:
                            break
            except Exception as e:
                print(f"Europe PMC error: {e}")

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
    
    # If NO papers match selected filters across all databases
    if len(combined) == 0:
        return JSONResponse({"deck": [], "error": "No Papers found matching your active topic filters. Please edit your search."})

    random.shuffle(combined)
    return JSONResponse({"deck": combined[:5], "error": None})


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

    return JSONResponse({"paper": None})