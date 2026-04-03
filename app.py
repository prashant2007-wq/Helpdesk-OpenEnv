from __future__ import annotations

import json
import sys
from pathlib import Path

import gradio as gr
from fastapi import FastAPI
from fastapi import Body
from fastapi.responses import JSONResponse

_SRC_DIR = Path(__file__).resolve().parent / "src"
if _SRC_DIR.exists():
    sys.path.insert(0, str(_SRC_DIR))

from helpdesk_openenv.env import HelpdeskEnv
from helpdesk_openenv.models import Action


def _render_obs(obs_dict: dict) -> str:
    kb = "\n".join([f"- {a['title']}" for a in obs_dict.get("kb_snippets", [])])
    convo = "\n\n".join([f"{m['role'].upper()}: {m['content']}" for m in obs_dict.get("conversation", [])])
    return (
        f"Task: {obs_dict['task_id']}  |  Step: {obs_dict['step']} / {obs_dict['max_steps']}\n\n"
        f"Ticket: {obs_dict['ticket']['subject']}\n\n"
        f"Policy: {json.dumps(obs_dict.get('policy', {}), indent=2, sort_keys=True)}\n\n"
        f"KB:\n{kb}\n\n"
        f"Conversation:\n{convo}"
    )


def build_demo() -> gr.Blocks:
    env = HelpdeskEnv()
    env.reset("triage_easy")

    with gr.Blocks(title="Helpdesk OpenEnv") as demo:
        gr.Markdown(
            "## Helpdesk OpenEnv\n"
            "A real-world environment for triage + routing + compliant response drafting.\n\n"
            "Use the JSON editor to send an Action. Click **Submit** in the action when ready to grade."
        )

        task = gr.Dropdown(
            choices=["triage_easy", "triage_medium", "triage_hard"],
            value="triage_easy",
            label="Task",
        )
        obs_box = gr.Textbox(label="Observation", value=_render_obs(env.state().model_dump()), lines=18)
        action_json = gr.Code(
            label="Action (JSON)",
            language="json",
            value=json.dumps(Action().model_dump(), indent=2, sort_keys=True),
        )
        reward_box = gr.Textbox(label="Reward / Info", value="", lines=4)

        def do_reset(task_id: str):
            obs = env.reset(task_id)
            return _render_obs(obs.model_dump()), json.dumps(Action().model_dump(), indent=2, sort_keys=True), ""

        def do_step(action_text: str):
            data = json.loads(action_text)
            obs, rew = env.step(data)
            info = {"reward": rew.reward, "done": rew.done, "info": rew.info}
            return _render_obs(obs.model_dump()), json.dumps(info, indent=2, sort_keys=True)

        with gr.Row():
            reset_btn = gr.Button("Reset")
            step_btn = gr.Button("Step")

        reset_btn.click(do_reset, inputs=[task], outputs=[obs_box, action_json, reward_box])
        step_btn.click(do_step, inputs=[action_json], outputs=[obs_box, reward_box])

    return demo


# Global environment instance for API endpoints
_env_instance = HelpdeskEnv()


def create_app() -> FastAPI:
    app = FastAPI(title="Helpdesk OpenEnv")

    @app.get("/health")
    def health():
        return JSONResponse({"status": "ok", "message": "Service is running"}, status_code=200)

    @app.post("/reset")
    def reset(task_id: str = "triage_easy", body: dict | None = Body(default=None)):
        global _env_instance
        try:
            # Accept task_id from either query param or JSON body.
            if body and isinstance(body, dict) and isinstance(body.get("task_id"), str) and body["task_id"].strip():
                task_id = body["task_id"].strip()
            obs = _env_instance.reset(task_id)
            return JSONResponse({"status": "ok", "observation": obs.model_dump()}, status_code=200)
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=400)

    @app.post("/step")
    def step(action: dict):
        global _env_instance
        try:
            obs, rew = _env_instance.step(action)
            return JSONResponse(
                {"status": "ok", "observation": obs.model_dump(), "reward": rew.model_dump()}, status_code=200
            )
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=400)

    @app.get("/state")
    def state():
        try:
            env_state = _env_instance.state()
            return JSONResponse({"status": "ok", "state": env_state.model_dump()}, status_code=200)
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=400)

    # Mount Gradio app
    demo = build_demo()
    app = gr.mount_gradio_app(app, demo, path="/")

    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(create_app(), host="0.0.0.0", port=7860)
