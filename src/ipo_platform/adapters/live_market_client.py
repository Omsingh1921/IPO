"""
Live Market HTTP Client and Web Scraper for Indian Exchanges & GMP Trackers.
Provides resilient network fetchers with anti-bot headers, session cookie management,
and graceful offline fallback for NSE, BSE, and Grey Market aggregators.
"""

from datetime import date, datetime, timedelta
import json
import logging
import os
import re
import ssl
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Standard browser User-Agent for financial market feeds
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _clean_price(val: Any, default: float = 100.0) -> Tuple[float, float]:
    """Extracts (low, high) float prices from strings like 'Rs.558 to Rs.586' or numbers."""
    if val is None:
        return default, default
    if isinstance(val, (int, float)):
        return float(val), float(val)
    nums = re.findall(r"\d+(?:\.\d+)?", str(val))
    if len(nums) >= 2:
        return float(nums[0]), float(nums[1])
    elif len(nums) == 1:
        return float(nums[0]), float(nums[0])
    return default, default


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        cleaned = re.sub(r"[^\d.-]", "", str(val))
        return float(cleaned) if cleaned else default
    except (ValueError, TypeError):
        return default


def _safe_int(val: Any, default: int = 50) -> int:
    if val is None:
        return default
    try:
        cleaned = re.sub(r"[^\d-]", "", str(val))
        return int(cleaned) if cleaned else default
    except (ValueError, TypeError):
        return default




def _parse_investorgain_date_to_iso(date_str: Any, default_year: Optional[int] = None) -> Optional[str]:
    """
    Parses dates like '21-Oct', '21-Oct-2026', '21/10/2026', or '2026-10-21' into ISO 'YYYY-MM-DD'.
    Handles '--', 'N/A', '', and invalid values gracefully by returning None.
    """
    if not date_str:
        return None
    cleaned = str(date_str).strip()
    if not cleaned or cleaned in ("--", "-", "N/A", "null", "None", "0"):
        return None

    # If already ISO YYYY-MM-DD
    if len(cleaned) == 10 and cleaned[4] == "-" and cleaned[7] == "-":
        return cleaned

    year = default_year or datetime.now().year

    # Try matching '21-Oct' or '21-October' or '21-Oct-2026' or '21-Oct-26'
    m = re.match(r"^(\d{1,2})[-/ ]([A-Za-z]{3,9})(?:[-/ ](\d{2,4}))?$", cleaned)
    if m:
        day_str, mon_str, yr_str = m.groups()
        if yr_str:
            yr = int(yr_str)
            if yr < 100:
                yr += 2000
        else:
            yr = year
        try:
            d = datetime.strptime(f"{day_str}-{mon_str[:3]}-{yr}", "%d-%b-%Y").date()
            return d.isoformat()
        except ValueError:
            pass

    # Try numeric dates: '21-10-2026' or '21/10/2026'
    m_num = re.match(r"^(\d{1,2})[-/](\d{1,2})(?:[-/](\d{2,4}))?$", cleaned)
    if m_num:
        day_str, mon_str, yr_str = m_num.groups()
        yr = int(yr_str) if yr_str else year
        if yr < 100:
            yr += 2000
        try:
            d = date(yr, int(mon_str), int(day_str))
            return d.isoformat()
        except ValueError:
            pass

    return None


class LiveMarketClient:
    """
    HTTP client for querying live Indian stock market IPO feeds and GMP aggregators.
    """

    def __init__(
        self,
        timeout_seconds: float = 8.0,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self.timeout = timeout_seconds
        self.user_agent = user_agent
        self._cookie_jar: Dict[str, str] = {}
        self._ssl_context = ssl.create_default_context()
        # Allow connecting even in corporate environments with custom proxy certificates
        if os.environ.get("IPO_INSECURE_SSL", "false").lower() in ("true", "1"):
            self._ssl_context.check_hostname = False
            self._ssl_context.verify_mode = ssl.CERT_NONE

    def _get_headers(
        self,
        referer: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        if referer:
            headers["Referer"] = referer
        if self._cookie_jar:
            cookie_str = "; ".join(f"{k}={v}" for k, v in self._cookie_jar.items())
            headers["Cookie"] = cookie_str
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def _update_cookies(self, response_headers: Any) -> None:
        """Extracts Set-Cookie headers from HTTP response into internal jar."""
        if hasattr(response_headers, "get_all"):
            cookies = response_headers.get_all("Set-Cookie", [])
        else:
            cookies = response_headers.get("Set-Cookie", "")
            cookies = [cookies] if cookies else []

        for cookie in cookies:
            parts = cookie.split(";")
            if parts:
                kv = parts[0].strip()
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    self._cookie_jar[k.strip()] = v.strip()

    def _http_get(
        self,
        url: str,
        referer: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> bytes:
        """Executes an HTTP GET request with cookie tracking and timeout protection."""
        headers = self._get_headers(referer=referer, extra_headers=extra_headers)
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=self.timeout, context=self._ssl_context) as resp:
            self._update_cookies(resp.headers)
            return resp.read()

    def fetch_nse_live(
        self,
        url: str = "https://www.nseindia.com/api/ipo-current-issue",
        limit: int = 50,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        Fetches live active IPO issues from NSE India API.
        Performs an initial handshake to establish session cookies if not present.
        """
        try:
            # 1. Warm-up handshake with homepage to acquire valid session cookies
            if not self._cookie_jar:
                try:
                    self._http_get("https://www.nseindia.com", referer="https://www.google.com/")
                except Exception as err:
                    logger.debug("NSE cookie handshake note: %s", err)

            # 2. Query official active issues endpoint
            referer = "https://www.nseindia.com/market-data/all-upcoming-issues-ipo"
            raw_data = self._http_get(url, referer=referer)
            data = json.loads(raw_data.decode("utf-8"))

            items: List[Dict[str, Any]] = []
            if isinstance(data, list):
                raw_list = data
            elif isinstance(data, dict):
                raw_list = data.get("data", data.get("items", []))
            else:
                raw_list = []

            for item in raw_list[:limit]:
                symbol = item.get("symbol") or item.get("issueSymbol") or item.get("companySymbol")
                company_name = item.get("companyName") or item.get("company") or symbol
                if not symbol:
                    continue

                raw_price = item.get("minPrice") or item.get("floorPrice") or item.get("issuePrice")
                min_price, max_price = _clean_price(raw_price, default=100.0)
                if item.get("maxPrice") or item.get("capPrice"):
                    _, max_price = _clean_price(item.get("maxPrice") or item.get("capPrice"), default=min_price)

                issue_start = item.get("issueStartDate", date.today().isoformat())
                issue_end = item.get("issueEndDate", date.today().isoformat())
                raw_listing = item.get("listingDate")
                listing_date_val = raw_listing if (raw_listing and str(raw_listing).strip() != "") else None

                # Calculate subscription multiple from NSE's "noOfTime" or bids / offered
                raw_times = item.get("noOfTime") or item.get("totalSubscribed") or item.get("total")
                total_sub = None
                if raw_times is not None:
                    try:
                        total_sub = round(float(str(raw_times).strip()), 2)
                    except (ValueError, TypeError):
                        total_sub = None

                if total_sub is None:
                    shares_bid = item.get("noOfsharesBid")
                    shares_offered = item.get("noOfSharesOffered")
                    if shares_bid is not None and shares_offered is not None:
                        try:
                            b_val = float(shares_bid)
                            o_val = float(shares_offered)
                            if o_val > 0:
                                total_sub = round(b_val / o_val, 2)
                        except (ValueError, TypeError):
                            pass

                final_sub = total_sub if total_sub is not None else 1.0

                items.append({
                    "symbol": str(symbol).strip(),
                    "companyName": str(company_name).strip(),
                    "series": item.get("series", "EQ"),
                    "issueStartDate": issue_start,
                    "issueEndDate": issue_end,
                    "listingDate": listing_date_val,
                    "minPrice": min_price,
                    "maxPrice": max_price,
                    "minBidQuantity": _safe_int(item.get("minBidQuantity") or item.get("lotSize"), 50),
                    "issueSize": round((_safe_float(item.get("issueSize") or item.get("totalIssueSize"), 500.0) * float(max_price)) / 10000000.0, 2) if _safe_float(item.get("issueSize") or item.get("totalIssueSize"), 500.0) > 50000 else _safe_float(item.get("issueSize") or item.get("totalIssueSize"), 500.0),
                    "noOfTime": str(final_sub),
                    "noOfsharesBid": _safe_float(item.get("noOfsharesBid"), 0.0),
                    "noOfSharesOffered": _safe_float(item.get("noOfSharesOffered"), 0.0),
                    "qibSubscribed": _safe_float(item.get("qibSubscribed") or item.get("qib"), final_sub),
                    "niiSubscribed": _safe_float(item.get("niiSubscribed") or item.get("nii"), final_sub),
                    "retailSubscribed": _safe_float(item.get("retailSubscribed") or item.get("retail"), final_sub),
                    "empSubscribed": _safe_float(item.get("empSubscribed"), 0.0),
                    "totalSubscribed": final_sub,
                    "pe": _safe_float(item.get("pe"), 25.0),
                })
            return items

        except Exception as err:
            logger.warning("Live NSE fetch encountered network/parsing error: %s", err)
            raise

    def fetch_bse_live(
        self,
        url: str = "https://api.bseindia.com/BseIndiaAPI/api/GetPublicIssue_par_updated/w?flag=1&scrip_Name=&ir_flag=&status=&exchange=",
        limit: int = 50,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        Fetches live active offerings from BSE India Public Issue API (GetPublicIssue_par_updated).
        """
        try:
            referer = "https://www.bseindia.com/"
            extra_headers = {"Origin": "https://www.bseindia.com"}
            raw_data = self._http_get(url, referer=referer, extra_headers=extra_headers)
            data = json.loads(raw_data.decode("utf-8"))

            items: List[Dict[str, Any]] = []
            raw_list = data if isinstance(data, list) else data.get("Table", data.get("data", []))

            seen_scrips = set()
            for item in raw_list[:limit]:
                # Strict Issue Type Filter: Exclude Rights Issues (RI), Buybacks (BB), and listed OFS
                ir_flag = str(item.get("IR_flag") or item.get("IR_FLAG_FULL") or item.get("Issue_Type") or "").strip().upper()
                if ir_flag and ir_flag not in ("IPO", "INITIAL PUBLIC OFFER", "PUBLIC ISSUE"):
                    continue

                scrip_id = (
                    item.get("Scrip_cd")
                    or item.get("Scrip_Id")
                    or item.get("scripCode")
                    or item.get("Security_Id")
                )
                name = (
                    item.get("Scrip_Name")
                    or item.get("Security_Name")
                    or item.get("companyName")
                    or str(scrip_id)
                )
                if not scrip_id or not name:
                    continue

                # Dynamically derive human-readable scrip / symbol if numeric or generic
                clean_brand = re.sub(
                    r"(?i)\b(limited|ltd|ipo|pvt|private|india|technologies|solutions|services|industries|holdings|enterprises|infra|energy)\b",
                    "",
                    str(name),
                ).strip()
                tokens = re.findall(r"[A-Za-z0-9]+", clean_brand)
                token_slug = tokens[0].upper()[:12] if (tokens and len(tokens[0]) >= 3) else "OFFERING"
                canonical_scrip_clean = str(scrip_id).strip().upper() if (scrip_id and not str(scrip_id).strip().isdigit() and str(scrip_id) != "BSE_OFFERING") else token_slug
                scrip_id = canonical_scrip_clean

                canonical_scrip_clean = str(scrip_id).strip().upper()
                if canonical_scrip_clean in seen_scrips:
                    continue
                seen_scrips.add(canonical_scrip_clean)

                # Parse price band or floor/cap
                price_band = item.get("Price_Band")
                if price_band:
                    floor, cap = _clean_price(price_band, default=100.0)
                else:
                    floor = item.get("Floor_Price") or item.get("minPrice", 100.0)
                    cap = item.get("Cap_Price") or item.get("maxPrice", floor)
                    floor, cap = float(floor), float(cap)

                # Parse start and end dates
                raw_start = item.get("Start_Dt") or item.get("Start_Date", date.today().isoformat())
                raw_end = item.get("End_Dt") or item.get("End_Date", date.today().isoformat())
                bse_start = str(raw_start).split("T")[0].strip()
                bse_end = str(raw_end).split("T")[0].strip()

                raw_bse_list = item.get("Listing_Date") or item.get("Listing_Dt")
                bse_listing = raw_bse_list if (raw_bse_list and str(raw_bse_list).strip() != "") else None

                # Determine platform / segment
                platform = str(item.get("eXCHANGE_PLATFORM") or item.get("Segment") or "Mainboard")
                segment = "SME" if "sme" in platform.lower() else "Mainboard"

                # Status
                st = item.get("Status") or item.get("Issue_Status") or ""
                if str(st).upper() == "L":
                    issue_status = "Live"
                elif str(st).upper() == "F":
                    issue_status = "Forthcoming"
                elif str(st).upper() == "C":
                    issue_status = "Closed"
                else:
                    issue_status = str(st) or "Live"

                items.append({
                    "Scrip_Id": str(scrip_id).strip(),
                    "Security_Name": str(name).strip(),
                    "Segment": segment,
                    "Start_Date": bse_start,
                    "End_Date": bse_end,
                    "Listing_Date": bse_listing,
                    "Floor_Price": float(floor),
                    "Cap_Price": float(cap),
                    "Market_Lot": int(item.get("Market_Lot", 50)),
                    "Issue_Size": round((float(item.get("IssueSize") or item.get("Issue_Size", 300.0)) * float(cap)) / 10000000.0, 2) if float(item.get("IssueSize") or item.get("Issue_Size", 300.0)) > 50000 else float(item.get("IssueSize") or item.get("Issue_Size", 300.0)),
                    "PE": float(item.get("PE", 22.0)),
                    "Issue_Status": issue_status,
                })
            return items

        except Exception as err:
            logger.warning("Live BSE fetch encountered network/parsing error: %s", err)
            raise

    def fetch_investorgain_live_subscriptions(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetches live real-time subscription book updates (Total, QIB, NII, Retail)
        and live GMP directly from InvestorGain /report/ipo-subscription-live/333/.
        """
        sub_map: Dict[str, Dict[str, Any]] = {}
        try:
            url = "https://www.investorgain.com/report/ipo-subscription-live/333/"
            extra_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/json,*/*",
            }
            raw_data = self._http_get(url, extra_headers=extra_headers)
            content_str = raw_data.decode("utf-8", errors="ignore")
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content_str, "html.parser")
            table = soup.find("table")
            if not table:
                return sub_map

            def _pf(txt: str) -> Optional[float]:
                if not txt:
                    return None
                m = re.search(r"([0-9\.]+)", txt.replace(",", ""))
                return float(m.group(1)) if m else None

            for r in table.find_all("tr")[1:]:
                cells = r.find_all("td")
                if not cells or len(cells) < 3:
                    continue
                raw_name = cells[0].get_text(strip=True)
                total_sub_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                qib_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                nii_text = cells[5].get_text(strip=True) if len(cells) > 5 else ""
                ret_text = cells[6].get_text(strip=True) if len(cells) > 6 else ""
                size_text = cells[8].get_text(strip=True) if len(cells) > 8 else ""
                price_text = cells[9].get_text(strip=True) if len(cells) > 9 else ""

                gmp_m = re.search(r"GMP:[^0-9]*([0-9\.\-]+)\s*\(([0-9\.\-]+)%\)", raw_name)
                gmp_val = float(gmp_m.group(1)) if gmp_m else None
                gmp_pct = float(gmp_m.group(2)) if gmp_m else None

                clean_name = re.sub(r"(?i)(BSE\s*SME|NSE\s*SME|SME|IPO|GMP:.*|CT|C|Allotted).*", "", raw_name).strip()
                sub_clean_str = re.sub(r"\d{1,2}(?:st|nd|rd|th).*", "", total_sub_text).strip()
                sub_val = _pf(sub_clean_str)

                brand = re.sub(r"(?i)\b(limited|ltd|ipo|pvt|private|india)\b", "", clean_name).strip().lower()
                toks = [t for t in re.split(r"\W+", brand) if len(t) >= 3]
                key = toks[0] if toks else clean_name.lower()

                sub_map[key] = {
                    "company_name": clean_name,
                    "sub_total": sub_val,
                    "qib": _pf(qib_text),
                    "nii": _pf(nii_text),
                    "retail": _pf(ret_text),
                    "gmp_val": gmp_val,
                    "gmp_pct": gmp_pct,
                    "size_cr": _pf(size_text),
                    "price": _pf(price_text),
                }
        except Exception as e:
            logger.debug("Live subscription table fetch note: %s", e)
        return sub_map

    def fetch_gmp_live(
        self,
        url: str = "https://www.investorgain.com/report/ipo-gmp-live/331/",
        limit: int = 50,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        Fetches live Grey Market Premium (GMP) quotes with sanity guards.
        Scrapes real-time quotes from InvestorGain or parses standard JSON feeds.
        """
        try:
            # First fetch live subscription breakdown if available
            live_subs = self.fetch_investorgain_live_subscriptions()

            extra_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/json,*/*",
            }
            raw_data = self._http_get(url, extra_headers=extra_headers)
            content_str = raw_data.decode("utf-8", errors="ignore")

            items: List[Dict[str, Any]] = []
            today_str = date.today().isoformat()
            now_time = datetime.now().strftime("%H:%M:%S")

            # Check if content is HTML from InvestorGain / GMP portal
            if "<html" in content_str.lower() or "investorgain" in url.lower():
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(content_str, "html.parser")
                    table = soup.find("table")
                    if table:
                        # Dynamically detect column indices from table header (<th>)
                        col_idx = {
                            "name": 0,
                            "gmp": 1,
                            "sub": 3,
                            "price": 4,
                            "size": 5,
                            "lot": 6,
                            "open": 7,
                            "close": 8,
                            "allotment": 9,
                            "listing": 10,
                        }
                        header_tr = table.find("tr")
                        if header_tr and header_tr.find_all("th"):
                            for th_pos, th in enumerate(header_tr.find_all("th")):
                                th_t = th.get_text(strip=True).lower()
                                if any(k in th_t for k in ("name", "company", "issuer", "security")) and "size" not in th_t:
                                    col_idx["name"] = th_pos
                                elif "gmp" in th_t:
                                    col_idx["gmp"] = th_pos
                                elif any(k in th_t for k in ("sub", "subscription")):
                                    col_idx["sub"] = th_pos
                                elif any(k in th_t for k in ("price", "cap", "band")):
                                    col_idx["price"] = th_pos
                                elif any(k in th_t for k in ("size", "issue size", "issue_size", "cr")):
                                    col_idx["size"] = th_pos
                                elif "lot" in th_t:
                                    col_idx["lot"] = th_pos
                                elif "open" in th_t:
                                    col_idx["open"] = th_pos
                                elif "close" in th_t:
                                    col_idx["close"] = th_pos
                                elif any(k in th_t for k in ("boa", "allotment", "basis")):
                                    col_idx["allotment"] = th_pos
                                elif "listing" in th_t:
                                    col_idx["listing"] = th_pos

                        name_pos = col_idx.get("name", 0)
                        gmp_pos = col_idx.get("gmp", 1)
                        sub_pos = col_idx.get("sub", 3)
                        price_pos = col_idx.get("price", 4)
                        size_pos = col_idx.get("size", 5)
                        lot_pos = col_idx.get("lot", 6)
                        boa_pos = col_idx.get("allotment", 9)
                        list_pos = col_idx.get("listing", 10)

                        for row in table.find_all("tr"):
                            cells = row.find_all("td")
                            if not cells or len(cells) < 3:
                                continue
                            if len(cells) <= name_pos or len(cells) <= gmp_pos:
                                continue

                            a_tag = cells[name_pos].find("a")
                            raw_name = a_tag.get_text(strip=True) if a_tag else cells[name_pos].get_text(strip=True)
                            name_cell = raw_name.lower()

                            # Dynamic canonical slug generation from live company name
                            clean_brand = re.sub(
                                r"(?i)\b(limited|ltd|ipo|pvt|private|india|technologies|solutions|services|industries|holdings|enterprises|infra|energy)\b",
                                "",
                                name_cell,
                            ).strip()
                            tokens = re.findall(r"[A-Za-z0-9]+", clean_brand)
                            if not tokens or len(tokens[0]) < 2:
                                continue
                            primary_slug = tokens[0].upper()[:12]
                            matched_id = f"IPO-{primary_slug}-{date.today().year}"

                            if not matched_id:
                                continue

                            gmp_cell = cells[gmp_pos].get_text(strip=True)
                            m = re.search(r"([-\d\.]+)\s*\(([-\d\.]+)%\)", gmp_cell)
                            gmp_val = 0.0
                            if m:
                                try:
                                    gmp_val = float(m.group(1))
                                except ValueError:
                                    gmp_val = 0.0

                            price_cell = cells[price_pos].get_text(strip=True) if len(cells) > price_pos else "0"
                            p_clean = re.sub(r"[^\d\.]", "", price_cell)
                            try:
                                ref_price = float(p_clean) if p_clean else 100.0
                            except ValueError:
                                ref_price = 100.0

                            # Dynamic subscription multiple
                            sub_val = None
                            if len(cells) > sub_pos:
                                sub_cell = cells[sub_pos].get_text(strip=True)
                                sub_cleaned = re.sub(r"\d{1,2}(?:st|nd|rd|th).*", "", sub_cell).strip()
                                sub_clean = re.sub(r"[^\d\.]", "", sub_cleaned)
                                try:
                                    sub_val = float(sub_clean) if sub_clean else None
                                except ValueError:
                                    sub_val = None

                            # Dynamic issue size (Cr)
                            size_cr_val = None
                            if size_pos is not None and len(cells) > size_pos:
                                size_cell = cells[size_pos].get_text(strip=True).replace(",", "")
                                sz_match = re.search(r"([0-9\.]+)", size_cell)
                                if sz_match:
                                    try:
                                        size_cr_val = float(sz_match.group(1))
                                    except ValueError:
                                        size_cr_val = None

                            # Dynamic lot size
                            lot_val = None
                            if len(cells) > lot_pos:
                                lot_cell = cells[lot_pos].get_text(strip=True)
                                lot_clean = re.sub(r"[^\d]", "", lot_cell)
                                try:
                                    lot_val = int(lot_clean) if lot_clean else None
                                except ValueError:
                                    lot_val = None

                            # Dynamic Basis of Allotment Date (BOA DT)
                            allotment_date = None
                            if len(cells) > boa_pos:
                                boa_cell = cells[boa_pos].get_text(strip=True)
                                allotment_date = _parse_investorgain_date_to_iso(boa_cell)

                            # Dynamic Listing Date
                            listing_date = None
                            if len(cells) > list_pos:
                                list_cell = cells[list_pos].get_text(strip=True)
                                listing_date = _parse_investorgain_date_to_iso(list_cell)

                            # Check live subscription map for enriched values
                            qib_sub = None
                            nii_sub = None
                            ret_sub = None
                            for sub_k, sub_info in live_subs.items():
                                if len(sub_k) >= 3 and any(sub_k == t.lower() for t in tokens):
                                    if sub_info.get("sub_total") is not None:
                                        sub_val = sub_info["sub_total"]
                                    if sub_info.get("gmp_val") is not None:
                                        gmp_val = sub_info["gmp_val"]
                                    if sub_info.get("size_cr") is not None:
                                        size_cr_val = sub_info["size_cr"]
                                    if sub_info.get("price") is not None:
                                        ref_price = sub_info["price"]
                                    qib_sub = sub_info.get("qib")
                                    nii_sub = sub_info.get("nii")
                                    ret_sub = sub_info.get("retail")
                                    break

                            items.append({
                                "ipo_id": matched_id,
                                "company_name": raw_name,
                                "gmp_value": gmp_val,
                                "reference_price": ref_price,
                                "date": today_str,
                                "time": now_time,
                                "source": "InvestorGain Live",
                                "allotment_date": allotment_date,
                                "listing_date": listing_date,
                                "subscription": sub_val,
                                "lot_size": lot_val,
                                "issue_size": size_cr_val,
                                "qib": qib_sub,
                                "nii": nii_sub,
                                "retail": ret_sub,
                            })
                            if len(items) >= limit:
                                break
                except Exception as parse_err:
                    logger.warning("Error parsing InvestorGain HTML table: %s", parse_err)

            # Fallback to JSON parsing if standard API payload
            if not items:
                try:
                    data = json.loads(content_str)
                    raw_list = data if isinstance(data, list) else data.get("quotes", data.get("data", []))
                    for item in raw_list[:limit]:
                        ipo_id = item.get("ipo_id") or item.get("symbol")
                        if not ipo_id:
                            continue
                        gmp_val = float(item.get("gmp_value", item.get("gmp", 0.0)))
                        ref_price = float(item.get("reference_price", item.get("price", 100.0)))
                        ad_json = _parse_investorgain_date_to_iso(item.get("allotment_date") or item.get("boa_date"))
                        ld_json = _parse_investorgain_date_to_iso(item.get("listing_date"))
                        items.append({
                            "ipo_id": str(ipo_id).strip(),
                            "gmp_value": gmp_val,
                            "reference_price": ref_price,
                            "date": item.get("date", today_str),
                            "time": item.get("time", now_time),
                            "source": item.get("source", "LiveTracker"),
                            "allotment_date": ad_json,
                            "listing_date": ld_json,
                            "subscription": item.get("subscription"),
                            "lot_size": item.get("lot_size"),
                        })
                except Exception:
                    pass

            return items

        except Exception as err:
            logger.warning("Live GMP fetch encountered network/parsing error: %s", err)
            raise

    def fetch_chittorgarh_dashboard(
        self,
        url: str = "https://www.chittorgarh.com/ipo/ipo_dashboard.asp",
        limit: int = 50,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        Fetches and parses Mainboard IPO listings, dates, and report links from Chittorgarh dashboard.
        """
        try:
            extra_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.chittorgarh.com/",
            }
            raw_data = self._http_get(url, extra_headers=extra_headers)
            content_str = raw_data.decode("utf-8", errors="ignore")

            items: List[Dict[str, Any]] = []
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content_str, "html.parser")
            tables = soup.find_all("table")

            # Table 0: Mainboard Offerings & Dates
            if tables:
                for r in tables[0].find_all("tr")[1:]:
                    cells = r.find_all("td")
                    if not cells:
                        continue
                    text = cells[0].get_text(" ", strip=True)
                    a_elem = cells[0].find("a")
                    link = ("https://www.chittorgarh.com" + a_elem.get("href")) if (a_elem and a_elem.get("href")) else None
                    name = a_elem.get_text(strip=True) if a_elem else text

                    m = re.search(r"(\d{1,2}\s*-\s*\d{1,2}\s+[A-Za-z]+)", text)
                    date_range = m.group(1) if m else ""

                    is_open = bool(re.search(r"\bO\b", text))
                    is_closed = bool(re.search(r"\bP\b", text))
                    status_val = "Currently Open" if is_open else ("Closed" if is_closed else "Upcoming")

                    items.append({
                        "company_name": name,
                        "date_range": date_range,
                        "status": status_val,
                        "report_url": link,
                        "source": "Chittorgarh Mainboard Dashboard",
                    })
                    if len(items) >= limit:
                        break

            return items

        except Exception as err:
            logger.warning("Chittorgarh fetch encountered error: %s", err)
            return []


# Global singleton instance
default_live_market_client = LiveMarketClient()
