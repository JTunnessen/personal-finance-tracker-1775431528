import csv
import io
import logging
import sqlite3
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Annotated, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator, model_validator

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s – %(message)s",
)
log = logging.getLogger("finance_tracker")

DB_PATH = "finance.db"

# ── Database helpers ─────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                type        TEXT    NOT NULL CHECK(type IN ('income', 'expense')),
                amount      REAL    NOT NULL CHECK(amount > 0),
                description TEXT    NOT NULL,
                category    TEXT    NOT NULL,
                txn_date    TEXT    NOT NULL,
                created_at  TEXT    NOT NULL
            )
        """)
        conn.commit()
    log.info("Database initialised at %s", DB_PATH)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="FinanceTracker", version="1.0.0", lifespan=lifespan)

# ── Pydantic schemas ──────────────────────────────────────────────────────────

VALID_TYPES = {"income", "expense"}


class TransactionIn(BaseModel):
    type: str
    amount: float
    description: str
    category: str
    txn_date: str  # ISO-8601 date string YYYY-MM-DD

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in VALID_TYPES:
            raise ValueError(f"type must be one of {VALID_TYPES}")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("amount must be positive")
        return round(v, 2)

    @field_validator("description", "category")
    @classmethod
    def not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("field must not be empty")
        return v

    @field_validator("txn_date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("txn_date must be in YYYY-MM-DD format")
        return v


class TransactionOut(BaseModel):
    id: int
    type: str
    amount: float
    description: str
    category: str
    txn_date: str
    created_at: str


class TransactionUpdate(BaseModel):
    type: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    category: Optional[str] = None
    txn_date: Optional[str] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.lower().strip()
            if v not in VALID_TYPES:
                raise ValueError(f"type must be one of {VALID_TYPES}")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("amount must be positive")
        return round(v, 2) if v is not None else v

    @field_validator("description", "category")
    @classmethod
    def not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("field must not be empty")
        return v

    @field_validator("txn_date")
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError("txn_date must be in YYYY-MM-DD format")
        return v


class Summary(BaseModel):
    total_income: float
    total_expense: float
    net_balance: float


class CategoryBreakdown(BaseModel):
    category: str
    type: str
    total: float


# ── Dependency ────────────────────────────────────────────────────────────────

def db_dep() -> sqlite3.Connection:
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()


DbDep = Annotated[sqlite3.Connection, Depends(db_dep)]


# ── Helpers ───────────────────────────────────────────────────────────────────

def row_to_txn(row: sqlite3.Row) -> TransactionOut:
    return TransactionOut(
        id=row["id"],
        type=row["type"],
        amount=row["amount"],
        description=row["description"],
        category=row["category"],
        txn_date=row["txn_date"],
        created_at=row["created_at"],
    )


def build_filter_query(
    base: str,
    date_from: Optional[str],
    date_to: Optional[str],
    category: Optional[str],
    txn_type: Optional[str],
) -> tuple[str, list]:
    conditions: list[str] = []
    params: list = []
    if date_from:
        conditions.append("txn_date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("txn_date <= ?")
        params.append(date_to)
    if category:
        conditions.append("category = ?")
        params.append(category)
    if txn_type:
        conditions.append("type = ?")
        params.append(txn_type.lower())
    if conditions:
        base += " WHERE " + " AND ".join(conditions)
    return base, params


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# Transactions CRUD

@app.post("/api/transactions", response_model=TransactionOut, status_code=201)
def create_transaction(body: TransactionIn, db: DbDep):
    now = datetime.utcnow().isoformat()
    cur = db.execute(
        """
        INSERT INTO transactions (type, amount, description, category, txn_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (body.type, body.amount, body.description, body.category, body.txn_date, now),
    )
    db.commit()
    row = db.execute("SELECT * FROM transactions WHERE id = ?", (cur.lastrowid,)).fetchone()
    log.info("Created transaction id=%s type=%s amount=%s", row["id"], row["type"], row["amount"])
    return row_to_txn(row)


@app.get("/api/transactions", response_model=List[TransactionOut])
def list_transactions(
    db: DbDep,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    txn_type: Optional[str] = Query(None),
):
    sql, params = build_filter_query(
        "SELECT * FROM transactions", date_from, date_to, category, txn_type
    )
    sql += " ORDER BY txn_date DESC, id DESC"
    rows = db.execute(sql, params).fetchall()
    return [row_to_txn(r) for r in rows]


@app.get("/api/transactions/{txn_id}", response_model=TransactionOut)
def get_transaction(txn_id: int, db: DbDep):
    row = db.execute("SELECT * FROM transactions WHERE id = ?", (txn_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return row_to_txn(row)


@app.put("/api/transactions/{txn_id}", response_model=TransactionOut)
def update_transaction(txn_id: int, body: TransactionUpdate, db: DbDep):
    row = db.execute("SELECT * FROM transactions WHERE id = ?", (txn_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Transaction not found")
    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    set_clause = ", ".join(f"{k} = ?" for k in data)
    params = list(data.values()) + [txn_id]
    db.execute(f"UPDATE transactions SET {set_clause} WHERE id = ?", params)
    db.commit()
    updated = db.execute("SELECT * FROM transactions WHERE id = ?", (txn_id,)).fetchone()
    log.info("Updated transaction id=%s", txn_id)
    return row_to_txn(updated)


@app.delete("/api/transactions/{txn_id}", status_code=204)
def delete_transaction(txn_id: int, db: DbDep):
    row = db.execute("SELECT id FROM transactions WHERE id = ?", (txn_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.execute("DELETE FROM transactions WHERE id = ?", (txn_id,))
    db.commit()
    log.info("Deleted transaction id=%s", txn_id)


# Summary / breakdown

@app.get("/api/summary", response_model=Summary)
def get_summary(
    db: DbDep,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
):
    sql, params = build_filter_query(
        "SELECT type, SUM(amount) as total FROM transactions",
        date_from, date_to, category, None,
    )
    sql += " GROUP BY type"
    rows = db.execute(sql, params).fetchall()
    totals = {r["type"]: r["total"] for r in rows}
    income = round(totals.get("income", 0.0), 2)
    expense = round(totals.get("expense", 0.0), 2)
    return Summary(total_income=income, total_expense=expense, net_balance=round(income - expense, 2))


@app.get("/api/breakdown", response_model=List[CategoryBreakdown])
def get_breakdown(
    db: DbDep,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    txn_type: Optional[str] = Query(None),
):
    sql, params = build_filter_query(
        "SELECT category, type, SUM(amount) as total FROM transactions",
        date_from, date_to, None, txn_type,
    )
    sql += " GROUP BY category, type ORDER BY total DESC"
    rows = db.execute(sql, params).fetchall()
    return [
        CategoryBreakdown(category=r["category"], type=r["type"], total=round(r["total"], 2))
        for r in rows
    ]


@app.get("/api/categories")
def get_categories(db: DbDep):
    rows = db.execute("SELECT DISTINCT category FROM transactions ORDER BY category").fetchall()
    return [r["category"] for r in rows]


# CSV Export

@app.get("/api/export")
def export_csv(
    db: DbDep,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    txn_type: Optional[str] = Query(None),
):
    sql, params = build_filter_query(
        "SELECT * FROM transactions", date_from, date_to, category, txn_type
    )
    sql += " ORDER BY txn_date DESC, id DESC"
    rows = db.execute(sql, params).fetchall()

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(["ID", "Type", "Amount", "Description", "Category", "Date", "Created At"])
    for r in rows:
        writer.writerow([
            r["id"], r["type"], f"{r['amount']:.2f}",
            r["description"], r["category"], r["txn_date"], r["created_at"]
        ])
    output.seek(0)
    filename = f"transactions_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    log.info("Exporting %d transactions to CSV", len(rows))
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# Serve frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
