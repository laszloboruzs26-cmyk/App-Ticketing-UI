"""
AI Ticketing System — Agent Console (Streamlit)
"""

import requests
import streamlit as st

BASE = "https://laszloboruzs222.app.n8n.cloud/webhook"
QUEUE_URL = st.secrets.get("QUEUE_URL", f"{BASE}/agent-queue")
DETAIL_URL = st.secrets.get("DETAIL_URL", f"{BASE}/agent-detail")
ANSWER_URL = st.secrets.get("ANSWER_URL", f"{BASE}/agent-answer")
API_TOKEN = st.secrets.get("API_TOKEN", "")

HEADERS = {"X-API-Token": API_TOKEN}

st.set_page_config(page_title="Agent Console", page_icon="🛠️", layout="wide")


def post(url, body=None):
    resp = requests.post(url, json=body or {}, headers=HEADERS, timeout=180)
    if resp.status_code == 401:
        raise PermissionError("Unauthorized — check your API_TOKEN secret.")
    resp.raise_for_status()
    try:
        return resp.json()
    except ValueError:
        return {}


if "tickets" not in st.session_state:
    st.session_state.tickets = []
if "selected" not in st.session_state:
    st.session_state.selected = None
if "detail" not in st.session_state:
    st.session_state.detail = None

st.title("🛠️ Agent Console")

if not API_TOKEN:
    st.warning(
        "No API_TOKEN configured. Add it under App settings -> Secrets "
        "(it must match the token set in the n8n workflows)."
    )

col_refresh, _ = st.columns([1, 4])
with col_refresh:
    if st.button("🔄 Load / refresh queue", use_container_width=True):
        try:
            data = post(QUEUE_URL)
            st.session_state.tickets = data.get("tickets", [])
            st.session_state.selected = None
            st.session_state.detail = None
        except Exception as exc:
            st.error(f"Could not load the queue: {exc}")

tickets = st.session_state.tickets

if not tickets:
    st.info("No open tickets loaded. Click **Load / refresh queue** above.")
    st.stop()

left, right = st.columns([1, 2])

with left:
    st.subheader(f"Open tickets ({len(tickets)})")
    for t in tickets:
        key = t.get("key", "")
        label = f"{key} — {t.get('summary', '')}"
        if st.button(label, key=f"sel_{key}", use_container_width=True):
            st.session_state.selected = key
            st.session_state.detail = None
        st.caption(f"{t.get('status', '')} · {t.get('created', '')}")

with right:
    selected = st.session_state.selected
    if not selected:
        st.info("Select a ticket on the left to view reference context and reply.")
        st.stop()

    st.subheader(f"Ticket {selected}")

    if st.session_state.detail is None:
        with st.spinner("Loading reference context..."):
            try:
                st.session_state.detail = post(DETAIL_URL, {"ticketKey": selected})
            except Exception as exc:
                st.error(f"Could not load ticket detail: {exc}")
                st.stop()

    detail = st.session_state.detail or {}

    if detail.get("summary"):
        st.markdown(f"**{detail['summary']}**")

    if detail.get("description"):
        with st.expander("📝 Ticket description", expanded=True):
            st.text(detail["description"])
    else:
        st.caption("No ticket description available.")

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