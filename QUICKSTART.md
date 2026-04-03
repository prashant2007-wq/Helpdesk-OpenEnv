# Quick Start Guide - OpenEnv Helpdesk

## Setup

### 1. Clone/Download the Repository
```bash
cd openenv-project
```

### 2. Create Python Environment (if not already done)
```bash
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -e .
```

Or using requirements.txt:
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
cp .env.example .env
# Edit .env with your API credentials
```

Example `.env`:
```env
OPENAI_API_KEY=your_openai_key_here
MODEL_NAME=gpt-4o-mini
API_BASE_URL=https://api.openai.com/v1
```

## Running the Project

### Option 1: Web Interface (Gradio + FastAPI)
```bash
python app.py
# Opens at http://localhost:7860
```

Features:
- Interactive UI for testing tasks
- Real-time step-by-step feedback
- HTTP endpoints for /health, /reset, /state

### Option 2: Run Full Baseline
Requires OPENAI_API_KEY:
```bash
export OPENAI_API_KEY="your-key"
python inference.py
```

Or using the CLI:
```bash
validate_openenv  # Validates all tasks
baseline          # Runs baseline scoring
```

## Project Structure

```
openenv-project/
├── app.py                    # Web interface (Gradio + FastAPI)
├── inference.py             # Baseline inference script
├── Dockerfile               # Docker configuration
├── openenv.yaml            # OpenEnv specification
├── pyproject.toml          # Python package config
├── requirements.txt        # Dependencies
├── .env.example            # Environment template
│
├── src/
│   └── helpdesk_openenv/
│       ├── __init__.py
│       ├── env.py          # Main HelpdeskEnv class
│       ├── models.py       # Pydantic models
│       ├── graders.py      # Scoring logic
│       ├── tasks.py        # Task definitions
│       └── cli/
│           ├── baseline.py # Baseline CLI
│           └── validate.py # Validation CLI
│
└── scripts/
    ├── baseline.py         # Baseline script
    └── validate_openenv.py # Validation script
```

## API Endpoints (when running app.py)

### Health Check
```bash
curl http://localhost:7860/health
# Response: {"status": "ok", "message": "Service is running"}
```

### Reset Environment
```bash
curl -X POST "http://localhost:7860/reset?task_id=triage_easy"
# Response includes new environment state
```

### Get Environment State
```bash
curl http://localhost:7860/state
# Response: {"status": "ok", "state": {...}}
```

## Available Tasks

### 1. triage_easy
- **Description**: Classify priority and route a straightforward ticket
- **Difficulty**: Easy
- **Target Team**: IT_SUPPORT
- **Target Priority**: P2

### 2. triage_medium
- **Description**: Handle missing details by asking 1-2 clarifying questions
- **Difficulty**: Medium
- **Target Team**: SECURITY
- **Target Priority**: P1
- **Min Questions**: 1

### 3. triage_hard
- **Description**: Draft a compliant response with conflicting constraints
- **Difficulty**: Hard
- **Target Team**: SECURITY
- **Target Priority**: P0
- **Requirements**: Policy-compliant response, no password sharing

## Example: Running a Single Task

```python
from helpdesk_openenv.env import HelpdeskEnv
from helpdesk_openenv.models import Action, Priority, Team

# Create environment
env = HelpdeskEnv()

# Reset to a specific task
obs = env.reset("triage_easy")
print(f"Task: {obs.task_id}")
print(f"Ticket: {obs.ticket.subject}")

# Take an action
action = Action(
    route_to_team=Team.IT_SUPPORT,
    set_priority=Priority.P2,
    submit=True
)
obs, reward = env.step(action)

print(f"Reward: {reward.reward}")
print(f"Done: {reward.done}")
print(f"Final Score: {reward.info.get('final_score')}")
```

## Troubleshooting

### Missing OPENAI_API_KEY
```
RuntimeError: Missing OPENAI_API_KEY in environment.
```
**Solution**: Set the environment variable before running:
```bash
export OPENAI_API_KEY="your-key"
```

### Module Import Errors
**Solution**: Ensure you've installed the package:
```bash
pip install -e .
```

### Port 7860 Already in Use
**Solution**: Run on a different port:
```bash
# Edit app.py and change port, or use environment variable
```

## Docker Deployment

### Build Docker Image
```bash
docker build -t helpdesk-openenv:latest .
```

### Run Docker Container
```bash
docker run -p 7860:7860 \
  -e OPENAI_API_KEY="your-key" \
  -e MODEL_NAME="gpt-4o-mini" \
  helpdesk-openenv:latest
```

## For Hugging Face Spaces Deployment

The project is ready for HF Spaces with:
- ✅ Health check endpoint at `/health`
- ✅ Reset endpoint at `/reset` accepting task_id
- ✅ Proper environment variable configuration
- ✅ Docker support with Dockerfile

Simply push to your HF Spaces repo and it will automatically deploy.

## Support

For issues or questions:
1. Check [SUBMISSION_CHECKLIST.md](SUBMISSION_CHECKLIST.md) for requirements
2. Review task definitions in `src/helpdesk_openenv/tasks.py`
3. Check grading logic in `src/helpdesk_openenv/graders.py`

---

**Last Updated**: April 1, 2026
