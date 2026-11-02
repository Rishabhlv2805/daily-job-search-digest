"""Fetch public postings and score them against a pasted profile.

Sources: Remotive and Arbeitnow. No LinkedIn login, no mass apply.
"""

from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

UA = {"User-Agent": "job-search-digest/1.0 (personal portfolio)"}

SKILL_TERMS = [
    "python",
    "pandas",
    "numpy",
    "scikit-learn",
    "sklearn",
    "xgboost",
    "streamlit",
    "machine learning",
    "sql",
    "jupyter",
    "matplotlib",
    "seaborn",
    "plotly",
    "git",
    "statistics",
    "regression",
    "classification",
    "random forest",
    "logistic regression",
    "feature engineering",
    "data analysis",
    "excel",
    "power bi",
    "tableau",
    "tensorflow",
    "pytorch",
    "docker",
    "fastapi",
    "flask",
    "aws",
    "spark",
    "nlp",
    "deep learning",
    "data visualization",
    "a/b testing",
    "experimentation",
]

SENIOR_WORDS = (
    "senior",
    "staff",
    "principal",
    "director",
    "head of",
    "vp ",
    "vice president",
    "lead ",
)

TITLE_HINTS = (
    "data analyst",
    "data scientist",
    "machine learning",
    "ml engineer",
    "analytics",
    "business analyst",
    "python developer",
    "data engineer",
    "research analyst",
)


@dataclass
class Profile:
    raw: str
    skills: list[str] = field(default_factory=list)
    years: int | None = None
    wants_remote: bool = True
    location_hint: str = ""
    target_titles: list[str] = field(default_factory=list)
    senior_signal: bool = False


@dataclass
class Role:
    title: str
    company: str
    location: str
    url: str
    source: str
    tags: list[str]
    summary: str
    score: int = 0
    reasons: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    next_step: str = "Skip"


def _strip(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_profile(raw: str, location: str = "", titles: str = "", remote: bool = True) -> Profile:
    text = raw.lower()
    skills = []
    for term in SKILL_TERMS:
        if term in text or term.replace("-", " ") in text:
            skills.append(term if term != "sklearn" else "scikit-learn")
    # unique preserve order
    seen = set()
    uniq = []
    for s in skills:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    years = None
    m = re.search(r"(\d+)\s*\+?\s*years?", text)
    if m:
        years = int(m.group(1))
    senior = any(w in text for w in ("senior", "lead", "staff", "principal", "manager"))
    targets = [t.strip().lower() for t in titles.split(",") if t.strip()]
    return Profile(
        raw=raw.strip(),
        skills=uniq,
        years=years,
        wants_remote=remote,
        location_hint=location.strip(),
        target_titles=targets,
        senior_signal=senior or (years is not None and years >= 5),
    )


def _get(url: str) -> dict | list:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode())


WEAK = {"git", "excel"}  # too common to carry a match on their own

CORE = [
    "python",
    "pandas",
    "numpy",
    "scikit-learn",
    "sql",
    "machine learning",
    "xgboost",
    "statistics",
    "tableau",
    "power bi",
    "pytorch",
    "tensorflow",
    "spark",
    "nlp",
    "streamlit",
    "jupyter",
    "feature engineering",
    "classification",
    "regression",
]

# (phrase, points) — first match wins, longest phrases first
TITLE_BANDS = [
    ("data scientist", 28),
    ("data analyst", 30),
    ("machine learning", 26),
    ("ml engineer", 24),
    ("analytics engineer", 24),
    ("data engineer", 16),
    ("business analyst", 14),
    ("quantitative analyst", 14),
    ("risk analyst", 12),
    ("analytics", 12),
    ("python", 8),
]


def fetch_roles() -> list[dict]:
    found: list[dict] = []
    found.extend(_jobicy())
    found.extend(_remoteok())
    found.extend(_arbeitnow())
    seen = set()
    unique = []
    for job in found:
        key = (job["title"].lower(), job["company"].lower())
        if key in seen or not job["url"]:
            continue
        seen.add(key)
        unique.append(job)
    return unique


def _jobicy() -> list[dict]:
    rows = []
    for tag in ("data", "analytics", "sql"):
        try:
            payload = _get(f"https://jobicy.com/api/v2/remote-jobs?count=50&tag={tag}")
        except Exception:
            continue
        for row in payload.get("jobs") or []:
            rows.append(
                {
                    "title": (row.get("jobTitle") or "").strip(),
                    "company": (row.get("companyName") or "").strip(),
                    "location": (row.get("jobGeo") or "Remote").strip(),
                    "url": row.get("url") or "",
                    "source": "Jobicy",
                    "tags": [str(row.get("jobLevel") or ""), str(row.get("jobType") or "")],
                    "summary": _strip(row.get("jobExcerpt") or row.get("jobDescription") or "")[:1600],
                    "level": (row.get("jobLevel") or "").lower(),
                }
            )
    return [r for r in rows if r["title"] and r["company"]]


def _remoteok() -> list[dict]:
    try:
        payload = _get("https://remoteok.com/api")
    except Exception:
        return []
    rows = payload[1:] if isinstance(payload, list) else []
    out = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("position"):
            continue
        tags = [str(t) for t in (row.get("tags") or [])][:10]
        out.append(
            {
                "title": row.get("position") or "",
                "company": row.get("company") or "",
                "location": row.get("location") or "Remote",
                "url": row.get("apply_url") or row.get("url") or f"https://remoteok.com/l/{row.get('id', '')}",
                "source": "Remote OK",
                "tags": tags,
                "summary": _strip(row.get("description") or "")[:1600],
                "level": "",
            }
        )
    return out


def _arbeitnow() -> list[dict]:
    try:
        payload = _get("https://www.arbeitnow.com/api/job-board-api")
    except Exception:
        return []
    out = []
    for row in payload.get("data") or []:
        slug = row.get("slug") or ""
        url = row.get("url") or (f"https://www.arbeitnow.com/jobs/{slug}" if slug else "")
        loc = row.get("location") or ""
        if row.get("remote") and "remote" not in loc.lower():
            loc = (loc + " · remote").strip(" ·")
        out.append(
            {
                "title": (row.get("title") or "").strip(),
                "company": (row.get("company_name") or "").strip(),
                "location": loc or "Location not listed",
                "url": url,
                "source": "Arbeitnow",
                "tags": [str(t) for t in (row.get("tags") or [])][:8],
                "summary": _strip(row.get("description") or "")[:1600],
                "level": "",
            }
        )
    return [r for r in out if r["title"] and r["company"]]


def _title_points(title: str) -> tuple[int, str]:
    for phrase, points in TITLE_BANDS:
        if phrase in title:
            return points, phrase
    return 0, ""


def _core_hits(profile: Profile, blob: str) -> list[str]:
    hits = []
    for skill in profile.skills:
        if skill in WEAK:
            continue
        if skill in CORE and skill in blob:
            hits.append(skill)
    return hits


def score_role(profile: Profile, job: dict) -> Role | None:
    title_l = job["title"].lower()
    blob = f"{title_l} {job['summary'].lower()}"
    points, band = _title_points(title_l)
    hits = _core_hits(profile, blob)
    # Drop postings that are not in the analyst / ML family and share almost no skills.
    if points < 12 and len(hits) < 2:
        return None
    if points == 0 and not any(w in title_l for w in ("data", "analy", "machine learning", " ml")):
        return None

    score = 22 + points + min(28, 7 * len(hits))
    reasons: list[str] = []
    gaps: list[str] = []

    if band:
        reasons.append(f"Title is in the {band} band.")
    if hits:
        reasons.append("Skills in the posting: " + ", ".join(hits[:4]) + ".")
    else:
        gaps.append("The posting does not name the tools listed in the profile.")
        score -= 6

    if profile.target_titles:
        if any(t in title_l for t in profile.target_titles):
            score += 8
            reasons.append("Matches a target title you wrote.")
        elif points < 16:
            gaps.append("Not one of the target titles you listed.")
            score -= 4

    level = (job.get("level") or "") + " " + title_l
    senior_post = any(w in level for w in SENIOR_WORDS) or bool(re.search(r"\b(sr|snr)\b", level))
    if senior_post and not profile.senior_signal:
        score -= 16
        gaps.append("Reads senior or director. The profile does not show that level.")
    elif any(w in title_l for w in ("junior", "associate", "intern", "entry", "medior")):
        score += 6
        reasons.append("Level looks closer to an early-career profile.")

    loc = job["location"].lower()
    remoteish = any(w in loc for w in ("remote", "worldwide", "anywhere", "europe", "global"))
    if profile.wants_remote and remoteish:
        score += 6
    elif profile.location_hint and profile.location_hint.lower() in loc:
        score += 10
        reasons.append(f"Location mentions {profile.location_hint}.")
    elif profile.location_hint and not remoteish:
        gaps.append(f"Listed location is {job['location']}.")
        score -= 3

    score = max(0, min(100, score))
    if score >= 72 and len(gaps) <= 1:
        step = "Strong enough to tailor. Apply only after you confirm."
    elif score >= 58:
        step = "Possible. Read the posting, then decide. Do not apply from this page."
    else:
        step = "Skip unless the description is closer than the title."

    bullets = (reasons[:2] + gaps[:1])[:3]
    place = job["location"]
    if remoteish and "remote" not in place.lower():
        place = place + " · remote"
    return Role(
        title=job["title"],
        company=job["company"],
        location=place,
        url=job["url"],
        source=job["source"],
        tags=job["tags"],
        summary=job["summary"][:280],
        score=score,
        reasons=bullets,
        gaps=gaps,
        next_step=step,
    )


def digest(profile: Profile, limit: int = 8) -> tuple[list[Role], int, str]:
    jobs = fetch_roles()
    ranked = []
    for job in jobs:
        role = score_role(profile, job)
        if role is not None:
            ranked.append(role)
    ranked.sort(key=lambda r: r.score, reverse=True)
    # one posting per company in the short list
    picked: list[Role] = []
    seen_co = set()
    for role in ranked:
        if role.company.lower() in seen_co:
            continue
        seen_co.add(role.company.lower())
        picked.append(role)
        if len(picked) >= limit:
            break
    note = (
        f"Scanned {len(jobs)} public postings (Jobicy, Remote OK, Arbeitnow) "
        f"and kept {len(picked)} with a title or skill overlap. "
        "These boards are mostly remote and English-language, so a specific onsite city will be thin. "
        "Nothing here is an application."
    )
    return picked, len(jobs), note
