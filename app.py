"""
===============================================================
  APP.PY — CONSTRUTORAS LEAD INTELLIGENCE
  Flask web interface for searching the companies database.
  Run with: python app.py
  Then open: http://localhost:5000
===============================================================
"""

import sqlite3
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
DB_PATH = "construtoras.db"

# ---------------------------------------------------------------
# DATABASE HELPER
# ---------------------------------------------------------------
def query_db(sql, args=(), one=False):
    """Opens a connection, runs a query, returns results."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    cursor = conn.cursor()
    cursor.execute(sql, args)
    results = cursor.fetchall()
    conn.close()
    return (results[0] if results else None) if one else results


# ---------------------------------------------------------------
# HTML TEMPLATE — the search page
# ---------------------------------------------------------------
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Construtoras Lead Intelligence</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: #f0f4ff;
            color: #1a1a2e;
            min-height: 100vh;
            padding: 2rem;
        }
        h1 {
            font-size: 1.6rem;
            font-weight: 600;
            margin-bottom: 0.25rem;
            color: #1a1a2e;
        }
        .subtitle {
            font-size: 0.9rem;
            color: #666;
            margin-bottom: 2rem;
        }
        .search-bar {
            display: flex;
            gap: 10px;
            margin-bottom: 2rem;
            max-width: 600px;
        }
        input[type="text"] {
            flex: 1;
            padding: 10px 16px;
            border: 1px solid #c5cae9;
            border-radius: 8px;
            font-size: 1rem;
            outline: none;
        }
        input[type="text"]:focus {
            border-color: #4361ee;
        }
        button {
            padding: 10px 24px;
            background: #1a1a2e;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            cursor: pointer;
        }
        button:hover { background: #4361ee; }

        .results { display: flex; flex-direction: column; gap: 16px; }

        .card {
            background: white;
            border: 0.5px solid #c5cae9;
            border-radius: 12px;
            padding: 1.25rem;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
            flex-wrap: wrap;
            gap: 8px;
        }
        .company-name {
            font-size: 1.1rem;
            font-weight: 600;
            color: #1a1a2e;
        }
        .rank { font-size: 0.85rem; color: #888; }
        .score-badge {
            font-size: 1rem;
            font-weight: 700;
            padding: 4px 14px;
            border-radius: 20px;
        }
        .hot  { background: #d8f3dc; color: #1b5e20; }
        .warm { background: #fff3cd; color: #e65100; }
        .cold { background: #ffede8; color: #b71c1c; }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 10px;
            margin-bottom: 1rem;
        }
        .field { font-size: 0.85rem; }
        .field-label {
            color: #888;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 2px;
        }
        .field-value { color: #1a1a2e; font-weight: 500; word-break: break-all; }
        .field-value.green { color: #2d6a4f; }
        .field-value.gold  { color: #b8860b; font-weight: 700; }
        .field-value.purple{ color: #6a4c93; word-break: break-word; }

        .growth-story {
            font-size: 0.85rem;
            color: #555;
            font-style: italic;
            border-left: 3px solid #c5cae9;
            padding-left: 10px;
            margin-top: 10px;
        }
        .news-highlights {
            font-size: 0.82rem;
            color: #1a3a5c;
            border-left: 3px solid #4361ee;
            padding-left: 10px;
            margin-top: 10px;
        }
        .news-highlights .news-label {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #4361ee;
            font-weight: 600;
            margin-bottom: 4px;
        }
        .news-item {
            margin-bottom: 3px;
        }
        .news-item + .news-item {
            padding-top: 3px;
            border-top: 1px dashed #e0e4f0;
        }
        .capital-note {
            font-size: 0.8rem;
            color: #888;
            margin-top: 4px;
        }
        .no-results {
            color: #888;
            font-style: italic;
            padding: 2rem 0;
        }
        .count {
            font-size: 0.85rem;
            color: #888;
            margin-bottom: 1rem;
        }
    </style>
</head>
<body>
    <h1>🏗️ Construtoras Lead Intelligence</h1>
    <p class="subtitle">INTEC 2025 · SUDESTE Region · 60 Companies</p>

    <div class="search-bar">
        <input
            type="text"
            id="query"
            placeholder="Search by company name..."
            onkeydown="if(event.key==='Enter') search()"
            autofocus
        />
        <button onclick="search()">Search</button>
    </div>

    <div id="count" class="count"></div>
    <div id="results" class="results"></div>

    <script>
        // Load all companies on page load
        window.onload = () => fetchResults("");

        function search() {
            const q = document.getElementById("query").value;
            fetchResults(q);
        }

        function fetchResults(q) {
            fetch(`/api/search?q=${encodeURIComponent(q)}`)
                .then(r => r.json())
                .then(data => renderResults(data));
        }

        function scoreClass(score) {
            if (score >= 65) return "hot";
            if (score >= 45) return "warm";
            return "cold";
        }

        function field(label, value, cls="") {
            if (!value || value === "N/A") return "";
            return `
                <div class="field">
                    <div class="field-label">${label}</div>
                    <div class="field-value ${cls}">${value}</div>
                </div>`;
        }

        function renderResults(companies) {
            const count = document.getElementById("count");
            const results = document.getElementById("results");

            if (companies.length === 0) {
                count.textContent = "";
                results.innerHTML = '<p class="no-results">No companies found.</p>';
                return;
            }

            count.textContent = `${companies.length} compan${companies.length === 1 ? 'y' : 'ies'} found`;

            results.innerHTML = companies.map(c => {
                const sc   = parseFloat(c.lead_score) || 0;
                const cls  = scoreClass(sc);
                const tier = sc >= 65 ? "🔥 Hot" : sc >= 45 ? "⚡ Warm" : "❄️ Cold";

                return `
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="company-name">${c.company}</div>
                            <div class="rank">Rank #${c.ranking} · ${c.state} · ${c.age}</div>
                        </div>
                        <span class="score-badge ${cls}">${tier} · ${sc} pts</span>
                    </div>
                    <div class="grid">
                        ${field("Official Email",   c.official_email,  "green")}
                        ${field("Official Phone",   c.official_phone,  "green")}
                        ${field("WhatsApp",         c.whatsapp,        "green")}
                        ${field("Website Email",    c.email,           "green")}
                        ${field("LinkedIn",         c.linkedin,        "green")}
                        ${field("Instagram",        c.instagram,       "green")}
                        ${field("B3 Ticker",        c.b3_ticker === "Private" ? "" : c.b3_ticker, "gold")}
                        ${field("Capital",          c.capital)}
                        ${field("m² 2025",          c.sqm_2025)}
                        ${field("Website",          c.website)}
                    </div>
                    ${c.decision_makers && c.decision_makers !== "N/A" ? `
                        <div class="field" style="margin-bottom:8px">
                            <div class="field-label">Decision Makers</div>
                            <div class="field-value purple">${c.decision_makers}</div>
                        </div>` : ""}
                    ${c.capital_note && c.capital_note !== "N/A" ? `
                        <div class="capital-note">${c.capital_note}</div>` : ""}
                    ${c.growth_story && c.growth_story !== "N/A" ? `
                        <div class="growth-story">${c.growth_story}</div>` : ""}
                    ${c.news_highlights && c.news_highlights !== "N/A" ? `
                        <div class="news-highlights">
                            <div class="news-label">📰 Recent News</div>
                            ${c.news_highlights.split(" | ").map(item =>
                                `<div class="news-item">${item}</div>`
                            ).join("")}
                        </div>` : ""}
                </div>`;
            }).join("");
        }
    </script>
</body>
</html>
"""

# ---------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------
@app.route("/")
def index():
    """Serves the search page."""
    return render_template_string(HTML)


@app.route("/api/search")
def search():
    """
    REST API endpoint — returns company data as JSON.
    Usage: /api/search?q=direcional
    Returns all companies if q is empty.
    """
    query = request.args.get("q", "").strip()

    if query:
        rows = query_db(
            "SELECT * FROM companies WHERE company LIKE ? ORDER BY CAST(lead_score AS INTEGER) DESC",
            (f"%{query.upper()}%",)
        )
    else:
        rows = query_db(
            "SELECT * FROM companies ORDER BY CAST(lead_score AS INTEGER) DESC"
        )

    companies = [dict(row) for row in rows]
    return jsonify(companies)


@app.route("/api/company/<int:ranking>")
def get_company(ranking):
    """
    Returns a single company by their INTEC ranking number.
    Usage: /api/company/1  → returns Direcional
    """
    row = query_db(
        "SELECT * FROM companies WHERE ranking = ?",
        (ranking,), one=True
    )
    if row is None:
        return jsonify({"error": "Company not found"}), 404
    return jsonify(dict(row))


# ---------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 50)
    print("  CONSTRUTORAS LEAD INTELLIGENCE — WEB APP")
    print("=" * 50)
    print("  Open your browser and go to:")
    print("  http://localhost:5000")
    print("  Press Ctrl+C to stop the server.")
    print("=" * 50)
    app.run(debug=True)
