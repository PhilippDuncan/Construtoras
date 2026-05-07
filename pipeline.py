<<<<<<< HEAD
import asyncio
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
            enriched_df = pd.read_excel(config.RAW_FILE, sheet_name=config.RAW_SHEET)
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
=======
"""
===============================================================
  PIPELINE — CONSTRUTORAS LEAD INTELLIGENCE
  Runs all steps in sequence with a single command:
    python pipeline.py

  Steps:
    1. Scrape INTEC ranking + company websites
    2. Cleanup failures and re-process
    3. Apply manual corrections
    4. Build enriched lead scoring report

  Individual scripts are preserved for fallback debugging.
  This pipeline imports and calls them in order.
===============================================================
  Author  : Your Name
  Version : 1.0
===============================================================
"""

import asyncio
import sys
import os
from datetime import datetime

# ---------------------------------------------------------------
# CONFIGURATION — edit these before running
# ---------------------------------------------------------------

# Set to True to skip a step if you've already run it successfully
SKIP_STEP_1 = True   # Set True if construtoras_sudeste.xlsx already exists
SKIP_STEP_2 = True   # Set True if cleanup already ran
SKIP_STEP_3 = False   # Set True if manual corrections already applied

# Manual URL corrections — add/edit as needed when wrong sites are found
# Format: "COMPANY NAME AS IN EXCEL": "https://correct-url.com/"
MANUAL_URL_CORRECTIONS = {
    "PATRIMAR ENGENHARIA"                     : "https://www.patrimar.com.br/",
    "CONSTRUTORA TENDA"                        : "https://www.tenda.com/",
    "BRNPAR INCORPORAÇÕES"                     : "https://brn.com.br/",
    "INC EMPREENDIMENTOS"                      : "https://www.meuinc.com.br/",
    "ECON CONSTRUTORA E INCORPORADORA"         : "https://www.econconstrutora.com.br/",
    "L. R. G. CONSTRUÇÕES E EMPREENDIMENTOS"  : "https://lrgconstrutora.com.br/",
    "RSF EMPREENDIMENTOS"                      : "https://www.rsf.com.br/",
    "CONSTRUTORA PLANETA"                      : "https://www.construtoraplaneta.com.br/",
    "MAIS LAR"                                 : "https://maislar.com/",
    "PERPLAN INCORPORAÇÃO"                     : "https://perplan.com.br/",
    "TARRAF INCORPORADORA"                     : "https://tarraf.com.br/",
    "MVITUZZO EMPREENDIMENTOS"                 : "https://mvituzzo.com.br/",
    "DOMO EMPREENDIMENTOS"                     : "https://domoempreendimentos.com.br/",
    "MPD ENGENHARIA"                           : "https://www.mpd.com.br/",
}

# Hardcoded email overrides — for emails known but not publicly scrapeable
EMAIL_OVERRIDES = {
    "CURY CONSTRUTORA": "vendas@curyconstrutoraoficial.com.br",
}

# Hardcoded Instagram overrides — for profiles found manually
INSTAGRAM_OVERRIDES = {
    "IBEN ENGENHARIA LTDA": "https://www.instagram.com/ibenengenharia",
}

# ---------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------
def banner(title: str):
    print("")
    print("=" * 55)
    print(f"  {title}")
    print("=" * 55)


def step_skipped(step: str):
    print(f"  ⏭️  Skipped (SKIP_{step} = True)")


def step_complete(step: str, duration: float):
    print(f"  ✅  {step} complete in {duration:.1f}s")


# ---------------------------------------------------------------
# STEP 1 — SCRAPE RANKING + CONTACTS
# ---------------------------------------------------------------
async def run_step1():
    banner("STEP 1 — SCRAPING RANKING & CONTACTS")

    if SKIP_STEP_1:
        step_skipped("STEP_1")
        return True

    if not os.path.exists("scraper_construtoras.py"):
        print("  ❌  scraper_construtoras.py not found in current directory.")
        return False

    t0 = datetime.now()
    try:
        # Import and run the scraper's main function directly
        import scraper_construtoras as s1
        s1.setup_logging()
        await s1.main_pipeline()
        step_complete("Step 1", (datetime.now() - t0).total_seconds())
        return True
    except AttributeError:
        # Fallback: run as subprocess if main_pipeline not available
        import subprocess
        result = subprocess.run(
            [sys.executable, "scraper_construtoras.py"],
            capture_output=False
        )
        step_complete("Step 1", (datetime.now() - t0).total_seconds())
        return result.returncode == 0
    except Exception as e:
        print(f"  ❌  Step 1 failed: {e}")
        return False


# ---------------------------------------------------------------
# STEP 2 — CLEANUP FAILURES
# ---------------------------------------------------------------
async def run_step2():
    banner("STEP 2 — CLEANUP FAILURES")

    if SKIP_STEP_2:
        step_skipped("STEP_2")
        return True

    if not os.path.exists("cleanup_construtoras.py"):
        print("  ❌  cleanup_construtoras.py not found.")
        return False

    t0 = datetime.now()
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "cleanup_construtoras.py"],
            capture_output=False
        )
        step_complete("Step 2", (datetime.now() - t0).total_seconds())
        return result.returncode == 0
    except Exception as e:
        print(f"  ❌  Step 2 failed: {e}")
        return False


# ---------------------------------------------------------------
# STEP 3 — MANUAL CORRECTIONS
# ---------------------------------------------------------------
async def run_step3():
    banner("STEP 3 — APPLYING MANUAL CORRECTIONS")

    if SKIP_STEP_3:
        step_skipped("STEP_3")
        return True

    import pandas as pd
    from openpyxl import load_workbook
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
    import re

    INPUT_EXCEL = "construtoras_sudeste.xlsx"

    if not os.path.exists(INPUT_EXCEL):
        print(f"  ❌  {INPUT_EXCEL} not found. Run Step 1 first.")
        return False

    t0 = datetime.now()

    df = pd.read_excel(INPUT_EXCEL, sheet_name="SUDESTE Companies")
    df = df.fillna("N/A")
    print(f"  Loaded {len(df)} companies.")
    print(f"  Corrections to apply: {len(MANUAL_URL_CORRECTIONS)}")

    def pick_best_email(emails):
        bad_ext = (".png",".jpg",".jpeg",".webp",".svg",".gif",".pdf")
        bad_kw  = ("sentry","example","domain","email@","test@","noreply","mysite.com","exemplo@")
        valid = [e for e in emails
                 if not any(e.lower().endswith(x) for x in bad_ext)
                 and not any(k in e.lower() for k in bad_kw)]
        if not valid:
            return "N/A"
        for kw in ["contato","comercial","vendas","atendimento","info","sac"]:
            for em in valid:
                if kw in em.lower():
                    return em
        return list(dict.fromkeys(valid))[0]

    async def extract_contacts(page, url):
        result = {"Website": url, "Email": "N/A", "WhatsApp": "N/A",
                  "Instagram": "N/A", "LinkedIn": "N/A"}
        try:
            await page.goto(url, timeout=20000, wait_until="domcontentloaded")
            await page.mouse.wheel(0, 2000)
            await asyncio.sleep(1)
            await page.mouse.wheel(0, 5000)
            await asyncio.sleep(1)
            result["Website"] = page.url
            html = await page.content()
            raw_emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", html)
            result["Email"] = pick_best_email(raw_emails)
            links = await page.locator("a[href]").all()
            for link in links:
                try:
                    href = await link.get_attribute("href")
                    if not href:
                        continue
                    hl = href.lower()
                    if result["WhatsApp"] == "N/A" and any(x in hl for x in ["wa.me","whatsapp.com/send","api.whatsapp"]):
                        result["WhatsApp"] = href
                    if result["Instagram"] == "N/A" and "instagram.com/" in hl and "instagram.com/p/" not in hl:
                        result["Instagram"] = href.split("?")[0].rstrip("/")
                    if result["LinkedIn"] == "N/A" and "linkedin.com/company/" in hl:
                        result["LinkedIn"] = href.split("?")[0].rstrip("/")
                except:
                    continue
            if result["Email"] == "N/A":
                for link in links:
                    try:
                        href = await link.get_attribute("href")
                        if href and href.lower().startswith("mailto:"):
                            result["Email"] = href.replace("mailto:","").split("?")[0].strip()
                            break
                    except:
                        continue
        except PlaywrightTimeout:
            result["Website"] = url + " [TIMEOUT]"
        except asyncio.CancelledError:
            result["Website"] = url + " [CANCELLED]"
            raise
        except Exception as e:
            result["Website"] = url + " [ERROR]"
        return result

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage","--no-sandbox","--disable-gpu"]
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()
        count = 0

        for idx, row in df.iterrows():
            company = str(row["Company"])
            if company not in MANUAL_URL_CORRECTIONS:
                continue

            correct_url = MANUAL_URL_CORRECTIONS[company]
            count += 1
            print(f"  [{count}/{len(MANUAL_URL_CORRECTIONS)}] {company[:40]}")

            if correct_url == "N/A":
                for field in ["Website","Email","WhatsApp","Instagram","LinkedIn"]:
                    df.at[idx, field] = "N/A"
                continue

            try:
                contacts = await extract_contacts(page, correct_url)
            except BaseException:
                page = await context.new_page()
                contacts = {"Website": correct_url + " [CRASHED]",
                            "Email": "N/A", "WhatsApp": "N/A",
                            "Instagram": "N/A", "LinkedIn": "N/A"}

            for field in ["Website","Email","WhatsApp","Instagram","LinkedIn"]:
                df.at[idx, field] = contacts[field]

            await asyncio.sleep(2)

        # Apply overrides
        for idx, row in df.iterrows():
            company = str(row["Company"])
            if company in EMAIL_OVERRIDES:
                df.at[idx, "Email"] = EMAIL_OVERRIDES[company]
                print(f"  ✉️  Email override: {company}")
            if company in INSTAGRAM_OVERRIDES:
                df.at[idx, "Instagram"] = INSTAGRAM_OVERRIDES[company]
                print(f"  📸  Instagram override: {company}")

        await context.close()
        await browser.close()

    # Save back
    df.to_excel(INPUT_EXCEL, index=False, sheet_name="SUDESTE Companies")
    _reformat_excel(df, INPUT_EXCEL)

    step_complete("Step 3", (datetime.now() - t0).total_seconds())
    return True


def _reformat_excel(df, path):
    """Apply consistent formatting to the data Excel."""
    from openpyxl import load_workbook
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = load_workbook(path)
    ws = wb.active
    NAVY = "1A1A2E"; WHITE = "FFFFFF"; LAVENDER = "EEF2FF"
    BLUE = "4361EE"; GREEN = "2D6A4F"; BORDER = "C5CAE9"

    thin = Border(
        left=Side(style="thin", color=BORDER), right=Side(style="thin", color=BORDER),
        top=Side(style="thin", color=BORDER),  bottom=Side(style="thin", color=BORDER),
    )
    headers = [cell.value for cell in ws[1]]

    for cell in ws[1]:
        cell.fill      = PatternFill("solid", fgColor=NAVY)
        cell.font      = Font(bold=True, color=WHITE, size=11, name="Calibri")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border    = thin

    for row_idx, row in enumerate(ws.iter_rows(min_row=2), start=2):
        bg = LAVENDER if row_idx % 2 == 0 else WHITE
        for col_idx, cell in enumerate(row, start=1):
            col_name = headers[col_idx - 1] if col_idx <= len(headers) else ""
            cell.fill      = PatternFill("solid", fgColor=bg)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border    = thin
            cell.font      = Font(size=10, name="Calibri")
            if col_name == "Ranking":
                cell.font = Font(bold=True, color=BLUE, size=10, name="Calibri")
            if col_name in ("Email","WhatsApp","Instagram","LinkedIn"):
                v = str(cell.value) if cell.value else ""
                if v and v not in ("N/A","nan",""):
                    cell.font = Font(color=GREEN, size=10, name="Calibri")

    for col in ws.columns:
        max_len = 0
        letter = get_column_letter(col[0].column)
        for cell in col:
            try:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            except:
                pass
        ws.column_dimensions[letter].width = min(max_len + 4, 55)

    ws.freeze_panes = "A2"
    wb.save(path)


# ---------------------------------------------------------------
# STEP 4 — ENRICHED LEAD SCORING REPORT
# ---------------------------------------------------------------
async def run_step4():
    banner("STEP 4 — BUILDING ENRICHED LEAD REPORT")

    if not os.path.exists("step3_enriched.py"):
        print("  ❌  step3_enriched.py not found.")
        return False

    t0 = datetime.now()
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "step3_enriched.py"],
            capture_output=False
        )
        step_complete("Step 4", (datetime.now() - t0).total_seconds())
        return result.returncode == 0
    except Exception as e:
        print(f"  ❌  Step 4 failed: {e}")
        return False


# ---------------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------------
async def main():
    start = datetime.now()

    print("")
    print("╔═══════════════════════════════════════════════════════╗")
    print("║   CONSTRUTORAS LEAD INTELLIGENCE PIPELINE            ║")
    print("║   Full run: Scrape → Cleanup → Correct → Score       ║")
    print("╚═══════════════════════════════════════════════════════╝")
    print(f"  Started: {start.strftime('%Y-%m-%d %H:%M:%S')}")

    steps = [
        ("Step 1 — Scrape",       run_step1),
        ("Step 2 — Cleanup",      run_step2),
        ("Step 3 — Corrections",  run_step3),
        ("Step 4 — Lead Report",  run_step4),
    ]

    results = {}
    for name, fn in steps:
        success = await fn()
        results[name] = success
        if not success:
            print(f"\n  ⚠️  {name} failed. Stopping pipeline.")
            print("  Check the individual script for details.")
            break

    # Final summary
    duration = (datetime.now() - start).total_seconds()
    banner("PIPELINE COMPLETE")
    for name, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status}  {name}")

    print(f"\n  Total time : {duration/60:.1f} minutes")
    print(f"  Output     : construtoras_leads_report.xlsx")
    print("=" * 55)


if __name__ == "__main__":
    asyncio.run(main())
>>>>>>> 2d4b1122371aeeb3fadc0075044f22fa4c8b4e68
