 from __future__ import annotations
 
 import json
 
 from helpdesk_openenv.env import HelpdeskEnv
 from helpdesk_openenv.models import Action, Priority, Team
 
 
 def main() -> None:
     env = HelpdeskEnv()
     for task_id in ["triage_easy", "triage_medium", "triage_hard"]:
         obs = env.reset(task_id=task_id, max_steps=6)
         assert obs.task_id == task_id
         assert obs.step == 0
         s = env.state()
         assert s.task_id == task_id
 
         # A deterministic "reasonable" policy for validation.
         if task_id == "triage_easy":
             obs, rew = env.step(Action(route_to_team=Team.IT_SUPPORT, set_priority=Priority.P2, submit=True))
         elif task_id == "triage_medium":
             obs, rew = env.step(Action(ask_clarifying_question="What time did you see this and did you approve any MFA prompts?"))
             obs, rew = env.step(Action(route_to_team=Team.SECURITY, set_priority=Priority.P1, submit=True))
         else:
             obs, rew = env.step(
                 Action(
                     route_to_team=Team.SECURITY,
                     set_priority=Priority.P0,
                     draft_reply=(
                         "Thanks for reporting this. Please do not share passwords in tickets. "
                         "Reset your password via Okta, and ensure MFA is enabled (required for admin access). "
                         "We’re routing this to Security to review the account activity and the urgent admin request."
                     ),
                     submit=True,
                 )
             )
 
         assert rew.done is True
         assert "final_score" in rew.info
         score = float(rew.info["final_score"])
         assert 0.0 <= score <= 1.0
 
     print(json.dumps({"ok": True}, indent=2))
 
 
 if __name__ == "__main__":
     main()
 
