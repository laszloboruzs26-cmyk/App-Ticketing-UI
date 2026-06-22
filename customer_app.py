"""
AI Ticketing System — Customer Intake (Streamlit)
"""

import requests
import streamlit as st

BASE = "https://laszloboruzs222.app.n8n.cloud/webhook"
INTAKE_URL = st.secrets.get("INTAKE_URL", f"{BASE}/ticket-api")
API_TOKEN = st.secrets.get("API_TOKEN", "")

HEADERS = {"X-API-Token": API_TOKEN}

st.set_page_config(page_title="Submit a Ticket", page_icon="🎫", layout="centered")


def post(url, body):
    resp = requests.post(url, json=body, headers=HEADERS, timeout=180)
    if resp.status_code == 401:
        raise PermissionError("Unauthorized — check your API_TOKEN secret.")
    resp.raise_for_status()
    try:
        return resp.json()
    except ValueError:
        return {}


st.title("🎫 Submit a Support Ticket")
st.caption(
    "Tell us what's going on and we'll get back to you by email. "
    "A ticket reference is generated automatically."
)

if not API_TOKEN:
    st.warning(
        "No API_TOKEN configured. Add it under App settings -> Secrets "
        "(it must match the token set in the n8n workflows)."
    )

with st.form("ticket_form", clear_on_submit=True):
    subject = st.text_input("Subject *")
    description = st.text_area("Description *", height=200)
    order_number = st.text_input("Order number *", placeholder="e.g. ORD-12345")
    email = st.text_input("Your email *")
    submitted = st.form_submit_button("Submit ticket")

if submitted:
    if not (subject.strip() and description.strip() and order_number.strip() and email.strip()):
        st.error("Please fill in all fields.")
    else:
        payload = {
            "subject": subject.strip(),
            "description": description.strip(),
            "orderNumber": order_number.strip(),
            "reporterEmail": email.strip(),
        }
        with st.spinner("Submitting your ticket..."):
            try:
                res = post(INTAKE_URL, payload)
                ref = res.get("ticketId", "")
                if ref:
                    st.success(f"Your ticket has been submitted. Reference: {ref}")
                else:
                    st.success("Your ticket has been submitted.")
            except Exception as exc:
                st.error(f"Could not submit your ticket: {exc}")
