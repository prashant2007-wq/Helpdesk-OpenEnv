from __future__ import annotations

from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Team(str, Enum):
    IT_SUPPORT = "it_support"
    SECURITY = "security"
    BILLING = "billing"
    HR = "hr"
    DATA = "data"


class Priority(str, Enum):
    P0 = "p0"  # outage / security incident
    P1 = "p1"  # major impact
    P2 = "p2"  # standard
    P3 = "p3"  # low priority


class Ticket(BaseModel):
    ticket_id: str
    subject: str
    body: str
    requester: str
    requester_role: Literal["employee", "contractor", "customer"]
    channel: Literal["email", "chat", "web"]
    created_at_iso: str
    metadata: Dict[str, str] = Field(default_factory=dict)


class Policy(BaseModel):
    no_passwords: bool = True
    no_sensitive_data: bool = True
    require_mfa_for_admin: bool = True
    approved_tools: List[str] = Field(default_factory=lambda: ["Okta", "Google Workspace", "Jira", "Slack"])


class KnowledgeBaseArticle(BaseModel):
    article_id: str
    title: str
    content: str
    tags: List[str] = Field(default_factory=list)


class Observation(BaseModel):
    task_id: str
    step: int
    max_steps: int

    ticket: Ticket
    policy: Policy
    kb_snippets: List[KnowledgeBaseArticle]

    conversation: List[Dict[str, str]] = Field(
        default_factory=list,
        description="A list of {role, content} messages in the ticket thread.",
    )

    allowed_teams: List[Team] = Field(default_factory=lambda: list(Team))
    allowed_priorities: List[Priority] = Field(default_factory=lambda: list(Priority))


class Action(BaseModel):
    ask_clarifying_question: Optional[str] = Field(
        default=None,
        description="Ask the requester a concise clarifying question (one per step).",
    )
    set_priority: Optional[Priority] = None
    route_to_team: Optional[Team] = None
    draft_reply: Optional[str] = Field(default=None, description="A short, policy-compliant reply.")
    submit: bool = Field(default=False, description="Submit your final decision for grading.")


class Reward(BaseModel):
    reward: float
    done: bool
    info: Dict[str, str] = Field(default_factory=dict)


class EnvState(BaseModel):
    task_id: str
    step: int
    max_steps: int
    ticket: Ticket
    policy: Policy
    kb_snippets: List[KnowledgeBaseArticle]
    conversation: List[Dict[str, str]]

    chosen_priority: Optional[Priority] = None
    chosen_team: Optional[Team] = None
    draft_reply: Optional[str] = None

    asked_questions: List[str] = Field(default_factory=list)
    submitted: bool = False
 
