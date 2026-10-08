import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8080")
EXAMPLES = [
    "How do I connect to the company VPN?",
    "What is our password reset policy?",
    "What is the latest Microsoft Teams outage guidance?",
]
WORKFLOW = [
    "1. Route question",
    "2. Retrieve private KB",
    "3. Grade evidence",
    "4. Web fallback if weak",
    "5. Rewrite & retry",
    "6. Grounded answer",
]

st.set_page_config(page_title="IT Support Agentic RAG", page_icon="🛠️", layout="wide")

# ---------- Styling (ported from style.css) ----------
st.markdown(
    """
<style>
.stApp{background:radial-gradient(circle at top,#141b26 0,#0a0d12 44%);color:#edf2f7}
[data-testid="stSidebar"]{background:#0f141c;border-right:1px solid #202936}
[data-testid="stHeader"]{background:transparent}
.brand-badge{display:inline-block;font-size:11px;font-weight:800;letter-spacing:.16em;
  background:#183b2e;color:#78e5af;padding:7px 9px;border-radius:7px}
.side-title{font-size:30px;line-height:1.05;margin:18px 0 12px;font-weight:700}
.muted{color:#8c98a8;line-height:1.55;font-size:14px}
.workflow-card{border:1px solid #273142;background:#121923;padding:16px;border-radius:14px;margin:18px 0}
.workflow-card h3{margin:0 0 12px;font-size:14px}
.flow-step{font-size:13px;padding:8px 10px;border-left:2px solid #3a4658;color:#bac4d1;margin:5px 0}
.topbar{display:flex;align-items:center;justify-content:space-between;padding:6px 0 14px;
  border-bottom:1px solid #202936;margin-bottom:18px;font-size:14px}
.status-dot{width:8px;height:8px;background:#65d69a;border-radius:50%;display:inline-block;margin-right:8px}
.pill{background:#151e29;border:1px solid #293446;padding:8px 11px;border-radius:999px;color:#aab6c5}
.answer-source{margin-top:10px;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#7ee6b1}
.citations{margin-top:12px;padding-top:10px;border-top:1px solid #293444;font-size:12px;color:#a9b5c4}
.citations a{color:#8bc4ff;text-decoration:none}
.trace-panel{border:1px solid #273244;background:#0f141c;border-radius:14px;padding:18px}
.trace-panel h3{margin:0 0 6px}
.trace-item{font-size:12px;background:#151c26;border:1px solid #273244;padding:11px;border-radius:10px;margin:9px 0}
.empty{color:#657184;font-size:13px}
.source-box{margin-top:20px;border:1px solid #2a3648;border-radius:12px;padding:14px}
.source-box span{display:block;font-size:11px;color:#7f8a99;text-transform:uppercase;letter-spacing:.08em}
.source-box strong{font-size:14px}
div[data-testid="stChatMessage"]{background:#141b24;border:1px solid #243041;border-radius:16px}
.stButton>button{border:1px solid #303b4b;background:#151c26;color:#dbe4ee;border-radius:10px}
.stButton>button:hover{border-color:#44c486;color:#78e5af}
</style>
""",
    unsafe_allow_html=True,
)

# ---------- State ----------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "text": "**How can I help with IT support?**\n\nTry: “How do I connect to the company VPN?” "
            "or ask a question that may require current external vendor information.",
        }
    ]
if "trace" not in st.session_state:
    st.session_state.trace = []
if "source_used" not in st.session_state:
    st.session_state.source_used = "—"
if "pending" not in st.session_state:
    st.session_state.pending = None


# ---------- API calls ----------
def ask_agent(q: str):
    st.session_state.messages.append({"role": "user", "text": q})
    try:
        res = requests.post(f"{API_URL}/api/chat", json={"question": q}, timeout=120)
        data = res.json()
        if not res.ok:
            raise RuntimeError(data.get("detail", "Request failed"))
        st.session_state.messages.append(
            {
                "role": "assistant",
                "text": data["answer"],
                "source": data.get("source_used", ""),
                "citations": data.get("citations") or [],
            }
        )
        st.session_state.trace = data.get("trace") or []
        st.session_state.source_used = data.get("source_used", "—")
    except Exception as e:
        st.session_state.messages.append({"role": "assistant", "text": f"Error: {e}"})
        st.session_state.trace = ["Request failed"]
        st.session_state.source_used = "Error"


@st.dialog("Ingest Company Document")
def upload_dialog():
    st.caption(
        "Upload PDF, TXT, Markdown, or DOCX. The document is chunked, embedded, and indexed into Pinecone."
    )
    admin_key = st.text_input("Admin API key", type="password")
    file = st.file_uploader("File", type=["pdf", "txt", "md", "docx"])
    if st.button("Index Document", type="primary", use_container_width=True):
        if not file:
            st.warning("Choose a file first.")
            return
        with st.spinner("Indexing document..."):
            try:
                r = requests.post(
                    f"{API_URL}/api/ingest",
                    headers={"X-Admin-Key": admin_key},
                    files={"file": (file.name, file.getvalue(), file.type or "application/octet-stream")},
                    timeout=300,
                )
                d = r.json()
                if not r.ok:
                    raise RuntimeError(d.get("detail", "Upload failed"))
                st.success(f"Indexed {d['file']}: {d['chunks']} chunks.")
            except Exception as e:
                st.error(f"Error: {e}")


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown(
        """
<div class="brand-badge">FDE Project</div>
<div class="side-title">IT Support<br/>Agentic RAG</div>
<p class="muted">Private company knowledge first. External web only when evidence is weak.</p>
<div class="workflow-card"><h3>LangGraph Workflow</h3>"""
        + "".join(f'<div class="flow-step">{s}</div>' for s in WORKFLOW)
        + "</div>",
        unsafe_allow_html=True,
    )
    if st.button("+ Add Company Document", use_container_width=True):
        upload_dialog()

# ---------- Handle input before rendering ----------
chat_prompt = st.chat_input("Ask an IT support question...")
question = st.session_state.pending or chat_prompt
st.session_state.pending = None
if question:
    with st.spinner("Running LangGraph workflow..."):
        ask_agent(question.strip())

# ---------- Main layout ----------
main_col, trace_col = st.columns([3, 1], gap="large")

with main_col:
    st.markdown(
        '<div class="topbar"><div><span class="status-dot"></span>Enterprise Knowledge Copilot</div>'
        '<span class="pill">Agentic RAG</span></div>',
        unsafe_allow_html=True,
    )

    for m in st.session_state.messages:
        with st.chat_message(m["role"], avatar="🤖" if m["role"] == "assistant" else None):
            st.markdown(m["text"])
            if m.get("source"):
                st.markdown(
                    f'<div class="answer-source">Source: {m["source"]}</div>', unsafe_allow_html=True
                )
            if m.get("citations"):
                links = "<br>".join(
                    f'<a href="{c["url"]}" target="_blank" rel="noopener">{c["title"]}</a>'
                    if c.get("url")
                    else c.get("title", "")
                    for c in m["citations"]
                )
                st.markdown(
                    f'<div class="citations"><strong>Sources</strong><br>{links}</div>',
                    unsafe_allow_html=True,
                )

    st.write("")
    cols = st.columns(len(EXAMPLES))
    for col, ex in zip(cols, EXAMPLES):
        if col.button(ex, key=f"ex_{ex}", use_container_width=True):
            st.session_state.pending = ex
            st.rerun()

with trace_col:
    items = (
        "".join(f'<div class="trace-item">{t}</div>' for t in st.session_state.trace)
        if st.session_state.trace
        else '<div class="empty">No request yet.</div>'
    )
    st.markdown(
        f"""
<div class="trace-panel">
<h3>Agent Trace</h3>
<p class="muted">Watch LangGraph decisions while the request runs.</p>
{items}
<div class="source-box"><span>Final Source</span><strong>{st.session_state.source_used}</strong></div>
</div>""",
        unsafe_allow_html=True,
    )