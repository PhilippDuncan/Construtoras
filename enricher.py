import time
from abc import ABC, abstractmethod
from datetime import datetime

import requests
import pandas as pd

NULL = ("N/A", "nan", "", "None")

# Every enricher must return a dict with exactly these keys.
STANDARD_FIELDS = [
    "CNPJ", "Official_Email", "Official_Phone", "Founded", "Age",
    "Capital", "Legal_Status", "Decision_Makers", "B3_Ticker",
]


class BaseEnricher(ABC):

    def empty(self) -> dict:
        return {k: "N/A" for k in STANDARD_FIELDS}

    @abstractmethod
    def enrich(self, identifier: str) -> dict:
        """Enrich one company. Must return a dict with STANDARD_FIELDS keys."""

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError("Concrete enrichers must override run().")


class ReceitaWSEnricher(BaseEnricher):
    """Enriches Brazilian companies via the ReceitaWS API.

    Requires CNPJ_MAP in config: {"COMPANY NAME": "00.000.000/0001-00"}
    API docs : https://receitaws.com.br/
    Free tier: 3 requests/minute → 20s rate limit between calls.
    B3 tickers are not available via this API — add them manually to CNPJ_MAP
    or set them as overrides after enrichment.
    """

    URL        = "https://receitaws.com.br/v1/cnpj/{cnpj}"
    RATE_LIMIT = 20  # seconds between calls (free tier: 3 req/min)

    def __init__(self, cnpj_map: dict):
        self.cnpj_map = cnpj_map

    def _enrich_news(self, company_name: str) -> str:
        """Search DuckDuckGo News for recent Portuguese-language coverage."""
        from ddgs import DDGS
        query = f'"{company_name}" construtora incorporadora'
        try:
            with DDGS() as ddgs:
                results = list(ddgs.news(query, region="br-pt", timelimit="y", max_results=3))
            if not results:
                with DDGS() as ddgs:
                    results = list(ddgs.news(query, max_results=3))
            if not results:
                return "N/A"
            parts = []
            for r in results:
                headline = (r.get("title")  or "").strip()
                source   = (r.get("source") or "").strip()
                date_raw = (r.get("date")   or "").strip()
                date     = date_raw[:10] if len(date_raw) >= 10 else date_raw
                if not headline:
                    continue
                meta = ", ".join(filter(None, [source, date]))
                parts.append(f"{headline} ({meta})" if meta else headline)
            return " | ".join(parts) if parts else "N/A"
        except Exception:
            return "N/A"

    def enrich(self, cnpj: str) -> dict:
        clean = cnpj.replace(".", "").replace("/", "").replace("-", "")
        try:
            resp = requests.get(self.URL.format(cnpj=clean), timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"\n      [ERR] {e}", end="")
            return self.empty()
        finally:
            time.sleep(self.RATE_LIMIT)

        if data.get("status") == "ERROR":
            return self.empty()

        # Founding year from "DD/MM/YYYY" format
        founded_raw = data.get("abertura", "")
        founded = "N/A"
        age     = "N/A"
        if founded_raw and len(founded_raw) >= 4:
            try:
                year    = int(founded_raw[-4:])
                founded = str(year)
                age     = str(datetime.now().year - year)
            except Exception:
                pass

        # QSA = Quadro Societário e Administração (decision makers / legal reps)
        qsa = data.get("qsa", [])
        decision_makers = " | ".join(
            f"{p.get('nome', '?')} ({p.get('qual', 'N/A')})"
            for p in qsa[:3]
            if p.get("nome")
        ) if qsa else "N/A"

        # Format capital social as human-readable R$ value
        capital_raw = data.get("capital_social", "")
        try:
            val = float(capital_raw.replace(".", "").replace(",", "."))
            if val >= 1_000_000_000:
                capital = f"R${val / 1_000_000_000:.1f}B"
            elif val >= 1_000_000:
                capital = f"R${val / 1_000_000:.0f}M"
            else:
                capital = f"R${val:,.0f}"
        except Exception:
            capital = capital_raw or "N/A"

        return {
            "CNPJ":            cnpj,
            "Official_Email":  data.get("email",    "N/A") or "N/A",
            "Official_Phone":  data.get("telefone", "N/A") or "N/A",
            "Founded":         founded,
            "Age":             age,
            "Capital":         capital,
            "Legal_Status":    data.get("situacao", "N/A") or "N/A",
            "Decision_Makers": decision_makers,
            "B3_Ticker":       "Private",
        }

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """Looks up each company by name in cnpj_map, calls enrich() per CNPJ,
        then fetches recent news highlights for every company."""
        rows            = []
        news_highlights = []
        total           = len(df)
        success = failed = skipped = news_found = 0

        for i, row in df.iterrows():
            rank    = int(row.get("Ranking", i + 1))
            company = str(row.get("Company", ""))
            cnpj    = self.cnpj_map.get(company)

            print(f"  [{rank:02d}/{total}] {company:<40}", end="", flush=True)

            if cnpj:
                result = self.enrich(cnpj)
                ok     = result.get("Official_Email", "N/A") not in NULL
                print(f"{'✓' if ok else '✗'}  {result.get('Founded','N/A')}  {result.get('Capital','N/A')}")
                success += 1 if ok else 0
                failed  += 0 if ok else 1
                rows.append(result)
            else:
                print("SKIP (no CNPJ in map)")
                rows.append(self.empty())
                skipped += 1

            news = self._enrich_news(company)
            news_highlights.append(news)
            if news != "N/A":
                news_found += 1
            time.sleep(1)

        enriched                    = pd.DataFrame(rows, index=df.index)
        enriched["News_Highlights"] = news_highlights
        result_df = pd.concat(
            [df.reset_index(drop=True), enriched.reset_index(drop=True)], axis=1
        )
        print(
            f"\n  Enriched: {success}/{total}  Failed: {failed}  "
            f"Skipped: {skipped}  News: {news_found}/{total}"
        )
        return result_df
