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
import signals_engine

app = Flask(__name__)
DB_PATH = "construtoras.db"

# initialise signals table on startup (no-op if already exists)
signals_engine.init_signals_table(DB_PATH)


# ---------------------------------------------------------------
# DATABASE HELPER
# ---------------------------------------------------------------
def query_db(sql, args=(), one=False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(sql, args)
    results = cursor.fetchall()
    conn.close()
    return (results[0] if results else None) if one else results


# ---------------------------------------------------------------
# SHARED CSS + NAV
# ---------------------------------------------------------------
SHARED_CSS = """
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
        margin-bottom: 1.25rem;
    }
    /* nav tabs */
    .nav-tabs {
        display: flex;
        gap: 8px;
        margin-bottom: 2rem;
    }
    .nav-tab {
        padding: 8px 20px;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: 600;
        cursor: pointer;
        text-decoration: none;
        border: 1.5px solid #c5cae9;
        color: #1a1a2e;
        background: white;
        transition: background 0.15s;
    }
    .nav-tab:hover { background: #e8ecff; }
    .nav-tab.active {
        background: #1a1a2e;
        color: white;
        border-color: #1a1a2e;
    }
    /* search bar */
    .search-bar {
        display: flex;
        gap: 10px;
        margin-bottom: 2rem;
        max-width: 600px;
    }
    input[type="text"], select {
        padding: 10px 16px;
        border: 1px solid #c5cae9;
        border-radius: 8px;
        font-size: 1rem;
        outline: none;
        background: white;
    }
    input[type="text"]:focus, select:focus { border-color: #4361ee; }
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
    button:disabled { background: #888; cursor: not-allowed; }
    /* cards */
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
    .company-name { font-size: 1.1rem; font-weight: 600; color: #1a1a2e; }
    .rank { font-size: 0.85rem; color: #888; }
    .score-badge {
        font-size: 1rem;
        font-weight: 700;
        padding: 4px 14px;
        border-radius: 20px;
    }
    .hot   { background: #d8f3dc; color: #1b5e20; }
    .warm  { background: #fff3cd; color: #e65100; }
    .watch { background: #e8ecff; color: #1a1a2e; }
    .cold  { background: #ffede8; color: #b71c1c; }
    /* field grid */
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
    .field-value.green  { color: #2d6a4f; }
    .field-value.gold   { color: #b8860b; font-weight: 700; }
    .field-value.purple { color: #6a4c93; word-break: break-word; }
    /* growth + news */
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
    .news-item { margin-bottom: 3px; }
    .news-item + .news-item {
        padding-top: 3px;
        border-top: 1px dashed #e0e4f0;
    }
    .capital-note { font-size: 0.8rem; color: #888; margin-top: 4px; }
    /* signals-specific */
    .signal-reasoning {
        font-size: 0.85rem;
        color: #1a1a2e;
        line-height: 1.5;
        margin-bottom: 8px;
    }
    .signal-trigger {
        font-size: 0.82rem;
        background: #eef0ff;
        border-left: 3px solid #4361ee;
        padding: 6px 10px;
        border-radius: 0 6px 6px 0;
        color: #1a3a5c;
        margin-bottom: 6px;
    }
    .signal-trigger strong { color: #4361ee; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; display: block; margin-bottom: 2px; }
    .signal-ts { font-size: 0.75rem; color: #aaa; margin-top: 6px; }
    /* filters row */
    .filters {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin-bottom: 2rem;
        align-items: center;
    }
    /* status bar */
    .status-bar {
        font-size: 0.82rem;
        color: #888;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .progress-text { color: #4361ee; font-weight: 600; }
    /* misc */
    .no-results { color: #888; font-style: italic; padding: 2rem 0; }
    .count { font-size: 0.85rem; color: #888; margin-bottom: 1rem; }
"""

NAV_SEARCH  = '<div class="nav-tabs"><a class="nav-tab active" href="/">🔍 Search</a><a class="nav-tab" href="/signals">⚡ Signals</a></div>'
NAV_SIGNALS = '<div class="nav-tabs"><a class="nav-tab" href="/">🔍 Search</a><a class="nav-tab active" href="/signals">⚡ Signals</a></div>'


# ---------------------------------------------------------------
# HTML TEMPLATE — search page
# ---------------------------------------------------------------
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Construtoras Lead Intelligence</title>
    <style>""" + SHARED_CSS + """</style>
</head>
<body>
    <h1>🏗️ Construtoras Lead Intelligence</h1>
    <p class="subtitle">INTEC 2025 · SUDESTE Region · 60 Companies</p>
    """ + NAV_SEARCH + """
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

        function linkField(label, value, cls="") {
            if (!value || value === "N/A") return "";
            const href = value.startsWith("http") ? value
                       : value.includes("@")      ? `mailto:${value}`
                       : "#";
            return `
                <div class="field">
                    <div class="field-label">${label}</div>
                    <div class="field-value ${cls}">
                        <a href="${href}" target="_blank" rel="noopener"
                           style="color:inherit;text-decoration:underline dotted">${value}</a>
                    </div>
                </div>`;
        }

        function renderResults(companies) {
            const count   = document.getElementById("count");
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
                        ${linkField("Official Email",  c.official_email,  "green")}
                        ${field("Official Phone",      c.official_phone,  "green")}
                        ${linkField("WhatsApp",        c.whatsapp,        "green")}
                        ${linkField("Website Email",   c.email,           "green")}
                        ${linkField("LinkedIn",        c.linkedin,        "green")}
                        ${linkField("Instagram",       c.instagram,       "green")}
                        ${field("B3 Ticker",           c.b3_ticker === "Private" ? "" : c.b3_ticker, "gold")}
                        ${field("Capital",             c.capital)}
                        ${field("m² 2025",             c.sqm_2025)}
                        ${linkField("Website",         c.website)}
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
# HTML TEMPLATE — signals page
# ---------------------------------------------------------------
SIGNALS_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Deal Signals · Construtoras</title>
    <style>""" + SHARED_CSS + """</style>
</head>
<body>
    <h1>🏗️ Construtoras Lead Intelligence</h1>
    <p class="subtitle">INTEC 2025 · SUDESTE Region · AI Deal Signals</p>
    """ + NAV_SIGNALS + """

    <div id="keyWarning" style="display:none;background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:10px 16px;margin-bottom:1.5rem;font-size:0.88rem;color:#7a4700">
        ⚠️ <strong>ANTHROPIC_API_KEY not set.</strong>
        Add <code>ANTHROPIC_API_KEY=sk-ant-...</code> to your <code>.env</code> file and restart the app, then click Refresh.
    </div>

    <div class="filters">
        <select id="filterState" onchange="loadSignals()">
            <option value="">All States</option>
        </select>
        <select id="filterStrength" onchange="loadSignals()">
            <option value="">All Signals</option>
            <option value="Hot">🔥 Hot</option>
            <option value="Warm">⚡ Warm</option>
            <option value="Watch">👀 Watch</option>
            <option value="Cold">❄️ Cold</option>
        </select>
        <button id="refreshBtn" onclick="startRefresh()">⚡ Refresh AI Signals</button>
        <span id="statusText" class="status-bar"></span>
    </div>

    <div id="count" class="count"></div>
    <div id="results" class="results"></div>

    <script>
        let pollInterval = null;

        window.onload = () => {
            loadStates();
            loadSignals();
            checkStatus();
            fetch("/api/signals/key").then(r => r.json()).then(d => {
                if (!d.set) document.getElementById("keyWarning").style.display = "block";
            });
        };

        function loadStates() {
            fetch("/api/signals/states")
                .then(r => r.json())
                .then(states => {
                    const sel = document.getElementById("filterState");
                    states.forEach(s => {
                        const opt = document.createElement("option");
                        opt.value = s; opt.textContent = s;
                        sel.appendChild(opt);
                    });
                });
        }

        function loadSignals() {
            const state    = document.getElementById("filterState").value;
            const strength = document.getElementById("filterStrength").value;
            const params   = new URLSearchParams();
            if (state)    params.set("state",    state);
            if (strength) params.set("strength", strength);
            fetch(`/api/signals?${params}`)
                .then(r => r.json())
                .then(data => renderSignals(data));
        }

        function signalClass(s) {
            if (s === "Hot")   return "hot";
            if (s === "Warm")  return "warm";
            if (s === "Watch") return "watch";
            return "cold";
        }

        function signalEmoji(s) {
            if (s === "Hot")   return "🔥";
            if (s === "Warm")  return "⚡";
            if (s === "Watch") return "👀";
            return "❄️";
        }

        function field(label, value, cls="") {
            if (!value || value === "N/A") return "";
            return `<div class="field">
                        <div class="field-label">${label}</div>
                        <div class="field-value ${cls}">${value}</div>
                    </div>`;
        }

        function linkField(label, value, cls="") {
            if (!value || value === "N/A") return "";
            const href = value.startsWith("http") ? value
                       : value.includes("@")      ? `mailto:${value}`
                       : "#";
            return `<div class="field">
                        <div class="field-label">${label}</div>
                        <div class="field-value ${cls}">
                            <a href="${href}" target="_blank" rel="noopener"
                               style="color:inherit;text-decoration:underline dotted">${value}</a>
                        </div>
                    </div>`;
        }

        function renderSignals(items) {
            const count   = document.getElementById("count");
            const results = document.getElementById("results");

            if (!items || items.length === 0) {
                count.textContent = "";
                results.innerHTML = '<p class="no-results">No signals yet — click "Refresh AI Signals" to analyse companies.</p>';
                return;
            }

            count.textContent = `${items.length} signal${items.length === 1 ? '' : 's'}`;

            results.innerHTML = items.map(c => {
                const cls   = signalClass(c.signal_strength);
                const emoji = signalEmoji(c.signal_strength);
                const score = parseFloat(c.lead_score) || 0;
                const scoreCls = score >= 65 ? "hot" : score >= 45 ? "warm" : "cold";

                return `
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="company-name">${c.company}</div>
                            <div class="rank">Rank #${c.ranking} · ${c.state}</div>
                        </div>
                        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                            <span class="score-badge ${scoreCls}">Lead ${score} pts</span>
                            <span class="score-badge ${cls}">${emoji} ${c.signal_strength}</span>
                        </div>
                    </div>

                    <div class="signal-reasoning">${c.ai_reasoning}</div>

                    <div class="signal-trigger">
                        <strong>Key Trigger</strong>
                        ${c.trigger_datapoint}
                    </div>

                    <div class="grid" style="margin-top:8px">
                        ${linkField("Official Email",  c.official_email,  "green")}
                        ${field("Official Phone",      c.official_phone,  "green")}
                        ${linkField("WhatsApp",        c.whatsapp,        "green")}
                        ${linkField("Website Email",   c.email,           "green")}
                        ${linkField("LinkedIn",        c.linkedin,        "green")}
                        ${linkField("Instagram",       c.instagram,       "green")}
                    </div>

                    ${c.news_highlights && c.news_highlights !== "N/A" ? `
                        <div class="news-highlights">
                            <div class="news-label">📰 Recent News</div>
                            ${c.news_highlights.split(" | ").map(item =>
                                `<div class="news-item">${item}</div>`
                            ).join("")}
                        </div>` : ""}

                    <div class="signal-ts">Last analysed: ${c.updated_at}</div>
                </div>`;
            }).join("");
        }

        function startRefresh() {
            fetch("/api/signals/refresh", { method: "POST" })
                .then(r => r.json())
                .then(d => {
                    if (d.status === "started" || d.status === "running") {
                        pollStatus();
                    }
                });
        }

        function checkStatus() {
            fetch("/api/signals/status")
                .then(r => r.json())
                .then(d => {
                    updateStatusBar(d);
                    if (d.running && !pollInterval) {
                        pollInterval = setInterval(pollStatus, 3000);
                    }
                });
        }

        function pollStatus() {
            fetch("/api/signals/status")
                .then(r => r.json())
                .then(d => {
                    updateStatusBar(d);
                    if (!d.running) {
                        clearInterval(pollInterval);
                        pollInterval = null;
                        loadSignals();
                    }
                });
        }

        function updateStatusBar(d) {
            const btn = document.getElementById("refreshBtn");
            const txt = document.getElementById("statusText");
            if (d.running) {
                btn.disabled = true;
                txt.innerHTML = `<span class="progress-text">Analysing… ${d.done} / ${d.total}</span>`;
            } else {
                btn.disabled = false;
                const last = d.last_run ? ` · Last run: ${d.last_run}` : "";
                const err  = d.error    ? ` · Error: ${d.error}` : "";
                txt.innerHTML = `<span>${last}${err}</span>`;
            }
        }
    </script>
</body>
</html>
"""


# ---------------------------------------------------------------
# ROUTES — search
# ---------------------------------------------------------------
@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/search")
def search():
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
    return jsonify([dict(row) for row in rows])


@app.route("/api/company/<int:ranking>")
def get_company(ranking):
    row = query_db("SELECT * FROM companies WHERE ranking = ?", (ranking,), one=True)
    if row is None:
        return jsonify({"error": "Company not found"}), 404
    return jsonify(dict(row))


# ---------------------------------------------------------------
# ROUTES — signals
# ---------------------------------------------------------------
@app.route("/signals")
def signals_page():
    return render_template_string(SIGNALS_HTML)


@app.route("/api/signals")
def api_signals():
    state    = request.args.get("state",    "").strip()
    strength = request.args.get("strength", "").strip()
    return jsonify(signals_engine.query_signals(DB_PATH, state, strength))


@app.route("/api/signals/refresh", methods=["POST"])
def api_signals_refresh():
    result = signals_engine.start_refresh(DB_PATH)
    return jsonify(result)


@app.route("/api/signals/status")
def api_signals_status():
    return jsonify(signals_engine.get_refresh_status())


@app.route("/api/signals/states")
def api_signals_states():
    return jsonify(signals_engine.get_states(DB_PATH))


@app.route("/api/signals/key")
def api_signals_key():
    return jsonify({"set": bool(signals_engine.ANTHROPIC_API_KEY)})


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
