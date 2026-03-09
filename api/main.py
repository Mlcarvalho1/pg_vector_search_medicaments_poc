from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import psycopg2

from search_engine import DB_DSN, OLLAMA_HOST, search, search_hybrid, _ollama_client

app = FastAPI(title="Medicaments Search API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=50)


def get_conn():
    return psycopg2.connect(DB_DSN)


@app.get("/health")
def health():
    try:
        conn = get_conn()
        conn.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"

    try:
        _ollama_client.list()
        ollama_status = "reachable"
    except Exception as e:
        ollama_status = f"error: {e}"

    return {"status": "ok", "db": db_status, "ollama": ollama_status}


@app.post("/search")
def semantic_search(req: SearchRequest):
    try:
        conn = get_conn()
        try:
            results = search(conn, req.query, req.limit)
        finally:
            conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "query": req.query,
        "mode": "semantic",
        "exclusions": [],
        "results": results,
    }


@app.post("/search/hybrid")
def hybrid_search(req: SearchRequest):
    try:
        conn = get_conn()
        try:
            results, exclusions = search_hybrid(conn, req.query, req.limit)
        finally:
            conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "query": req.query,
        "mode": "hybrid",
        "exclusions": exclusions,
        "results": results,
    }
