---
title: Helpdesk OpenEnv
emoji: "\U0001F4DE"
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: "4.44.0"
python_version: "3.11"
app_file: app.py
pinned: false
---
 
 ## Links (update these for your submission)

 Replace the placeholders with your real URLs once published:

 | | |
 | --- | --- |
 | **Source code (GitHub)** | `https://github.com/<YOUR_USERNAME>/<YOUR_REPO>` |
 | **Live demo (Hugging Face Space)** | `https://huggingface.co/spaces/<YOUR_USERNAME_OR_ORG>/<YOUR_SPACE_NAME>` |

 **How to get the GitHub URL**

 1. Create a new repository on [GitHub](https://github.com/new) (public, unless your course says otherwise).
 2. Push this project: `git remote add origin https://github.com/<USER>/<REPO>.git` then `git push -u origin main` (or your default branch).
 3. The repo link is the page URL in your browser, e.g. `https://github.com/username/helpdesk-openenv`.

 **How to get the Hugging Face Space URL**

 1. Sign in at [huggingface.co](https://huggingface.co) and accept the Spaces terms if prompted.
 2. Click **New Space** → choose **Gradio** (this repo’s `README.md` frontmatter already matches the Gradio SDK).
 3. Name the Space → **Create Space**.
 4. Upload or connect your code:
    - **GitHub sync:** in Space **Settings → Repository**, connect the same GitHub repo and branch so pushes redeploy the Space; or  
    - **Manual:** `git clone` the Space (HF gives you a git URL), copy `app.py`, `pyproject.toml`, `openenv.yaml`, `src/`, `requirements.txt`, and `README.md`, then commit and push.
 5. Wait for the build to finish. The **Space URL** is always:
    `https://huggingface.co/spaces/<your-username-or-org>/<space-name>`  
    You can copy it from the browser address bar on the Space page, or from **Settings → General → Space URL**.

 **Keep them up to date**

 - After each change: `git push` to GitHub; if the Space is linked to the repo, HF will rebuild automatically (or trigger a rebuild from the Space UI).
 - Confirm the Gradio app loads and **Reset** / **Step** work on the Space before sharing the link.

 ## What this is
 
 **Helpdesk OpenEnv** is a real-world environment that simulates an IT helpdesk workflow: interpreting a ticket, asking clarifying questions, selecting **priority**, routing to the correct **team**, and (for the hardest task) drafting a **policy-compliant reply**.
 
 It’s designed so an AI agent can learn via the standard `reset()` / `step()` / `state()` loop, with:
 
 - **3 tasks** (easy → medium → hard)
 - **Deterministic graders** producing **scores 0.0–1.0**
 - **Dense reward shaping** (partial progress, small loop penalty)
 - **Reproducible baseline** using the OpenAI API (temperature 0)
 - **Docker + Hugging Face Spaces** ready
 
 ## Environment API (OpenEnv-style)
 
 - **Entrypoint**: `helpdesk_openenv.env:HelpdeskEnv`
 - **Config**: `openenv.yaml`
 
 The environment implements:
 
 - `reset(task_id=..., max_steps=...) -> Observation`
 - `step(action: Action | dict) -> (Observation, Reward)`
 - `state() -> EnvState`
 
 Typed models live in `src/helpdesk_openenv/models.py`:
 
 - **Observation**: ticket + policy + KB snippets + conversation thread
 - **Action**: ask a question, set priority, route to team, draft reply, submit
 - **Reward**: `{reward: float, done: bool, info: dict}`
 - **EnvState**: internal state + agent decisions
 
 ## Tasks
 
 All tasks are deterministic (fixed tickets, KB snippets, and expected outcomes) to keep grading stable.
 
 - **Easy (`triage_easy`)**: Straightforward VPN ticket → route to IT Support, set standard priority.
 - **Medium (`triage_medium`)**: Suspicious login hint → ask at least 1 clarifying question, then route to Security and set higher priority.
 - **Hard (`triage_hard`)**: Urgent admin + data export request with a password disclosure → treat as an incident, route to Security, set highest priority, and draft a reply that is compliant and avoids leaking sensitive info.
 
 ## Action space
 
 `Action` fields:
 
 - `ask_clarifying_question: str | null` (one concise question per step)
 - `set_priority: "p0" | "p1" | "p2" | "p3" | null`
 - `route_to_team: "it_support" | "security" | "billing" | "hr" | "data" | null`
 - `draft_reply: str | null` (used in the hard task)
 - `submit: bool` (ends the episode and triggers final grading)
 
 ## Reward design
 
 Reward is **dense** and aligned with grading:
 
 - **Partial progress**: small positive signals for setting team/priority, asking the expected clarifying question, and drafting a reply (hard)
 - **Loop penalty**: small per-step negative penalty to discourage stalling
 - **Terminal bonus**: on submit (or max steps), adds the **final score** (0–1)
 
 ## Grading (0.0–1.0)
 
 Graders are deterministic and purely programmatic (`src/helpdesk_openenv/graders.py`):
 
 - **Routing**: exact match (0 or 1)
 - **Priority**: exact match (1) with partial credit for near misses
 - **Clarifying questions**: medium task expects at least 1 before submission
 - **Reply quality** (hard): must-include phrases and must-not-include phrases
 
## Run locally

**Requirements:** Python **3.11+** (see `pyproject.toml`).

1. **Go to the project directory**
   ```bash
   cd openenv-project
   ```
2. **Create and activate a virtual environment**
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```
3. **Install dependencies (editable install)**
   ```bash
   pip install -U pip
   pip install -e .
   ```
4. **(Optional) Validate the environment** — runs scripted actions on all three tasks and checks scores are in `[0, 1]`:
   ```bash
   validate_openenv
   ```
   Expect: `{"ok": true}`.
5. **Launch the Gradio UI**
   ```bash
   python app.py
   ```
6. **Open in a browser:** [http://127.0.0.1:7860](http://127.0.0.1:7860) (the app listens on `0.0.0.0:7860`).

**Using the UI:** choose a **Task** (`triage_easy`, `triage_medium`, or `triage_hard`), edit **Action (JSON)** as needed, then click **Step** to apply one action. Set `"submit": true` in the JSON when you want to end the episode and see the final reward; use **Reset** to start the selected task from the beginning.

## Baseline inference (reproducible)
 
 The baseline uses the OpenAI API with `temperature=0.0` and prints JSON with per-task scores and mean score.
 
 ```bash
 export OPENAI_API_KEY="..."
 export OPENENV_BASELINE_MODEL="gpt-4o-mini"
 baseline
 ```
 
 Output format:
 
 ```json
 {
   "mean_score": 0.83,
   "model": "gpt-4o-mini",
   "results": [
     {"final_score": 1.0, "steps": 1, "task_id": "triage_easy"},
     {"final_score": 0.95, "steps": 2, "task_id": "triage_medium"},
     {"final_score": 0.55, "steps": 1, "task_id": "triage_hard"}
   ]
 }
 ```
 
 ## Docker
 
 ```bash
 docker build -t helpdesk-openenv .
 docker run -p 7860:7860 helpdesk-openenv
 ```
 
 ## Files to know
 
 - `openenv.yaml`: environment metadata + entrypoint + model paths
 - `src/helpdesk_openenv/env.py`: `HelpdeskEnv` implementation
 - `src/helpdesk_openenv/tasks.py`: task definitions (easy/medium/hard)
 - `src/helpdesk_openenv/graders.py`: deterministic graders (0–1)
 - `scripts/baseline.py`: baseline inference runner
 - `scripts/validate_openenv.py`: local validation checks
 - `app.py`: Gradio UI for Hugging Face Spaces
 
