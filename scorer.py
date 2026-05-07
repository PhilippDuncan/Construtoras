import asyncio
import re
from datetime import datetime

import pandas as pd
from playwright.async_api import async_playwright

NULL = ("N/A", "nan", "", "None")


class Scorer:
    """Fetches 2024 ranking + Instagram metrics, then computes lead scores.

    async because it uses Playwright to fetch supplemental web data before
    the pure numerical scoring pass.
    """

    _USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    def __init__(self, cfg):
        self.cfg = cfg

    async def run(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.fillna("N/A").copy()

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-dev-shm-usage", "--no-sandbox", "--disable-gpu"],
            )
            context = await browser.new_context(user_agent=self._USER_AGENT)
            page    = await context.new_page()

            print("  [1/3] Fetching 2024 ranking data...")
            data_2024   = await self._fetch_2024_data(page)
            df["Rank_2024"] = df["Company"].map(
                lambda n: data_2024.get(n, {}).get("Rank_2024", "N/A")
            )
            df["Sqm_2024"]  = df["Company"].map(
                lambda n: data_2024.get(n, {}).get("Sqm_2024",  "N/A")
            )
            df["Growth_Rank"]    = df.apply(self._rank_growth, axis=1)
            df["Growth_Sqm_Pct"] = df.apply(self._sqm_growth_pct, axis=1)

            print("  [2/3] Scraping Instagram metrics...")
            ig_followers, ig_posts = [], []
            total = len(df)
            for i, (_, row) in enumerate(df.iterrows(), start=1):
                ig_url = str(row.get("Instagram", "N/A"))
                if ig_url in NULL:
                    ig_followers.append("N/A")
                    ig_posts.append("N/A")
                    continue
                print(
                    f"    [{i:02d}/{total}] {str(row.get('Company',''))[:35]:<35}",
                    end=" ", flush=True,
                )
                result = await self._scrape_instagram(page, ig_url)
                ig_followers.append(result["IG_Followers"])
                ig_posts.append(result["IG_Posts"])
                print(f"Followers: {result['IG_Followers']:>8}  Posts: {result['IG_Posts']}")
                await asyncio.sleep(1.5)

            df["IG_Followers"] = ig_followers
            df["IG_Posts"]     = ig_posts

            await context.close()
            await browser.close()

        print("  [3/3] Calculating Lead Scores...")
        df["Growth_Story"] = df.apply(self._growth_story, axis=1)
        df["Capital_Note"] = df.apply(self._capital_note, axis=1)

        total       = len(df)
        max_sqm     = df["Sqm_2025"].apply(lambda x: self._parse_sqm(str(x))).max()
        max_capital = (
            df["Capital"].apply(lambda x: self._parse_capital(str(x))).max()
            if "Capital" in df.columns else 0
        )
        growth_vals = [
            int(x) for x in df["Growth_Rank"]
            if str(x) not in NULL and str(x).lstrip("-").isdigit() and int(x) > 0
        ]
        max_growth = max(growth_vals) if growth_vals else 1

        scores, breakdowns, tiers = [], [], []
        for _, row in df.iterrows():
            s, b = self._score(row, total, max_sqm, max_growth, max_capital)
            scores.append(s)
            breakdowns.append(b)
            tiers.append(self._tier(s))

        df["Lead_Score"]      = scores
        df["Tier"]            = tiers
        df["Score_Breakdown"] = breakdowns

        # Normalize so the top company always reaches 100 pts
        raw_max = max(scores) if scores else 1
        if raw_max < 100:
            scores = [round(s * 100 / raw_max) for s in scores]
            df["Lead_Score"] = scores
            df["Tier"]       = [self._tier(s) for s in scores]

        df.sort_values(["Lead_Score", "Ranking"], ascending=[False, True], inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    # ---- Playwright helpers -------------------------------------------------

    async def _fetch_2024_data(self, page) -> dict:
        data = {}
        try:
            await page.goto(
                self.cfg.INTEC_URL_2024,
                timeout=self.cfg.PAGE_TIMEOUT,
                wait_until="domcontentloaded",
            )
            await page.wait_for_selector("table", timeout=self.cfg.PAGE_TIMEOUT)
            rows = await page.locator("table tr").all()
            for row in rows:
                cells = await row.locator("td").all_inner_texts()
                if len(cells) == 3:
                    pos  = cells[0].strip().replace("º", "").replace("°", "")
                    name = cells[1].strip().upper()
                    sqm  = cells[2].strip()
                    if pos.isdigit() and name:
                        data[name] = {"Rank_2024": int(pos), "Sqm_2024": sqm}
            print(f"    {len(data)} companies found in 2024 ranking.")
        except Exception as e:
            print(f"    Warning: could not fetch 2024 data: {e}")
        return data

    async def _scrape_instagram(self, page, url: str) -> dict:
        result = {"IG_Followers": "N/A", "IG_Posts": "N/A"}
        url    = url.strip().rstrip("/")
        if not url.startswith("http"):
            url = "https://" + url
        try:
            await page.goto(url, timeout=self.cfg.IG_TIMEOUT, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            html = await page.content()

            fm = re.search(r'"userInteractionCount"\s*:\s*"?(\d[\d,\.]*)"?', html)
            if not fm:
                fm = re.search(r'([\d,\.]+)\s*[Ff]ollowers', html)
            pm = re.search(r'([\d,\.]+)\s*[Pp]osts?', html)

            if fm:
                raw = fm.group(1).replace(",", "").replace(".", "")
                try:
                    n = int(raw)
                    result["IG_Followers"] = (
                        f"{n/1_000_000:.1f}M" if n >= 1_000_000 else
                        f"{n/1_000:.1f}K"     if n >= 1_000     else str(n)
                    )
                except Exception:
                    pass
            if pm:
                raw = pm.group(1).replace(",", "").replace(".", "")
                try:
                    result["IG_Posts"] = str(int(raw))
                except Exception:
                    pass
        except Exception:
            pass
        return result

    # ---- Growth helpers used before scoring ---------------------------------

    def _rank_growth(self, row) -> int | str:
        try:
            return int(row["Rank_2024"]) - int(row["Ranking"])
        except Exception:
            return "N/A"

    def _sqm_growth_pct(self, row) -> float | str:
        try:
            s24 = self._parse_sqm(str(row["Sqm_2024"]))
            s25 = self._parse_sqm(str(row["Sqm_2025"]))
            return round((s25 - s24) / s24 * 100, 1) if s24 > 0 else "N/A"
        except Exception:
            return "N/A"

    # ---- Scoring ------------------------------------------------------------

    def _score(self, row, total, max_sqm, max_growth, max_capital) -> tuple[int, str]:
        w     = self.cfg.SCORING_WEIGHTS
        score = 0
        parts = []

        def has(field):
            return str(row.get(field, "N/A")).strip() not in NULL

        # Position in national ranking
        try:
            rank     = int(row["Ranking"])
            rank_pts = max(1, round(w["position"] * (1 - (rank - 1) / total)))
        except Exception:
            rank_pts = 0
        score += rank_pts
        parts.append(f"Position #{rank}: +{rank_pts}")

        # m² construction volume 2025
        sqm_2025 = self._parse_sqm(str(row.get("Sqm_2025", "0")))
        vol_pts  = (
            max(1, round(w["sqm_volume"] * (sqm_2025 / max_sqm)))
            if max_sqm > 0 and sqm_2025 > 0 else 0
        )
        score   += vol_pts
        sqm_fmt  = f"{sqm_2025/1_000:.0f}K m²" if sqm_2025 >= 1000 else f"{sqm_2025:.0f} m²"
        parts.append(f"Volume {sqm_fmt}: +{vol_pts}")

        # YoY ranking growth
        rank_2024  = row.get("Rank_2024", None)
        growth_pts = 0
        if rank_2024 and str(rank_2024) not in NULL:
            try:
                delta = int(rank_2024) - int(row["Ranking"])
                if delta > 0:
                    growth_pts = min(
                        w["yoy_rank_growth"],
                        round(w["yoy_rank_growth"] * (delta / max(max_growth, 1))),
                    )
                    parts.append(f"Ranking up {delta}: +{growth_pts}")
                elif delta == 0:
                    growth_pts = round(w["yoy_rank_growth"] * 0.3)
                    parts.append(f"Ranking stable: +{growth_pts}")
                else:
                    growth_pts = round(w["yoy_rank_growth"] * 0.1)
                    parts.append(f"Ranking down {abs(delta)}: +{growth_pts}")
            except Exception:
                pass
        else:
            growth_pts = round(w["yoy_rank_growth"] * 0.5)
            parts.append(f"New entrant: +{growth_pts}")
        score += growth_pts

        # m² volume growth YoY
        sqm_2024_raw   = row.get("Sqm_2024", None)
        vol_growth_pts = 0
        if sqm_2024_raw and str(sqm_2024_raw) not in NULL:
            sqm_2024 = self._parse_sqm(str(sqm_2024_raw))
            if sqm_2024 > 0 and sqm_2025 > 0:
                pct = (sqm_2025 - sqm_2024) / sqm_2024 * 100
                if pct > 0:
                    vol_growth_pts = min(
                        w["sqm_growth"],
                        round(w["sqm_growth"] * min(pct / 100, 1)),
                    )
                    parts.append(f"Volume +{pct:.0f}%: +{vol_growth_pts}")
                else:
                    vol_growth_pts = round(w["sqm_growth"] * 0.1)
                    parts.append(f"Volume {pct:.0f}%: +{vol_growth_pts}")
        else:
            vol_growth_pts = round(w["sqm_growth"] * 0.4)
            parts.append(f"New entrant: +{vol_growth_pts}")
        score += vol_growth_pts

        # Contact accessibility (official channels weighted higher)
        contact_pts = 0
        if has("Official_Email"):
            contact_pts += 5; parts.append("Official email: +5")
        elif has("Email"):
            contact_pts += 3; parts.append("Website email: +3")
        if has("WhatsApp"):
            contact_pts += 5; parts.append("WhatsApp: +5")
        if has("Official_Phone"):
            contact_pts += 3; parts.append("Official phone: +3")
        if has("LinkedIn"):
            contact_pts += 4; parts.append("LinkedIn: +4")
        if has("Instagram"):
            contact_pts += 3; parts.append("Instagram: +3")
        score += contact_pts

        # Capital & maturity (B3 listing is the strongest signal)
        b3            = str(row.get("B3_Ticker", "Private"))
        founding_year = self._founding_year(str(row.get("Founded", "")))
        capital_val   = self._parse_capital(str(row.get("Capital", "N/A")))
        maturity_pts  = 0

        if b3 != "Private":
            maturity_pts += 5
            parts.append(f"B3 listed ({b3}): +5")
            if max_capital > 0 and capital_val > 0:
                cap_pts = min(3, round(3 * (capital_val / max_capital)))
                maturity_pts += cap_pts
                if cap_pts > 0:
                    parts.append(f"Verified capital: +{cap_pts}")
        else:
            if founding_year >= 2010 and max_capital > 0 and capital_val > 0:
                cap_pts = min(3, round(3 * (capital_val / max_capital)))
                maturity_pts += cap_pts
                if cap_pts > 0:
                    parts.append(f"Capital: +{cap_pts}")
            if founding_year > 0:
                age = datetime.now().year - founding_year
                if age >= 20:
                    maturity_pts += 2; parts.append(f"Established {age}yr: +2")
                elif age >= 10:
                    maturity_pts += 1; parts.append(f"Growing {age}yr: +1")

        score += maturity_pts
        return min(score, 100), " | ".join(parts)

    def _tier(self, score: int) -> str:
        if score >= self.cfg.TIER_THRESHOLDS["Hot"]:
            return "🔥 Hot Lead"
        if score >= self.cfg.TIER_THRESHOLDS["Warm"]:
            return "⚡ Warm Lead"
        return "❄️ Cold Lead"

    # ---- Narrative generation -----------------------------------------------

    def _capital_note(self, row: pd.Series) -> str:
        b3            = str(row.get("B3_Ticker", "Private"))
        founding_year = self._founding_year(str(row.get("Founded", "")))
        capital       = str(row.get("Capital", "N/A"))
        if capital in NULL:
            return "N/A"
        if b3 != "Private":
            return "✅ Verified (B3 listed — legally updated)"
        if founding_year == 0:
            return "⚠️ Historical (founding date unknown)"
        age = datetime.now().year - founding_year
        if founding_year >= 2010:
            return f"✅ Reasonably current (founded {founding_year})"
        elif founding_year >= 2000:
            return f"⚠️ May be outdated (founded {founding_year}, {age} years ago)"
        return (
            f"❌ Historical only (founded {founding_year}, {age} years ago "
            f"— use m² volume instead)"
        )

    def _growth_story(self, row: pd.Series) -> str:
        founded  = str(row.get("Founded",  "N/A"))
        capital  = str(row.get("Capital",  "N/A"))
        sqm_2025 = self._parse_sqm(str(row.get("Sqm_2025", "0")))
        b3       = str(row.get("B3_Ticker", "Private"))
        year     = self._founding_year(founded)
        sqm_fmt  = (
            f"{sqm_2025/1_000_000:.1f}M m²/year" if sqm_2025 >= 1_000_000 else
            f"{sqm_2025/1_000:.0f}K m²/year"     if sqm_2025 >= 1_000     else
            f"{sqm_2025:.0f} m²/year"
        )
        b3_note = f" Listed on B3 ({b3})." if b3 != "Private" else ""
        if year > 0 and capital not in NULL:
            return (
                f"Founded {year} with {capital} in registered capital — "
                f"now delivering {sqm_fmt} nationally.{b3_note}"
            )
        elif year > 0:
            return f"Founded {year} — delivering {sqm_fmt} nationally.{b3_note}"
        return f"Delivering {sqm_fmt} nationally.{b3_note}"

    # ---- Parsing helpers ----------------------------------------------------

    @staticmethod
    def _parse_sqm(s: str) -> float:
        if not s or s in NULL:
            return 0.0
        try:
            return float(s.strip().replace(".", "").replace(",", "."))
        except Exception:
            return 0.0

    @staticmethod
    def _parse_capital(s: str) -> float:
        if not s or s.upper() in ("N/A", "NAN", ""):
            return 0.0
        s = s.upper().replace("R$", "").replace(" ", "").strip()
        try:
            if "B" in s: return float(s.replace("B", "")) * 1_000_000_000
            if "M" in s: return float(s.replace("M", "")) * 1_000_000
            return float(s.replace(",", ""))
        except Exception:
            return 0.0

    @staticmethod
    def _founding_year(s: str) -> int:
        try:
            return int(str(s).strip()[-4:])
        except Exception:
            return 0
