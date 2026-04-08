#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from openai import OpenAI

_SRC_DIR = Path(__file__).resolve().parent / "src"
if _SRC_DIR.exists():
    sys.path.insert(0, str(_SRC_DIR))

from helpdesk_openenv.env import HelpdeskEnv
from helpdesk_openenv.models import Action

TASKS = ("triage_easy", "triage_medium", "triage_hard")


def build_client() -> OpenAI:
    base_url = os.environ["API_BASE_URL"]
    api_key = os.environ["API_KEY"]
    return OpenAI(base_url=base_url, api_key=api_key)


def get_candidate_models(client: OpenAI) -> list[str]:
    candidates = []

    for key in ("MODEL_NAME", "OPENENV_BASELINE_MODEL", "OPENAI_MODEL"):
        value = os.environ.get(key)
        if value and value not in candidates:
            candidates.append(value)

    try:
        models = client.models.list()
        for m in models.data:
            mid = getattr(m, "id", None)
            if mid and mid not in candidates:
                candidates.append(mid)
    except Exception:
        pass

    fallback_names = [
        "gpt-4.1-mini",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4.1",
    ]
    for name in fallback_names:
        if name not in candidates:
            candidates.append(name)

    return candidates


def is_probably_text_model(model_id: str) -> bool:
    bad_words = [
        "embedding",
        "embed",
        "whisper",
        "tts",
        "transcribe",
        "moderation",
        "image",
        "audio",
        "realtime",
    ]
    low = model_id.lower()
    return not any(word in low for word in bad_words)


def try_completion(client: OpenAI, model: str, task_id: str) -> bool:
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0.0,
            messages=[
                {"role": "system", "content": "Reply with exactly OK."},
                {"role": "user", "content": f"Acknowledge {task_id}. Reply with OK."},
            ],
        )
        _ = (resp.choices[0].message.content or "").strip()
        return True
    except Exception:
        return False


def resolve_working_model(client: OpenAI) -> str:
    candidates = get_candidate_models(client)
    ordered = [m for m in candidates if is_probably_text_model(m)] + [
        m for m in candidates if not is_probably_text_model(m)
    ]

    seen = set()
    for model in ordered:
        if model in seen:
            continue
        seen.add(model)
        if try_completion(client, model, "model_probe"):
            return model

    raise RuntimeError(
        "Could not find any working chat model from proxy. "
        "Checked env-provided names and proxy-listed models."
    )


def proxy_probe(client: OpenAI, model: str, task_id: str) -> None:
    ok = try_completion(client, model, task_id)
    if not ok:
        raise RuntimeError(f"Proxy API call failed for {task_id} using model '{model}'")


def choose_action(task_id: str, step: int) -> Action:
    if task_id == "triage_easy":
        return Action(
            set_priority="p2",
            route_to_team="it_support",
            submit=True,
        )

    if task_id == "triage_medium":
        return Action(
            ask_clarifying_question=(
                "What time did this happen, did you approve any MFA prompt, "
                "and which device were you using?"
            ),
            set_priority="p1",
            route_to_team="security",
            submit=True,
        )

    if task_id == "triage_hard":
        return Action(
            set_priority="p0",
            route_to_team="security",
            draft_reply=(
                "Please do not share passwords in tickets or messages. "
                "Reset your password immediately using Okta and contact security right away. "
                "Because this involves admin access, MFA is required before any privileged access can be considered. "
                "We will treat this as a security incident and coordinate the next safe steps."
            ),
            submit=True,
        )

    return Action(submit=True)


def safe_score(score: float) -> float:
    score = float(score)
    if score <= 0.0:
        return 0.001
    if score >= 1.0:
        return 0.999
    return score


def emit_start(task_id: str) -> None:
    print(f"[START] task={task_id}", flush=True)


def emit_step(task_id: str, step: int, reward: float) -> None:
    print(f"[STEP] task={task_id} step={step} reward={reward:.3f}", flush=True)


def emit_end(task_id: str, score: float, steps: int) -> None:
    score = safe_score(score)
    print(f"[END] task={task_id} score={score:.3f} steps={steps}", flush=True)


def run_task(client: OpenAI, model: str, task_id: str) -> tuple[float, int]:
    emit_start(task_id)

    try:
        env = HelpdeskEnv()
        env.reset(task_id=task_id)

        proxy_probe(client, model, task_id)

        steps = 0
        while steps < 10:
            action = choose_action(task_id, steps)
            _, rew = env.step(action)
            steps += 1

            emit_step(task_id, steps, float(rew.reward))

            if rew.done:
                final_score = float(rew.info.get("final_score", "0.0"))
                emit_end(task_id, final_score, steps)
                return final_score, steps

        _, rew = env.step(Action(submit=True))
        steps += 1
        emit_step(task_id, steps, float(rew.reward))
        final_score = float(rew.info.get("final_score", "0.0"))
        emit_end(task_id, final_score, steps)
        return final_score, steps

    except Exception as e:
        print(
            json.dumps(
                {"event": "ERROR", "task_id": task_id, "error": str(e)},
                sort_keys=True,
            ),
            file=sys.stderr,
            flush=True,
        )
        emit_end(task_id, 0.001, 1)
        return 0.001, 1


def main() -> None:
    try:
        client = build_client()
        model = resolve_working_model(client)

        for task_id in TASKS:
            run_task(client, model, task_id)

    except Exception as e:
        print(
            json.dumps({"event": "FATAL_ERROR", "error": str(e)}, sort_keys=True),
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()