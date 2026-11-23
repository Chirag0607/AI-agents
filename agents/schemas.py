"""Pydantic models: the contracts between the LLM and the application."""
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


class Category(str, Enum):
    urgent = "urgent"
    action_required = "action_required"
    meeting = "meeting"
    fyi = "fyi"
    newsletter = "newsletter"
    spam = "spam"


class EmailTriage(BaseModel):
    category: Category
    priority: int = Field(ge=1, le=5, description="1 = lowest, 5 = needs action today")
    summary: str = Field(max_length=300)
    action_items: list[str] = Field(default_factory=list)
    deadline: Optional[str] = Field(default=None, pattern=DATE_PATTERN, description="YYYY-MM-DD or null")
    needs_reply: bool
    draft_reply: Optional[str] = None


class AddTaskArgs(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    owner: str = "me"
    due_date: Optional[str] = Field(default=None, pattern=DATE_PATTERN)
    priority: Literal["low", "medium", "high"] = "medium"

    @field_validator("due_date", mode="before")
    @classmethod
    def empty_to_none(cls, v):
        return v or None


class ListTasksArgs(BaseModel):
    status: Literal["open", "done", "all"] = "open"
    owner: Optional[str] = None

    @field_validator("owner", mode="before")
    @classmethod
    def empty_owner(cls, v):
        return v or None


class CompleteTaskArgs(BaseModel):
    task_id: int
