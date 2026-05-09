"""
signals_engine.py — AI deal-signal analysis using the Anthropic Claude API.

Reads companies from SQLite, calls Claude once per company, writes results
to the `signals` table. Runs in a background thread so Flask stays responsive.
"""

import json
import sqlite3
import threading
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
import os

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL      = "claude-sonnet-4-6"
API_URL           = "https://api.anthropic.com/v1/messages"

# ── shared refresh state ────────────────────────────────────────────────────
_status = {
    "running":   False,
    "total":     0,
    "done":      0,
    "last_run":  None,
    "error":     None,
}
_lock = threading.Lock()


# ── table setup ─────────────────────────────────────────────────────────────
def init_signals_table(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id        INTEGER,
            company_name      TEXT    NOT NULL UNIQUE,
            signal_strength   TEXT    NOT NULL,
            ai_reasoning      TEXT    NOT NULL,
            trigger_datapoint TEXT    NOT NULL,
            updated_at        TEXT    NOT NULL
        )
    """)
    conn.commit()
    conn.close()


# ── Claude prompt + call ─────────────────────────────────────────────────────
def _prompt(company: dict) -> str:
    return f"""You are a B2B sales intelligence analyst specialising in the Brazilian construction sector.

Analyse this company and return a JSON object — nothing else, no markdown, no explanation.

Company data:
- Name: {company.get('company', 'N/A')}
- INTEC Ranking 2025: #{company.get('ranking', 'N/A')}
- State: {company.get('state', 'N/A')}
- m² 2025: {company.get('sqm_2025', 'N/A')}
- Lead Score: {company.get('lead_score', 'N/A')} / 100
- Tier: {company.get('tier', 'N/A')}
- Capital type: {company.get('capital', 'N/A')}
- B3 Ticker: {company.get('b3_ticker', 'N/A')}
- Growth Story: {company.get('growth_story', 'N/A')}
- Recent News: {company.get('news_highlights', 'N/A')}
- Website: {company.get('website', 'N/A')}
- Email: {company.get('email', 'N/A')}
- Decision Makers: {company.get('decision_makers', 'N/A')}

Return exactly this JSON shape:
{{
  "signal_strength": "<Hot|Warm|Watch|Cold>",
  "ai_reasoning": "<2-3 sentence explanation of why this company is or isn't a strong prospect right now>",
  "trigger_datapoint": "<the single most compelling data point that drives the signal>"
}}

Criteria:
- Hot  → strong growth signals + good contact data + recent positive news
- Warm → moderate growth or good contacts but missing one dimension
- Watch → interesting but unclear timing or limited contact info
- Cold → declining, no contacts, or no actionable data"""


def _call_claude(company: dict) -> dict:
    headers = {
        "x-api-key":         ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
    }
    body = {
        "model":      CLAUDE_MODEL,
        "max_tokens": 400,
        "messages":   [{"role": "user", "content": _prompt(company)}],
    }
    resp = requests.post(API_URL, headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    raw = resp.json()["content"][0]["text"].strip()

    # strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


# ── background worker ────────────────────────────────────────────────────────
def _run_refresh(db_path: str) -> None:
    with _lock:
        _status["running"] = True
        _status["error"]   = None
        _status["done"]    = 0

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        companies = [dict(r) for r in conn.execute(
            "SELECT * FROM companies ORDER BY CAST(lead_score AS INTEGER) DESC"
        ).fetchall()]
        conn.close()

        with _lock:
            _status["total"] = len(companies)

        for company in companies:
            try:
                result = _call_claude(company)
                now    = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                conn   = sqlite3.connect(db_path)
                conn.execute("""
                    INSERT INTO signals
                        (company_id, company_name, signal_strength, ai_reasoning, trigger_datapoint, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(company_name) DO UPDATE SET
                        company_id        = excluded.company_id,
                        signal_strength   = excluded.signal_strength,
                        ai_reasoning      = excluded.ai_reasoning,
                        trigger_datapoint = excluded.trigger_datapoint,
                        updated_at        = excluded.updated_at
                """, (
                    company.get("id"),
                    company["company"],
                    result.get("signal_strength", "Watch"),
                    result.get("ai_reasoning",    "N/A"),
                    result.get("trigger_datapoint", "N/A"),
                    now,
                ))
                conn.commit()
                conn.close()
            except Exception as e:
                pass  # skip individual failures, continue with rest

            with _lock:
                _status["done"] += 1

    except Exception as e:
        with _lock:
            _status["error"] = str(e)
    finally:
        with _lock:
            _status["running"]  = False
            _status["last_run"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def start_refresh(db_path: str) -> dict:
    if not ANTHROPIC_API_KEY:
        return {"status": "error", "message": "ANTHROPIC_API_KEY not set in .env"}
    with _lock:
        if _status["running"]:
            return {"status": "running"}
    t = threading.Thread(target=_run_refresh, args=(db_path,), daemon=True)
    t.start()
    return {"status": "started"}


def get_refresh_status() -> dict:
    with _lock:
        return dict(_status)


# ── query helpers ─────────────────────────────────────────────────────────────
def query_signals(db_path: str, state: str = "", strength: str = "") -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    sql  = """
        SELECT
            s.signal_strength,
            s.ai_reasoning,
            s.trigger_datapoint,
            s.updated_at,
            c.company,
            c.ranking,
            c.state,
            c.lead_score,
            c.tier,
            c.email,
            c.official_email,
            c.official_phone,
            c.whatsapp,
            c.website,
            c.linkedin,
            c.instagram,
            c.growth_story,
            c.news_highlights
        FROM signals s
        JOIN companies c ON s.company_name = c.company
        WHERE 1=1
    """
    args: list = []

    if state:
        sql += " AND c.state = ?"
        args.append(state)
    if strength:
        sql += " AND s.signal_strength = ?"
        args.append(strength)

    order = "CASE s.signal_strength WHEN 'Hot' THEN 1 WHEN 'Warm' THEN 2 WHEN 'Watch' THEN 3 ELSE 4 END"
    sql += f" ORDER BY {order}, CAST(c.lead_score AS INTEGER) DESC"

    rows = conn.execute(sql, args).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_states(db_path: str) -> list[str]:
    conn  = sqlite3.connect(db_path)
    rows  = conn.execute(
        "SELECT DISTINCT state FROM companies WHERE state IS NOT NULL AND state != 'N/A' ORDER BY state"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]
