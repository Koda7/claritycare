"""
PDF Download: downloads all discovered PDFs with rate limiting and retries.
"""
import httpx
import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_connection, init_db

PDF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pdfs")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
MAX_RETRIES = 3
RATE_LIMIT_SECONDS = 1.0


def download_all():
    """Download all discovered PDFs that haven't been successfully downloaded yet."""
    init_db()
    os.makedirs(PDF_DIR, exist_ok=True)

    conn = get_connection()
    # Get policies that don't have a successful download
    policies = conn.execute("""
        SELECT p.id, p.title, p.pdf_url
        FROM policies p
        LEFT JOIN downloads d ON d.policy_id = p.id AND d.http_status = 200
        WHERE d.id IS NULL
    """).fetchall()
    conn.close()

    print("=" * 60)
    print("PDF DOWNLOAD")
    print("=" * 60)
    print(f"Policies to download: {len(policies)}")
    print("-" * 60)

    success_count = 0
    fail_count = 0

    for i, policy in enumerate(policies, 1):
        policy_id = policy["id"]
        title = policy["title"]
        pdf_url = policy["pdf_url"]
        print(f"[{i}/{len(policies)}] {title}")
        print(f"  URL: {pdf_url}")

        stored_location = os.path.join(PDF_DIR, f"{policy_id}.pdf")
        status_code, error = download_with_retry(pdf_url, stored_location)

        # Record the outcome
        conn = get_connection()
        conn.execute(
            """INSERT OR REPLACE INTO downloads (policy_id, stored_location, http_status, error)
               VALUES (?, ?, ?, ?)""",
            (policy_id, stored_location if status_code == 200 else None, status_code, error),
        )
        conn.commit()
        conn.close()

        if status_code == 200:
            size_kb = os.path.getsize(stored_location) / 1024
            print(f"  OK ({size_kb:.1f} KB)")
            success_count += 1
        else:
            print(f"  FAILED: {error}")
            fail_count += 1

        # Rate limit between requests
        if i < len(policies):
            time.sleep(RATE_LIMIT_SECONDS)

    print("-" * 60)
    print(f"Results: {success_count} succeeded, {fail_count} failed")
    print("=" * 60)


def download_with_retry(url: str, dest: str) -> tuple[int, str | None]:
    """Download a PDF with manual backoff retries. Returns (status_code, error)."""
    backoff = [1, 2, 4]

    for attempt in range(MAX_RETRIES):
        try:
            with httpx.Client(follow_redirects=True, timeout=30) as client:
                resp = client.get(url, headers=HEADERS)

            if resp.status_code == 200:
                content_type = resp.headers.get("content-type", "")
                if "pdf" in content_type or "octet-stream" in content_type or len(resp.content) > 1000:
                    with open(dest, "wb") as f:
                        f.write(resp.content)
                    return (200, None)
                else:
                    return (resp.status_code, f"Response not a PDF (content-type: {content_type})")

            if resp.status_code in (429, 500, 502, 503, 504):
                if attempt < MAX_RETRIES - 1:
                    time.sleep(backoff[attempt])
                    continue
                return (resp.status_code, f"HTTP {resp.status_code} after {MAX_RETRIES} retries")

            return (resp.status_code, f"HTTP {resp.status_code}")

        except httpx.TimeoutException:
            if attempt < MAX_RETRIES - 1:
                time.sleep(backoff[attempt])
                continue
            return (0, f"Timeout after {MAX_RETRIES} retries")
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(backoff[attempt])
                continue
            return (0, str(e))

    return (0, "Max retries exceeded")


if __name__ == "__main__":
    download_all()
