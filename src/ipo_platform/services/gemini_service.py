"""
Google Gemini AI Service for Indian IPO Platform.
Provides AI Investment Thesis (Bull Case, Bear Case, Smart Verdict)
and an interactive IPO Copilot Q&A assistant using Google's Gemini models
via direct high-performance REST API with zero-downtime algorithmic fallback.
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional
import requests

from ipo_platform.models.schema import MasterIPORecord

logger = logging.getLogger("ipo_platform.services.gemini")

DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
FALLBACK_CANDIDATE_MODELS = ["gemini-3.8-flash", "gemini-flash-latest", "gemini-3.5-flash"]


class GeminiService:
    """Enterprise AI Service wrapper for Google Gemini models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 15,
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
        self.model = model or os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip()
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        """Checks if a valid Gemini API key is configured."""
        return bool(self.api_key and len(self.api_key) > 10)

    def _call_gemini_api(self, prompt: str, system_instruction: Optional[str] = None) -> Optional[str]:
        """Executes REST request to Google Generative Language API with smart model fallback."""
        if not self.is_configured:
            return None

        headers = {"Content-Type": "application/json"}
        contents = [{"parts": [{"text": prompt}]}]
        body: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.3,
                "topP": 0.85,
                "maxOutputTokens": 2048,
            },
        }

        if system_instruction:
            body["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        models_to_try = [self.model]
        for fb in FALLBACK_CANDIDATE_MODELS:
            if fb not in models_to_try:
                models_to_try.append(fb)

        for mod in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={self.api_key}"
            try:
                resp = requests.post(url, headers=headers, json=body, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            if self.model != mod:
                                self.model = mod
                            return parts[0].get("text", "").strip()
                elif resp.status_code == 404:
                    logger.info("Model '%s' returned 404, attempting fallback model...", mod)
                    continue
                else:
                    logger.warning(
                        "Gemini API returned status %s for model '%s': %s",
                        resp.status_code,
                        mod,
                        resp.text[:200],
                    )
            except Exception as exc:
                logger.error("Gemini API call failed for model '%s': %s", mod, exc)

        return None

    def _build_ipo_context_prompt(self, record: MasterIPORecord) -> str:
        """Constructs rich contextual factual payload from MasterIPORecord."""
        comp_name = record.ipo_entity.company_name if record.ipo_entity else "Target IPO"
        sector = getattr(record.ipo_entity, "sector", "General") if record.ipo_entity else "General"
        segment = getattr(record.ipo_entity, "segment", "Mainboard") if record.ipo_entity else "Mainboard"

        issue_size_cr = "Not disclosed"
        price_band = "TBA"
        lot_size = "N/A"
        if record.issue_structure:
            if getattr(record.issue_structure, "issue_size", None):
                sz = getattr(record.issue_structure.issue_size, "value", None) or record.issue_structure.issue_size
                issue_size_cr = f"₹{sz} Cr"
            low = getattr(record.issue_structure.price_band_low, "value", None)
            high = getattr(record.issue_structure.price_band_high, "value", None)
            if low and high:
                price_band = f"₹{low} - ₹{high}"
            elif high:
                price_band = f"₹{high}"
            if getattr(record.issue_structure, "lot_size", None):
                lot_size = f"{record.issue_structure.lot_size} shares"

        gmp_str = "GMP Not Available"
        gmp_pct = 0.0
        if record.gmp_data and getattr(record.gmp_data, "gmp_value", None) is not None:
            gmp_val = record.gmp_data.gmp_value
            gmp_pct = getattr(record.gmp_data, "gmp_percentage", 0.0) or 0.0
            gmp_str = f"₹{gmp_val} (+{gmp_pct:.1f}%)"

        subs_str = "No active bidding feed"
        if record.subscription_data:
            parts = []
            for k, v in record.subscription_data.items():
                if v and getattr(v, "subscription_multiple", None) is not None:
                    parts.append(f"{k}: {v.subscription_multiple:.2f}x")
            if parts:
                subs_str = ", ".join(parts)

        fin_lines = []
        if record.financial_data and record.financial_data.restated_financials:
            for f in record.financial_data.restated_financials[:3]:
                fin_lines.append(
                    f"FY{getattr(f, 'fiscal_year', 'N/A')}: Rev ₹{getattr(f, 'total_revenue_cr', 'N/A')} Cr, "
                    f"PAT ₹{getattr(f, 'pat_cr', 'N/A')} Cr, ROE {getattr(f, 'roe_percentage', 'N/A')}%, "
                    f"D/E {getattr(f, 'debt_equity_ratio', 'N/A')}"
                )
        fin_str = "\n".join(fin_lines) if fin_lines else "Restated financials not yet populated from RHP."

        dates_str = (
            f"Opens: {record.ipo_status.open_date if record.ipo_status else 'TBA'}, "
            f"Closes: {record.ipo_status.close_date if record.ipo_status else 'TBA'}, "
            f"Allotment: {getattr(record.ipo_status, 'allotment_date', 'TBA') if record.ipo_status else 'TBA'}, "
            f"Listing: {record.ipo_status.listing_date if record.ipo_status else 'TBA'}"
        )

        return f"""
IPO Profile:
- Company Name: {comp_name}
- Sector / Segment: {sector} ({segment})
- Price Band: {price_band} | Lot Size: {lot_size} | Issue Size: {issue_size_cr}
- Dates: {dates_str}
- Live Subscription Bidding: {subs_str}
- Grey Market Premium (GMP): {gmp_str}

Key 3-Year Financials (SEBI RHP):
{fin_str}
""".strip()

    def generate_ipo_thesis(
        self,
        record: MasterIPORecord,
        rec_result: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Generates an institutional-grade AI Investment Thesis for the IPO.
        Returns structured JSON with Bull Case, Bear Case, Listing Strategy, and Verdict.
        """
        comp_name = record.ipo_entity.company_name if record.ipo_entity else "This IPO"
        ipo_context = self._build_ipo_context_prompt(record)

        system_instruction = (
            "You are an elite Indian Capital Markets Investment Banking Analyst specializing in Mainboard & SME IPOs. "
            "Your job is to provide unbiased, objective, factual investment intelligence. "
            "Strictly return valid JSON only (no markdown code blocks, no backticks, no commentary). "
            "Evaluate fundamentals, valuation, subscription momentum, and grey market sentiment."
        )

        user_prompt = f"""
Analyze the following Indian IPO and generate an authoritative research thesis in strict JSON format:

{ipo_context}

Return EXACTLY this JSON schema:
{{
  "verdict": "STRONG APPLY | APPLY FOR LISTING GAIN | APPLY FOR LONG TERM | CAUTION / NEUTRAL | AVOID",
  "one_line_verdict": "A punchy 1-2 sentence executive bottom-line summary.",
  "confidence_percentage": 85,
  "listing_day_strategy": "Actionable guidance on whether to hold, book profits, or place trailing stop-loss.",
  "long_term_outlook": "Evaluation of business durability, moats, and 2-3 year compounding potential.",
  "bull_case": [
    "Growth driver 1 with numbers",
    "Growth driver 2",
    "Competitive moat or strength 3"
  ],
  "bear_case": [
    "Key risk or red flag 1 with numbers",
    "Valuation / debt / margin concern 2",
    "Governance or sector headwind 3"
  ],
  "retail_advice": "Clear advice specifically for retail investors with single lot bidding.",
  "hni_advice": "Advice for HNI / sNII / bNII bidding considering funding costs."
}}
"""

        raw_text = self._call_gemini_api(user_prompt, system_instruction=system_instruction)

        if raw_text:
            try:
                # Clean up any potential markdown fences
                cleaned = raw_text.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                parsed = json.loads(cleaned.strip())
                parsed["ai_provider"] = f"Google Gemini ({self.model})"
                parsed["is_fallback"] = False
                return parsed
            except Exception as e:
                logger.warning("Failed to parse Gemini JSON response: %s", e)

        # Resilient Algorithmic Fallback
        return self._generate_fallback_thesis(record, rec_result)

    def ask_ipo_copilot(
        self,
        record: MasterIPORecord,
        question: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Interactive Q&A assistant for a specific IPO.
        Answers user questions in English or Hindi/Hinglish depending on the query language.
        """
        comp_name = record.ipo_entity.company_name if record.ipo_entity else "the company"
        ipo_context = self._build_ipo_context_prompt(record)

        system_instruction = (
            "You are 'Gemini IPO Copilot', an AI financial assistant for Indian stock market IPOs. "
            "You answer questions from investors accurately using the provided factual IPO data. "
            "Be concise, actionable, and objective. "
            "If the user asks in Hindi or Hinglish, answer naturally in friendly, clear Hinglish. "
            "Always include relevant numbers (GMP %, P/E, Subscription, Revenue) where appropriate. "
            "Add a brief regulatory note: 'Disclaimer: For research only, not SEBI investment advice.'"
        )

        history_text = ""
        if chat_history:
            history_text = "\nPrior conversation:\n" + "\n".join(
                f"{m.get('role', 'user').title()}: {m.get('content', '')}" for m in chat_history[-4:]
            )

        prompt = f"""
Factual Data for {comp_name}:
{ipo_context}
{history_text}

User Question: {question}

Provide a crisp, direct, highly insightful answer:
"""

        answer = self._call_gemini_api(prompt, system_instruction=system_instruction)
        if answer:
            return answer

        # Smart fallback answer if Gemini API key is missing
        return self._generate_fallback_answer(record, question)

    def _generate_fallback_thesis(
        self,
        record: MasterIPORecord,
        rec_result: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Provides an empirical, quantitative algorithmic thesis when Gemini API is unconfigured."""
        comp_name = record.ipo_entity.company_name if record.ipo_entity else "Target IPO"
        gmp_pct = 0.0
        if record.gmp_data and getattr(record.gmp_data, "gmp_percentage", None) is not None:
            gmp_pct = float(record.gmp_data.gmp_percentage)

        sub_multiple = 0.0
        if record.subscription_data:
            totals = [v.subscription_multiple for v in record.subscription_data.values() if v and v.subscription_multiple]
            if totals:
                sub_multiple = max(totals)

        # Determine verdict based on mathematical scoring
        if gmp_pct >= 25.0 and sub_multiple >= 3.0:
            verdict = "STRONG APPLY"
            one_liner = f"{comp_name} exhibits powerful grey market traction ({gmp_pct:+.1f}%) and heavy institutional bidding ({sub_multiple:.1f}x), suggesting strong listing day gains."
            conf = 88
        elif gmp_pct >= 10.0:
            verdict = "APPLY FOR LISTING GAIN"
            one_liner = f"Moderate positive GMP premium ({gmp_pct:+.1f}%) provides a comfortable buffer for listing-day flip, subject to overall market stability."
            conf = 78
        elif gmp_pct < 0:
            verdict = "AVOID"
            one_liner = f"Negative GMP ({gmp_pct:.1f}%) and muted bidding indicate high probability of discount listing. Better to wait for post-listing price discovery."
            conf = 82
        else:
            verdict = "CAUTION / NEUTRAL"
            one_liner = f"Balanced risk-reward profile. Demand indicators are moderate; apply with limited retail capital only after reviewing day-3 QIB subscription."
            conf = 72

        bull = [
            f"Grey Market Premium of {gmp_pct:+.1f}% signals favorable initial secondary market appetite.",
            f"Aggregated subscription demand recorded at {sub_multiple:.1f}x across active categories.",
            f"Diversified issuer profile in {getattr(record.ipo_entity, 'sector', 'growth')} sector with defined expansion roadmap.",
        ]

        bear = [
            "Listing gains are highly sensitive to broader equity market volatility on listing day.",
            "Potential post-listing supply pressure once anchor lock-in expires after 30-90 days.",
            "Higher working capital intensity and sector-specific raw material cost escalations.",
        ]

        return {
            "verdict": verdict,
            "one_line_verdict": one_liner,
            "confidence_percentage": conf,
            "listing_day_strategy": "Book partial 50% profits on listing pop if opened above +15%; hold balance with a trailing stop loss at the issue price.",
            "long_term_outlook": "Evaluate quarterly PAT compounding and debt reduction over 2 quarters before committing large long-term capital.",
            "bull_case": bull,
            "bear_case": bear,
            "retail_advice": "Apply via UPI in Retail category (1 lot per PAN) for maximum allotment probability without incurring funding cost.",
            "hni_advice": "For sNII/bNII, calculate break-even cost including 5-day financing interest before placing heavy bids.",
            "ai_provider": "Algorithmic Quantitative Fallback (Set GEMINI_API_KEY for Real-time LLM)",
            "is_fallback": True,
        }

    def _generate_fallback_answer(self, record: MasterIPORecord, question: str) -> str:
        """Generates smart contextual response when LLM is offline."""
        q_lower = question.lower()
        comp_name = record.ipo_entity.company_name if record.ipo_entity else "this IPO"

        gmp_pct = getattr(record.gmp_data, "gmp_percentage", None) if record.gmp_data else None
        gmp_str = f"+{gmp_pct:.1f}%" if gmp_pct is not None else "N/A"

        if "listing" in q_lower or "gain" in q_lower or "profit" in q_lower:
            return (
                f"**Listing Gain Analysis for {comp_name}:**\n"
                f"- Current Grey Market Premium (GMP): **{gmp_str}**\n"
                f"- If GMP holds above 15-20% till closing, listing-day flip offers positive risk-reward.\n"
                f"- Recommended strategy: Place trailing stop-loss at the upper price band to protect listing gains.\n\n"
                f"*Note: Configure `GEMINI_API_KEY` in `.env` for deep interactive LLM reasoning!*"
            )
        elif "retail" in q_lower or "lot" in q_lower or "apply" in q_lower:
            return (
                f"**Retail Application Strategy for {comp_name}:**\n"
                f"- For retail investors, applying for **1 lot per family member (unique PAN)** maximizes allotment odds.\n"
                f"- Always bid strictly at the **Cut-off Price** (upper price band) to prevent bid rejection.\n\n"
                f"*Note: Configure `GEMINI_API_KEY` in `.env` for deep interactive LLM reasoning!*"
            )
        elif "risk" in q_lower or "flag" in q_lower or "avoid" in q_lower:
            return (
                f"**Key Risk Considerations for {comp_name}:**\n"
                f"1. Valuation multiples relative to listed peers in the same industry.\n"
                f"2. Dependency on top 5-10 customers for revenue concentration.\n"
                f"3. High debt-to-equity or negative free cashflow in recent fiscal years.\n\n"
                f"*Note: Configure `GEMINI_API_KEY` in `.env` for deep interactive LLM reasoning!*"
            )

        return (
            f"**{comp_name} Intelligence Summary:**\n"
            f"- Status: Currently tracked in platform catalog.\n"
            f"- Latest GMP Sentiment: **{gmp_str}**.\n"
            f"- For deep natural language answers and personalized prompts, please add your free `GEMINI_API_KEY` in `.env`!\n\n"
            f"*Disclaimer: For research and educational purposes only; not SEBI investment advice.*"
        )


_gemini_service_instance: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    """Singleton provider for GeminiService."""
    global _gemini_service_instance
    if _gemini_service_instance is None:
        _gemini_service_instance = GeminiService()
    return _gemini_service_instance
