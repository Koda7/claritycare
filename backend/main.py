"""
FastAPI application serving the Oscar Guidelines API.
"""
import json
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from database import get_connection, init_db

app = FastAPI(
    title="Oscar Medical Guidelines API",
    root_path=os.getenv("ROOT_PATH", ""),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PolicySummary(BaseModel):
    id: int
    title: str
    pdf_url: str
    source_page_url: str
    discovered_at: str
    has_structured_data: bool
    download_status: Optional[int] = None


class PolicyDetail(BaseModel):
    id: int
    title: str
    pdf_url: str
    source_page_url: str
    discovered_at: str
    download_status: Optional[int] = None
    download_error: Optional[str] = None
    structured_json: Optional[dict] = None
    structured_at: Optional[str] = None
    llm_model: Optional[str] = None
    validation_error: Optional[str] = None


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/policies", response_model=list[PolicySummary])
def list_policies():
    conn = get_connection()
    rows = conn.execute("""
        SELECT
            p.id, p.title, p.pdf_url, p.source_page_url, p.discovered_at,
            d.http_status as download_status,
            CASE WHEN sp.structured_json IS NOT NULL THEN 1 ELSE 0 END as has_structured_data
        FROM policies p
        LEFT JOIN downloads d ON d.policy_id = p.id
        LEFT JOIN structured_policies sp ON sp.policy_id = p.id
        ORDER BY p.id
    """).fetchall()
    conn.close()

    return [
        PolicySummary(
            id=row["id"],
            title=row["title"],
            pdf_url=row["pdf_url"],
            source_page_url=row["source_page_url"],
            discovered_at=row["discovered_at"] or "",
            has_structured_data=bool(row["has_structured_data"]),
            download_status=row["download_status"],
        )
        for row in rows
    ]


@app.get("/api/policies/{policy_id}", response_model=PolicyDetail)
def get_policy(policy_id: int):
    conn = get_connection()
    row = conn.execute("""
        SELECT
            p.id, p.title, p.pdf_url, p.source_page_url, p.discovered_at,
            d.http_status as download_status, d.error as download_error,
            sp.structured_json, sp.structured_at, sp.llm_model, sp.validation_error
        FROM policies p
        LEFT JOIN downloads d ON d.policy_id = p.id
        LEFT JOIN structured_policies sp ON sp.policy_id = p.id
        WHERE p.id = ?
    """, (policy_id,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Policy not found")

    structured = None
    if row["structured_json"]:
        try:
            structured = json.loads(row["structured_json"])
        except json.JSONDecodeError:
            structured = None

    return PolicyDetail(
        id=row["id"],
        title=row["title"],
        pdf_url=row["pdf_url"],
        source_page_url=row["source_page_url"],
        discovered_at=row["discovered_at"] or "",
        download_status=row["download_status"],
        download_error=row["download_error"],
        structured_json=structured,
        structured_at=row["structured_at"],
        llm_model=row["llm_model"],
        validation_error=row["validation_error"],
    )


@app.get("/api/stats")
def get_stats():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as c FROM policies").fetchone()["c"]
    downloaded = conn.execute("SELECT COUNT(*) as c FROM downloads WHERE http_status = 200").fetchone()["c"]
    structured = conn.execute("SELECT COUNT(*) as c FROM structured_policies WHERE structured_json IS NOT NULL").fetchone()["c"]
    failed = conn.execute("SELECT COUNT(*) as c FROM structured_policies WHERE validation_error IS NOT NULL AND structured_json IS NULL").fetchone()["c"]
    conn.close()

    return {
        "total_policies": total,
        "downloaded": downloaded,
        "structured": structured,
        "failed_structuring": failed,
    }
