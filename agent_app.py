"""
AI Ticketing System — Agent Console (Streamlit)
HelpDesk-style ticket list UI.
"""

import hashlib

import requests
import streamlit as st

BASE = "https://laszloboruzs222.app.n8n.cloud/webhook"
QUEUE_URL = st.secrets.get("QUEUE_URL", f"{BASE}/agent-queue")
DETAIL_URL = st.secrets.get("DETAIL_URL", f"{BASE}/agent-detail")
ANSWER_URL = st.secrets.get("ANSWER_URL", f"{BASE}/agent-answer")
API_TOKEN = st.secrets.get("API_TOKEN", "")

HEADERS = {"X-API-Token": API_TOKEN}

st.set_page_config(page_title="Agent Console", page_icon="🎫", layout="wide")

# ----------------------------------------------------------------------------
# Styling
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
      .block-container { padding-top: 2rem; }
      .ticket-head {
        display: grid;
        grid-template-columns: 2.6fr 3fr 1.1fr 1fr;
        gap: 12px;
        padding: 8px 14px;
        font-size: 0.72rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #8a93a3;
        border-bottom: 1px solid #e6e9ef;
      }
      .req-cell { display: flex; align-items: center; gap: 10px; }
      .avatar {
        width: 34px; height: 34px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        color: #fff; font-weight: 600; font-size: 0.8rem; flex: 0 0 34px;
      }
      .req-name { font-weight: 600; font-size: 0.88rem; line-height: 1.15;
        word-break: break-all; }
      .req-key { font-size: 0.74rem; color: #8a93a3; }
      .subject { font-size: 0.92rem; color: #1f2733; }
      .badge {
        display: inline-block; padding: 3px 10px; border-radius: 12px;
        font-size: 0.72rem; font-weight: 600;
      }
      .b-open   { background: #e7f0ff; color: #2563eb; }
      .b-done   { background: #e7f7ed; color: #1a9d54; }
      .b-prog   { background: #fff4e5; color: #d97706; }
      .prio-high { color: #e0352b; font-weight: 700; }
      .prio-med  { color: #8a93a3; }
    </style>
    """,
    unsafe_allow_html=True,
)


def post(url, body=None):
    resp = requests.post(url, json=body or {}, headers=HEADERS, timeout=180)
    if resp.status_code == 401:
        raise PermissionError("Unauthorized — check your API_TOKEN secret.")
    resp.raise_for_status()
    try:
        return resp.json()
    except ValueError:
        return {}


_PALETTE = ["#6366f1", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444",
            "#8b5cf6", "#ec4899", "#14b8a6", "#f97316", "#3b82f6"]


def requester_label(ticket):
    """Always prefer the reporter email; never show 'Unknown' if we have one."""
    return (
        ticket.get("reporter")
        or ticket.get("reporterEmail")
        or ticket.get("email")
        or "No email on ticket"
    )


def avatar_html(label):
    label = (label or "?").strip() or "?"
    # initials from an email/name
    base = label.split("@")[0] if "@" in label else label
    parts = [p for p in base.replace(".", " ").replace("_", " ").split() if p]
    if parts:
        initials = (parts[0][0] + (parts[1][0] if len(parts) > 1 else "")).upper()
    else:
        initials = label[0].upper()
    color = _PALETTE[int(hashlib.md5(label.encode()).hexdigest(), 16) % len(_PALETTE)]
    return f'<div class="avatar" style="background:{color}">{initials}</div>'


def status_badge(status):
    s = (status or "").lower()
    if "done" in s or "solved" in s or "closed" in s:
        return f'<span class="badge b-done">{status or "Done"}</span>'
    if "progress" in s or "pending" in s:
        return f'<span class="badge b-prog">{status}</span>'
    return f'<span class="badge b-open">{status or "To Do"}</span>'


def prio_marker(priority):
    if (priority or "").lower() == "high":
        return '<span class="prio-high">↑ HIGH</span>'
    return '<span class="prio-med">•</span>'


# ----------------------------------------------------------------------------
# State
# ----------------------------------------------------------------------------
if "tickets" not in st.session_state:
    st.session_state.tickets = []
if "selected" not in st.session_state:
    st.session_state.selected = None
if "detail" not in st.session_state:
    st.session_state.detail = None
if "loaded" not in st.session_state:
    st.session_state.loaded = False


def load_queue():
    data = post(QUEUE_URL)
    st.session_state.tickets = data.get("tickets", [])
    st.session_state.selected = None
    st.session_state.detail = None
    st.session_state.loaded = True


# ----------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------
top_l, top_r = st.columns([3, 1])
with top_l:
    st.title("🎫 Agent Console")
with top_r:
    st.write("")
    if st.button("🔄 Refresh", use_container_width=True):
        try:
            load_queue()
        except Exception as exc:
            st.error(f"Could not load the queue: {exc}")

if not API_TOKEN:
    st.warning(
        "No API_TOKEN configured. Add it under App settings → Secrets "
        "(it must match the token set in the n8n workflows)."
    )

if not st.session_state.loaded:
    try:
        load_queue()
    except Exception as exc:
        st.error(f"Could not load the queue: {exc}")

tickets = st.session_state.tickets

# ----------------------------------------------------------------------------
# Detail view
# ----------------------------------------------------------------------------
if st.session_state.selected:
    selected = st.session_state.selected
    if st.button("← Back to all tickets"):
        st.session_state.selected = None
        st.session_state.detail = None
        st.rerun()

    if st.session_state.detail is None:
        with st.spinner("Loading reference context..."):
            try:
                st.session_state.detail = post(DETAIL_URL, {"ticketKey": selected})
            except Exception as exc:
                st.error(f"Could not load ticket detail: {exc}")
                st.stop()

    detail = st.session_state.detail or {}

    st.markdown(f"### {selected}")
    head_bits = []
    if detail.get("priority") == "high":
        head_bits.append('<span class="prio-high">🔴 HIGH PRIORITY</span>')
    head_bits.append(status_badge(detail.get("status", "To Do")))
    st.markdown(" &nbsp; ".join(head_bits), unsafe_allow_html=True)

    if detail.get("summary"):
        st.markdown(f"**{detail['summary']}**")

    requester = requester_label(detail)
    st.caption(f"Requester: {requester}")

    if detail.get("description"):
        with st.expander("📝 Ticket description", expanded=True):
            st.text(detail["description"])

    with st.expander("📚 Similar past tickets (reference)", expanded=True):
        st.text(detail.get("historical_context", "—"))

    with st.expander("👤 This reporter's previous tickets", expanded=True):
        st.text(detail.get("reporter_history", "—"))

    st.divider()
    reply = st.text_area("Your reply to the customer", height=200, key="reply_box")
    if st.button("✅ Send reply & close ticket", type="primary"):
        if not reply.strip():
            st.error("Please write a reply first.")
        else:
            with st.spinner("Posting reply, closing ticket, emailing customer..."):
                try:
                    res = post(ANSWER_URL, {"ticketKey": selected, "reply": reply.strip()})
                    if res.get("ok"):
                        st.success(
                            f"Reply posted to {selected}, issue moved to Done, "
                            "and the customer was emailed."
                        )
                        st.session_state.tickets = [
                            t for t in st.session_state.tickets
                            if t.get("key") != selected
                        ]
                        st.session_state.selected = None
                        st.session_state.detail = None
                        st.rerun()
                    else:
                        st.error(
                            f"The answer endpoint returned an error: "
                            f"{res.get('error', 'unknown error')}"
                        )
                except Exception as exc:
                    st.error(f"Could not send the reply: {exc}")
    st.stop()

# ----------------------------------------------------------------------------
# List view
# ----------------------------------------------------------------------------
st.caption("High-priority tickets that need a human agent.")
st.markdown(f"**{len(tickets)} tickets**")

if not tickets:
    st.info("No high-priority tickets in the queue right now. Click **Refresh** to check again.")
    st.stop()

st.markdown(
    '<div class="ticket-head">'
    '<div>Requester</div><div>Subject</div><div>Status</div><div>Priority</div>'
    '</div>',
    unsafe_allow_html=True,
)

for t in tickets:
    key = t.get("key", "")
    requester = requester_label(t)
    summary = t.get("summary", "(no subject)")
    status = t.get("status", "To Do")
    priority = t.get("priority", "")

    row = st.columns([2.6, 3, 1.1, 1, 0.8])
    with row[0]:
        st.markdown(
            f'<div class="req-cell">{avatar_html(requester)}'
            f'<div><div class="req-name">{requester}</div>'
            f'<div class="req-key">{key}</div></div></div>',
            unsafe_allow_html=True,
        )
    with row[1]:
        st.markdown(f'<div class="subject">{summary}</div>', unsafe_allow_html=True)
    with row[2]:
        st.markdown(status_badge(status), unsafe_allow_html=True)
    with row[3]:
        st.markdown(prio_marker(priority), unsafe_allow_html=True)
    with row[4]:
        if st.button("Open", key=f"open_{key}", use_container_width=True):
            st.session_state.selected = key
            st.session_state.detail = None
            st.rerun()