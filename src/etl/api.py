import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

DB_PATH = Path(__file__).parents[2] / 'nifty100.db'


class Company(BaseModel):
    company_id: int
    company_name: str
    ticker: str
    sector_name: str | None = None


class CompanyDetail(Company):
    website_url: str | None = None
    nse_symbol: str | None = None
    bse_code: str | None = None


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not DB_PATH.exists():
        raise RuntimeError(f"Database not found: {DB_PATH}")
    yield


app = FastAPI(title="Nifty 100 Data API", lifespan=lifespan)


@app.get("/")
def root():
    return {"message": "Nifty 100 Data API", "endpoints": ["/companies", "/companies/{ticker}", "/tables"]}


@app.get("/companies")
def list_companies():
    conn = get_db()
    rows = conn.execute("""
        SELECT c.company_id, c.company_name, c.ticker, s.sector_name
        FROM companies c LEFT JOIN sectors s ON c.sector_id = s.sector_id
        ORDER BY c.ticker
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/companies/{ticker}")
def get_company(ticker: str):
    conn = get_db()
    row = conn.execute("""
        SELECT c.*, s.sector_name
        FROM companies c LEFT JOIN sectors s ON c.sector_id = s.sector_id
        WHERE c.ticker = ?
    """, (ticker.upper(),)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Company not found")
    return dict(row)


@app.get("/tables")
def list_tables():
    conn = get_db()
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    result = []
    for t in tables:
        name = t[0]
        count = conn.execute(f"SELECT COUNT(*) FROM \"{name}\"").fetchone()[0]
        result.append({"table": name, "row_count": count})
    conn.close()
    return result
