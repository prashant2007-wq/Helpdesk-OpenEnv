#!/usr/bin/env python3
"""
Inference script for Helpdesk OpenEnv.

Runs a simple baseline agent across all tasks using OpenAI Client.
Respects API_BASE_URL, MODEL_NAME, and HF_TOKEN environment variables.

Runtime: < 20 min on vcpu=2, memory=8gb.
"""

from __future__ import annotations

import json
import os
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from openai import OpenAI
from pydantic import TypeAdapter

_SRC_DIR = Path(__file__).resolve().parent / "src"
if _SRC_DIR.exists():
    sys.path.insert(0, str(_SRC_DIR))

from helpdesk_openenv.env import HelpdeskEnv
from helpdesk_openenv.models import Action


@dataclass(frozen=True)
class RunResult:
    task_id: str
    final_score: float
    steps: int


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)


def _system_prompt() -> str:
    return (
        "You are an AI agent operating an IT helpdesk environment. "
        "You must output ONLY valid JSON for an Action object.\n\n"
        "Action schema:\n"
        "{\n"
        '  "ask_clarifying_question": string|null,\n'
        '  "set_priority": "p0"|"p1"|"p2"|"p3"|null,\n'
        '  "route_to_team": "it_support"|"security"|"billing"|"hr"|"data"|null,\n'
        '  "draft_reply": string|null,\n'
        '  "submit": boolean\n'
        "}\n\n"
        "Guidelines:\n"
        "- Prefer asking at most one clarifying question when needed.\n"
        "- Set priority and route_to_team once you're confident.\n"
        "- For hard tasks: be policy-compliant, do NOT repeat passwords or request sensitive data.\n"
        "- Submit when ready.\n"
    )


def _obs_to_prompt(obs: Dict[str, Any]) -> str:
    kb = "\n\n".join([f"- {a['title']}: {a['content']}" for a in obs.get("kb_snippets", [])])
    convo = "\n\n".join([f"{m['role'].upper()}: {m['content']}" for m in obs.get("conversation", [])])
    policy = obs.get("policy", {})
    return (
        f"Task: {obs['task_id']}\n"
        f"Step: {obs['step']} / {obs['max_steps']}\n\n"
        f"Policy:\n{json.dumps(policy, sort_keys=True)}\n\n"
        f"KB snippets:\n{kb}\n\n"
        f"Conversation:\n{convo}\n\n"
        "Return the next Action as JSON only."
    )


def _call_model(client: OpenAI, model: str, prompt: str) -> str:
    resp = client.chat.completions.create(
        model=model,
        temperature=0.0,
        messages=[
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content or ""


def _parse_action(text: str) -> Action:
    text = text.strip()
    # Best-effort: if model wraps JSON in markdown fences, strip them deterministically.
    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("json", "", 1).strip()
    data = json.loads(text)
    return TypeAdapter(Action).validate_python(data)


def run_task(client: OpenAI, model: str, task_id: str, seed: int = 7) -> RunResult:
    _seed_everything(seed)
    env = HelpdeskEnv()
    obs = env.reset(task_id=task_id)

    final_score: Optional[float] = None
    steps = 0

    while True:
        print(json.dumps({"event": "STEP", "task_id": task_id, "step": steps}, sort_keys=True))
        prompt = _obs_to_prompt(obs.model_dump())
        raw = _call_model(client, model, prompt)
        action = _parse_action(raw)
        obs, rew = env.step(action)
        steps += 1

        if rew.done:
            final_score = float(rew.info.get("final_score", "0.0"))
            break

        if steps > 32:
            # Safety stop; shouldn't happen.
            obs, rew = env.step(Action(submit=True))
            final_score = float(rew.info.get("final_score", "0.0"))
            break

    return RunResult(task_id=task_id, final_score=final_score or 0.0, steps=steps)


def main() -> None:
    # Load environment variables
    api_base_url = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
    model_name = os.environ.get("MODEL_NAME", "gpt-4o-mini")
    hf_token = os.environ.get("HF_TOKEN")
    
    # Get API key (support both OPENAI_API_KEY and HF_TOKEN as fallback)
    api_key = os.environ.get("OPENAI_API_KEY") or hf_token
    if not api_key:
        raise RuntimeError(
            "Missing API credentials. Please set either OPENAI_API_KEY or HF_TOKEN environment variable."
        )

    print(json.dumps({"event": "START", "api_base_url": api_base_url, "model": model_name}, sort_keys=True))

    # Initialize OpenAI client with custom base URL if provided
    client = OpenAI(api_key=api_key, base_url=api_base_url)

    tasks = ["triage_easy", "triage_medium", "triage_hard"]
    results = [run_task(client, model_name, t) for t in tasks]

    out = {
        "model": model_name,
        "api_base_url": api_base_url,
        "results": [
            {"task_id": r.task_id, "final_score": r.final_score, "steps": r.steps} for r in results
        ],
        "mean_score": float(np.mean([r.final_score for r in results])),
    }
    print(json.dumps({"event": "END"}, sort_keys=True))
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
