"""Tests run without an API key: a scripted fake client stands in for the LLM."""
import json
from types import SimpleNamespace

import pytest

import config
from agents import email_agent
from agents.llm import structured_call
from agents.schemas import EmailTriage
from agents.task_agent import execute_tool, run_agent
from agents.task_store import TaskStore


class FakeClient:
    """Returns scripted responses in order, like client.chat.completions.create()."""

    def __init__(self, scripted):
        self.scripted = list(scripted)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        return self.scripted.pop(0)


def text_resp(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=None))])


def tool_resp(name, args, call_id="call_1"):
    tc = SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=json.dumps(args)))
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[tc]))])


VALID = {"category": "action_required", "priority": 4, "summary": "Send deck.", "action_items": ["Send deck"],
         "deadline": "2026-11-26", "needs_reply": True, "draft_reply": "Will do."}


@pytest.fixture
def store(tmp_path):
    return TaskStore(str(tmp_path / "t.db"))


def test_structured_call_retries_after_invalid_output():
    client = FakeClient([text_resp("not json"), text_resp(json.dumps(VALID))])
    result = structured_call("sys", "user", EmailTriage, client=client)
    assert result.priority == 4 and client.scripted == []


def test_structured_call_gives_up_after_retries():
    client = FakeClient([text_resp("bad")] * 3)
    with pytest.raises(ValueError):
        structured_call("sys", "user", EmailTriage, client=client, max_retries=2)


def test_priority_out_of_range_is_rejected_then_fixed():
    bad = dict(VALID, priority=9)
    client = FakeClient([text_resp(json.dumps(bad)), text_resp(json.dumps(VALID))])
    assert structured_call("s", "u", EmailTriage, client=client).priority == 4


def test_triage_many_sorts_by_priority():
    low = dict(VALID, priority=1, needs_reply=False, draft_reply=None)
    client = FakeClient([text_resp(json.dumps(low)), text_resp(json.dumps(VALID))])
    results = email_agent.triage_many(["email a", "email b"], client=client)
    assert [r.priority for _, r in results] == [4, 1]


def test_split_emails_and_title():
    parts = email_agent.split_emails("Subject: A\nbody\n---\nSubject: B\nbody")
    assert len(parts) == 2 and email_agent.email_title(parts[1]) == "B"


def test_agent_calls_tool_and_stores_task(store):
    client = FakeClient([
        tool_resp("add_task", {"title": "Fix login bug", "owner": "Rahul", "due_date": "2026-12-01", "priority": "high"}),
        text_resp("Created 1 task."),
    ])
    res = run_agent("notes...", store, client=client)
    tasks = store.list("all")
    assert res.reply == "Created 1 task." and len(res.tool_log) == 1
    assert tasks[0]["title"] == "Fix login bug" and tasks[0]["owner"] == "Rahul"


def test_invalid_tool_arguments_return_error_not_crash(store):
    out = json.loads(execute_tool("add_task", json.dumps({"title": "x", "due_date": "next friday"}), store))
    assert "error" in out and store.list("all") == []


def test_unknown_tool_and_missing_task(store):
    assert "error" in json.loads(execute_tool("delete_everything", "{}", store))
    assert "error" in json.loads(execute_tool("complete_task", json.dumps({"task_id": 99}), store))


def test_complete_task_flow(store):
    t = store.add("Write report")
    assert json.loads(execute_tool("complete_task", json.dumps({"task_id": t["id"]}), store)) == {"completed": t["id"]}
    assert store.list("open") == []


def test_agent_stops_after_max_steps(store, monkeypatch):
    monkeypatch.setattr(config, "MAX_AGENT_STEPS", 3)
    client = FakeClient([tool_resp("list_tasks", {}, f"c{i}") for i in range(3)])
    res = run_agent("loop forever", store, client=client)
    assert "too many steps" in res.reply and len(res.tool_log) == 3
