import re
import json
from datetime import date
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 CourseDataFinder/1.0; for internal research and admin verification"
}


def normalize_spaces(text):
    return re.sub(r"\s+", " ", text or "").strip()


def fetch_html(url):
    if not url.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")

    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        raise ValueError(f"Unsupported content type: {content_type}")

    return response.text


def soup_to_text(html):
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "noscript", "svg", "canvas"]):
        tag.decompose()

    title = normalize_spaces(soup.title.get_text(" ")) if soup.title else ""

    h1 = ""
    h1_tag = soup.find("h1")
    if h1_tag:
        h1 = normalize_spaces(h1_tag.get_text(" "))

    meta_description = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        meta_description = normalize_spaces(meta_tag["content"])

    text = normalize_spaces(soup.get_text(" "))

    return {
        "soup": soup,
        "title": title,
        "h1": h1,
        "meta_description": meta_description,
        "text": text
    }


def make_snippet(text, start, end, radius=130):
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    return normalize_spaces(text[left:right])


def search_first(patterns, text, flags=re.IGNORECASE):
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return {
                "value": normalize_spaces(match.group(0)),
                "snippet": make_snippet(text, match.start(), match.end()),
                "pattern": pattern
            }
    return None


def search_all_months(text):
    found = []
    for month in MONTHS:
        if re.search(rf"\b{month}\b", text, re.IGNORECASE):
            found.append(month)
    return ", ".join(found)


def confidence(value, snippet="", required_keywords=None):
    if not value or value == "Not found":
        return "Low"

    required_keywords = required_keywords or []
    haystack = f"{value} {snippet}".lower()
    hits = sum(1 for kw in required_keywords if kw.lower() in haystack)

    if hits >= 2:
        return "High"
    if hits == 1:
        return "Medium"
    return "Medium"


def guess_currency(value):
    if not value:
        return ""
    if "£" in value or "gbp" in value.lower():
        return "GBP"
    if "€" in value or "eur" in value.lower():
        return "EUR"
    if "aud" in value.lower():
        return "AUD"
    if "cad" in value.lower():
        return "CAD"
    if "$" in value:
        return "USD/CAD/AUD"
    return ""


def guess_level(course_name, full_text):
    value = f"{course_name} {full_text[:500]}".lower()
    if any(word in value for word in ["msc", "ma ", "mba", "master", "postgraduate", "pgdip"]):
        return "Masters"
    if any(word in value for word in ["bsc", "ba ", "beng", "bachelor", "undergraduate"]):
        return "Bachelors"
    if "phd" in value or "doctor" in value:
        return "PhD"
    return ""


def guess_university_name(url, title, soup):
    candidates = []

    og_site = soup.find("meta", property="og:site_name")
    if og_site and og_site.get("content"):
        candidates.append(normalize_spaces(og_site["content"]))

    for sep in ["|", "-", "–", "—", ":"]:
        if sep in title:
            parts = [normalize_spaces(p) for p in title.split(sep) if normalize_spaces(p)]
            if len(parts) >= 2:
                candidates.append(parts[-1])

    domain = urlparse(url).netloc.replace("www.", "")
    candidates.append(domain)

    for candidate in candidates:
        if candidate and len(candidate) <= 100:
            return candidate

    return domain


def extract_course_name(parsed):
    h1 = parsed["h1"]
    title = parsed["title"]

    if h1:
        return h1

    if title:
        for sep in ["|", "–", "—", "-"]:
            if sep in title:
                return normalize_spaces(title.split(sep)[0])
        return title

    return "Not found"


def extract_data_from_text(url, parsed):
    text = parsed["text"]
    soup = parsed["soup"]

    snippets = {}
    conf = {}

    course_name = extract_course_name(parsed)
    university_name = guess_university_name(url, parsed["title"], soup)

    tuition = search_first([
        r"(international\s+(tuition\s+)?fees?|overseas\s+(tuition\s+)?fees?|tuition\s+fees?|course\s+fees?).{0,180}(£|GBP|€|EUR|AUD|CAD|\$)\s?[0-9]{1,3}(?:,[0-9]{3})+(?:\.\d{2})?",
        r"(£|GBP|€|EUR|AUD|CAD|\$)\s?[0-9]{1,3}(?:,[0-9]{3})+(?:\.\d{2})?.{0,100}(international|overseas|tuition|fee)",
        r"(£|GBP|€|EUR|AUD|CAD|\$)\s?[0-9]{4,6}(?:\.\d{2})?"
    ], text)

    ielts = search_first([
        r"IELTS.{0,160}?(overall|score|minimum|required).{0,80}?([0-9]\.[0-9]|[0-9])(?:.{0,120}?(no\s+(component|band|element)\s+(below|less than)\s+([0-9]\.[0-9]|[0-9])))?",
        r"IELTS.{0,120}?([0-9]\.[0-9]|[0-9]).{0,120}?(no\s+(component|band|element)\s+(below|less than)\s+([0-9]\.[0-9]|[0-9]))?",
        r"overall\s+(IELTS\s+)?score\s+of\s+([0-9]\.[0-9]|[0-9]).{0,120}?(no\s+(component|band|element)\s+(below|less than)\s+([0-9]\.[0-9]|[0-9]))?"
    ], text)

    pte = search_first([
        r"(PTE|Pearson Test of English).{0,120}?([0-9]{2,3})"
    ], text)

    toefl = search_first([
        r"(TOEFL|TOEFL iBT).{0,120}?([0-9]{2,3})"
    ], text)

    duration = search_first([
        r"(duration|length).{0,100}?(one year|two years|three years|four years|1 year|2 years|3 years|4 years|12 months|18 months|24 months|36 months)",
        r"\b(1 year|2 years|3 years|4 years|12 months|18 months|24 months|36 months|one year|two years|three years|four years)\b"
    ], text)

    application_fee = search_first([
        r"(application\s+fee).{0,120}(£|GBP|€|EUR|AUD|CAD|\$)\s?[0-9]{1,4}(?:,[0-9]{3})?",
        r"(£|GBP|€|EUR|AUD|CAD|\$)\s?[0-9]{1,4}.{0,80}(application\s+fee)"
    ], text)

    deposit = search_first([
        r"(deposit|tuition\s+deposit|CAS\s+deposit).{0,140}(£|GBP|€|EUR|AUD|CAD|\$)\s?[0-9]{1,3}(?:,[0-9]{3})+",
        r"(£|GBP|€|EUR|AUD|CAD|\$)\s?[0-9]{1,3}(?:,[0-9]{3})+.{0,80}(deposit)"
    ], text)

    scholarship = search_first([
        r"(scholarship|bursary|discount).{0,220}(£|GBP|€|EUR|AUD|CAD|\$)\s?[0-9]{1,3}(?:,[0-9]{3})+",
        r"(scholarship|bursary|discount).{0,160}"
    ], text)

    entry_req = search_first([
        r"(entry requirements?|admission requirements?|academic requirements?).{0,400}",
        r"(minimum requirements?).{0,300}"
    ], text)

    intake_months = search_all_months(text)
    intake_value = intake_months if intake_months else "Not found"

    results = {
        "source_url": url,
        "university_name": university_name,
        "course_name": course_name,
        "country": "",
        "level": guess_level(course_name, text),
        "tuition_fee": tuition["value"] if tuition else "Not found",
        "currency": guess_currency(tuition["value"]) if tuition else "",
        "ielts_requirement": ielts["value"] if ielts else "Not found",
        "pte_requirement": pte["value"] if pte else "Not found",
        "toefl_requirement": toefl["value"] if toefl else "Not found",
        "duration": duration["value"] if duration else "Not found",
        "intake": intake_value,
        "application_fee": application_fee["value"] if application_fee else "Not found",
        "deposit": deposit["value"] if deposit else "Not found",
        "scholarship_info": scholarship["value"] if scholarship else "Not found",
        "entry_requirement_snippet": entry_req["value"] if entry_req else "Not found",
        "verified_status": "draft",
    }

    field_matches = {
        "tuition_fee": tuition,
        "ielts_requirement": ielts,
        "pte_requirement": pte,
        "toefl_requirement": toefl,
        "duration": duration,
        "application_fee": application_fee,
        "deposit": deposit,
        "scholarship_info": scholarship,
        "entry_requirement_snippet": entry_req,
    }

    for field, match in field_matches.items():
        if match:
            snippets[field] = match["snippet"]
        else:
            snippets[field] = ""

    snippets["intake"] = "Months detected across the page. Verify manually because months may appear in unrelated sections."
    snippets["course_name"] = f"Detected from H1/title: {course_name}"
    snippets["university_name"] = f"Detected from site/title/domain: {university_name}"

    conf["course_name"] = "High" if course_name != "Not found" else "Low"
    conf["university_name"] = "Medium"
    conf["tuition_fee"] = confidence(results["tuition_fee"], snippets["tuition_fee"], ["tuition", "fee", "international"])
    conf["ielts_requirement"] = confidence(results["ielts_requirement"], snippets["ielts_requirement"], ["ielts", "overall"])
    conf["pte_requirement"] = confidence(results["pte_requirement"], snippets["pte_requirement"], ["pte"])
    conf["toefl_requirement"] = confidence(results["toefl_requirement"], snippets["toefl_requirement"], ["toefl"])
    conf["duration"] = confidence(results["duration"], snippets["duration"], ["duration"])
    conf["intake"] = "Medium" if intake_value != "Not found" else "Low"
    conf["application_fee"] = confidence(results["application_fee"], snippets["application_fee"], ["application", "fee"])
    conf["deposit"] = confidence(results["deposit"], snippets["deposit"], ["deposit"])
    conf["scholarship_info"] = confidence(results["scholarship_info"], snippets["scholarship_info"], ["scholarship", "bursary", "discount"])
    conf["entry_requirement_snippet"] = confidence(results["entry_requirement_snippet"], snippets["entry_requirement_snippet"], ["entry", "requirements"])

    results["raw_confidence_json"] = json.dumps(conf, ensure_ascii=False)
    results["raw_snippets_json"] = json.dumps(snippets, ensure_ascii=False)
    results["confidence"] = conf
    results["snippets"] = snippets
    results["last_checked"] = str(date.today())

    return results


def extract_course_data(url):
    html = fetch_html(url)
    parsed = soup_to_text(html)
    return extract_data_from_text(url, parsed)
