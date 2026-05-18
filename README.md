## ClarityCare — Oscar Medical Guidelines Structuring Pipeline

End-to-end system that discovers, downloads, and structures Oscar Health's medical guideline PDFs into navigable JSON decision trees.

- Scrapes **all** medical guideline PDF links from Oscar's [clinical guidelines page](https://www.hioscar.com/clinical-guidelines/medical)
- Uses an LLM to extract **initial** medical necessity criteria into structured JSON decision trees
- Persists policy metadata, download records, and structured trees in SQLite
- Provides a React UI to browse policies and explore criteria trees with expand/collapse navigation

---

### Prerequisites
- Python 3.11+
- Node.js 18+
- OpenAI API key

### Quick Start

1. **Set up environment:**
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

2. **Run the full pipeline (discovery → download → structuring):**
```bash
./run.sh
```

3. **Start the API server:**
```bash
cd backend && uvicorn main:app --reload
```

4. **Start the frontend (separate terminal):**
```bash
cd frontend && npm install && npm run dev
```

5. **Open the UI:** http://localhost:5173

---

### Running Each Step Independently

```bash
# Initialize database
cd backend && python database.py

# Discover all PDF links
python -m scraper.discover

# Download all PDFs (1s rate limit, 3 retries with backoff)
python -m scraper.download

# Structure policies via LLM
python -m pipeline.structure --limit 15
```

---

### Initial-Only Selection Logic

The structuring pipeline uses a **regex-based heuristic** to extract only the "Initial" criteria section from each PDF:

1. **Section detection**: Searches for headers matching patterns like:
   - "Initial Authorization Criteria"
   - "Initial Approval Criteria"
   - "Initial Medical Necessity"
   - "Criteria for Initial Authorization"
   - "Initial Certification/Request"

2. **Boundary detection**: The initial section ends at the first occurrence of:
   - "Continuation Authorization/Criteria"
   - "Reauthorization Criteria"
   - "Renewal Criteria"
   - "Continued Stay Criteria"

3. **Fallback**: If no explicit "Initial" header is found, the full document text is sent to the LLM with instructions to extract only initial/first-time criteria. The LLM prompt explicitly states "Extract ONLY the initial/first-time authorization criteria."

**Known limitations**: PDFs with non-standard headers (e.g., "First-time Authorization") or unconventional formatting may fall through to the full-text fallback. The heuristic path taken is logged for auditability.

---

### Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend | Python + FastAPI | Best ecosystem for scraping + PDF + LLM |
| Database | SQLite | Zero-infrastructure, ACID, single-file persistence |
| Scraping | BeautifulSoup + httpx | Server-rendered page, sync is fine for ~30 PDFs |
| PDF Extraction | PyMuPDF (fitz) | Fast, reliable text extraction |
| LLM | OpenAI gpt-4o | Best JSON adherence, structured output mode |
| Validation | Pydantic | Recursive model validation with clear errors |
| Frontend | React + TypeScript + Vite + Tailwind | Natural fit for recursive tree rendering |

---

### Architecture

**Pipeline stages:**
1. **Discovery** — scrapes the Oscar guidelines page, extracts all PDF links, stores policy metadata in SQLite (idempotent on `pdf_url`)
2. **Download** — fetches each PDF with 1s rate limiting and exponential backoff retries, records success/failure
3. **Structuring** — extracts text via PyMuPDF, isolates "Initial" criteria via regex heuristics, sends to GPT-4o for JSON structuring, validates output with Pydantic

**Data model:**
- `policies` — all discovered guidelines (title, pdf_url, source_page_url, discovered_at)
- `downloads` — download records per policy (stored_location, http_status, error)
- `structured_policies` — LLM-structured JSON trees (extracted_text, structured_json, llm_metadata, validation_error)

**JSON tree format** (matches `oscar.json`):
- Top level: `title`, `insurance_name`, `rules` (root node)
- Each node: `rule_id`, `rule_text`, optional `operator` (AND/OR), optional `rules` (children)
- Leaf nodes have `rule_id` + `rule_text`; non-leaf nodes include `operator` and `rules` array
