#!/usr/bin/env python3
"""
!job -s "keyword" [-l "location"] — search LinkedIn public (guest) job listings and format a Teams reply.

Examples:
  !job -s "python developer"
  !job -s "c++" -l "Ho Chi Minh City"
  !job -s devops -l Singapore
"""

import html as html_lib
import re
import sys
import urllib.parse
import urllib.request

DEFAULT_LOCATION = "Vietnam"
MAX_RESULTS = 5
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
GUEST_API = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"


def is_job_command(msg_text: str) -> bool:
    lower = msg_text.lower().strip()
    if lower.startswith("💼 linkedin jobs"):
        return False
    return bool(re.search(r"(^|\s)[!/]jobs?\b", lower))


def _grab_option(text: str, flags: str) -> str:
    """Value after -s/--search or -l/--location: either quoted ("..." / “...”) or up to the next -flag / end."""
    m = re.search(
        rf"(?:^|\s)(?:{flags})\s+(?:[\"“'‘]([^\"”'’]+)[\"”'’]|(.+?))(?=\s+--?[a-z]+\s|\s*$)",
        text,
        flags=re.IGNORECASE,
    )
    if not m:
        return ""
    return (m.group(1) or m.group(2) or "").strip()[:80]


LOCATION_ALIASES = {
    "hcm": "Ho Chi Minh City, Vietnam",
    "hcmc": "Ho Chi Minh City, Vietnam",
    "tphcm": "Ho Chi Minh City, Vietnam",
    "tp hcm": "Ho Chi Minh City, Vietnam",
    "sai gon": "Ho Chi Minh City, Vietnam",
    "saigon": "Ho Chi Minh City, Vietnam",
    "ho chi minh": "Ho Chi Minh City, Vietnam",
    "ho chi minh city": "Ho Chi Minh City, Vietnam",
    "hn": "Hanoi, Vietnam",
    "ha noi": "Hanoi, Vietnam",
    "hanoi": "Hanoi, Vietnam",
    "da nang": "Da Nang, Vietnam",
    "danang": "Da Nang, Vietnam",
    "dn": "Da Nang, Vietnam",
    "vn": "Vietnam",
    "viet nam": "Vietnam",
    "remote": "Vietnam",
}


def _strip_diacritics(text: str) -> str:
    import unicodedata

    text = text.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def normalize_location(location: str) -> str:
    """LinkedIn only geocodes ASCII names reliably ('Hà Nội' → nearby provinces, 'Hanoi, Vietnam' → correct)."""
    ascii_loc = _strip_diacritics(location).strip()
    key = re.sub(r"[^a-z ]", " ", ascii_loc.lower())
    key = re.sub(r"\s+", " ", key).strip()
    return LOCATION_ALIASES.get(key) or LOCATION_ALIASES.get(key.replace(" ", "")) or ascii_loc


def parse_job_command(msg_text: str) -> tuple[str, str]:
    """Return (keyword, location). Also accepts `!job python dev` without -s."""
    text = msg_text.strip()
    keyword = _grab_option(text, r"-s|--search")
    location = normalize_location(_grab_option(text, r"-l|--location") or DEFAULT_LOCATION)
    if not keyword:
        m = re.search(r"[!/]jobs?\s+(.+)$", text, flags=re.IGNORECASE)
        if m and not m.group(1).strip().startswith("-"):
            keyword = m.group(1).strip().strip("\"“”'")[:80]
    return keyword, location


def build_search_url(keyword: str, location: str, guest_api: bool = True, recent_only: bool = True) -> str:
    params = {"keywords": keyword, "location": location, "sortBy": "DD", "start": "0"}
    if recent_only:
        params["f_TPR"] = "r2592000"  # posted in the past 30 days
    if guest_api:
        return f"{GUEST_API}?{urllib.parse.urlencode(params)}"
    params.pop("start")
    return f"https://www.linkedin.com/jobs/search/?{urllib.parse.urlencode(params)}"


def _clean(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment or "")
    return re.sub(r"\s+", " ", html_lib.unescape(text)).strip()


def parse_jobs_html(page_html: str) -> list[dict]:
    """Parse LinkedIn guest job cards (<li> ... base-search-card ...)."""
    jobs = []
    for card in re.split(r"<li[\s>]", page_html)[1:]:
        title = re.search(r'class="base-search-card__title"[^>]*>(.*?)</h3>', card, re.S)
        if not title:
            continue
        company = re.search(r'class="base-search-card__subtitle"[^>]*>(.*?)</h4>', card, re.S)
        loc = re.search(r'class="job-search-card__location"[^>]*>(.*?)</span>', card, re.S)
        posted = re.search(r'<time[^>]*class="job-search-card__listdate[^"]*"[^>]*>(.*?)</time>', card, re.S)
        salary = re.search(r'class="job-search-card__salary-info"[^>]*>(.*?)</span>', card, re.S)
        link = re.search(r'class="base-card__full-link[^"]*"[^>]*href="([^"]+)"', card, re.S) or re.search(
            r'href="(https://[a-z]+\.linkedin\.com/jobs/view/[^"]+)"', card
        )
        url = html_lib.unescape(link.group(1)).split("?")[0] if link else ""
        jobs.append(
            {
                "title": _clean(title.group(1)),
                "company": _clean(company.group(1)) if company else "",
                "location": _clean(loc.group(1)) if loc else "",
                "posted": _clean(posted.group(1)) if posted else "",
                "salary": _clean(salary.group(1)) if salary else "",
                "url": url,
            }
        )
    # Drop duplicate postings (same title + company)
    seen, unique = set(), []
    for j in jobs:
        key = (j["title"].lower(), j["company"].lower())
        if key not in seen:
            seen.add(key)
            unique.append(j)
    return unique


def _fetch_with_browser(context, url: str, attempts: int = 3) -> str:
    """LinkedIn resets non-browser TLS clients; a real Chromium tab gets through far more often."""
    page = context.new_page()
    try:
        for i in range(attempts):
            try:
                resp = page.goto(url, wait_until="domcontentloaded", timeout=8000)
                if resp and resp.status == 200:
                    page.wait_for_timeout(300)
                    return page.content()
                print(f"LinkedIn guest API returned HTTP {resp.status if resp else '?'}", file=sys.stderr)
            except Exception as e:
                print(f"LinkedIn browser attempt {i + 1} failed: {str(e).splitlines()[0]}", file=sys.stderr)
            page.wait_for_timeout(800 * (i + 1))
    finally:
        try:
            page.close()
        except Exception:
            pass
    return ""


def _fetch_with_urllib(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"LinkedIn HTTP fetch failed: {e}", file=sys.stderr)
        return ""


def search_linkedin_jobs(keyword: str, location: str = DEFAULT_LOCATION, context=None) -> list[dict]:
    jobs: list[dict] = []
    for recent_only in (True, False):  # past-30-days first; widen if a niche keyword returns nothing
        url = build_search_url(keyword, location, recent_only=recent_only)
        page_html = _fetch_with_browser(context, url) if context is not None else ""
        if not page_html or "base-search-card__title" not in page_html:
            page_html = _fetch_with_urllib(url) or page_html
        if not page_html:
            break  # network/LinkedIn blocked — don't waste time on a second query
        jobs = parse_jobs_html(page_html)[:MAX_RESULTS]
        if jobs:
            break
    return jobs


def format_jobs_message(keyword: str, location: str, jobs: list[dict]) -> str:
    search_url = build_search_url(keyword, location, guest_api=False)
    header = f"💼 LinkedIn Jobs: '{keyword}' — 📍 {location}"
    if not jobs:
        return f"{header}\n😢 Không lấy được kết quả (LinkedIn chặn hoặc không có job). Xem trực tiếp: {search_url}"
    lines = [header, ""]
    for i, j in enumerate(jobs, 1):
        lines.append(f"{i}. {j['title']}")
        meta = " | ".join(x for x in [f"🏢 {j['company']}" if j["company"] else "", f"📍 {j['location']}" if j["location"] else "", f"🕒 {j['posted']}" if j["posted"] else ""] if x)
        if meta:
            lines.append(f"   {meta}")
        if j["salary"]:
            lines.append(f"   💰 {j['salary']}")
        if j["url"]:
            lines.append(f"   🔗 {j['url']}")
    lines.append("")
    lines.append(f"🔎 Xem thêm: {search_url}")
    return "\n".join(lines)


def handle_job_command(msg_text: str, context=None) -> str:
    keyword, location = parse_job_command(msg_text)
    if not keyword:
        return '💼 Cách dùng: !job -s "python developer" [-l "Ho Chi Minh City"]'
    jobs = search_linkedin_jobs(keyword, location, context)
    return format_jobs_message(keyword, location, jobs)


if __name__ == "__main__":
    print(handle_job_command(" ".join(sys.argv[1:]) or '!job -s "python developer"'))

