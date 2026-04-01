from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Dict, Tuple

from .models import EnvState, Priority
from .tasks import TaskSpec


def _norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


@dataclass(frozen=True)
class GradeResult:
    score: float  # 0.0..1.0
    breakdown: Dict[str, float]
    notes: Dict[str, str]


def grade(task: TaskSpec, state: EnvState) -> GradeResult:
    breakdown: Dict[str, float] = {}
    notes: Dict[str, str] = {}

    team_score = 1.0 if state.chosen_team == task.target_team else 0.0
    breakdown["route_to_team"] = team_score
    notes["target_team"] = task.target_team.value
    notes["chosen_team"] = state.chosen_team.value if state.chosen_team else "none"

    pri_score = 0.0
    if state.chosen_priority is None:
        pri_score = 0.0
    elif state.chosen_priority == task.target_priority:
        pri_score = 1.0
    else:
        order = [Priority.P0, Priority.P1, Priority.P2, Priority.P3]
        di = abs(order.index(state.chosen_priority) - order.index(task.target_priority))
        pri_score = max(0.0, 1.0 - 0.5 * di)
    breakdown["set_priority"] = pri_score
    notes["target_priority"] = task.target_priority.value
    notes["chosen_priority"] = state.chosen_priority.value if state.chosen_priority else "none"

    q_score = 1.0
    if task.min_questions > 0:
        asked = len(state.asked_questions)
        q_score = min(1.0, asked / float(task.min_questions))
        notes["questions_asked"] = str(asked)
        notes["min_questions"] = str(task.min_questions)
    breakdown["clarifying_questions"] = q_score

    reply_score = 1.0
    if task.reply_must_include or task.reply_must_not_include:
        reply = _norm_text(state.draft_reply or "")
        if not reply:
            reply_score = 0.0
        else:
            must_hits = sum(1 for phrase in task.reply_must_include if _norm_text(phrase) in reply)
            must_score = must_hits / max(1, len(task.reply_must_include))

            violates = sum(1 for phrase in task.reply_must_not_include if _norm_text(phrase) in reply)
            violation_penalty = 0.5**violates
            reply_score = must_score * violation_penalty
    breakdown["draft_reply"] = reply_score

    if task.task_id == "triage_hard":
        weights: Tuple[Tuple[str, float], ...] = (
            ("route_to_team", 0.35),
            ("set_priority", 0.25),
            ("draft_reply", 0.35),
            ("clarifying_questions", 0.05),
        )
    else:
        weights = (
            ("route_to_team", 0.5),
            ("set_priority", 0.35),
            ("clarifying_questions", 0.15),
        )

    score = 0.0
    for k, w in weights:
        score += breakdown.get(k, 0.0) * w

    score = float(max(0.0, min(1.0, score)))
    score = float(math.floor(score * 10000) / 10000.0)
    return GradeResult(score=score, breakdown=breakdown, notes=notes)
 
