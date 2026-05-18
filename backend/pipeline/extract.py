"""
PDF Text Extraction: extracts text from PDFs using PyMuPDF, identifies "Initial" criteria sections.
"""
import fitz  # PyMuPDF
import re
import os


# Patterns that indicate the start of an "Initial" criteria section (content, not TOC)
INITIAL_PATTERNS = [
    r"(?i)medical\s+necessity\s+criteria\s+for\s+initial\s+clinical\s+review\s*\n",
    r"(?i)initial\s+clinical\s+review\s*\n.*?(?:criteria|medically\s+necessary)",
    r"(?i)initial\s+authorization\s+criteria",
    r"(?i)initial\s+approval\s+criteria",
    r"(?i)criteria\s+for\s+initial",
    r"(?i)initial\s+medical\s+necessity",
]

# Patterns that indicate the end of the "Initial" section
END_PATTERNS = [
    r"(?i)medical\s+necessity\s+criteria\s+for\s+subsequent\s+clinical\s+review",
    r"(?i)subsequent\s+clinical\s+review\s*\n",
    r"(?i)continuation\s+(of\s+services|authorization|criteria|therapy|treatment)",
    r"(?i)medical\s+necessity\s+criteria\s+for\s+continued",
    r"(?i)reauthorization\s+criteria",
    r"(?i)continued\s+stay\s+criteria",
    r"(?i)experimental\s+or\s+investigational",
    r"(?i)not\s+medically\s+necessary\s*\n",
]


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract full text from a PDF file."""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def find_initial_section(full_text: str) -> str:
    """
    Heuristic to extract only the "Initial" criteria section from the full text.
    
    Strategy:
    1. Skip the table of contents (first ~2000 chars typically)
    2. Find the actual "Initial" content section header
    3. Extract until a "Subsequent/Continuation" header or end of document
    4. Fallback: return full text if no initial section is identified
    """
    # Skip TOC: look for actual content sections (after first ~1500 chars which is usually TOC)
    # But if the doc is short, don't skip
    toc_cutoff = min(1500, len(full_text) // 4)
    search_text = full_text[toc_cutoff:]

    # Try each initial pattern to find the content section start
    best_match = None
    best_pos = len(search_text)

    for pattern in INITIAL_PATTERNS:
        match = re.search(pattern, search_text)
        if match and match.start() < best_pos:
            best_match = match
            best_pos = match.start()

    if best_match is None:
        # No initial section found - return full text as fallback
        return full_text

    # Calculate absolute position
    section_start = toc_cutoff + best_pos
    remaining_text = full_text[section_start:]

    # Find the end boundary - look for end patterns after some minimum content
    min_content = 500  # Need at least 500 chars of content
    end_pos = len(remaining_text)

    for pattern in END_PATTERNS:
        match = re.search(pattern, remaining_text[min_content:])
        if match:
            candidate = match.start() + min_content
            if candidate < end_pos:
                end_pos = candidate

    return remaining_text[:end_pos]


def extract_for_policy(pdf_path: str) -> tuple[str, str]:
    """
    Extract text and identify initial section.
    Returns: (full_text, initial_section_text)
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    full_text = extract_text_from_pdf(pdf_path)
    initial_text = find_initial_section(full_text)
    return full_text, initial_text
