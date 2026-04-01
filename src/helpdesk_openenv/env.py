from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from pydantic import TypeAdapter

from .graders import grade
from .models import Action, EnvState, Observation, Reward
from .tasks import get_task
 
 
class HelpdeskEnv:
    """
    OpenEnv-style environment.

    API:
      - reset(task_id=...) -> Observation
      - step(action=Action | dict) -> (Observation, Reward)
      - state() -> EnvState

    Notes:
      - Deterministic tasks and graders for reproducible baseline scores.
      - Reward is dense (partial credit) and aligned with final graders.
    """

    def __init__(self, task_id: str = "triage_easy", max_steps: int = 6):
        self._default_task_id = task_id
        self._default_max_steps = max_steps
        self._task = None
        self._state: Optional[EnvState] = None

    def reset(self, task_id: Optional[str] = None, *, max_steps: Optional[int] = None) -> Observation:
        task_id = task_id or self._default_task_id
        task = get_task(task_id)
        max_steps = int(max_steps if max_steps is not None else self._default_max_steps)
        max_steps = max(2, max_steps)

        ticket = task.build_ticket()
        self._task = task
        self._state = EnvState(
            task_id=task.task_id,
            step=0,
            max_steps=max_steps,
            ticket=ticket,
            policy=task.build_policy(),
            kb_snippets=task.build_kb(),
            conversation=[{"role": "requester", "content": f"Subject: {ticket.subject}\n\n{ticket.body}"}],
        )
        return self._obs()

    def state(self) -> EnvState:
        if self._state is None:
            raise RuntimeError("Call reset() before state().")
        return self._state

    def step(self, action: Action | Dict[str, Any]) -> Tuple[Observation, Reward]:
        if self._state is None or self._task is None:
            raise RuntimeError("Call reset() before step().")

        a = action if isinstance(action, Action) else TypeAdapter(Action).validate_python(action)
        s = self._state

        if s.submitted:
            res = grade(self._task, s)
            return self._obs(), Reward(reward=0.0, done=True, info={"final_score": str(res.score)})

        info: Dict[str, str] = {}

        if a.ask_clarifying_question:
            q = a.ask_clarifying_question.strip()
            if q:
                s.asked_questions.append(q)
                s.conversation.append({"role": "agent", "content": q})
                if self._task.task_id == "triage_medium" and len(s.asked_questions) == 1:
                    s.conversation.append(
                        {
                            "role": "requester",
                            "content": "It popped up around 9am. I did not approve any MFA prompt. I'm on macOS.",
                        }
                    )

        if a.set_priority is not None:
            s.chosen_priority = a.set_priority
        if a.route_to_team is not None:
            s.chosen_team = a.route_to_team
        if a.draft_reply is not None:
            s.draft_reply = a.draft_reply.strip() if a.draft_reply else ""

        s.step += 1

        shaped = 0.0
        if s.chosen_team is not None:
            shaped += 0.05
        if s.chosen_priority is not None:
            shaped += 0.05
        if a.ask_clarifying_question and self._task.min_questions > 0:
            shaped += 0.05
        if s.draft_reply and self._task.task_id == "triage_hard":
            shaped += 0.05
        shaped -= 0.01

        done = False
        if a.submit or s.step >= s.max_steps:
            s.submitted = True
            done = True
            res = grade(self._task, s)
            shaped += res.score
            info["final_score"] = str(res.score)

        shaped = float(max(-1.0, min(1.0, shaped)))
        return self._obs(), Reward(reward=shaped, done=done, info=info)

    def _obs(self) -> Observation:
        if self._state is None or self._task is None:
            raise RuntimeError("Call reset() first.")
        s = self._state
        return Observation(
            task_id=s.task_id,
            step=s.step,
            max_steps=s.max_steps,
            ticket=s.ticket,
            policy=s.policy,
            kb_snippets=s.kb_snippets,
            conversation=list(s.conversation),
        )
 
