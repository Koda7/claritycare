"""
PDF Discovery: scrapes Oscar's clinical guidelines page and resolves actual PDF URLs.

Two-phase approach:
1. Scrape the main page for guideline page links
2. Visit each guideline page to extract the embedded PDF URL (hosted on Contentful CDN)
"""
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_connection, init_db

SOURCE_URL = "https://www.hioscar.com/clinical-guidelines/medical"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
RATE_LIMIT = 0.5


def discover_pdfs() -> list[dict]:
    """Fetch the source page and resolve all PDF links."""
    print("=" * 60)
    print("PDF DISCOVERY")
    print("=" * 60)
    print(f"Fetching: {SOURCE_URL}")

    response = httpx.get(SOURCE_URL, headers=HEADERS, follow_redirects=True, timeout=30)
    response.raise_for_status()
    print(f"Status: {response.status_code}, Content-Length: {len(response.text)}")

    soup = BeautifulSoup(response.text, "html.parser")
    links = soup.find_all("a", href=True)

    # Phase 1: collect guideline page URLs and titles
    guidelines = []
    seen_urls = set()

    for link in links:
        href = link["href"]
        if "/medical/cg" not in href.lower():
            continue
        page_url = urljoin(SOURCE_URL, href)
        if page_url in seen_urls:
            continue
        seen_urls.add(page_url)

        title = extract_title(link)
        guidelines.append({"title": title, "page_url": page_url})

    print(f"Found {len(guidelines)} guideline pages")
    print("-" * 60)

    # Phase 2: resolve actual PDF URLs from each guideline page
    print("Resolving PDF download URLs from guideline pages...")
    pdfs = []
    client = httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30)

    for i, g in enumerate(guidelines, 1):
        pdf_url = resolve_pdf_url(client, g["page_url"])
        if pdf_url:
            pdfs.append({"title": g["title"], "pdf_url": pdf_url})
            if i % 10 == 0 or i == len(guidelines):
                print(f"  [{i}/{len(guidelines)}] Resolved {len(pdfs)} PDFs so far")
        else:
            # Fallback: store the page URL as-is for record keeping
            pdfs.append({"title": g["title"], "pdf_url": g["page_url"]})

        time.sleep(RATE_LIMIT)

    client.close()
    print(f"Resolved {len(pdfs)} total PDF links")
    print("-" * 60)
    return pdfs


def resolve_pdf_url(client: httpx.Client, page_url: str) -> str | None:
    """Visit a guideline page and extract the embedded PDF URL."""
    try:
        resp = client.get(page_url)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")

        # Look for embed/iframe with PDF source (Contentful CDN)
        for tag in soup.find_all(["embed", "object", "iframe"]):
            src = tag.get("src") or tag.get("data") or ""
            if ".pdf" in src or "ctfassets" in src:
                if src.startswith("//"):
                    src = "https:" + src
                return src

        # Fallback: look for any ctfassets PDF link in the page source
        match = re.search(r'(//assets\.ctfassets\.net/[^\s"\']+\.pdf)', resp.text)
        if match:
            return "https:" + match.group(1) if match.group(1).startswith("//") else match.group(1)

        return None
    except Exception:
        return None


def extract_title(link) -> str:
    """Extract a meaningful title from the link's surrounding HTML context."""
    link_text = link.get_text(strip=True)

    parent = link.parent
    if parent:
        grandparent = parent.parent
        if grandparent:
            full_text = grandparent.get_text(strip=True)
            if full_text.endswith("PDF"):
                title = full_text[:-3].strip()
                if title:
                    return title

    # Fallback: derive from URL
    href = link.get("href", "")
    match = re.search(r"(cg\d+v?\d*)", href)
    if match:
        return match.group(1).upper()

    return link_text or os.path.basename(href)


def store_policies(pdfs: list[dict]):
    """Insert discovered PDFs into the database (idempotent via UNIQUE constraint)."""
    conn = get_connection()
    inserted = 0
    skipped = 0

    for pdf in pdfs:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO policies (title, pdf_url, source_page_url) VALUES (?, ?, ?)",
            (pdf["title"], pdf["pdf_url"], SOURCE_URL),
        )
        if cursor.rowcount > 0:
            inserted += 1
        else:
            skipped += 1

    conn.commit()
    conn.close()
    print(f"Inserted: {inserted} new | Skipped: {skipped} existing")
    print("=" * 60)
    return inserted


def run():
    init_db()
    pdfs = discover_pdfs()
    if not pdfs:
        print("WARNING: No PDFs discovered! The page structure may have changed.")
    store_policies(pdfs)
    return pdfs


if __name__ == "__main__":
    run()
