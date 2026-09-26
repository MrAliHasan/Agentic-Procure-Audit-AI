"""
Design system for the Streamlit UI: global CSS and small HTML components.

Every component returns an HTML string that is rendered with
st.markdown(..., unsafe_allow_html=True). Any text that may come from
users, documents, the web or the LLM goes through `esc()` first.
"""
from html import escape
from typing import Iterable, Optional

import streamlit as st


# ============== Tokens ==============

COLORS = {
    "bg": "#07080d",
    "surface": "rgba(255,255,255,0.035)",
    "border": "rgba(255,255,255,0.08)",
    "text": "#e7e9f0",
    "muted": "#8b91a7",
    "violet": "#8b5cf6",
    "cyan": "#22d3ee",
    "green": "#34d399",
    "amber": "#fbbf24",
    "red": "#f87171",
}

RECOMMENDATION_STYLE = {
    "APPROVED": ("green", "✓ Approved"),
    "REVIEW": ("amber", "◐ Needs review"),
    "REJECTED": ("red", "✕ Rejected"),
}


def esc(value) -> str:
    """HTML-escape any value for safe inline rendering."""
    return escape("" if value is None else str(value))


def score_color(score: float) -> str:
    if score >= 70:
        return COLORS["green"]
    if score >= 50:
        return COLORS["amber"]
    return COLORS["red"]


def clean(html: str) -> str:
    """Collapse an HTML fragment onto one line so Markdown never treats it as code or splits it."""
    return " ".join(line.strip() for line in html.splitlines() if line.strip())


def render(html: str, slot=None):
    """Render an HTML fragment, optionally into an st.empty() slot."""
    (slot or st).markdown(clean(html), unsafe_allow_html=True)


# ============== Global CSS ==============

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
:root {
  --bg: #07080d; --surface: rgba(255,255,255,0.035); --surface-2: rgba(255,255,255,0.06);
  --border: rgba(255,255,255,0.08); --text: #e7e9f0; --muted: #8b91a7;
  --violet: #8b5cf6; --cyan: #22d3ee; --green: #34d399; --amber: #fbbf24; --red: #f87171;
  --grad: linear-gradient(120deg, #8b5cf6 0%, #6366f1 45%, #22d3ee 100%);
}
html, body, [class*="css"], .stApp, .stMarkdown, button, input, textarea, select {
  font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
}
code, pre, .mono { font-family: 'JetBrains Mono', ui-monospace, monospace !important; }

.stApp {
  background:
    radial-gradient(900px 500px at 85% -10%, rgba(139,92,246,0.16), transparent 60%),
    radial-gradient(700px 400px at -10% 20%, rgba(34,211,238,0.10), transparent 60%),
    var(--bg);
  color: var(--text);
}
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer, [data-testid="stDecoration"] { visibility: hidden; height: 0; }
.block-container { padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1240px; }

/* Sidebar */
section[data-testid="stSidebar"] {
  background: rgba(10,11,18,0.92);
  border-right: 1px solid var(--border);
  backdrop-filter: blur(12px);
}
section[data-testid="stSidebar"] .stRadio > label { display: none; }
section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] { gap: 2px; }
section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
  padding: 9px 12px; border-radius: 10px; border: 1px solid transparent;
  transition: background .15s ease, border-color .15s ease; width: 100%;
}
section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover { background: var(--surface-2); }
section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked) {
  background: linear-gradient(120deg, rgba(139,92,246,0.18), rgba(34,211,238,0.08));
  border-color: rgba(139,92,246,0.35);
}
section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label > div:first-child { display: none; }
section[data-testid="stSidebar"] .stRadio p { font-size: 0.92rem; font-weight: 500; }

/* Inputs */
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div, .stNumberInput input {
  background: rgba(255,255,255,0.03) !important; border: 1px solid var(--border) !important;
  border-radius: 12px !important; color: var(--text) !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: rgba(139,92,246,0.6) !important; box-shadow: 0 0 0 3px rgba(139,92,246,0.18) !important;
}
label, .stMarkdown p { color: var(--text); }

/* Buttons */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
  border-radius: 12px; border: 1px solid var(--border); background: var(--surface-2);
  color: var(--text); font-weight: 600; padding: 0.55rem 1.1rem; transition: all .18s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover { border-color: rgba(139,92,246,0.5); transform: translateY(-1px); }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
  background: var(--grad); border: none; color: white;
  box-shadow: 0 8px 28px -8px rgba(139,92,246,0.65);
}
.stButton > button[kind="primary"]:hover { box-shadow: 0 10px 34px -6px rgba(139,92,246,0.85); }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid var(--border); }
.stTabs [data-baseweb="tab"] { border-radius: 10px 10px 0 0; padding: 10px 16px; color: var(--muted); }
.stTabs [aria-selected="true"] { color: var(--text) !important; }
.stTabs [data-baseweb="tab-highlight"] { background: var(--grad); height: 2px; }

/* Expanders, uploader, status */
[data-testid="stExpander"] { border: 1px solid var(--border); border-radius: 14px; background: var(--surface); }
[data-testid="stFileUploaderDropzone"] {
  background: rgba(139,92,246,0.05); border: 1.5px dashed rgba(139,92,246,0.45); border-radius: 16px;
}
[data-testid="stStatusWidget"] { display: none; }

/* ---------- Components ---------- */
.eyebrow { display: inline-flex; align-items: center; gap: 8px; font-size: 0.72rem; font-weight: 600;
  letter-spacing: .14em; text-transform: uppercase; color: var(--cyan);
  padding: 5px 11px; border: 1px solid rgba(34,211,238,0.3); border-radius: 999px; background: rgba(34,211,238,0.06); }
.eyebrow .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--cyan); box-shadow: 0 0 10px var(--cyan); }
.hero h1 { font-size: 2.6rem; line-height: 1.1; font-weight: 800; letter-spacing: -0.03em; margin: 14px 0 10px; }
.hero h1 .grad { background: var(--grad); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.hero p { color: var(--muted); font-size: 1.05rem; max-width: 720px; margin: 0; }
.page-head { margin-bottom: 22px; }
.page-head h2 { font-size: 1.75rem; font-weight: 750; letter-spacing: -0.02em; margin: 10px 0 6px; }
.page-head p { color: var(--muted); margin: 0; }

.card { background: var(--surface); border: 1px solid var(--border); border-radius: 18px; padding: 20px 22px;
  position: relative; overflow: hidden; }
.card.glow::before { content: ""; position: absolute; inset: 0; border-radius: 18px; padding: 1px;
  background: linear-gradient(140deg, rgba(139,92,246,0.55), transparent 40%, rgba(34,211,238,0.35));
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor; mask-composite: exclude; pointer-events: none; }
.card h4 { margin: 0 0 6px; font-size: 1rem; font-weight: 650; }
.card p { margin: 0; color: var(--muted); font-size: 0.9rem; line-height: 1.55; }
.card .icon { width: 38px; height: 38px; border-radius: 11px; display: grid; place-items: center; font-size: 1.1rem;
  background: linear-gradient(140deg, rgba(139,92,246,0.25), rgba(34,211,238,0.12)); margin-bottom: 14px; }

.kpi { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 16px 18px; }
.kpi .label { color: var(--muted); font-size: 0.78rem; font-weight: 500; text-transform: uppercase; letter-spacing: .08em; }
.kpi .value { font-size: 1.7rem; font-weight: 750; letter-spacing: -0.02em; margin-top: 6px; }
.kpi .sub { color: var(--muted); font-size: 0.8rem; margin-top: 2px; }

.pill { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px;
  font-size: 0.78rem; font-weight: 600; border: 1px solid; }
.chip { display: inline-block; padding: 4px 10px; margin: 3px 4px 3px 0; border-radius: 8px; font-size: 0.8rem;
  background: var(--surface-2); border: 1px solid var(--border); color: var(--text); }

/* Pipeline */
.pipeline { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; position: relative; }
.step { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 16px; position: relative;
  transition: all .3s ease; }
.step .num { font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: var(--muted); }
.step .name { font-weight: 700; font-size: 1.02rem; margin: 6px 0 4px; letter-spacing: .02em; }
.step .desc { color: var(--muted); font-size: 0.82rem; line-height: 1.45; min-height: 2.4em; }
.step .state { margin-top: 10px; font-size: 0.75rem; font-weight: 600; }
.step.active { border-color: rgba(139,92,246,0.8); box-shadow: 0 0 0 1px rgba(139,92,246,0.4), 0 12px 40px -12px rgba(139,92,246,0.7);
  animation: pulse 1.6s ease-in-out infinite; }
.step.done { border-color: rgba(52,211,153,0.45); }
.step.skipped { opacity: 0.45; }
.step:not(:last-child)::after { content: "→"; position: absolute; right: -13px; top: 50%; transform: translateY(-50%);
  color: var(--muted); font-size: 0.9rem; z-index: 2; }
@keyframes pulse { 0%,100% { box-shadow: 0 0 0 1px rgba(139,92,246,0.35), 0 10px 30px -14px rgba(139,92,246,0.6); }
  50% { box-shadow: 0 0 0 1px rgba(139,92,246,0.7), 0 14px 46px -10px rgba(139,92,246,0.95); } }

/* Reasoning log */
.log { margin-top: 12px; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; background: rgba(0,0,0,0.35);
  border: 1px solid var(--border); border-radius: 14px; padding: 14px 16px; line-height: 1.7; }
.log .row { display: flex; gap: 10px; }
.log .t { color: var(--violet); min-width: 76px; }
.log .m { color: #c9cde0; }

/* Scores */
.ring-wrap { display: flex; align-items: center; gap: 22px; }
.ring-meta .big { font-size: 0.8rem; color: var(--muted); text-transform: uppercase; letter-spacing: .08em; }
.crit { padding: 14px 0; border-bottom: 1px solid var(--border); }
.crit:last-child { border-bottom: none; }
.crit .top { display: flex; justify-content: space-between; align-items: baseline; }
.crit .nm { font-weight: 650; text-transform: capitalize; }
.crit .sc { font-family: 'JetBrains Mono', monospace; font-weight: 600; }
.bar { height: 7px; border-radius: 99px; background: rgba(255,255,255,0.06); margin: 8px 0 8px; overflow: hidden; }
.bar > span { display: block; height: 100%; border-radius: 99px; }
.crit .why { color: var(--muted); font-size: 0.86rem; line-height: 1.55; }

/* Fields */
.fields { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
.field { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 14px 16px; }
.field .k { color: var(--muted); font-size: 0.74rem; text-transform: uppercase; letter-spacing: .08em; }
.field .v { font-weight: 650; margin: 6px 0 10px; word-break: break-word; }
.field .conf { display: flex; align-items: center; gap: 8px; font-size: 0.72rem; color: var(--muted); }
.field .conf .bar { flex: 1; margin: 0; height: 5px; }

/* SWOT */
.swot { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.swot .q { border-radius: 16px; padding: 18px; border: 1px solid; }
.swot .q h5 { margin: 0 0 10px; font-size: 0.8rem; text-transform: uppercase; letter-spacing: .1em; }
.swot .q ul { margin: 0; padding-left: 18px; }
.swot .q li { margin: 6px 0; font-size: 0.9rem; line-height: 1.45; color: #d7dae6; }

/* Result list */
.result { padding: 14px 0; border-bottom: 1px solid var(--border); }
.result:last-child { border-bottom: none; }
.result a { color: var(--text); font-weight: 600; text-decoration: none; }
.result a:hover { color: var(--cyan); }
.result p { color: var(--muted); font-size: 0.87rem; margin: 6px 0 4px; line-height: 1.55; }
.result .url { font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #6b7190; }

.section-title { font-size: 0.78rem; font-weight: 600; letter-spacing: .12em; text-transform: uppercase;
  color: var(--muted); margin: 26px 0 12px; }
.brand { display: flex; align-items: center; gap: 10px; padding: 6px 4px 14px; }
.brand .logo { width: 34px; height: 34px; border-radius: 10px; background: var(--grad); display: grid; place-items: center;
  font-weight: 800; color: white; box-shadow: 0 6px 20px -6px rgba(139,92,246,0.8); }
.brand .t1 { font-weight: 750; font-size: 0.98rem; letter-spacing: -0.01em; }
.brand .t2 { color: var(--muted); font-size: 0.72rem; }
.side-stat { display: flex; justify-content: space-between; font-size: 0.84rem; padding: 6px 2px; color: var(--muted); }
.side-stat b { color: var(--text); font-weight: 600; }
.status-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 7px; }

@media (max-width: 900px) {
  .pipeline { grid-template-columns: 1fr 1fr; }
  .step:nth-child(2)::after { display: none; }
  .swot { grid-template-columns: 1fr; }
  .hero h1 { font-size: 2rem; }
}
</style>
"""


def inject_css():
    st.html(CSS)


# ============== Components ==============

def page_header(eyebrow: str, title: str, subtitle: str) -> str:
    return f"""
    <div class="page-head">
    <span class="eyebrow"><span class="dot"></span>{esc(eyebrow)}</span>
    <h2>{esc(title)}</h2>
    <p>{esc(subtitle)}</p>
    </div>
    """


def section(title: str) -> str:
    return f'<div class="section-title">{esc(title)}</div>'


def kpi(label: str, value, sub: str = "", color: Optional[str] = None) -> str:
    style = f' style="color:{color}"' if color else ""
    return f"""
    <div class="kpi">
    <div class="label">{esc(label)}</div>
    <div class="value"{style}>{esc(value)}</div>
    <div class="sub">{esc(sub)}</div>
    </div>
    """


def feature_card(icon: str, title: str, body: str, glow: bool = False) -> str:
    return f"""
    <div class="card{' glow' if glow else ''}">
    <div class="icon">{icon}</div>
    <h4>{esc(title)}</h4>
    <p>{esc(body)}</p>
    </div>
    """


def pill(text: str, color_key: str) -> str:
    c = COLORS[color_key]
    return f'<span class="pill" style="color:{c};border-color:{c}55;background:{c}14">{esc(text)}</span>'


def recommendation_pill(recommendation: str) -> str:
    color_key, label = RECOMMENDATION_STYLE.get(str(recommendation).upper(), ("muted", str(recommendation)))
    if color_key == "muted":
        return f'<span class="chip">{esc(label)}</span>'
    return pill(label, color_key)


def chips(items: Iterable) -> str:
    return "".join(f'<span class="chip">{esc(i)}</span>' for i in items if i)


PIPELINE_STEPS = [
    ("retrieve", "RETRIEVE", "Semantic search over your private ChromaDB knowledge base"),
    ("grade", "GRADE", "LLM scores whether local data can answer the question"),
    ("web_search", "SEARCH", "Deep web research with Serper + Tavily, only if needed"),
    ("generate", "GENERATE", "Weighted scores, reasoning and extracted bid variables"),
]

STEP_STATE_LABEL = {
    "idle": ("Waiting", COLORS["muted"]),
    "active": ("● Running", COLORS["violet"]),
    "done": ("✓ Complete", COLORS["green"]),
    "skipped": ("— Skipped", COLORS["muted"]),
}


def pipeline(states: Optional[dict] = None, notes: Optional[dict] = None) -> str:
    states = states or {}
    notes = notes or {}
    cells = []
    for i, (key, name, desc) in enumerate(PIPELINE_STEPS, 1):
        state = states.get(key, "idle")
        label, color = STEP_STATE_LABEL[state]
        detail = notes.get(key, desc)
        cells.append(f"""
        <div class="step {state}">
        <div class="num">0{i}</div>
        <div class="name">{name}</div>
        <div class="desc">{esc(detail)}</div>
        <div class="state" style="color:{color}">{label}</div>
        </div>
        """)
    return f'<div class="pipeline">{"".join(cells)}</div>'


def reasoning_log(rows: list[tuple[str, str]]) -> str:
    body = "".join(
        f'<div class="row"><span class="t">{esc(tag)}</span><span class="m">{esc(msg)}</span></div>'
        for tag, msg in rows
    )
    return f'<div class="log">{body or "<span class=m>Waiting for the agent…</span>"}</div>'


def score_ring(score: float, size: int = 132, label: str = "Overall") -> str:
    score = max(0, min(100, float(score or 0)))
    stroke = 11
    r = (size - stroke) / 2
    circ = 2 * 3.14159 * r
    offset = circ * (1 - score / 100)
    color = score_color(score)
    return f"""
    <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" role="img" aria-label="{esc(label)} score {score:.0f} of 100">
    <circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="rgba(255,255,255,0.07)" stroke-width="{stroke}"/>
    <circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round"
    stroke-dasharray="{circ:.1f}" stroke-dashoffset="{offset:.1f}" transform="rotate(-90 {size/2} {size/2})"
    style="filter: drop-shadow(0 0 10px {color}66)"/>
    <text x="50%" y="48%" text-anchor="middle" dominant-baseline="middle" fill="#e7e9f0"
    font-family="Inter" font-size="{size*0.27:.0f}" font-weight="800">{score:.0f}</text>
    <text x="50%" y="68%" text-anchor="middle" fill="#8b91a7" font-family="Inter" font-size="{size*0.09:.0f}">/ 100</text>
    </svg>
    """


def score_summary(score: float, recommendation: str, confidence: Optional[float], title: str) -> str:
    conf = f"{float(confidence):.0%}" if confidence is not None else "—"
    return f"""
    <div class="card glow">
    <div class="ring-wrap">
    {score_ring(score)}
    <div class="ring-meta">
    <div class="big">{esc(title)}</div>
    <div style="font-size:1.35rem;font-weight:750;margin:6px 0 10px">{recommendation_pill(recommendation)}</div>
    <div style="color:var(--muted);font-size:0.86rem">Model confidence <b style="color:var(--text)">{conf}</b></div>
    </div>
    </div>
    </div>
    """


def criteria_breakdown(breakdown: dict) -> str:
    rows = []
    for name, detail in breakdown.items():
        if hasattr(detail, "score"):
            score, reasoning = detail.score, detail.reasoning
        else:
            score, reasoning = (detail or {}).get("score", 0), (detail or {}).get("reasoning", "")
        score = float(score or 0)
        color = score_color(score)
        rows.append(f"""
        <div class="crit">
        <div class="top"><span class="nm">{esc(name)}</span><span class="sc" style="color:{color}">{score:.0f}</span></div>
        <div class="bar"><span style="width:{score}%;background:linear-gradient(90deg,{color}aa,{color})"></span></div>
        <div class="why">{esc(reasoning)}</div>
        </div>
        """)
    return f'<div class="card">{"".join(rows)}</div>'


def extracted_fields(fields: dict) -> str:
    """Render {name: value} or {name: {value, confidence, source}} as field cards."""
    cards = []
    for key, raw in fields.items():
        if isinstance(raw, dict) and "value" in raw:
            value, confidence, source = raw.get("value"), raw.get("confidence"), raw.get("source", "")
        else:
            value, confidence, source = raw, None, ""
        if value in (None, "", [], {}):
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = f"{value:,}"
        conf_html = ""
        if confidence is not None:
            pct = float(confidence) * 100
            conf_html = f"""
            <div class="conf"><div class="bar"><span style="width:{pct:.0f}%;background:{score_color(pct)}"></span></div>
            {pct:.0f}%</div>
            """
        src = f'<div class="conf" style="margin-top:6px">{esc(source)}</div>' if source else ""
        cards.append(f"""
        <div class="field">
        <div class="k">{esc(key.replace('_', ' '))}</div>
        <div class="v">{esc(value)}</div>
        {conf_html}{src}
        </div>
        """)
    if not cards:
        return '<div class="card"><p>No structured fields were extracted.</p></div>'
    return f'<div class="fields">{"".join(cards)}</div>'


def swot_grid(swot: dict) -> str:
    quadrants = [
        ("strengths", "Strengths", "green"),
        ("weaknesses", "Weaknesses", "amber"),
        ("opportunities", "Opportunities", "cyan"),
        ("threats", "Threats", "red"),
    ]
    cells = []
    for key, title, color_key in quadrants:
        c = COLORS[color_key]
        items = "".join(f"<li>{esc(i)}</li>" for i in (swot.get(key) or [])[:5]) or "<li>—</li>"
        cells.append(f"""
        <div class="q" style="border-color:{c}40;background:linear-gradient(160deg,{c}14,transparent 70%)">
        <h5 style="color:{c}">{title}</h5>
        <ul>{items}</ul>
        </div>
        """)
    return f'<div class="swot">{"".join(cells)}</div>'


def result_list(results: list[dict], limit: int = 5, snippet_len: int = 280) -> str:
    rows = []
    for r in results[:limit]:
        title = r.get("title") or "Untitled"
        url = r.get("url") or ""
        content = (r.get("content") or r.get("snippet") or "")[:snippet_len]
        link = f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(title)}</a>' if url else f"<b>{esc(title)}</b>"
        rows.append(f"""
        <div class="result">
        {link}
        <p>{esc(content)}{'…' if content else ''}</p>
        <div class="url">{esc(url)}</div>
        </div>
        """)
    if not rows:
        return '<div class="card"><p>No results returned.</p></div>'
    return f'<div class="card">{"".join(rows)}</div>'


def text_card(title: str, body: str, accent: Optional[str] = None) -> str:
    border = f' style="border-left:3px solid {COLORS[accent]}"' if accent else ""
    return f"""
    <div class="card"{border}>
    <h4>{esc(title)}</h4>
    <p style="color:#cfd3e2">{esc(body).replace(chr(10), "<br>")}</p>
    </div>
    """


def status_row(label: str, ok: bool, detail: str, warn: bool = False) -> str:
    color = COLORS["green"] if ok else (COLORS["amber"] if warn else COLORS["red"])
    state = "Online" if ok else ("Not configured" if warn else "Offline")
    return f"""
    <div class="card" style="padding:16px 18px;margin-bottom:12px">
    <div style="display:flex;justify-content:space-between;align-items:center">
    <b>{esc(label)}</b>
    <span style="color:{color};font-size:0.8rem;font-weight:600">
    <span class="status-dot" style="background:{color};box-shadow:0 0 8px {color}"></span>{state}</span>
    </div>
    <p style="margin-top:6px">{esc(detail)}</p>
    </div>
    """
