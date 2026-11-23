# AI Work Assistant: two agents that save a professional's time

Two small, practical GenAI agents with a shared design: a thin LLM gateway, Pydantic-validated outputs, and humans kept in the loop.

| Agent | What it does | Key techniques |
|---|---|---|
| **Email Triage Agent** | Reads emails and returns category, priority (1-5), summary, action items, deadline and a draft reply | Structured JSON output, schema validation with retry, prompt-injection defence, human-in-the-loop (drafts only) |
| **Meeting & Task Agent** | Turns meeting notes into tasks and answers questions about your task list | LLM function calling, bounded agent loop, validated tool arguments, SQLite persistence |

## Architecture

```
Streamlit UI (app.py) ─┐
                       ├─> agents/email_agent.py  ─> agents/llm.py (JSON mode + Pydantic validation + retry) ─> OpenAI
FastAPI (api.py)    ───┤
                       └─> agents/task_agent.py   ─> tools ─> agents/task_store.py (SQLite)
```

## Design decisions
- **Validated outputs:** every LLM response is parsed with Pydantic. If it is invalid the error is fed back to the model and it retries (max 2).
- **Safe tools:** tool arguments are validated before anything runs. Bad arguments return an error to the model instead of crashing.
- **Bounded agent loop:** `MAX_AGENT_STEPS` stops runaway loops and cost.
- **Prompt injection:** email and meeting text is treated as data, never as instructions. The sample inbox includes an injection attempt.
- **Human in the loop:** the agents draft and record; they never send emails or delete data.
- **Testable:** the LLM client is injectable, so all tests run offline with a scripted fake model (`pytest`).

## Run it (Windows, Python 3.11)
```
py -3.11 -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env      (then put your OpenAI key in .env)
python -m streamlit run app.py
```
Optional API: `python -m uvicorn api:app --reload` then open http://localhost:8000/docs
Tests: `python -m pytest -q`

## Demo (3 minutes)
1. **Email tab:** Load sample emails, Triage. Show the priority-sorted table, a draft reply, and the injection email being flagged as spam.
2. Click **Add action items to my tasks** on the manager's email.
3. **Task tab:** Use sample meeting notes. Open "Agent actions" to show the tool calls. Then ask "what is due this week?" and "mark task 1 done".

## Limitations / next steps
No real inbox or calendar integration yet (Gmail/Calendar connectors would replace the paste box). Single user, no authentication. Next: evaluation set for triage accuracy, caching, and Docker.
