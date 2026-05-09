import asyncio
import os
import pandas as pd
from datetime import datetime

import config
from scraper  import Scraper
from enricher import ReceitaWSEnricher
from scorer   import Scorer
from reporter import Reporter


class Pipeline:
    """Orchestrates the full lead intelligence pipeline from config.

    Instantiate once and call run(). All behaviour is driven by config.py —
    swap the config file to run a different region with zero code changes.
    """

    def __init__(self):
        self.scraper  = Scraper(config)
        self.enricher = ReceitaWSEnricher(config.CNPJ_MAP)
        self.scorer   = Scorer(config)
        self.reporter = Reporter(
            config.INDUSTRY, config.MARKET,
            config.REPORT_FILE, config.DB_FILE, config.TOP_N,
        )

    async def run(self):
        start = datetime.now()
        skip  = config.SKIP

        print(f"\n  {config.INDUSTRY} Lead Intelligence Pipeline")
        print(f"  Market : {config.MARKET}")
        print(f"  Started: {start.strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Step 1 — Scrape INTEC ranking + website contacts
        if skip.get("scrape"):
            print("  [SKIP] Step 1 — Scraping")
            raw_df = pd.read_excel(config.RAW_FILE, sheet_name=config.RAW_SHEET)
        else:
            print("  Step 1 — Scraping INTEC ranking & company websites")
            raw_df = await self.scraper.run()

        # Step 2 — CNPJ enrichment via ReceitaWS
        if skip.get("enrich"):
            print("  [SKIP] Step 2 — CNPJ Enrichment")
            src = config.ENRICHED_FILE if os.path.exists(config.ENRICHED_FILE) else config.RAW_FILE
            if src == config.RAW_FILE:
                print(f"  [WARN] {config.ENRICHED_FILE} not found — falling back to {config.RAW_FILE}")
            enriched_df = pd.read_excel(src, sheet_name=config.RAW_SHEET)
            enriched_df = enriched_df.fillna("N/A")
        else:
            print("\n  Step 2 — ReceitaWS CNPJ enrichment")
            enriched_df = self.enricher.run(raw_df)
            enriched_df.to_excel(
                config.ENRICHED_FILE, index=False, sheet_name=config.RAW_SHEET
            )

        # Step 3 — Score + Excel report
        if skip.get("score"):
            print("  [SKIP] Step 3 — Scoring")
            scored_df = pd.read_excel(config.REPORT_FILE, sheet_name="📋 All Companies")
        else:
            print("\n  Step 3 — Scoring & building report")
            scored_df = await self.scorer.run(enriched_df)
            self.reporter.build_excel(scored_df)

        # Step 4 — SQLite database
        if skip.get("db"):
            print("  [SKIP] Step 4 — Database")
        else:
            print("  Step 4 — Building database")
            self.reporter.build_database(scored_df)

        duration = (datetime.now() - start).total_seconds()
        print(f"\n  Done in {duration / 60:.1f} minutes")
        print(f"  Report  : {config.REPORT_FILE}")
        print(f"  Database: {config.DB_FILE}")
        print(f"  Web app : python app.py -> http://localhost:5000")


if __name__ == "__main__":
    asyncio.run(Pipeline().run())
