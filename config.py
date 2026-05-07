"""
config.py — Brazilian Construction pipeline
To run for a new region: copy this file, update every value below.
Zero changes needed in any other file.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---- Identity ---------------------------------------------------------------
INDUSTRY = "Brazilian Construction"
MARKET   = "SUDESTE Region"

# ---- Source -----------------------------------------------------------------
INTEC_URL_2025 = "https://100maioresconstrutoras.com.br/ranking-intec-2025"
INTEC_URL_2024 = "https://100maioresconstrutoras.com.br/ranking-intec-2024"
TARGET_REGION  = "SUDESTE"

# ---- Enrichment -------------------------------------------------------------
# "receita_ws" → ReceitaWSEnricher (Brazilian companies, needs CNPJ_MAP below)
ENRICHER = "receita_ws"

# CNPJ map: "COMPANY NAME AS IN EXCEL" → "00.000.000/0001-00"
# Required only when SKIP["enrich"] = False.
# Data is already enriched — SKIP["enrich"] = True is safe.
CNPJ_MAP: dict = {}

# ---- Manual corrections -----------------------------------------------------
# Verified domains for companies with wrong or missing websites.
# Applied automatically during scraping — no separate correction step needed.
MANUAL_URL_CORRECTIONS = {
    "PATRIMAR ENGENHARIA"                    : "https://www.patrimar.com.br/",
    "CONSTRUTORA TENDA"                      : "https://www.tenda.com/",
    "BRNPAR INCORPORAÇÕES"                   : "https://brn.com.br/",
    "INC EMPREENDIMENTOS"                    : "https://www.meuinc.com.br/",
    "ECON CONSTRUTORA E INCORPORADORA"       : "https://www.econconstrutora.com.br/",
    "L. R. G. CONSTRUÇÕES E EMPREENDIMENTOS": "https://lrgconstrutora.com.br/",
    "RSF EMPREENDIMENTOS"                    : "https://www.rsf.com.br/",
    "CONSTRUTORA PLANETA"                    : "https://www.construtoraplaneta.com.br/",
    "MAIS LAR"                               : "https://maislar.com/",
    "PERPLAN INCORPORAÇÃO"                   : "https://perplan.com.br/",
    "TARRAF INCORPORADORA"                   : "https://tarraf.com.br/",
    "MVITUZZO EMPREENDIMENTOS"               : "https://mvituzzo.com.br/",
    "DOMO EMPREENDIMENTOS"                   : "https://domoempreendimentos.com.br/",
    "MPD ENGENHARIA"                         : "https://www.mpd.com.br/",
}

# Contact overrides — manually verified data not scrapeable from websites
EMAIL_OVERRIDES = {
    "CURY CONSTRUTORA": "vendas@curyconstrutoraoficial.com.br",
}
INSTAGRAM_OVERRIDES = {
    "IBEN ENGENHARIA LTDA": "https://www.instagram.com/ibenengenharia",
}

# ---- Scoring ----------------------------------------------------------------
# Weights must sum to 100.
SCORING_WEIGHTS = {
    "position":         20,
    "sqm_volume":       20,
    "yoy_rank_growth":  20,
    "sqm_growth":       10,
    "contact":          20,
    "capital_maturity": 10,
}
TIER_THRESHOLDS = {"Hot": 65, "Warm": 45}
TOP_N = 20

# ---- Skip flags -------------------------------------------------------------
# Set True once a step's output already exists and you don't want to re-run it.
# IMPORTANT: Keep scrape=True and enrich=True to protect your clean data.
SKIP = {
    "scrape": True,
    "enrich": False,
    "score":  False,
    "db":     False,
}

# ---- Output files -----------------------------------------------------------
RAW_FILE      = "construtoras_sudeste.xlsx"
ENRICHED_FILE = "construtoras_enriched.xlsx"
REPORT_FILE   = "construtoras_leads_report.xlsx"
DB_FILE       = "construtoras.db"
RAW_SHEET     = "SUDESTE Companies"

# ---- Playwright config ------------------------------------------------------
PAGE_TIMEOUT  = 30000   # ms — INTEC ranking page load
VISIT_TIMEOUT = 20000   # ms — company website visit
IG_TIMEOUT    = 15000   # ms — Instagram profile load
DELAY_BETWEEN = 2       # seconds between company visits (polite scraping)
MAX_RETRIES   = 3       # retries for ranking page + website search
CONTEXT_RESET = 10      # restart browser context every N companies
