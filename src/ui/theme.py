"""
Design system for the Streamlit UI: global CSS and small HTML components.

Direction: "audit ledger" — warm paper, near-black ink, one signal-orange
accent, an editorial serif for display type and tabular numerals for data.
Hairlines instead of boxes; colour is reserved for meaning (status, scores).

Every component returns an HTML string rendered with render(). Any text that
may come from users, documents, the web or the LLM goes through `esc()` first.
"""
from html import escape
from typing import Iterable, Optional

import streamlit as st


# ============== Tokens ==============

COLORS = {
    "bg": "#f4f2ec",
    "paper": "#fbfaf6",
    "ink": "#141412",
    "text": "#141412",
    "muted": "#6f6b62",
    "faint": "#a19c91",
    "line": "#e2ddd2",
    "accent": "#ff4f00",
    "violet": "#ff4f00",   # legacy key: primary accent
    "cyan": "#141412",     # legacy key: secondary accent (ink)
    "green": "#157a4a",
    "amber": "#b7791f",
    "red": "#c2362b",
}

RECOMMENDATION_STYLE = {
    "APPROVED": ("green", "Approved"),
    "REVIEW": ("amber", "Needs review"),
    "REJECTED": ("red", "Rejected"),
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
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500&display=swap');
:root {
  --bg: #f4f2ec; --paper: #fbfaf6; --ink: #141412; --muted: #6f6b62; --faint: #a19c91;
  --line: #e2ddd2; --line-strong: #cfc9bc; --accent: #ff4f00; --accent-soft: #fff1ea;
  --green: #157a4a; --amber: #b7791f; --red: #c2362b;
  --serif: 'Instrument Serif', Georgia, serif;
  --sans: 'Geist', system-ui, -apple-system, sans-serif;
  --mono: 'Geist Mono', ui-monospace, monospace;
}
html, body, .stApp, .stMarkdown, button, input, textarea, select, label, p { font-family: var(--sans) !important; }
.stApp { background: var(--bg); color: var(--ink); }
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer, [data-testid="stDecoration"], [data-testid="stStatusWidget"] { visibility: hidden; height: 0; }
.block-container { padding-top: 2.6rem; padding-bottom: 5rem; max-width: 1180px; }
.stMarkdown p, label { color: var(--ink); }
::selection { background: var(--accent); color: white; }

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] { background: var(--ink); border-right: none; }
section[data-testid="stSidebar"] * { color: #d9d5cb; }
section[data-testid="stSidebar"] .stRadio > label { display: none; }
section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] { gap: 0; }
section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
  padding: 10px 12px; border-radius: 6px; width: 100%; transition: background .15s ease;
}
section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label > div:first-child { display: none; }
section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover { background: rgba(255,255,255,0.05); }
section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked) { background: rgba(255,255,255,0.08); }
section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked) p { color: #fff; }
section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked)::before {
  content: ""; width: 6px; height: 6px; border-radius: 50%; background: var(--accent); margin: 0 10px 0 -2px; align-self: center;
}
section[data-testid="stSidebar"] .stRadio p { font-size: 0.9rem; font-weight: 500; color: #a8a398; }
section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] svg { fill: #a8a398; }

/* ---------- Inputs ---------- */
.stTextInput input, .stTextArea textarea, .stNumberInput input,
.stSelectbox div[data-baseweb="select"] > div {
  background: var(--paper) !important; border: 1px solid var(--line-strong) !important;
  border-radius: 8px !important; color: var(--ink) !important; font-size: 0.98rem !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: var(--ink) !important; box-shadow: 0 0 0 3px rgba(20,20,18,0.08) !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder { color: var(--faint) !important; }
[data-testid="stWidgetLabel"] p { font-size: 0.8rem !important; font-weight: 500; color: var(--muted) !important; }

/* ---------- Buttons ---------- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
  border-radius: 8px; border: 1px solid var(--line-strong); background: var(--paper);
  color: var(--ink); font-weight: 500; padding: 0.55rem 1rem; box-shadow: none; transition: all .15s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover { border-color: var(--ink); color: var(--ink); background: white; }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
  background: var(--ink); border: 1px solid var(--ink); color: #fff; font-weight: 600;
}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {
  background: var(--accent); border-color: var(--accent); color: #fff;
}
.stButton > button[kind="tertiary"] {
  border: none; background: transparent; padding: 0; color: var(--ink); font-weight: 600;
  text-decoration: underline; text-decoration-color: var(--line-strong); text-underline-offset: 4px;
}
.stButton > button[kind="tertiary"]:hover { color: var(--accent); text-decoration-color: var(--accent); background: transparent; }

/* Pills / toggles */
[data-testid="stPills"] button, [data-testid="stButtonGroup"] button {
  border-radius: 999px !important; background: var(--paper) !important; border: 1px solid var(--line-strong) !important;
  color: var(--muted) !important; font-size: 0.85rem !important;
}
[data-testid="stPills"] button[aria-checked="true"], [data-testid="stButtonGroup"] button[kind="pillsActive"],
[data-testid="stButtonGroup"] button[aria-checked="true"] {
  background: var(--ink) !important; border-color: var(--ink) !important; color: #fff !important;
}
[data-testid="stButtonGroup"] button[kind="pillsActive"] p { color: #fff !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 28px; border-bottom: 1px solid var(--line); }
.stTabs [data-baseweb="tab"] { padding: 10px 0; color: var(--muted); background: transparent; }
.stTabs [aria-selected="true"] { color: var(--ink) !important; }
.stTabs [data-baseweb="tab-highlight"] { background: var(--ink); height: 2px; }
.stTabs [data-baseweb="tab-border"] { display: none; }

/* Expanders, uploader, status, dataframe */
[data-testid="stExpander"] { border: 1px solid var(--line); border-radius: 10px; background: var(--paper); }
[data-testid="stExpander"] summary p { font-weight: 500; }
[data-testid="stFileUploaderDropzone"] { background: var(--paper); border: 1px dashed var(--line-strong); border-radius: 12px; }
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--ink); }
[data-testid="stStatus"], [data-testid="stExpander"] details { background: var(--paper); }
[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 10px; }

/* ---------- Type ---------- */
.eyebrow { font-family: var(--mono); font-size: 0.72rem; letter-spacing: .12em; text-transform: uppercase; color: var(--muted); }
.eyebrow b { color: var(--accent); font-weight: 500; }
.hero { padding: 8px 0 34px; border-bottom: 1px solid var(--line); margin-bottom: 8px; }
.hero h1 { font-family: var(--serif) !important; font-weight: 400; font-size: 4.4rem; line-height: 0.98;
  letter-spacing: -0.02em; margin: 18px 0 20px; color: var(--ink); }
.hero h1 em { font-style: italic; color: var(--accent); }
.hero p { color: var(--muted); font-size: 1.08rem; max-width: 620px; margin: 0; line-height: 1.6; }
.page-head { padding-bottom: 22px; margin-bottom: 26px; border-bottom: 1px solid var(--line); }
.page-head h2 { font-family: var(--serif) !important; font-weight: 400; font-size: 3rem; line-height: 1;
  letter-spacing: -0.015em; margin: 14px 0 10px; color: var(--ink); }
.page-head p { color: var(--muted); margin: 0; font-size: 1rem; max-width: 640px; }
.section-title { display: flex; align-items: center; gap: 12px; font-family: var(--mono); font-size: 0.7rem;
  letter-spacing: .14em; text-transform: uppercase; color: var(--muted); margin: 34px 0 14px; }
.section-title::after { content: ""; flex: 1; height: 1px; background: var(--line); }
.num { font-family: var(--sans); font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }

/* ---------- Surfaces ---------- */
.card { background: var(--paper); border: 1px solid var(--line); border-radius: 12px; padding: 22px 24px; }
.card h4 { margin: 0 0 8px; font-size: 1rem; font-weight: 600; color: var(--ink); }
.card p { margin: 0; color: var(--muted); font-size: 0.93rem; line-height: 1.6; }
.card.ink { background: var(--ink); border-color: var(--ink); }
.card.ink, .card.ink p, .card.ink h4 { color: #e9e5db; }

.kpi { border-top: 1px solid var(--ink); padding: 14px 0 4px; }
.kpi .label { font-family: var(--mono); color: var(--muted); font-size: 0.68rem; text-transform: uppercase; letter-spacing: .12em; }
.kpi .value { font-size: 2.3rem; font-weight: 500; letter-spacing: -0.03em; margin-top: 10px; line-height: 1;
  font-variant-numeric: tabular-nums; color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.kpi .sub { color: var(--muted); font-size: 0.82rem; margin-top: 8px; }

.feature { border-top: 1px solid var(--line-strong); padding: 18px 0 6px; }
.feature .n { font-family: var(--mono); font-size: 0.72rem; color: var(--accent); }
.feature h4 { font-family: var(--serif); font-weight: 400; font-size: 1.6rem; margin: 10px 0 8px; line-height: 1.05; color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.feature p { color: var(--muted); font-size: 0.9rem; line-height: 1.55; margin: 0 0 8px; min-height: 3em; }

.pill { display: inline-flex; align-items: center; gap: 7px; padding: 4px 11px; border-radius: 999px;
  font-size: 0.8rem; font-weight: 600; }
.pill .d { width: 7px; height: 7px; border-radius: 50%; }
.chip { display: inline-block; padding: 5px 11px; margin: 3px 6px 3px 0; border-radius: 999px; font-size: 0.82rem;
  background: var(--paper); border: 1px solid var(--line-strong); color: var(--ink); }

/* ---------- Pipeline ---------- */
.pipe { display: grid; grid-template-columns: repeat(4, 1fr); position: relative; padding-top: 6px; }
.pipe::before { content: ""; position: absolute; top: 18px; left: 12px; right: 12px; height: 1px; background: var(--line-strong); }
.node { position: relative; padding-right: 22px; }
.node .dot { width: 25px; height: 25px; border-radius: 50%; background: var(--bg); border: 1px solid var(--line-strong);
  display: grid; place-items: center; font-family: var(--mono); font-size: 0.66rem; color: var(--muted); position: relative; z-index: 1; }
.node .name { font-family: var(--mono); font-size: 0.74rem; letter-spacing: .14em; margin: 16px 0 6px; color: var(--ink); }
.node .desc { color: var(--muted); font-size: 0.86rem; line-height: 1.5; min-height: 2.6em; }
.node .state { margin-top: 10px; font-family: var(--mono); font-size: 0.7rem; letter-spacing: .06em; text-transform: uppercase; color: var(--faint); }
.node.active .dot { background: var(--accent); border-color: var(--accent); color: white; animation: ping 1.4s ease-out infinite; }
.node.active .state { color: var(--accent); }
.node.done .dot { background: var(--ink); border-color: var(--ink); color: white; }
.node.done .state { color: var(--green); }
.node.skipped { opacity: 0.5; }
.node.skipped .dot { border-style: dashed; }
.node.skipped .name { text-decoration: line-through; text-decoration-color: var(--faint); }
@keyframes ping { 0% { box-shadow: 0 0 0 0 rgba(255,79,0,0.45); } 100% { box-shadow: 0 0 0 12px rgba(255,79,0,0); } }

/* Reasoning log: the one dark "terminal" surface */
.log { margin-top: 22px; font-family: var(--mono); font-size: 0.8rem; background: var(--ink); color: #d9d5cb;
  border-radius: 10px; padding: 16px 18px; line-height: 1.85; }
.log .row { display: flex; gap: 14px; }
.log .t { color: var(--accent); min-width: 84px; }
.log .m { color: #e9e5db; }
.log .idle { color: #8a857a; }

/* ---------- Scores ---------- */
.verdict { display: flex; align-items: center; gap: 26px; }
.verdict .big { font-family: var(--mono); font-size: 0.68rem; letter-spacing: .12em; text-transform: uppercase; color: var(--muted); }
.crit { padding: 16px 0; border-bottom: 1px solid var(--line); }
.crit:first-child { padding-top: 2px; }
.crit:last-child { border-bottom: none; padding-bottom: 2px; }
.crit .top { display: flex; justify-content: space-between; align-items: baseline; }
.crit .nm { font-weight: 600; text-transform: capitalize; }
.crit .sc { font-variant-numeric: tabular-nums; font-weight: 600; font-size: 1.05rem; }
.bar { height: 4px; border-radius: 99px; background: var(--line); margin: 10px 0; overflow: hidden; }
.bar > span { display: block; height: 100%; border-radius: 99px; }
.crit .why { color: var(--muted); font-size: 0.9rem; line-height: 1.6; }

/* ---------- Fields ---------- */
.fields { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); border-top: 1px solid var(--line); border-left: 1px solid var(--line); }
.field { padding: 16px 18px; border-right: 1px solid var(--line); border-bottom: 1px solid var(--line); background: var(--paper); }
.field .k { font-family: var(--mono); color: var(--muted); font-size: 0.66rem; text-transform: uppercase; letter-spacing: .12em; }
.field .v { font-weight: 600; font-size: 1.02rem; margin: 8px 0 12px; word-break: break-word; font-variant-numeric: tabular-nums; }
.field .conf { display: flex; align-items: center; gap: 10px; font-family: var(--mono); font-size: 0.68rem; color: var(--muted); }
.field .conf .bar { flex: 1; margin: 0; height: 3px; }

/* ---------- SWOT ---------- */
.swot { display: grid; grid-template-columns: 1fr 1fr; border-top: 1px solid var(--ink); }
.swot .q { padding: 22px 24px 22px 0; border-bottom: 1px solid var(--line); }
.swot .q:nth-child(odd) { border-right: 1px solid var(--line); }
.swot .q:nth-child(even) { padding-left: 24px; padding-right: 0; }
.swot .q h5 { margin: 0 0 12px; font-family: var(--serif); font-weight: 400; font-size: 1.6rem; display: flex; align-items: center; gap: 10px; }
.swot .q h5 .d { width: 8px; height: 8px; border-radius: 50%; }
.swot .q ul { margin: 0 !important; padding: 0 !important; list-style: none; }
.swot .q li { margin: 0 !important; padding: 7px 0; font-size: 0.93rem; line-height: 1.45; border-top: 1px dashed var(--line); color: var(--ink); }

/* ---------- Result list ---------- */
.result { padding: 16px 0; border-bottom: 1px solid var(--line); }
.result:first-child { padding-top: 0; }
.result:last-child { border-bottom: none; padding-bottom: 0; }
.result a { color: var(--ink); font-weight: 600; text-decoration: none; }
.result a:hover { color: var(--accent); }
.result p { color: var(--muted); font-size: 0.9rem; margin: 6px 0; line-height: 1.6; }
.result .url { font-family: var(--mono); font-size: 0.7rem; color: var(--faint); }

/* ---------- Sidebar pieces ---------- */
.brand { padding: 4px 4px 26px; }
.brand .mark { font-family: var(--serif); font-size: 1.7rem; color: #fff; line-height: 1; }
.brand .mark em { color: var(--accent); font-style: italic; }
.brand .t2 { font-family: var(--mono); font-size: 0.64rem; letter-spacing: .14em; text-transform: uppercase; color: #8a857a !important; margin-top: 8px; }
.side-label { font-family: var(--mono); font-size: 0.64rem; letter-spacing: .14em; text-transform: uppercase;
  color: #8a857a !important; margin: 28px 0 8px; padding: 0 2px; }
.side-stat { display: flex; justify-content: space-between; font-size: 0.9rem; padding: 9px 2px; color: var(--muted);
  border-bottom: 1px solid var(--line); }
.side-stat:last-child { border-bottom: none; }
.side-stat b { color: var(--ink); font-weight: 600; font-variant-numeric: tabular-nums; }
section[data-testid="stSidebar"] .side-stat { font-size: 0.84rem; padding: 7px 2px; color: #a8a398;
  border-bottom: 1px solid rgba(255,255,255,0.06); }
section[data-testid="stSidebar"] .side-stat b { color: #fff !important; font-weight: 500; }
.status-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 8px; }

@media (max-width: 900px) {
  .hero h1 { font-size: 3rem; }
  .page-head h2 { font-size: 2.3rem; }
  .pipe { grid-template-columns: 1fr 1fr; row-gap: 22px; }
  .pipe::before { display: none; }
  .swot { grid-template-columns: 1fr; }
  .swot .q, .swot .q:nth-child(even) { padding: 18px 0; border-right: none; }
}
</style>
"""


def inject_css():
    st.html(CSS)


# ============== Components ==============

def page_header(eyebrow: str, title: str, subtitle: str) -> str:
    number, _, label = eyebrow.partition("·")
    eyebrow_html = f"<b>{esc(number.strip())}</b> — {esc(label.strip())}" if label else esc(eyebrow)
    return f"""
    <div class="page-head">
    <div class="eyebrow">{eyebrow_html}</div>
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


def feature_card(number: str, title: str, body: str, glow: bool = False) -> str:
    return f"""
    <div class="feature">
    <div class="n">{esc(number)}</div>
    <h4>{esc(title)}</h4>
    <p>{esc(body)}</p>
    </div>
    """


def pill(text: str, color_key: str) -> str:
    c = COLORS[color_key]
    return (f'<span class="pill" style="color:{c};background:{c}14;border:1px solid {c}33">'
            f'<span class="d" style="background:{c}"></span>{esc(text)}</span>')


def recommendation_pill(recommendation: str) -> str:
    color_key, label = RECOMMENDATION_STYLE.get(str(recommendation).upper(), ("muted", str(recommendation)))
    return pill(label, color_key)


def chips(items: Iterable) -> str:
    return "".join(f'<span class="chip">{esc(i)}</span>' for i in items if i)


PIPELINE_STEPS = [
    ("retrieve", "RETRIEVE", "Semantic search over your private ChromaDB knowledge base"),
    ("grade", "GRADE", "The LLM decides whether local data can answer the question"),
    ("web_search", "SEARCH", "Deep web research with Serper + Tavily, only when needed"),
    ("generate", "GENERATE", "Weighted scores, reasoning and extracted bid variables"),
]

STEP_STATE_LABEL = {
    "idle": "Waiting",
    "active": "Running",
    "done": "Complete",
    "skipped": "Skipped",
}


def pipeline(states: Optional[dict] = None, notes: Optional[dict] = None) -> str:
    states = states or {}
    notes = notes or {}
    cells = []
    for i, (key, name, desc) in enumerate(PIPELINE_STEPS, 1):
        state = states.get(key, "idle")
        mark = "✓" if state == "done" else f"0{i}"
        cells.append(f"""
        <div class="node {state}">
        <div class="dot">{mark}</div>
        <div class="name">{name}</div>
        <div class="desc">{esc(notes.get(key, desc))}</div>
        <div class="state">{STEP_STATE_LABEL[state]}</div>
        </div>
        """)
    return f'<div class="pipe">{"".join(cells)}</div>'


def reasoning_log(rows: list[tuple[str, str]]) -> str:
    body = "".join(
        f'<div class="row"><span class="t">{esc(tag)}</span><span class="m">{esc(msg)}</span></div>'
        for tag, msg in rows
    )
    return f'<div class="log">{body or "<span class=idle>$ waiting for a question_</span>"}</div>'


def score_ring(score: float, size: int = 148, label: str = "Overall") -> str:
    score = max(0, min(100, float(score or 0)))
    stroke = 3
    r = (size - 14) / 2
    circ = 2 * 3.14159 * r
    offset = circ * (1 - score / 100)
    color = score_color(score)
    c = size / 2
    return f"""
    <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" role="img" aria-label="{esc(label)} score {score:.0f} of 100">
    <circle cx="{c}" cy="{c}" r="{r}" fill="none" stroke="#e2ddd2" stroke-width="{stroke}"/>
    <circle cx="{c}" cy="{c}" r="{r}" fill="none" stroke="{color}" stroke-width="{stroke + 1}" stroke-linecap="round"
    stroke-dasharray="{circ:.1f}" stroke-dashoffset="{offset:.1f}" transform="rotate(-90 {c} {c})"/>
    <text x="50%" y="52%" text-anchor="middle" dominant-baseline="middle" fill="#141412"
    font-family="Instrument Serif, Georgia, serif" font-size="{size * 0.42:.0f}">{score:.0f}</text>
    <text x="50%" y="75%" text-anchor="middle" fill="#6f6b62" font-family="Geist Mono, monospace"
    font-size="{size * 0.07:.0f}" letter-spacing="1.5">/ 100</text>
    </svg>
    """


def score_summary(score: float, recommendation: str, confidence: Optional[float], title: str) -> str:
    conf = f"{float(confidence):.0%}" if confidence is not None else "—"
    return f"""
    <div class="card">
    <div class="verdict">
    {score_ring(score)}
    <div>
    <div class="big">{esc(title)}</div>
    <div style="margin:12px 0 14px">{recommendation_pill(recommendation)}</div>
    <div style="color:var(--muted);font-size:0.86rem">Model confidence
    <b class="num" style="color:var(--ink)">{conf}</b></div>
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
        <div class="bar"><span style="width:{score}%;background:{color}"></span></div>
        <div class="why">{esc(reasoning)}</div>
        </div>
        """)
    return f'<div class="card">{"".join(rows)}</div>'


def extracted_fields(fields: dict) -> str:
    """Render {name: value} or {name: {value, confidence, source}} as a ledger grid."""
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
            <div class="conf"><div class="bar"><span style="width:{pct:.0f}%;background:var(--ink)"></span></div>
            {pct:.0f}%</div>
            """
        src = f'<div class="conf" style="margin-top:8px">{esc(source)}</div>' if source else ""
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
        ("opportunities", "Opportunities", "accent"),
        ("threats", "Threats", "red"),
    ]
    cells = []
    for key, title, color_key in quadrants:
        items = "".join(f"<li>{esc(i)}</li>" for i in (swot.get(key) or [])[:5]) or "<li>—</li>"
        cells.append(f"""
        <div class="q">
        <h5><span class="d" style="background:{COLORS[color_key]}"></span>{title}</h5>
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
        link = f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(title)} ↗</a>' if url else f"<b>{esc(title)}</b>"
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
    border = f' style="border-left:2px solid {COLORS[accent]}"' if accent else ""
    return f"""
    <div class="card"{border}>
    <h4>{esc(title)}</h4>
    <p style="color:var(--ink);font-size:0.97rem;line-height:1.7">{esc(body).replace(chr(10), "<br>")}</p>
    </div>
    """


def status_row(label: str, ok: bool, detail: str, warn: bool = False) -> str:
    color = COLORS["green"] if ok else (COLORS["amber"] if warn else COLORS["red"])
    state = "Online" if ok else ("Not configured" if warn else "Offline")
    return f"""
    <div class="card" style="padding:18px 20px;margin-bottom:12px">
    <div style="display:flex;justify-content:space-between;align-items:center">
    <b style="font-weight:600">{esc(label)}</b>
    <span style="color:{color};font-family:var(--mono);font-size:0.7rem;letter-spacing:.08em;text-transform:uppercase">
    <span class="status-dot" style="background:{color}"></span>{state}</span>
    </div>
    <p style="margin-top:6px">{esc(detail)}</p>
    </div>
    """
