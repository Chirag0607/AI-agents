"""Streamlit UI: two agents in one app. Run with: streamlit run app.py"""
from pathlib import Path

import pandas as pd
import streamlit as st

import config
from agents.email_agent import email_title, split_emails, triage_many
from agents.task_agent import run_agent
from agents.task_store import TaskStore

st.set_page_config(page_title="AI Work Assistant", page_icon="🤖", layout="wide")
st.title("🤖 AI Work Assistant")
st.caption("Two small agents that save a professional's time: email triage and meeting-to-tasks.")

store = TaskStore()


def read_sample(name: str) -> str:
    p = Path("samples") / name
    return p.read_text(encoding="utf-8") if p.exists() else ""


with st.sidebar:
    st.subheader("About")
    st.write(f"Model: `{config.LLM_MODEL}`")
    st.write("Agents only **draft** and **record**. Nothing is sent or deleted without you.")
    if st.button("Clear all tasks", use_container_width=True):
        store.clear()
        st.rerun()

tab_email, tab_tasks = st.tabs(["📧 Email Triage Agent", "✅ Meeting & Task Agent"])

# ---------------------------------------------------------------- Agent 1
with tab_email:
    st.write("Paste one or more emails (separate emails with a line containing only `---`).")
    if st.button("Load sample emails"):
        st.session_state.emails_text = read_sample("emails.txt")
    text = st.text_area("Emails", key="emails_text", height=260, label_visibility="collapsed")
    c1, c2 = st.columns(2)
    role = c1.text_input("Your role", value="software engineer")
    tone = c2.text_input("Reply tone", value="professional and concise")

    if st.button("Triage emails", type="primary", disabled=not text.strip()):
        try:
            with st.spinner("Reading and prioritising..."):
                st.session_state.triage = triage_many(split_emails(text), role, tone)
        except Exception as e:  # show a clear message instead of a stack trace
            st.error(str(e))

    results = st.session_state.get("triage")
    if results:
        st.subheader("Inbox by priority")
        df = pd.DataFrame(
            [
                {
                    "Priority": r.priority,
                    "Category": r.category.value,
                    "Email": email_title(e),
                    "Summary": r.summary,
                    "Reply needed": r.needs_reply,
                    "Deadline": r.deadline or "",
                }
                for e, r in results
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)

        for i, (e, r) in enumerate(results):
            with st.expander(f"P{r.priority} · {r.category.value} · {email_title(e)}"):
                st.write(r.summary)
                if r.action_items:
                    st.markdown("**Action items**")
                    for item in r.action_items:
                        st.write(f"- {item}")
                    if st.button("Add action items to my tasks", key=f"add_{i}"):
                        for item in r.action_items:
                            store.add(item, due_date=r.deadline, priority="high" if r.priority >= 4 else "medium", source="email")
                        st.success("Added to your task list (see the other tab).")
                if r.draft_reply:
                    st.markdown("**Draft reply (review before sending)**")
                    st.text_area("Draft", r.draft_reply, height=150, key=f"draft_{i}", label_visibility="collapsed")

# ---------------------------------------------------------------- Agent 2
with tab_tasks:
    left, right = st.columns([3, 2])
    if "chat" not in st.session_state:
        st.session_state.chat = []
        st.session_state.agent_history = []

    with left:
        st.write("Paste meeting notes, or ask things like *what is due this week?* or *mark task 2 done*.")
        if st.button("Use sample meeting notes"):
            st.session_state.queued = "Here are my meeting notes. Create the tasks:\n\n" + read_sample("meeting_notes.txt")
        for m in st.session_state.chat:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
                if m.get("tools"):
                    with st.expander(f"Agent actions ({len(m['tools'])})"):
                        for t in m["tools"]:
                            st.code(f"{t['tool']}({t['arguments']})\n-> {t['result']}", language="text")

        prompt = st.chat_input("Message the task agent") or st.session_state.pop("queued", None)
        if prompt:
            st.session_state.chat.append({"role": "user", "content": prompt})
            try:
                with st.spinner("Working..."):
                    res = run_agent(prompt, store, st.session_state.agent_history)
                st.session_state.agent_history = res.history
                st.session_state.chat.append({"role": "assistant", "content": res.reply, "tools": res.tool_log})
            except Exception as e:
                st.session_state.chat.append({"role": "assistant", "content": f"Error: {e}"})
            st.rerun()

    with right:
        st.subheader("Task list")
        tasks = store.list("all")
        if tasks:
            st.dataframe(
                pd.DataFrame(tasks)[["id", "title", "owner", "due_date", "priority", "status", "source"]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No tasks yet.")
