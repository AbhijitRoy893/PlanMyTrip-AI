import json
import time
import uuid
from datetime import datetime

import requests
import streamlit as st

# --------------------------------------------------
# Backend URL (FastAPI)
# --------------------------------------------------
API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="PlanMyTrip AI",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# Constants
# --------------------------------------------------
AGENTS = [
    ("flight_agent", "Flight Agent", "Searching flights"),
    ("hotel_agent", "Hotel Agent", "Finding hotels"),
    ("itinerary_agent", "Itinerary Agent", "Building day-by-day plan"),
    ("final_agent", "Final Agent", "Writing your trip plan"),
]

DESTINATIONS = [
    ("🇯🇵", "Tokyo", "linear-gradient(135deg,#ff5f9e,#5b3df5)"),
    ("🇫🇷", "Paris", "linear-gradient(135deg,#5f8bff,#e0b3ff)"),
    ("🇹🇭", "Bangkok", "linear-gradient(135deg,#ff8a3d,#b3122d)"),
    ("🇮🇹", "Rome", "linear-gradient(135deg,#f2c078,#3a86c8)"),
    ("🇦🇪", "Dubai", "linear-gradient(135deg,#f5a962,#1c3b6e)"),
]

QUICK_PROMPTS = {
    "7-day Japan under ₹2L": "Plan a complete 7 days Japan trip including flights, hotels and sightseeing under 2 lakhs.",
    "Paris trip for 5 days": "Plan a complete 5 days Paris trip including flights, hotels and sightseeing.",
    "Dubai weekend trip": "Plan a Dubai weekend trip including flights, hotels and sightseeing.",
    "Bali backpacking 10 days": "Plan a 10 days Bali backpacking trip on a budget including flights, stays and sightseeing.",
}

# --------------------------------------------------
# Session state
# --------------------------------------------------
st.session_state.setdefault("query", "")
st.session_state.setdefault("history", [])   # past results for this browser session
st.session_state.setdefault("result", None)  # currently shown result


def set_query(text: str):
    st.session_state["query"] = text


# --------------------------------------------------
# Styling
# --------------------------------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp { font-family: 'Inter', sans-serif; }
.stApp { background: radial-gradient(1200px 600px at 60% -10%, #12235a 0%, #060b1d 55%, #040814 100%); color: #e8ecf8; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2rem; max-width: 1100px; }

/* Sidebar */
section[data-testid="stSidebar"] { background: #070d22; border-right: 1px solid rgba(255,255,255,.06); }
.brand { font-size: 1.15rem; font-weight: 700; margin-bottom: .5rem; }
.side-title { font-size: 1rem; font-weight: 700; margin: 1.4rem 0 .6rem; }
.pill { display:flex; align-items:center; gap:.6rem; padding:.55rem .8rem; margin-bottom:.4rem;
        background: rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.06);
        border-radius:10px; font-size:.86rem; color:#c9d3f0; }
.pill .dot { width:22px; height:22px; border-radius:50%; display:flex; align-items:center;
             justify-content:center; font-size:.72rem; background:rgba(255,255,255,.08); }
.pill.running { border-color:#4c8dff; background:rgba(76,141,255,.14); color:#fff; }
.pill.running .dot { background:#4c8dff; }
.pill.done { border-color:rgba(52,211,153,.5); color:#d5f7ea; }
.pill.done .dot { background:#10b981; color:#fff; }
.pill.error { border-color:#f87171; color:#fecaca; }

/* Hero */
.hero { text-align:center; margin: .5rem 0 1.6rem; }
.hero h1 { font-size: 3rem; font-weight: 800; margin:0; letter-spacing:-.02em; }
.hero p { color:#9fb0da; font-size:1.05rem; max-width:640px; margin:.6rem auto 0; }

/* Destination cards */
.dest { height:120px; border-radius:16px; display:flex; flex-direction:column; align-items:center;
        justify-content:center; gap:.2rem; box-shadow:0 8px 24px rgba(0,0,0,.35); }
.dest .flag { font-size:2rem; }
.dest .name { font-weight:700; font-size:.95rem; text-shadow:0 1px 6px rgba(0,0,0,.5); }

.section-label { font-weight:700; color:#8fb4ff; margin:1.6rem 0 .6rem; font-size:.9rem; }

/* Buttons */
div.stButton > button {
    width:100%; border:none; color:#fff; font-weight:600; border-radius:14px; padding:.9rem 1rem;
    background: linear-gradient(180deg,#3b78e7,#2453b3); box-shadow:0 6px 18px rgba(36,83,179,.35);
    transition: transform .15s ease, box-shadow .15s ease;
}
div.stButton > button:hover { transform: translateY(-2px); box-shadow:0 10px 24px rgba(59,120,231,.5); color:#fff; }
div.stButton > button[kind="primary"] { padding:1rem; font-size:1.05rem; background:linear-gradient(90deg,#2f6bde,#4f8dff); }

/* Text area */
div[data-baseweb="textarea"] { background:#080f26; border:1.5px solid #c7cbe6 !important; border-radius:14px; }
textarea { color:#f2f5ff !important; font-size:1rem !important; }

/* Tabs / result */
button[data-baseweb="tab"] { font-weight:600; }
.result-card { background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08);
               border-radius:16px; padding:1.2rem 1.4rem; }
div[data-testid="stMetric"] { background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08);
                              border-radius:12px; padding:.6rem .9rem; }
</style>
""",
    unsafe_allow_html=True,
)


# --------------------------------------------------
# Sidebar
# --------------------------------------------------
sidebar_pipeline = None

with st.sidebar:
    st.markdown('<div class="brand">🌍 PlanMyTrip AI</div>', unsafe_allow_html=True)
    st.divider()

    user_id = st.text_input(
        "👤 User ID",
        value="user_abhijit",
        help="Sent to the backend as the LangGraph thread_id, so each user has their own saved conversation in PostgreSQL.",
    ).strip()

    st.markdown('<div class="side-title">Powered by</div>', unsafe_allow_html=True)
    for icon, label in [
        ("⚡", "FastAPI backend"),
        ("🔗", "LangGraph"),
        ("🧠", "Groq · gpt-oss-120b"),
        ("🐘", "PostgreSQL"),
        ("🔍", "Tavily Search"),
        ("✈️", "Flight search tool"),
    ]:
        st.markdown(f'<div class="pill">{icon} {label}</div>', unsafe_allow_html=True)

    st.markdown('<div class="side-title">Agent Pipeline</div>', unsafe_allow_html=True)
    sidebar_pipeline = st.empty()


def render_pipeline(states: dict):
    """states: {node_name: 'idle'|'running'|'done'|'error'}"""
    icons = {"idle": "", "running": "⏳", "done": "✓", "error": "!"}
    html = ""
    for i, (node, label, _) in enumerate(AGENTS, start=1):
        s = states.get(node, "idle")
        dot = icons[s] or i
        html += f'<div class="pill {s if s != "idle" else ""}"><span class="dot">{dot}</span>{label}</div>'
    sidebar_pipeline.markdown(html, unsafe_allow_html=True)


render_pipeline({})


# --------------------------------------------------
# Hero + destinations
# --------------------------------------------------
st.markdown(
    """
<div class="hero">
  <h1>✈️ PlanMyTrip AI</h1>
  <p>Four specialized agents work together: searching flights, hotels, building an itinerary,
  and delivering your complete trip plan.</p>
</div>
""",
    unsafe_allow_html=True,
)

cols = st.columns(len(DESTINATIONS))
for col, (flag, name, grad) in zip(cols, DESTINATIONS):
    col.markdown(
        f'<div class="dest" style="background:{grad}"><span class="flag">{flag}</span>'
        f'<span class="name">{name}</span></div>',
        unsafe_allow_html=True,
    )

# --------------------------------------------------
# Trip input
# --------------------------------------------------
st.markdown('<div class="section-label">📋 Describe your trip</div>', unsafe_allow_html=True)

qcols = st.columns(len(QUICK_PROMPTS))
for col, (label, full_text) in zip(qcols, QUICK_PROMPTS.items()):
    col.button(label, key=f"q_{label}", on_click=set_query, args=(full_text,))

st.text_area(
    "Trip description",
    key="query",
    height=130,
    placeholder="e.g. Plan a complete 7 days Japan trip including flights, hotels and sightseeing under 2 lakhs.",
    label_visibility="collapsed",
)

generate = st.button("🚀 Generate My Travel Plan", type="primary")


# --------------------------------------------------
# Call the FastAPI backend (streaming) with live progress
# --------------------------------------------------
def run_plan(query: str, user: str) -> dict:
    payload = {"query": query, "thread_id": user}

    states = {node: "idle" for node, _, _ in AGENTS}
    states[AGENTS[0][0]] = "running"
    render_pipeline(states)

    out = {"flights": "", "hotels": "", "itinerary": "", "final": "", "llm_calls": 0}
    key_map = {
        "flight_results": "flights",
        "hotel_results": "hotels",
        "itinerary": "itinerary",
    }
    started = time.time()

    with st.status("Planning your trip...", expanded=True) as status:
        status.write(f"⏳ {AGENTS[0][2]}...")
        try:
            with requests.post(
                f"{API_URL}/plan-trip/stream",
                json=payload,
                stream=True,
                timeout=300,
            ) as r:
                r.raise_for_status()

                for line in r.iter_lines():
                    if not line:
                        continue

                    event = json.loads(line)

                    if "error" in event:
                        raise RuntimeError(event["error"])

                    node = event.get("node")
                    if node not in states:
                        continue

                    states[node] = "done"

                    for api_key, out_key in key_map.items():
                        if api_key in event:
                            out[out_key] = event[api_key]
                    if "final" in event:
                        out["final"] = event["final"]
                    out["llm_calls"] = event.get("llm_calls", out["llm_calls"])

                    label = next(l for n, l, _ in AGENTS if n == node)
                    status.write(f"✅ {label} finished")

                    idx = [n for n, _, _ in AGENTS].index(node)
                    if idx + 1 < len(AGENTS):
                        nxt = AGENTS[idx + 1]
                        states[nxt[0]] = "running"
                        status.write(f"⏳ {nxt[2]}...")
                    render_pipeline(states)

            status.update(label="Your travel plan is ready", state="complete", expanded=False)

        except requests.exceptions.ConnectionError:
            for n, s in states.items():
                if s == "running":
                    states[n] = "error"
            render_pipeline(states)
            status.update(label="Backend is not running", state="error")
            raise RuntimeError(
                "Cannot reach the backend. Start it with: python -m uvicorn api:api"
            )

        except Exception as e:
            for n, s in states.items():
                if s == "running":
                    states[n] = "error"
            render_pipeline(states)
            status.update(label="Something went wrong", state="error")
            raise e

    out["seconds"] = round(time.time() - started, 1)
    out["query"] = query
    out["user"] = user
    out["time"] = datetime.now().strftime("%d %b %Y, %I:%M %p")
    out["id"] = uuid.uuid4().hex[:8]
    return out


if generate:
    if not user_id:
        st.warning("Enter a User ID in the sidebar first.")
    elif not st.session_state["query"].strip():
        st.warning("Describe your trip above, or pick one of the quick options.")
    else:
        try:
            res = run_plan(st.session_state["query"].strip(), user_id)
            st.session_state["result"] = res
            st.session_state["history"].insert(0, res)
        except Exception as e:
            st.error(f"The planner failed: {e}")
            st.caption(
                "Make sure the backend is running (python -m uvicorn api:api) and that "
                "DATABASE_URL, GROQ_API_KEY and your Tavily/flight API keys are set in .env."
            )


# --------------------------------------------------
# Results
# --------------------------------------------------
def show_text(value):
    if not value:
        st.info("Nothing returned for this section.")
    elif isinstance(value, (dict, list)):
        st.json(value)
    else:
        st.markdown(value)


res = st.session_state["result"]
if res:
    st.markdown('<div class="section-label">🧳 Your trip plan</div>', unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("Agents run", len(AGENTS))
    m2.metric("LLM / tool calls", res["llm_calls"])
    m3.metric("Time taken", f'{res["seconds"]} s')

    t_final, t_flights, t_hotels, t_itin = st.tabs(
        ["📌 Final Plan", "✈️ Flights", "🏨 Hotels", "🗺️ Itinerary"]
    )
    with t_final:
        show_text(res["final"])
        if res["final"]:
            st.download_button(
                "⬇️ Download plan (.md)",
                data=res["final"],
                file_name=f'travel_plan_{res["id"]}.md',
                mime="text/markdown",
            )
    with t_flights:
        show_text(res["flights"])
    with t_hotels:
        show_text(res["hotels"])
    with t_itin:
        show_text(res["itinerary"])

# Past plans from this session
if len(st.session_state["history"]) > 1:
    with st.expander(f'🕘 Earlier plans this session ({len(st.session_state["history"]) - 1})'):
        for h in st.session_state["history"][1:]:
            st.markdown(f'**{h["time"]}** · {h["query"]}')
            if st.button("Show this plan", key=f'show_{h["id"]}'):
                st.session_state["result"] = h
                st.rerun()