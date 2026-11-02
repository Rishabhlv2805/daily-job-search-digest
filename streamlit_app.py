"""Daily job-search digest. Rank public postings against a pasted resume."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from src.jobs import digest, parse_profile

GITHUB = "https://github.com/Rishabhlv2805"

APP_CSS = """
@import url("https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Source+Sans+3:wght@400;600&display=swap");
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stAppViewBlockContainer"] {
  background: #F3EFE6 !important;
  color: #1A1916;
}
[data-testid="stHeader"] { background: rgba(243,239,230,0.92); }
[data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"],
footer, #MainMenu, .stDeployButton, [data-testid="stDeployButton"] { display: none !important; }
iframe[height="0"], iframe[height="0px"] { display: none !important; }
h1, h2, h3, .word, .hero {
  font-family: Fraunces, Georgia, serif;
  letter-spacing: -0.03em;
  color: #1A1916;
  font-weight: 500;
}
p, label, .stMarkdown, .stCaption, li { font-family: "Source Sans 3", Helvetica, sans-serif; }
.word { font-size: 1.55rem; margin: 0; }
.kicker { letter-spacing: 0.16em; text-transform: uppercase; font-size: 0.72rem; color: #5C574E; margin: 0; font-weight: 600; }
.hero { font-size: clamp(2.1rem, 4vw, 3.1rem); line-height: 1.08; margin: 0.3rem 0 0.6rem; }
.lede { color: #3F3B34; font-size: 1.05rem; max-width: 40rem; }
.card {
  background: #FBF8F2;
  border: 1px solid rgba(26,25,22,0.12);
  border-radius: 16px;
  padding: 1rem 1.1rem 0.85rem;
  margin-bottom: 0.75rem;
}
.score {
  font-family: Fraunces, Georgia, serif;
  font-size: 2rem;
  line-height: 1;
  margin: 0;
}
.meta { color: #5C574E; font-size: 0.92rem; margin: 0.15rem 0 0.35rem; }
.warn {
  background: #EFE6D4;
  border-radius: 12px;
  padding: 0.75rem 0.9rem;
  margin: 0.4rem 0 0.8rem;
}
a.job { color: #1F4E5F; font-weight: 600; }
.stRadio [role="radiogroup"] { background: #E7E1D4; padding: 0.2rem; border-radius: 999px; }
"""


def inject_css() -> None:
    components.html(
        f"""
        <script>
        (function () {{
          const doc = window.parent.document;
          let style = doc.getElementById("job-css");
          if (!style) {{
            style = doc.createElement("style");
            style.id = "job-css";
            doc.head.appendChild(style);
          }}
          style.textContent = {json.dumps(APP_CSS)};
        }})();
        </script>
        """,
        height=0,
    )


SAMPLE = """Rishabh Sharma
Ghaziabad / open to remote
GitHub: https://github.com/Rishabhlv2805

Projects
- House price prediction: pandas, scikit-learn, XGBoost, regression, Streamlit
- Credit-card fraud detection: imbalanced classification, random forest, logistic regression, precision/recall, ROC-AUC
- Customer churn analysis: classification, feature engineering, model comparison

Skills: Python, pandas, numpy, matplotlib, seaborn, scikit-learn, XGBoost, Jupyter, Git, SQL basics, data visualization
Education: bachelor's coursework in a technical field
Looking for: data analyst, junior data scientist, machine learning intern or associate roles
"""


def ensure_state() -> None:
    st.session_state.setdefault("resume", "")
    st.session_state.setdefault("location", "")
    st.session_state.setdefault("titles", "data analyst, data scientist, machine learning")
    st.session_state.setdefault("remote", True)
    st.session_state.setdefault("roles", None)
    st.session_state.setdefault("scanned", 0)
    st.session_state.setdefault("note", "")
    st.session_state.setdefault("tracker", [])
    st.session_state.setdefault("using_sample", False)


def run_digest() -> None:
    raw = st.session_state.resume.strip()
    if len(raw) < 40:
        st.session_state.roles = None
        st.warning("Paste a resume or profile first. A title and a skill list is enough.")
        return
    profile = parse_profile(
        raw,
        location=st.session_state.location,
        titles=st.session_state.titles,
        remote=st.session_state.remote,
    )
    with st.spinner("Reading the profile and scanning public boards…"):
        roles, scanned, note = digest(profile)
    st.session_state.roles = roles
    st.session_state.scanned = scanned
    st.session_state.note = note
    st.session_state.profile_skills = profile.skills
    st.session_state.jump = "Digest"


def save_role(role, status: str) -> None:
    tracker = st.session_state.tracker
    for row in tracker:
        if row["url"] == role.url and row["title"] == role.title:
            row["status"] = status
            return
    tracker.append(
        {
            "title": role.title,
            "company": role.company,
            "url": role.url,
            "score": role.score,
            "status": status,
        }
    )


st.set_page_config(page_title="Job digest", page_icon="⌂", layout="wide", initial_sidebar_state="collapsed")
inject_css()
ensure_state()
if st.session_state.get("jump"):
    st.session_state["nav"] = st.session_state.pop("jump")

left, mid, right = st.columns([1.3, 2.2, 1.3], vertical_alignment="center")
with left:
    st.markdown('<p class="word">Job digest</p>', unsafe_allow_html=True)
with mid:
    page = st.radio(
        "Navigate",
        ["Profile", "Digest", "Tracker"],
        horizontal=True,
        label_visibility="collapsed",
        key="nav",
    )
with right:
    st.markdown(
        f'<p class="meta" style="text-align:right">Rishabh Sharma · <a href="{GITHUB}">GitHub</a></p>',
        unsafe_allow_html=True,
    )
st.divider()

if page == "Profile":
    st.markdown('<p class="kicker">Start here</p>', unsafe_allow_html=True)
    st.markdown('<p class="hero">Paste the profile. Then I will rank roles.</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="lede">Nothing is searched until you paste a resume, GitHub blurb, or project list. '
        "I only use that text. Applications are never sent from here.</p>",
        unsafe_allow_html=True,
    )
    st.text_area(
        "Resume, profile, or project notes",
        height=260,
        key="resume",
        placeholder="Paste skills, projects, education, and the titles you want…",
    )
    c1, c2, c3 = st.columns([1.2, 1.4, 1])
    with c1:
        st.text_input("Location preference (optional)", key="location", placeholder="Berlin, remote, India…")
    with c2:
        st.text_input("Target titles, comma-separated", key="titles")
    with c3:
        st.checkbox("Include remote roles", key="remote")
    a, b = st.columns([1, 1])
    with a:
        if st.button("Build today’s digest", type="primary"):
            st.session_state.using_sample = False
            run_digest()
            st.rerun()
    with b:
        if st.button("Load a labeled sample, then rank"):
            st.session_state.resume = SAMPLE
            st.session_state.using_sample = True
            st.session_state.location = st.session_state.location or "remote"
            run_digest()
            st.rerun()
    st.caption(
        "Missing and useful later: salary range, visa or student status, deal-breakers, "
        "onsite cities you will not consider, and the exact titles you want."
    )

elif page == "Digest":
    roles = st.session_state.roles
    if not roles:
        st.markdown('<p class="kicker">No digest yet</p>', unsafe_allow_html=True)
        st.markdown('<p class="hero">Paste a profile on the Profile tab.</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="lede">The digest stays empty until there is a resume or project list to match against.</p>',
            unsafe_allow_html=True,
        )
    else:
        if st.session_state.using_sample:
            st.markdown(
                '<div class="warn"><strong>Sample profile.</strong> These matches use the labeled sample, not a private resume. Replace it on Profile before you act.</div>',
                unsafe_allow_html=True,
            )
        st.markdown('<p class="kicker">Top matches</p>', unsafe_allow_html=True)
        st.markdown('<p class="hero">A short list, not a flood.</p>', unsafe_allow_html=True)
        skills = ", ".join(st.session_state.get("profile_skills") or []) or "none detected"
        st.markdown(
            f'<p class="lede">Skills read from the text: {skills}. '
            "Nothing is applied until you confirm it yourself.</p>",
            unsafe_allow_html=True,
        )
        st.markdown(f'<div class="warn">{st.session_state.note}</div>', unsafe_allow_html=True)
        for role in roles:
            st.markdown(
                f"""
                <div class="card">
                  <p class="kicker">{role.source} · match {role.score}/100</p>
                  <p class="score">{role.score}</p>
                  <h3 style="margin:0.35rem 0 0">{role.title}</h3>
                  <p class="meta">{role.company} · {role.location}</p>
                  <p><a class="job" href="{role.url}" target="_blank" rel="noreferrer">Open posting</a></p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            for bullet in role.reasons:
                st.markdown(f"- {bullet}")
            st.caption(role.next_step)
            s1, s2, s3 = st.columns(3)
            if s1.button("Save", key=f"save-{role.url}-{role.title}"):
                save_role(role, "Saved")
            if s2.button("Mark applied (you did this)", key=f"app-{role.url}-{role.title}"):
                save_role(role, "Applied — confirmed by me")
            if s3.button("Skip", key=f"skip-{role.url}-{role.title}"):
                save_role(role, "Skipped")
        st.markdown(
            '<div class="warn">Applications require your explicit confirmation. '
            "This page does not submit anything. Prefer a tailored application over applying to every row.</div>",
            unsafe_allow_html=True,
        )

else:
    st.markdown('<p class="kicker">Application tracker</p>', unsafe_allow_html=True)
    st.markdown('<p class="hero">Only roles you chose.</p>', unsafe_allow_html=True)
    rows = st.session_state.tracker
    if not rows:
        st.markdown('<p class="lede">Nothing saved yet. Mark roles on the Digest tab. This list lives in the session and can be exported.</p>', unsafe_allow_html=True)
    else:
        st.dataframe(
            [
                {
                    "Status": r["status"],
                    "Score": r["score"],
                    "Title": r["title"],
                    "Company": r["company"],
                    "Link": r["url"],
                }
                for r in rows
            ],
            use_container_width=True,
            hide_index=True,
        )
        payload = json.dumps(rows, indent=2)
        st.download_button("Download tracker JSON", payload, file_name="application-tracker.json", mime="application/json")
    uploaded = st.file_uploader("Import an earlier tracker", type=["json"])
    if uploaded is not None:
        try:
            incoming = json.loads(uploaded.read().decode())
            if isinstance(incoming, list):
                st.session_state.tracker = incoming
                st.success(f"Loaded {len(incoming)} rows.")
        except json.JSONDecodeError:
            st.error("That file is not valid JSON.")
