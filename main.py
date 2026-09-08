from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import arxiv
import requests
import random

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
        }
    },
    "Computer Science & AI": {
        "arxiv_query": "cat:cs.LG OR cat:cs.AI OR cat:cs.CV OR cat:cs.CC",
        "subcategories": {
            "Machine Learning": "cat:cs.LG",
            "Artificial Intelligence": "cat:cs.AI",
            "Computer Vision": "cat:cs.CV",
            "Theory of Computation": "cat:cs.CC",
        }
    },
    "Psychology & Cognitive Science": {
        "arxiv_query": None,
        "subcategories": {
            "General Psychology": "Psychology",
            "Social Psychology": "Social Psychology",
            "Cognitive Psychology": "Cognitive Psychology",
            "Developmental Psychology": "Developmental Psychology",
        }
    },
    "Biology & Medicine": {
        "arxiv_query": "cat:q-bio.NC OR cat:q-bio.BM OR cat:q-bio.GN",
        "subcategories": {
            "Neurons & Cognition": "cat:q-bio.NC",
            "Genomics": "cat:q-bio.GN",
            "Biomolecules": "cat:q-bio.BM",
        }
    }
}

def fetch_arxiv(topics, limit=5, is_classic=False):
    """Fetches preprints/papers from arXiv."""
    if not topics or limit <= 0:
        return []
    
    papers = []
    seen = set()
    per_topic = max(1, limit // len(topics))
    
    for t in topics:
        code = t.get("code", "")
        if not code:
            continue
        query_str = code if "cat:" in code else f"abs:\"{code}\""
        
        try:
            client = arxiv.Client(page_size=15, delay_seconds=1, num_retries=1)
            sort_criterion = arxiv.SortCriterion.Relevance if is_classic else arxiv.SortCriterion.SubmittedDate
            search = arxiv.Search(
                query=query_str,
                max_results=15,
                sort_by=sort_criterion,
                sort_order=arxiv.SortOrder.Descending
            )
            count = 0
            for r in list(client.results(search)):
                t_clean = r.title.replace("\n", " ").strip()
                pub_year = int(r.published.strftime("%Y"))
                
                if is_classic and pub_year > 2005:
                    continue
                
                if t_clean not in seen:
                    seen.add(t_clean)
                    papers.append({
                        "id": f"arxiv_{r.entry_id.split('/')[-1]}",
                        "title": t_clean,
                        "authors": ", ".join([a.name for a in r.authors[:2]]) + (" et al." if len(r.authors) > 2 else ""),
                        "year": str(pub_year),
                        "category": t["name"],
                        "summary": r.summary.replace("\n", " "),
                        "url": r.entry_id,
                        "pdf": r.pdf_url,
                        "type": "Seminal Classic" if is_classic else "Fresh Preprint"
                    })
                    count += 1
                    if count >= per_topic:
                        break
        except Exception as e:
            print(f"arXiv error: {e}")
            
    return papers

def fetch_openalex_classics(topics, limit=5):
    """Queries OpenAlex for high-citation historical literature (pre-2005)."""
    if not topics or limit <= 0:
        return []
    
    papers = []
    seen = set()
    per_topic = max(1, limit // len(topics))
    
    for t in topics:
        search_term = t["name"].replace("All ", "")
        try:
            url = f"https://api.openalex.org/works?search={search_term}&filter=is_oa:true,publication_year:<2005,cited_by_count:>150&sort=cited_by_count:desc&per-page=15"
            res = requests.get(url, timeout=3).json()
            results = res.get("results", [])
            
            count = 0
            for r in results:
                t_clean = r.get("display_name", "").strip()
                citations = r.get("cited_by_count", 0)
                if t_clean and t_clean not in seen:
                    seen.add(t_clean)
                    oa_pdf = r.get("open_access", {}).get("oa_url") or f"https://www.google.com/search?q={t_clean}"
                    authorships = r.get("authorships", [])
                    authors_str = ", ".join([a.get("author", {}).get("display_name", "") for a in authorships[:2]])
                    
                    papers.append({
                        "id": f"oa_{r.get('id', random.randint(1000, 9999))}",
                        "title": t_clean,
                        "authors": authors_str or "Unknown Authors",
                        "year": str(r.get("publication_year", "N/A")),
                        "category": f"{t['name']} ({citations:,} Citations)",
                        "summary": f"Landmark paper in {search_term}. Cited over {citations:,} times in academic literature.",
                        "url": oa_pdf,
                        "pdf": oa_pdf,
                        "type": "Seminal Classic"
                    })
                    count += 1
                    if count >= per_topic:
                        break
        except Exception as e:
            print(f"OpenAlex error: {e}")
            
    return papers

def fetch_europe_pmc_classics(topics, limit=5):
    """Queries Europe PMC's open-access archive for historical papers (1900-2005)."""
    if not topics or limit <= 0:
        return []
    
    papers = []
    seen = set()
    per_topic = max(1, limit // len(topics))
    
    for t in topics:
        search_term = t["name"].replace("All ", "")
        try:
            url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={search_term}%20PUB_YEAR:[1900%20TO%202005]%20OPEN_ACCESS:y&format=json&pageSize=10&sort=CITED:desc"
            res = requests.get(url, timeout=3).json()
            results = res.get("resultList", {}).get("result", [])
            
            count = 0
            for r in results:
                t_clean = r.get("title", "").strip(".")
                if t_clean and t_clean not in seen:
                    seen.add(t_clean)
                    papers.append({
                        "id": f"epmc_{r.get('id', random.randint(1000, 9999))}",
                        "title": t_clean,
                        "authors": r.get("authorString", "Unknown Authors"),
                        "year": str(r.get("pubYear", "N/A")),
                        "category": f"{t['name']} Classic",
                        "summary": r.get("abstractText", "Foundational paper retrieved from Europe PMC historical archives."),
                        "url": f"https://europepmc.org/article/MED/{r.get('id')}",
                        "pdf": f"https://europepmc.org/article/MED/{r.get('id')}",
                        "type": "Seminal Classic"
                    })
                    count += 1
                    if count >= per_topic:
                        break
        except Exception as e:
            print(f"Europe PMC error: {e}")
            
    return papers

def get_classics_multidb(topics, limit=5):
    """Aggregates classics from OpenAlex, Europe PMC, and historical arXiv records."""
    papers = fetch_openalex_classics(topics, limit=limit)
    if len(papers) < limit:
        papers.extend(fetch_europe_pmc_classics(topics, limit=(limit - len(papers))))
    if len(papers) < limit:
        papers.extend(fetch_arxiv(topics, limit=(limit - len(papers)), is_classic=True))
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
    
    system_messages = []

    modern_papers = fetch_arxiv(modern_topics, limit=modern_count, is_classic=False) if modern_count > 0 else []
    classic_papers = get_classics_multidb(classic_topics, limit=classic_count) if classic_count > 0 else []

    # Detect if specific topic ratio fell short
    if modern_count > 0 and len(modern_papers) < modern_count:
        system_messages.append("Ratio adjusted: Modern preprints for active filters were limited. Filled remaining slots with available literature.")
    if classic_count > 0 and len(classic_papers) < classic_count:
        system_messages.append("Ratio adjusted: Classic literature for active filters was limited. Filled remaining slots with open-access archives.")

    combined = modern_papers + classic_papers

    # If deck has fewer than 5 items, fill using broader topic queries
    if len(combined) < 5:
        needed = 5 - len(combined)
        all_active_topics = modern_topics + classic_topics
        extra_fill = get_classics_multidb(all_active_topics, limit=needed)
        combined.extend(extra_fill)
        if len(extra_fill) > 0:
            system_messages.append("Choosing additional articles based on your other active topic filters to ensure a full 5-card deck.")

    if len(combined) == 0:
        return JSONResponse({
            "deck": [],
            "error": "No open-access papers found matching your active topic filters across all databases. Please broaden your selection."
        })

    random.shuffle(combined)
    return JSONResponse({
        "deck": combined[:5],
        "messages": list(set(system_messages)),
        "error": None
    })

@app.post("/api/replacement-card")
async def get_replacement_card(request: Request):
    data = await request.json()
    type_needed = data.get("type", "modern")
    topics = data.get("topics", [])
    seen_titles = set(data.get("seenTitles", []))

    if type_needed == "classic":
        candidates = get_classics_multidb(topics, limit=10)
    else:
        candidates = fetch_arxiv(topics, limit=10, is_classic=False)

    for c in candidates:
        if c["title"] not in seen_titles:
            return JSONResponse({"paper": c})

    # Secondary fill if candidates are seen
    all_candidates = get_classics_multidb(topics, limit=10) + fetch_arxiv(topics, limit=10)
    for c in all_candidates:
        if c["title"] not in seen_titles:
            return JSONResponse({"paper": c})

    return JSONResponse({"paper": None})