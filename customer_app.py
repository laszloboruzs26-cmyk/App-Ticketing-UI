"""
AI Ticketing System — Customer Intake (Streamlit)

A simple customer-facing form that submits a support ticket to the n8n
Intake API webhook. The n8n workflow generates the ticket ID, creates a
Jira issue, runs the AI triage/RAG pipeline, and emails the customer.

Run locally:
    pip install -r requirements.txt
    streamlit run customer_app.py
"""

import requests
import streamlit as st

# --- Configuration -------------------------------------------------------
INTAKE_URL = st.secrets.get(
    "INTAKE_URL",
    "https://laszloboruzs222.app.n8n.cloud/webhook/ticket",
)

st.set_page_config(page_title="Support — Submit a Ticket", page_icon="🎫")

st.title("Submit a Support Ticket")
st.caption(
    "Tell us what's going on and we'll get back to you by email. "
    "A ticket reference is generated automatically."
)

with st.form("intake", clear_on_submit=False):
    subject = st.text_input("Subject *", placeholder="Short summary of the issue")
    description = st.text_area(
        "Description *",
        placeholder="Describe the problem in as much detail as you can.",
        height=180,
    )
    order_number = st.text_input("Order number *", placeholder="e.g. ORD-12345")
    reporter = st.text_input("Your email *", placeholder="you@example.com")
    priority = st.selectbox("Priority", ["Low", "Medium", "High"], index=1)

    submitted = st.form_submit_button("Submit ticket")

if submitted:
    missing = []
    if not subject.strip():
        missing.append("Subject")
    if not description.strip():
        missing.append("Description")
    if not order_number.strip():
        missing.append("Order number")
    if not reporter.strip():
        missing.append("Your email")

    if missing:
        st.error("Please fill in: " + ", ".join(missing))
    else:
        payload = {
            "subject": subject.strip(),
            "description": description.strip(),
            "orderNumber": order_number.strip(),
            "reporter": reporter.strip(),
            "priority": priority,
        }
        with st.spinner("Submitting your ticket..."):
            try:
                resp = requests.post(INTAKE_URL, json=payload, timeout=120)
                resp.raise_for_status()
                try:
                    data = resp.json()
                except ValueError:
                    data = {}

                ticket_id = (
                    data.get("ticketId")
                    or data.get("ticketKey")
                    or data.get("key")
                    or ""
                )
                st.success("Your ticket has been submitted.")
                if ticket_id:
                    st.info(f"Your ticket reference is **{ticket_id}**.")
                st.write(
                    "We've emailed a confirmation to "
                    f"**{reporter.strip()}**. Our team will follow up there."
                )
                if data:
                    with st.expander("Response details"):
                        st.json(data)
            except requests.exceptions.RequestException as exc:
                st.error(
                    "Sorry — we couldn't submit your ticket right now. "
                    "Please try again in a moment."
                )
                st.caption(f"Technical detail: {exc}")